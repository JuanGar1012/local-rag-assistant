from pathlib import Path

from app.db.sqlite import init_db, log_eval_run, log_request
from app.metrics.summary import build_metrics_summary


def test_required_tables_exist(tmp_path: Path) -> None:
    db = tmp_path / "app.db"
    init_db(db)
    import sqlite3

    conn = sqlite3.connect(db)
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    names = {row[0] for row in rows}
    assert "request_logs" in names
    assert "retrieval_events" in names
    assert "eval_runs" in names


def test_metrics_summary_aggregation(tmp_path: Path) -> None:
    db = tmp_path / "app.db"
    init_db(db)
    log_request(db, request_id="r1", method="POST", path="/query", status_code=200, latency_ms=100, success=True, error=None)
    log_request(db, request_id="r2", method="POST", path="/query", status_code=500, latency_ms=300, success=False, error="boom")
    log_eval_run(
        db,
        total_cases=10,
        retrieval_hit_rate=0.8,
        recall_at_k=0.75,
        recall_at_5=0.7,
        groundedness_proxy=0.6,
        eval_pass_rate=0.65,
        eval_coverage=1.0,
        latency_p50_ms=120.0,
        latency_p95_ms=240.0,
        metrics={"recall_at_5": 0.7, "eval_pass_rate": 0.65, "eval_coverage": 1.0},
    )
    summary = build_metrics_summary(db)
    assert summary["requests_24h"] == 2
    assert summary["success_rate"] == 0.5
    assert summary["error_rate"] == 0.5
    assert summary["recall_at_5"] == 0.7
    assert summary["eval_pass_rate"] == 0.65
    assert summary["eval_coverage"] == 1.0
