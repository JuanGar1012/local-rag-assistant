from pathlib import Path

from app.db.sqlite import create_ingestion_job, get_ingestion_job, ingestion_metrics, init_db, update_ingestion_job


def test_ingestion_metrics_summary(tmp_path: Path) -> None:
    db = tmp_path / "app.db"
    init_db(db)

    j1 = create_ingestion_job(db, source_type="link", source="https://a.com", max_attempts=3)
    update_ingestion_job(db, job_id=j1, status="success", attempt_count=2, latency_ms=1200.0, summary={"docs": 1, "chunks": 2, "vector_count": 2})
    j2 = create_ingestion_job(db, source_type="upload", source="doc.md", max_attempts=1)
    update_ingestion_job(db, job_id=j2, status="error", attempt_count=1, latency_ms=500.0, error="boom")

    summary = ingestion_metrics(db)
    assert summary["total_jobs"] == 2
    assert summary["success_rate"] == 0.5
    assert summary["error_rate"] == 0.5
    assert summary["retried_jobs"] == 1
    assert summary["avg_attempts"] == 1.5
    assert summary["latency_p50_ms"] > 0


def test_ingestion_job_status_includes_attempts(tmp_path: Path) -> None:
    db = tmp_path / "app.db"
    init_db(db)
    job_id = create_ingestion_job(db, source_type="link", source="https://example.com", max_attempts=4)
    update_ingestion_job(db, job_id=job_id, status="running", attempt_count=3, latency_ms=123.4)
    job = get_ingestion_job(db, job_id=job_id)
    assert job is not None
    assert job["attempt_count"] == 3
    assert job["max_attempts"] == 4
    assert float(job["latency_ms"]) == 123.4
