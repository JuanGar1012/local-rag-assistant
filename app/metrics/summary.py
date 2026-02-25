from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.db.sqlite import latest_eval_metrics, query_run_confidence_24h, query_run_feedback_24h, request_metrics_24h


def build_metrics_summary(db_path: Path) -> dict[str, Any]:
    req = request_metrics_24h(db_path, path_filter="/query")
    eval_metrics = latest_eval_metrics(db_path)
    confidence = query_run_confidence_24h(db_path)
    feedback = query_run_feedback_24h(db_path)
    feedback_weight = min(feedback["feedback_samples_24h"], 20) / 20 if feedback["feedback_samples_24h"] > 0 else 0.0
    calibrated = (1 - feedback_weight) * confidence["correctness_confidence_avg_24h"] + (feedback_weight * feedback["feedback_accuracy_rate_24h"])
    return {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "latency_p95_ms": req["latency_p95_ms"],
        "success_rate": req["success_rate"],
        "error_rate": req["error_rate"],
        "requests_24h": req["requests_24h"],
        "recall_at_5": eval_metrics.get("recall_at_5", 0.0),
        "eval_pass_rate": eval_metrics.get("eval_pass_rate", 0.0),
        "eval_coverage": eval_metrics.get("eval_coverage", 0.0),
        "correctness_confidence_avg_24h": confidence["correctness_confidence_avg_24h"],
        "confidence_samples_24h": confidence["confidence_samples_24h"],
        "feedback_accuracy_rate_24h": feedback["feedback_accuracy_rate_24h"],
        "feedback_samples_24h": feedback["feedback_samples_24h"],
        "calibrated_quality_24h": calibrated,
    }
