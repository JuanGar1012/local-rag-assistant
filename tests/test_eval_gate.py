from scripts.eval_gate import evaluate_metrics


def test_eval_gate_passes_good_metrics() -> None:
    failures = evaluate_metrics(
        {
            "eval_coverage": 1.0,
            "recall_at_5": 0.8,
            "eval_pass_rate": 0.75,
            "latency_p95_ms": 1200.0,
        },
        min_eval_coverage=1.0,
        min_recall_at_5=0.45,
        min_eval_pass_rate=0.5,
        max_latency_p95_ms=20000.0,
    )
    assert failures == []


def test_eval_gate_fails_bad_metrics() -> None:
    failures = evaluate_metrics(
        {
            "eval_coverage": 0.8,
            "recall_at_5": 0.2,
            "eval_pass_rate": 0.3,
            "latency_p95_ms": 50000.0,
        },
        min_eval_coverage=1.0,
        min_recall_at_5=0.45,
        min_eval_pass_rate=0.5,
        max_latency_p95_ms=20000.0,
    )
    assert len(failures) == 4
