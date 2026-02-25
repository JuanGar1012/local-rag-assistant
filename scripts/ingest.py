from app.core.config import get_settings
from app.core.logging import configure_logging
from app.rag.ingestion import run_ingestion
from app.rag.ollama_client import OllamaClient
from app.rag.vector_store import ChromaVectorStore


def main() -> None:
    configure_logging()
    settings = get_settings()
    store = ChromaVectorStore(settings)
    ollama = OllamaClient(settings)
    summary = run_ingestion(settings, store, ollama)
    print(summary)


if __name__ == "__main__":
    main()
