# Architecture Overview

## Purpose
Local-first RAG assistant for zero-cost inference, retrieval traceability, and portfolio-grade observability.

## High-Level Components
- `Frontend (React/Vite)`: Home, Dashboard, History UX.
- `API (FastAPI)`: query, ingestion, metrics, model control, feedback endpoints.
- `RAG Pipeline`: embedding, retrieval, prompt assembly, generation, citations.
- `Vector Store (Chroma)`: chunk embeddings and nearest-neighbor retrieval.
- `Operational DB (SQLite)`: request logs, retrieval events, eval runs, query runs, feedback, app settings.
- `Model Runtime (Ollama)`: local chat + embedding models.

## Request Flow (Query)
1. `POST /query` receives question + `top_k`.
2. Active chat model resolved from `app_settings` (fallback to env default).
3. Pipeline embeds query (`OLLAMA_EMBED_MODEL`) and retrieves from Chroma.
4. Prompt built with ranked context blocks and citation references.
5. Chat model generates answer (`active_chat_model`).
6. API returns answer + citations + latency + confidence + model metadata.
7. Query run and retrieval event are logged to SQLite.

## Ingestion Flow
1. Upload/link request creates ingestion job row.
2. Background task fetches/parses content and chunks text.
3. Chunks embedded and upserted into Chroma.
4. Source tracking row stored in `ingested_sources`.
5. Job status and metrics updated in SQLite.

## Metrics and Evaluation Flow
- Runtime metrics: request/retrieval/query-run logs aggregated into `/metrics/summary` and `/metrics/history`.
- Offline eval: `python -m scripts.run_eval` writes `data/reports/eval_latest.json` and `eval_runs`.
- Quality calibration: combines heuristic confidence with user feedback (`Correct`/`Incorrect`) into `calibrated_quality_24h`.

## Security Baseline
- Optional write-route protection via `WRITE_API_KEY` (`X-API-Key` header).
- Ingestion hardening controls: upload limits, host allow/block lists, private IP policy, retries/backoff.

## Storage Model (Core Tables)
- `request_logs`
- `retrieval_events`
- `eval_runs`
- `ingestion_jobs`
- `ingested_sources`
- `index_state`
- `query_runs`
- `query_run_feedback`
- `app_settings`

## Design Tradeoffs
- Chosen for local simplicity: SQLite + Chroma + Ollama.
- Tradeoff: excellent local DX, limited horizontal scale.
- Planned scale path: Postgres + worker queue + stronger auth/rate limiting + containerized environments.
