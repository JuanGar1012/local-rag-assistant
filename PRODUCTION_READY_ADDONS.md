# Production-Ready Add-ons Checklist

This file tracks what should be added after the current local-first baseline to reach production-grade readiness.

## Completed Baseline (current)
- [x] Query + citations + run history persistence
- [x] Ingestion lifecycle (upload/link/jobs/reset/sources)
- [x] Metrics summary + trend history
- [x] Eval harness + report generation
- [x] Runtime model visibility/selection
- [x] Write endpoint API-key guard (`WRITE_API_KEY`)
- [x] CI workflow with tests + eval gate script
- [x] Quality calibration loop (heuristic + user feedback)

## Priority 1: Reliability and Governance
- [ ] Move SQLite logs/state to Postgres
- [ ] Add retry/backoff/circuit policies for model calls
- [ ] Add background workers for ingestion and eval queues
- [ ] Add SLOs and alerting rules (latency, error rate, eval regressions)
- [ ] Add incident runbook and rollback checklist

## Priority 2: Security and Access Control
- [ ] Add user auth + role separation (admin/write/read)
- [ ] Add rate limiting and abuse controls on write endpoints
- [ ] Add audit log table for all mutating actions
- [ ] Add secrets policy and key rotation docs

## Priority 3: Evaluation Depth
- [ ] Expand benchmark sets (domain + adversarial questions)
- [ ] Add grounding/attribution precision metrics
- [ ] Add regression matrix across models and `top_k`
- [ ] Persist eval artifacts per run for comparability

## Priority 4: Deployment and Scale
- [ ] Containerize API/frontend/workers
- [ ] Add staging + production configs
- [ ] Add vector DB/DB migration plan for scale
- [ ] Add load test suite and throughput targets

## Portfolio Artifacts to Publish
- [x] `docs/ARCHITECTURE.md` with diagrams
- [x] `docs/ADR/` decisions (model selection, confidence, eval gates)
- [x] `docs/EVAL_PROTOCOL.md` with thresholds and rationale
- [x] `docs/SECURITY_BASELINE.md` and hardening plan
- [ ] `reports/benchmark_matrix_YYYY-MM-DD.md`
