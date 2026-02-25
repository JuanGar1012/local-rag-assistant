from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.db.sqlite import init_db, log_retrieval_event
from app.main import app


def test_query_history_endpoint_smoke(tmp_path: Path) -> None:
    db = tmp_path / "app.db"
    init_db(db)
    log_retrieval_event(
        db,
        request_id="q1",
        source="live_query",
        query_text="What stack does this project use?",
        top_k=5,
        hit=True,
        recall_at_k=1.0,
        recall_at_5=1.0,
        citations=[],
        retrieved_doc_ids=[],
    )
    log_retrieval_event(
        db,
        request_id="q2",
        source="live_query",
        query_text="This one failed",
        top_k=5,
        hit=False,
        recall_at_k=0.0,
        recall_at_5=0.0,
        citations=[],
        retrieved_doc_ids=[],
        error="Simulated generation failure",
    )

    def override_settings() -> Settings:
        return Settings(SQLITE_PATH=str(db))

    app.dependency_overrides[get_settings] = override_settings
    client = TestClient(app)
    response = client.get("/query/history?limit=10")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert "items" in payload
    assert len(payload["items"]) == 2
    assert payload["items"][0]["question"] == "This one failed"
    assert payload["items"][0]["error"] == "Simulated generation failure"
    assert payload["items"][1]["question"] == "What stack does this project use?"
    assert payload["items"][1]["top_k"] == 5
