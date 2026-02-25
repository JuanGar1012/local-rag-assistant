from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.db.sqlite import init_db, log_query_run
from app.main import app


def test_query_runs_endpoint_smoke(tmp_path: Path) -> None:
    db = tmp_path / "app.db"
    init_db(db)
    log_query_run(
        db,
        request_id="run-1",
        question="What is this project?",
        answer="A local RAG assistant.",
        citations=[{"rank": 1, "source": "doc.md"}],
        retrieved_doc_ids=["doc.md"],
        latency_ms=123.4,
        top_k=6,
        correctness_probability=0.82,
        chat_model="llama3.2:3b",
    )

    def override_settings() -> Settings:
        return Settings(SQLITE_PATH=str(db))

    app.dependency_overrides[get_settings] = override_settings
    client = TestClient(app)
    response = client.get("/query/runs?limit=10")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert "items" in payload
    assert len(payload["items"]) == 1
    assert payload["items"][0]["question"] == "What is this project?"
    assert payload["items"][0]["answer"] == "A local RAG assistant."
    assert payload["items"][0]["top_k"] == 6
    assert payload["items"][0]["correctness_probability"] == 0.82
    assert payload["items"][0]["chat_model"] == "llama3.2:3b"
