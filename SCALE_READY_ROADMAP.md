# Scale-Ready Roadmap (Back Pocket)

## Goal
Evolve this local RAG assistant into a production architecture that can scale to large user traffic while keeping model/provider flexibility.

## Core Best Practices
1. Separate control plane and inference plane.
2. Containerize all services (`api`, `frontend`, workers, data).
3. Move durable state to scalable stores (Postgres + vector DB).
4. Run ingestion/evals asynchronously via job queue workers.
5. Enforce security defaults (auth, RBAC, rate limits, audit logs).
6. Add full observability (logs, traces, metrics, alerts).
7. Version datasets/evals/prompts/chunking and gate deploys on eval.
8. Use staged environments (`dev`, `staging`, `prod`) with canary rollout.
9. Keep model client abstraction so provider can be swapped later.
10. Add cost controls (caching, batching, quotas, autoscaling).

## Practical Upgrade Path For This Repo
1. Replace SQLite logs with Postgres.
2. Move ingestion and eval to background workers.
3. Add auth + rate limiting + write endpoint protection.
4. Add Docker Compose for local prod-like orchestration.
5. Add CI gate to run eval before merge/deploy.

## Suggested Milestones
- Phase 1: Security and reliability hardening on current architecture.
- Phase 2: Data layer and async worker migration.
- Phase 3: Multi-tenant and horizontal scale patterns.

## Notes
- Keep Ollama for zero API-cost local inference initially.
- Move to a stronger serving stack only when traffic/latency requires it.
