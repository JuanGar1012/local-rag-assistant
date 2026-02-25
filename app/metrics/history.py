from __future__ import annotations

from pathlib import Path
from typing import Any

from app.db.sqlite import eval_metrics_history, request_metrics_history


def build_metrics_history(
    db_path: Path,
    *,
    hours: int = 24,
    bucket_minutes: int = 15,
) -> dict[str, Any]:
    return {
        "window_hours": max(1, min(hours, 168)),
        "bucket_minutes": max(1, min(bucket_minutes, 60)),
        "request_trend": request_metrics_history(
            db_path,
            hours=hours,
            bucket_minutes=bucket_minutes,
            path_filter="/query",
        ),
        "eval_trend": eval_metrics_history(db_path, limit=30),
    }
