from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.db.sqlite import init_db, log_eval_run, log_request
from app.main import app


def test_metrics_history_endpoint_smoke(tmp_path: Path) -> None:
    db = tmp_path / "app.db"
    init_db(db)
    log_request(db, request_id="h1", method="POST", path="/query", status_code=200, latency_ms=120, success=True, error=None)
    log_request(db, request_id="h2", method="POST", path="/query", status_code=500, latency_ms=900, success=False, error="boom")
    log_eval_run(
        db,
        total_cases=2,
        retrieval_hit_rate=1.0,
        recall_at_k=1.0,
        recall_at_5=1.0,
        groundedness_proxy=1.0,
        eval_pass_rate=0.5,
        eval_coverage=1.0,
        latency_p50_ms=100.0,
        latency_p95_ms=150.0,
        metrics={"recall_at_5": 1.0, "eval_pass_rate": 0.5, "eval_coverage": 1.0},
    )

    def override_settings() -> Settings:
        return Settings(SQLITE_PATH=str(db))

    app.dependency_overrides[get_settings] = override_settings
    client = TestClient(app)
    response = client.get("/metrics/history?hours=24&bucket_minutes=15")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert "request_trend" in payload
    assert "eval_trend" in payload
    assert isinstance(payload["request_trend"], list)
    assert isinstance(payload["eval_trend"], list)
