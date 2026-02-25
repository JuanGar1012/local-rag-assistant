from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.db.sqlite import init_db, log_query_run
from app.main import app


def test_query_run_feedback_endpoint_smoke(tmp_path: Path) -> None:
    db = tmp_path / "app.db"
    init_db(db)
    log_query_run(
        db,
        request_id="run-fb-1",
        question="What is this project?",
        answer="A local RAG assistant.",
        citations=[{"rank": 1, "source": "doc.md"}],
        retrieved_doc_ids=["doc.md"],
        latency_ms=111.0,
        top_k=3,
        correctness_probability=0.8,
        chat_model="llama3.2:3b",
    )

    def override_settings() -> Settings:
        return Settings(SQLITE_PATH=str(db))

    app.dependency_overrides[get_settings] = override_settings
    client = TestClient(app)
    response = client.post("/query/runs/1/feedback", json={"is_correct": False, "note": "Hallucinated details"})
    runs = client.get("/query/runs?limit=10")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["query_run_id"] == 1
    assert payload["is_correct"] is False
    assert payload["note"] == "Hallucinated details"

    assert runs.status_code == 200
    run = runs.json()["items"][0]
    assert run["feedback_is_correct"] is False
    assert run["feedback_note"] == "Hallucinated details"
