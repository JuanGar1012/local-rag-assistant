# Evaluation Protocol

## Objective
Provide reproducible quality gates for retrieval and answer quality before merge/deploy.

## Primary Metrics
- `eval_coverage`: fraction of benchmark cases processed.
- `recall_at_5`: retrieval quality against expected doc IDs.
- `eval_pass_rate`: answer pass rate against expected substrings.
- `latency_p95_ms`: tail latency during eval.

## Data Sources
- Benchmark input: `data/benchmarks/golden_eval.jsonl`
- Eval output: `data/reports/eval_latest.json`
- Historical eval table: `eval_runs` (SQLite)

## Default Gate Thresholds
- `eval_coverage >= 1.0`
- `recall_at_5 >= 0.45`
- `eval_pass_rate >= 0.50`
- `latency_p95_ms <= 20000`

These are intentionally pragmatic for local Ollama setups. Tighten over time as dataset quality improves.

## Gate Command
```powershell
python -m scripts.eval_gate --report data/reports/eval_latest.json
```

## Threshold Tuning Guidance
- Raise `recall_at_5` first when retrieval quality is the bottleneck.
- Raise `eval_pass_rate` after prompt/context formatting is stable.
- Lower `latency_p95_ms` only after model and `top_k` are fixed for the target demo profile.

## Change Control
When changing thresholds:
1. Add rationale in PR description.
2. Include before/after metrics table from `eval_latest.json`.
3. Update this document.
