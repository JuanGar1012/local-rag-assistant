from functools import lru_cache

from app.core.config import Settings, get_settings
from app.rag.ollama_client import OllamaClient
from app.rag.pipeline import RAGPipeline
from app.rag.vector_store import ChromaVectorStore
from app.services.query_service import QueryService


@lru_cache
def get_store() -> ChromaVectorStore:
    settings = get_settings()
    return ChromaVectorStore(settings)


@lru_cache
def get_ollama() -> OllamaClient:
    settings = get_settings()
    return OllamaClient(settings)


@lru_cache
def get_pipeline() -> RAGPipeline:
    settings: Settings = get_settings()
    return RAGPipeline(settings=settings, store=get_store(), ollama=get_ollama())


@lru_cache
def get_query_service() -> QueryService:
    settings: Settings = get_settings()
    return QueryService(settings=settings, pipeline=get_pipeline())
