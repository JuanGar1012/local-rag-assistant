import json

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.sqlite import init_db
from app.eval.harness import run_eval
from app.rag.ollama_client import OllamaClient
from app.rag.pipeline import RAGPipeline
from app.rag.vector_store import ChromaVectorStore


def main() -> None:
    configure_logging()
    settings = get_settings()
    init_db(settings.sqlite_path)

    store = ChromaVectorStore(settings)
    ollama = OllamaClient(settings)
    pipeline = RAGPipeline(settings, store, ollama)
    metrics = run_eval(settings, pipeline)

    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = settings.reports_dir / "eval_latest.json"
    report_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
