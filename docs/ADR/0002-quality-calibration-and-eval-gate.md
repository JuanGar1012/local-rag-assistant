# ADR 0002: Quality Calibration and Eval Gate

## Status
Accepted

## Context
Raw LLM confidence is unavailable in this local stack, and heuristic confidence alone can be misleading. The project needed a practical quality signal for dashboarding and merge safety.

## Decision
Use a two-layer quality approach:
1. Per-run heuristic confidence (`correctness_probability`) from retrieval/citation signals.
2. User feedback (`Correct`/`Incorrect`) persisted per run and blended with heuristic confidence.

Expose:
- `calibrated_quality_24h`
- `feedback_accuracy_rate_24h`
- `feedback_samples_24h`

Add CI eval gate script:
- `scripts/eval_gate.py`
- Threshold checks on `eval_latest.json` for coverage, recall@5, pass rate, p95 latency.

## Consequences
### Positive
- Better quality signal than heuristic-only confidence.
- Observable and defensible quality governance artifact for hiring review.
- Regression protection via CI gate.

### Negative
- Quality metric depends on feedback participation volume.
- Heuristic confidence is still proxy-based, not claim-level truth verification.

## Alternatives Considered
1. Heuristic-only confidence (rejected): insufficiently trustworthy.
2. Human-label-only quality (rejected): sparse early data, too slow for continuous signal.
3. Full claim verification pipeline now (deferred): high complexity, planned in future hardening phase.
