from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.metrics.history import build_metrics_history
from app.metrics.summary import build_metrics_summary

router = APIRouter(prefix="/metrics", tags=["metrics"])


class MetricsSummaryResponse(BaseModel):
    updated_at: str
    latency_p95_ms: float
    success_rate: float
    error_rate: float
    requests_24h: int
    recall_at_5: float
    eval_pass_rate: float
    eval_coverage: float
    correctness_confidence_avg_24h: float
    confidence_samples_24h: int
    feedback_accuracy_rate_24h: float
    feedback_samples_24h: int
    calibrated_quality_24h: float


class RequestTrendPoint(BaseModel):
    bucket_utc: str
    requests: int
    success_rate: float
    error_rate: float
    latency_p95_ms: float


class EvalTrendPoint(BaseModel):
    ts_utc: str
    recall_at_5: float
    eval_pass_rate: float
    eval_coverage: float
    latency_p95_ms: float


class MetricsHistoryResponse(BaseModel):
    window_hours: int
    bucket_minutes: int
    request_trend: list[RequestTrendPoint]
    eval_trend: list[EvalTrendPoint]


@router.get("/summary", response_model=MetricsSummaryResponse)
def metrics_summary(settings: Settings = Depends(get_settings)) -> MetricsSummaryResponse:
    summary = build_metrics_summary(settings.sqlite_path)
    return MetricsSummaryResponse(**summary)


@router.get("/history", response_model=MetricsHistoryResponse)
def metrics_history(
    hours: int = 24,
    bucket_minutes: int = 15,
    settings: Settings = Depends(get_settings),
) -> MetricsHistoryResponse:
    history = build_metrics_history(settings.sqlite_path, hours=hours, bucket_minutes=bucket_minutes)
    return MetricsHistoryResponse(**history)
