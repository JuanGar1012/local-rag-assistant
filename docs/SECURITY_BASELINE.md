# Security Baseline

## Scope
Baseline protections for local/demo deployment before public sharing.

## 1) Write Endpoint Protection
- Config: `WRITE_API_KEY` in `.env`
- Behavior: when set, write endpoints require `X-API-Key`.
- Protected routes:
  - `POST /models/select`
  - `POST /query/runs/{id}/feedback`
  - `POST /ingest/upload`
  - `POST /ingest/link`
  - `POST /ingest/reset`

If `WRITE_API_KEY` is empty, behavior remains open (for local development).

## 2) Ingestion Hardening (already present)
- Host allow/block lists
- Private IP restrictions
- Upload size limits
- Retry/backoff controls for links

## 3) Recommended Next Controls
- Add request rate limiting for write routes.
- Add auth tokens (JWT/session) for non-local deployments.
- Add audit logging for all write actions.
- Add CORS origin tightening per environment.

## 4) Operational Practices
- Keep `.env` out of source control.
- Rotate `WRITE_API_KEY` when sharing demos externally.
- Run with non-default host bindings only on trusted networks.
