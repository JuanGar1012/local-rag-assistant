from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone

from app.core.config import Settings
from app.db.sqlite import log_eval_run, log_retrieval_event
from app.rag.pipeline import RAGPipeline


@dataclass
class EvalCase:
    case_id: str
    question: str
    expected_doc_ids: list[str]
    expected_substrings: list[str]


def load_cases(path) -> list[EvalCase]:  # type: ignore[no-untyped-def]
    cases: list[EvalCase] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        cases.append(
            EvalCase(
                case_id=row["id"],
                question=row["question"],
                expected_doc_ids=row.get("expected_doc_ids", []),
                expected_substrings=row.get("expected_substrings", []),
            )
        )
    return cases


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = (len(ordered) - 1) * p
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    if lower == upper:
        return ordered[lower]
    weight = index - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def run_eval(settings: Settings, pipeline: RAGPipeline) -> dict[str, object]:
    cases = load_cases(settings.benchmark_path)

    retrieval_hits = 0
    recall_scores: list[float] = []
    recall_at_5_scores: list[float] = []
    pass_count = 0
    grounded_scores: list[float] = []
    latencies: list[float] = []
    processed = 0
    detailed: list[dict[str, object]] = []

    for case in cases:
        result = pipeline.answer(case.question, top_k=settings.TOP_K)
        processed += 1
        retrieved_ids = set(result["retrieved_doc_ids"])
        expected_ids = set(case.expected_doc_ids)
        if expected_ids:
            matched = retrieved_ids.intersection(expected_ids)
            recall = len(matched) / len(expected_ids)
            hit = 1 if matched else 0
        else:
            recall = 0.0
            hit = 0
        recall_at_5 = recall if settings.TOP_K >= 5 else min(1.0, recall)
        retrieval_hits += hit
        recall_scores.append(recall)
        recall_at_5_scores.append(recall_at_5)

        answer_l = str(result["answer"]).lower()
        expected_terms = [term.lower() for term in case.expected_substrings]
        passed = all(term in answer_l for term in expected_terms) if expected_terms else True
        pass_count += int(passed)

        context_l = str(result.get("retrieved_context", "")).lower()
        if expected_terms:
            supported = sum(1 for term in expected_terms if term in context_l)
            groundedness_case = supported / len(expected_terms)
        else:
            groundedness_case = 1.0
        grounded_scores.append(groundedness_case)

        latencies.append(float(result["latency_ms"]))
        detailed.append(
            {
                "id": case.case_id,
                "hit": bool(hit),
                "recall_at_k": recall,
                "recall_at_5": recall_at_5,
                "groundedness_proxy": groundedness_case,
                "passed": passed,
                "retrieved_doc_ids": result["retrieved_doc_ids"],
                "latency_ms": round(float(result["latency_ms"]), 2),
            }
        )
        log_retrieval_event(
            settings.sqlite_path,
            request_id=f"eval::{case.case_id}",
            source="eval",
            query_text=case.question,
            top_k=settings.TOP_K,
            hit=bool(hit),
            recall_at_k=recall,
            recall_at_5=recall_at_5,
            citations=result.get("citations", []),
            retrieved_doc_ids=result.get("retrieved_doc_ids", []),
        )

    total = len(cases)
    coverage = (processed / total) if total else 0.0
    metrics: dict[str, object] = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "total_cases": total,
        "processed_cases": processed,
        "retrieval_hit_rate": (retrieval_hits / total) if total else 0.0,
        "recall_at_k": (sum(recall_scores) / total) if total else 0.0,
        "recall_at_5": (sum(recall_at_5_scores) / total) if total else 0.0,
        "groundedness_proxy": (sum(grounded_scores) / total) if total else 0.0,
        "eval_pass_rate": (pass_count / total) if total else 0.0,
        "eval_coverage": coverage,
        "latency_p50_ms": percentile(latencies, 0.5),
        "latency_p95_ms": percentile(latencies, 0.95),
        "details": detailed,
    }

    log_eval_run(
        settings.sqlite_path,
        total_cases=int(metrics["total_cases"]),
        retrieval_hit_rate=float(metrics["retrieval_hit_rate"]),
        recall_at_k=float(metrics["recall_at_k"]),
        recall_at_5=float(metrics["recall_at_5"]),
        groundedness_proxy=float(metrics["groundedness_proxy"]),
        eval_pass_rate=float(metrics["eval_pass_rate"]),
        eval_coverage=float(metrics["eval_coverage"]),
        latency_p50_ms=float(metrics["latency_p50_ms"]),
        latency_p95_ms=float(metrics["latency_p95_ms"]),
        metrics=metrics,
    )
    return metrics
