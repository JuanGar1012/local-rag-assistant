from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Iterable

from pypdf import PdfReader

from app.core.config import Settings
from app.rag.models import Chunk
from app.rag.ollama_client import OllamaClient
from app.rag.vector_store import ChromaVectorStore

SUPPORTED_EXTENSIONS = {".pdf", ".md", ".txt"}


def _read_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(str(path))
        pages = [(page.extract_text() or "") for page in reader.pages]
        return "\n".join(pages).strip()
    return path.read_text(encoding="utf-8", errors="ignore").strip()


def text_from_bytes(filename: str, raw: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file extension: {ext}")
    if ext == ".pdf":
        reader = PdfReader(io.BytesIO(raw))
        pages = [(page.extract_text() or "") for page in reader.pages]
        return "\n".join(pages).strip()
    return raw.decode("utf-8", errors="ignore").strip()


def source_to_doc_id(source: str) -> str:
    normalized = source.replace("\\", "/")
    base = re.sub(r"[^a-zA-Z0-9._/-]+", "_", normalized)
    return base.replace("/", "__")


def iter_documents(root: Path) -> Iterable[tuple[str, str, str]]:
    if not root.exists():
        return
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        text = _read_text(path)
        if not text:
            continue
        rel = path.relative_to(root).as_posix()
        doc_id = rel.replace("/", "__")
        yield doc_id, rel, text


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    cleaned = " ".join(text.split())
    if not cleaned:
        return []
    if overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")
    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(len(cleaned), start + chunk_size)
        chunks.append(cleaned[start:end])
        if end == len(cleaned):
            break
        start = end - overlap
    return chunks


def build_chunks(settings: Settings) -> list[Chunk]:
    chunks: list[Chunk] = []
    for doc_id, source, text in iter_documents(settings.docs_dir):
        chunks.extend(document_to_chunks(settings, doc_id=doc_id, source=source, text=text))
    return chunks


def document_to_chunks(settings: Settings, *, doc_id: str, source: str, text: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    parts = chunk_text(text, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)
    for idx, part in enumerate(parts):
        chunk_id = f"{doc_id}::chunk::{idx}"
        chunks.append(
            Chunk(
                chunk_id=chunk_id,
                text=part,
                metadata={
                    "doc_id": doc_id,
                    "source": source,
                    "chunk_index": idx,
                },
            )
        )
    return chunks


def ingest_document_texts(
    settings: Settings,
    store: ChromaVectorStore,
    ollama: OllamaClient,
    docs: list[tuple[str, str, str]],
    batch_size: int = 32,
) -> dict[str, int]:
    chunks: list[Chunk] = []
    for doc_id, source, text in docs:
        chunks.extend(document_to_chunks(settings, doc_id=doc_id, source=source, text=text))
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        vectors = ollama.embed([chunk.text for chunk in batch])
        store.upsert_chunks(batch, vectors)
    unique_docs = len({chunk.metadata["doc_id"] for chunk in chunks}) if chunks else 0
    return {"docs": unique_docs, "chunks": len(chunks), "vector_count": store.count()}


def run_ingestion(settings: Settings, store: ChromaVectorStore, ollama: OllamaClient, batch_size: int = 32) -> dict[str, int]:
    docs = list(iter_documents(settings.docs_dir))
    return ingest_document_texts(settings, store, ollama, docs=docs, batch_size=batch_size)
