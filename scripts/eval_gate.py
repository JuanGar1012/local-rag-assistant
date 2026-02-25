from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def evaluate_metrics(
    metrics: dict[str, Any],
    *,
    min_eval_coverage: float,
    min_recall_at_5: float,
    min_eval_pass_rate: float,
    max_latency_p95_ms: float,
) -> list[str]:
    failures: list[str] = []
    if float(metrics.get("eval_coverage", 0.0)) < min_eval_coverage:
        failures.append(f"eval_coverage below threshold: {metrics.get('eval_coverage')} < {min_eval_coverage}")
    if float(metrics.get("recall_at_5", 0.0)) < min_recall_at_5:
        failures.append(f"recall_at_5 below threshold: {metrics.get('recall_at_5')} < {min_recall_at_5}")
    if float(metrics.get("eval_pass_rate", 0.0)) < min_eval_pass_rate:
        failures.append(f"eval_pass_rate below threshold: {metrics.get('eval_pass_rate')} < {min_eval_pass_rate}")
    if float(metrics.get("latency_p95_ms", 0.0)) > max_latency_p95_ms:
        failures.append(f"latency_p95_ms above threshold: {metrics.get('latency_p95_ms')} > {max_latency_p95_ms}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail build when eval metrics regress below configured thresholds.")
    parser.add_argument("--report", default="data/reports/eval_latest.json", help="Path to eval report JSON.")
    parser.add_argument("--allow-missing", action="store_true", help="Return success when report is missing.")
    parser.add_argument("--min-eval-coverage", type=float, default=1.0)
    parser.add_argument("--min-recall-at-5", type=float, default=0.45)
    parser.add_argument("--min-eval-pass-rate", type=float, default=0.5)
    parser.add_argument("--max-latency-p95-ms", type=float, default=20000.0)
    args = parser.parse_args()

    report_path = Path(args.report)
    if not report_path.exists():
        message = f"Eval report not found: {report_path}"
        if args.allow_missing:
            print(f"[eval-gate] SKIP: {message}")
            return 0
        print(f"[eval-gate] FAIL: {message}")
        return 2

    data = json.loads(report_path.read_text(encoding="utf-8"))
    failures = evaluate_metrics(
        data,
        min_eval_coverage=args.min_eval_coverage,
        min_recall_at_5=args.min_recall_at_5,
        min_eval_pass_rate=args.min_eval_pass_rate,
        max_latency_p95_ms=args.max_latency_p95_ms,
    )
    if failures:
        print("[eval-gate] FAIL")
        for item in failures:
            print(f"- {item}")
        return 1
    print("[eval-gate] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
