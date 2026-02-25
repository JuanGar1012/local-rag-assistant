from __future__ import annotations

from typing import Any

from app.core.config import Settings
from app.db.sqlite import log_retrieval_event
from app.rag.pipeline import RAGPipeline


class QueryService:
    def __init__(self, settings: Settings, pipeline: RAGPipeline) -> None:
        self.settings = settings
        self.pipeline = pipeline

    def run_query(self, *, question: str, top_k: int | None, request_id: str | None, chat_model: str | None = None) -> dict[str, Any]:
        k = top_k or self.settings.TOP_K
        result = self.pipeline.answer(question, top_k=k, chat_model=chat_model)
        hit = len(result.get("citations", [])) > 0
        log_retrieval_event(
            self.settings.sqlite_path,
            request_id=request_id,
            source="live_query",
            query_text=question,
            top_k=k,
            hit=hit,
            recall_at_k=1.0 if hit else 0.0,
            recall_at_5=1.0 if hit else 0.0,
            citations=result.get("citations", []),
            retrieved_doc_ids=result.get("retrieved_doc_ids", []),
        )
        return result
