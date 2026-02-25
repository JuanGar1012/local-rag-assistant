from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.db.sqlite import init_db, log_eval_run, log_query_run, log_request
from app.main import app


def test_metrics_summary_endpoint_smoke(tmp_path: Path) -> None:
    db = tmp_path / "app.db"
    init_db(db)
    log_request(db, request_id="x1", method="POST", path="/query", status_code=200, latency_ms=111, success=True, error=None)
    log_eval_run(
        db,
        total_cases=2,
        retrieval_hit_rate=1.0,
        recall_at_k=1.0,
        recall_at_5=1.0,
        groundedness_proxy=1.0,
        eval_pass_rate=1.0,
        eval_coverage=1.0,
        latency_p50_ms=100.0,
        latency_p95_ms=150.0,
        metrics={"recall_at_5": 1.0, "eval_pass_rate": 1.0, "eval_coverage": 1.0},
    )
    log_query_run(
        db,
        request_id="r1",
        question="q",
        answer="a",
        citations=[{"rank": 1, "source": "doc.md"}],
        retrieved_doc_ids=["doc.md"],
        latency_ms=111.0,
        top_k=3,
        correctness_probability=0.75,
        chat_model="llama3.2:3b",
    )

    def override_settings() -> Settings:
        return Settings(SQLITE_PATH=str(db))

    app.dependency_overrides[get_settings] = override_settings
    client = TestClient(app)
    response = client.get("/metrics/summary")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert "updated_at" in payload
    assert payload["requests_24h"] == 1
    assert payload["recall_at_5"] == 1.0
    assert "correctness_confidence_avg_24h" in payload
    assert payload["correctness_confidence_avg_24h"] == 0.75
    assert payload["confidence_samples_24h"] == 1
    assert "feedback_accuracy_rate_24h" in payload
    assert "feedback_samples_24h" in payload
    assert "calibrated_quality_24h" in payload
