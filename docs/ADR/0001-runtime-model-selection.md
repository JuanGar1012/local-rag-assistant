# ADR 0001: Runtime Chat Model Selection

## Status
Accepted

## Context
The project supports multiple local Ollama chat models. Requiring `.env` edits and backend restarts for model changes slows experimentation and degrades demo UX.

## Decision
Implement runtime model selection persisted in SQLite:
- `GET /models` exposes:
  - active model
  - default model
  - locally available Ollama models (`/api/tags`)
- `POST /models/select` sets active chat model in `app_settings`.
- `/query` resolves active model at request time (fallback to env default).

## Consequences
### Positive
- Faster model experimentation and comparison.
- Better portfolio signal for operations/product maturity.
- No restart needed to change serving model.

### Negative
- Adds mutable runtime state and validation logic.
- Requires guarding write endpoint when deployed (handled via optional API key baseline).

## Alternatives Considered
1. Env-only model config (rejected): operational friction too high.
2. Per-request model parameter (rejected): exposes unsafe public control surface for non-admin users.
