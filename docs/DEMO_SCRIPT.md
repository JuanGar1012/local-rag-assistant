# Demo Script

## Goal
Showcase end-to-end RAG workflow, observability, and quality controls in 10-15 minutes.

## Audience
AI hiring managers, senior engineers, technical interview panels.

## Setup (before demo)
1. Start backend:
```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
2. Start frontend:
```powershell
cd frontend
npm.cmd run dev
```
3. Ensure Ollama is running and models are pulled:
```powershell
ollama serve
ollama pull llama3.2:3b
ollama pull nomic-embed-text
```

## 10-Minute Version

### 1) Product overview (1 min)
- Open Home (`#/`).
- Explain local-first architecture and zero-cost inference.
- Point out model selector and quality/metrics cards.

### 2) Ingest and retrieve (2 min)
- Ingest one link in `Knowledge Ingestion`.
- Show ingestion job status and source tracking.
- Ask a question tied to that source with `Context Scope = 3`.

### 3) Grounded answer + traceability (2 min)
- Highlight answer, citations, latency, model used, confidence.
- Open citation details and explain source grounding.

### 4) History and quality loop (2 min)
- Go to History (`#/history`).
- Show full run record, context scope, copy action.
- Mark one run `Correct`/`Incorrect` and explain calibrated quality metric.

### 5) Dashboard observability (2 min)
- Go to Dashboard (`#/dashboard`).
- Hover charts to show interactive values.
- Explain hourly request trends vs eval-driven trends.

### 6) Production-readiness callout (1 min)
- Mention CI gate (`.github/workflows/ci.yml` + `scripts/eval_gate.py`).
- Mention security baseline (`WRITE_API_KEY`, ingestion hardening).

## 15-Minute Version Add-ons
- Switch runtime model and rerun the same question.
- Compare latency/quality across `top_k` values.
- Show docs:
  - `docs/ARCHITECTURE.md`
  - `docs/ADR/0001-runtime-model-selection.md`
  - `docs/ADR/0002-quality-calibration-and-eval-gate.md`

## Backup Flows
- If eval trends are empty: run `python -m scripts.run_eval`.
- If reliability trend is empty: run 2-3 quick queries on Home.
- If write routes reject: verify `WRITE_API_KEY` and `VITE_WRITE_API_KEY` alignment.
