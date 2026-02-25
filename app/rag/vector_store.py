from __future__ import annotations

from typing import Sequence

import chromadb
from chromadb.api.models.Collection import Collection

from app.core.config import Settings
from app.rag.models import Chunk, RetrievedChunk


class ChromaVectorStore:
    def __init__(self, settings: Settings) -> None:
        settings.chroma_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(settings.chroma_dir))
        self._collection: Collection = self._client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert_chunks(self, chunks: Sequence[Chunk], embeddings: Sequence[Sequence[float]]) -> None:
        if not chunks:
            return
        self._collection.upsert(
            ids=[chunk.chunk_id for chunk in chunks],
            documents=[chunk.text for chunk in chunks],
            metadatas=[chunk.metadata for chunk in chunks],
            embeddings=[list(embed) for embed in embeddings],
        )

    def query(self, query_embedding: Sequence[float], top_k: int) -> list[RetrievedChunk]:
        result = self._collection.query(
            query_embeddings=[list(query_embedding)],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        ids = result.get("ids", [[]])[0]
        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        retrieved: list[RetrievedChunk] = []
        for chunk_id, text, metadata, distance in zip(ids, docs, metas, distances):
            retrieved.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    text=text,
                    metadata=dict(metadata) if metadata else {},
                    distance=float(distance),
                )
            )
        return retrieved

    def count(self) -> int:
        return self._collection.count()

    def reset_collection(self) -> int:
        name = self._collection.name
        self._client.delete_collection(name=name)
        self._collection = self._client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )
        return self._collection.count()
