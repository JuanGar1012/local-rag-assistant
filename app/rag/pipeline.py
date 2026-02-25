from __future__ import annotations

import re
import time
from typing import Any

from app.core.config import Settings
from app.rag.ollama_client import OllamaClient
from app.rag.vector_store import ChromaVectorStore


class RAGPipeline:
    def __init__(self, settings: Settings, store: ChromaVectorStore, ollama: OllamaClient) -> None:
        self.settings = settings
        self.store = store
        self.ollama = ollama

    def retrieve(self, question: str, top_k: int | None = None) -> tuple[list[dict[str, Any]], list[str]]:
        k = top_k or self.settings.TOP_K
        query_vector = self.ollama.embed([question])[0]
        chunks = self.store.query(query_vector, top_k=k)
        citations: list[dict[str, Any]] = []
        retrieved_doc_ids: list[str] = []
        seen: set[str] = set()
        for idx, chunk in enumerate(chunks, start=1):
            doc_id = str(chunk.metadata.get("doc_id", "unknown"))
            if doc_id not in seen:
                seen.add(doc_id)
                retrieved_doc_ids.append(doc_id)
            citations.append(
                {
                    "rank": idx,
                    "doc_id": doc_id,
                    "source": str(chunk.metadata.get("source", "unknown")),
                    "chunk_index": int(chunk.metadata.get("chunk_index", -1)),
                    "distance": round(chunk.distance, 5),
                    "text_preview": chunk.text[:180],
                    "chunk_text": chunk.text,
                }
            )
        return citations, retrieved_doc_ids

    def estimate_correctness_probability(self, *, answer: str, citations: list[dict[str, Any]]) -> float:
        if not citations:
            return 0.1

        count_score = min(len(citations), 6) / 6.0
        distances = [float(c.get("distance", 1.0)) for c in citations if isinstance(c.get("distance"), (int, float))]
        avg_distance = (sum(distances) / len(distances)) if distances else 1.0
        if avg_distance <= 0.25:
            distance_score = 1.0
        elif avg_distance <= 0.5:
            distance_score = 0.8
        elif avg_distance <= 0.8:
            distance_score = 0.6
        elif avg_distance <= 1.2:
            distance_score = 0.4
        else:
            distance_score = 0.2

        cited_refs = {int(m.group(1)) for m in re.finditer(r"\[(\d+)\]", answer)}
        citation_ref_score = min(len(cited_refs), len(citations)) / max(1, min(len(citations), 5))

        raw = 0.1 + (0.35 * count_score) + (0.4 * distance_score) + (0.15 * citation_ref_score)
        if "insufficient" in answer.lower() or "not enough context" in answer.lower():
            raw = min(raw, 0.6)
        return max(0.05, min(0.95, raw))

    def answer(self, question: str, top_k: int | None = None, chat_model: str | None = None) -> dict[str, Any]:
        start = time.perf_counter()
        citations, retrieved_doc_ids = self.retrieve(question, top_k=top_k)
        if not citations:
            return {
                "answer": "No indexed context was found. Ingest documents first.",
                "citations": [],
                "retrieved_doc_ids": [],
                "retrieved_context": "",
                "correctness_probability": 0.1,
                "chat_model": chat_model or self.settings.OLLAMA_CHAT_MODEL,
                "embed_model": self.settings.OLLAMA_EMBED_MODEL,
                "token_usage": {"prompt_tokens": None, "completion_tokens": None, "total_tokens": None},
                "latency_ms": (time.perf_counter() - start) * 1000,
            }
        context_blocks = []
        for citation in citations:
            context_blocks.append(
                f"[{citation['rank']}] source={citation['source']} doc_id={citation['doc_id']} chunk={citation['chunk_index']}\n{citation['chunk_text']}"
            )
        prompt = (
            "You are a portfolio RAG assistant. Answer with concise factual statements grounded in the context.\n"
            "If context is insufficient, explicitly say so.\n"
            "Cite claims using [n] references matching context blocks.\n\n"
            f"Question: {question}\n\n"
            "Context:\n"
            f"{chr(10).join(context_blocks)}\n\n"
            "Answer:"
        )
        if hasattr(self.ollama, "generate_with_meta"):
            try:
                generation = self.ollama.generate_with_meta(prompt, model=chat_model)  # type: ignore[attr-defined]
            except TypeError:
                generation = self.ollama.generate_with_meta(prompt)  # type: ignore[attr-defined]
            answer = str(generation["text"])
            token_usage = {
                "prompt_tokens": generation.get("prompt_tokens"),
                "completion_tokens": generation.get("completion_tokens"),
                "total_tokens": generation.get("total_tokens"),
            }
        else:
            try:
                answer = self.ollama.generate(prompt, model=chat_model)
            except TypeError:
                answer = self.ollama.generate(prompt)
            token_usage = {"prompt_tokens": None, "completion_tokens": None, "total_tokens": None}
        latency_ms = (time.perf_counter() - start) * 1000
        retrieved_context = "\n".join(citation["chunk_text"] for citation in citations)
        correctness_probability = self.estimate_correctness_probability(answer=answer, citations=citations)
        for citation in citations:
            citation.pop("chunk_text", None)
        return {
            "answer": answer,
            "citations": citations,
            "retrieved_doc_ids": retrieved_doc_ids,
            "retrieved_context": retrieved_context,
            "correctness_probability": correctness_probability,
            "chat_model": chat_model or self.settings.OLLAMA_CHAT_MODEL,
            "embed_model": self.settings.OLLAMA_EMBED_MODEL,
            "token_usage": token_usage,
            "latency_ms": latency_ms,
        }
