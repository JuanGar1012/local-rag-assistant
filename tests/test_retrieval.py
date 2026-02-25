from app.core.config import Settings
from app.rag.pipeline import RAGPipeline


class FakeOllama:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _ in texts]

    def generate(self, prompt: str) -> str:
        assert "Question:" in prompt
        return "The backend uses FastAPI, Chroma, and SQLite. [1]"


class FakeStore:
    def query(self, query_embedding, top_k: int):  # type: ignore[no-untyped-def]
        return [
            type(
                "Chunk",
                (),
                {
                    "chunk_id": "portfolio_overview.md::chunk::0",
                    "text": "The backend stack uses FastAPI, Chroma, and SQLite.",
                    "metadata": {
                        "doc_id": "portfolio_overview.md",
                        "source": "portfolio_overview.md",
                        "chunk_index": 0,
                    },
                    "distance": 0.02,
                },
            )()
        ][:top_k]


def test_pipeline_answer_with_citations() -> None:
    settings = Settings()
    pipeline = RAGPipeline(settings=settings, store=FakeStore(), ollama=FakeOllama())  # type: ignore[arg-type]
    result = pipeline.answer("What backend stack is used?", top_k=2)
    assert "FastAPI" in result["answer"]
    assert result["citations"]
    assert result["retrieved_doc_ids"] == ["portfolio_overview.md"]
    assert result["latency_ms"] >= 0
