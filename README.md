# Local RAG Assistant (Local-First, Zero-Cost)

## 1. Project Overview
This project is a local Retrieval-Augmented Generation (RAG) assistant built for practical AI engineering workflows: ingesting documents/links, retrieving grounded context, generating cited answers, and measuring quality over time. It solves a common systems problem in LLM projects: moving from a one-off demo to an observable, testable, reproducible stack with clear operational signals. The system includes ingestion lifecycle management, query/run history, evaluation pipelines, and UI-level instrumentation for reliability and answer quality tracking.

Local-first and zero-cost by design.

- Fully local runtime: Ollama models run on your machine.
- No paid API keys required.
- No cloud dependency required for core functionality.

## 2. Key Capabilities
- RAG query pipeline with citations.
  - Solves traceability and answer-grounding needs for AI applications.
- Link/file ingestion with job tracking.
  - Solves ingestion reliability, retries, and status visibility.
- Runtime model visibility and selection.
  - Solves experiment control across local Ollama chat models.
- Query run history and feedback loop (`Correct`/`Incorrect`).
  - Solves post-hoc quality review and calibration.
- Metrics APIs and dashboard trends.
  - Solves operational visibility for latency, reliability, retrieval quality, and eval pass rate.
- Offline evaluation harness with gate thresholds.
  - Solves regression detection with deterministic checks.
- Optional write-route protection (`WRITE_API_KEY`).
  - Solves baseline hardening for shared demos.

## 3. System Architecture
Major components:
- Frontend: React + Vite (`frontend/`) for Home, Dashboard, History UX.
- API layer: FastAPI (`app/api/`) for query, ingestion, metrics, model control, feedback.
- Orchestration/service layer: `QueryService` + `RAGPipeline`.
- Model runtime: Ollama (chat + embedding models).
- Retrieval layer: Chroma vector store (persistent local index).
- Operational state: SQLite (request logs, retrieval events, eval runs, query runs, feedback, settings).
- Evaluation layer: offline harness + CI eval gate.

ASCII architecture diagram:

```text
User (UI / API client)
        |
        v
FastAPI Endpoints
  - /query
  - /ingest/*
  - /metrics/*
  - /models/*
  - /query/runs/*
        |
        v
QueryService / RAGPipeline ---------------------------+
  1) Embed question (Ollama embed model)             |
  2) Retrieve top-k chunks (Chroma)                  |
  3) Build grounded prompt with ranked context       |
  4) Generate answer (Ollama chat model)             |
  5) Return answer + citations + metadata            |
        |                                            |
        +--> SQLite logs (request/retrieval/runs) <--+
        |
        +--> Metrics summary/history APIs
        |
        +--> Eval harness (offline) -> eval report + eval_runs
```

Layer purpose:
- API layer: typed interfaces and route-level orchestration.
- Retrieval/generation layer: grounding and answer synthesis.
- Persistence layer: operational telemetry and historical traceability.
- Evaluation layer: repeatable quality checks and threshold gating.

## 4. Repository Structure
- `app/`
  - `api/`: FastAPI routes (`/query`, `/ingest`, `/metrics`, `/models`).
  - `core/`: configuration and logging setup.
  - `db/sqlite.py`: schema, migrations, and telemetry persistence.
  - `rag/`: ingestion, chunking, embedding, retrieval, generation pipeline.
  - `services/query_service.py`: query orchestration and retrieval event logging.
  - `metrics/`: summary/history aggregation logic.
  - `eval/`: offline evaluation harness.
  - `middleware/`: request logging + latency/token capture.
- `frontend/`
  - React/Vite UI with Home, Dashboard, History routes and charting.
- `scripts/`
  - local automation for ingestion, eval, metrics report, smoke checks, eval gate.
- `tests/`
  - endpoint, schema, ingestion, model selection, feedback, eval gate tests.
- `docs/`
  - architecture, eval protocol, security baseline, ADRs, demo script.
- `data/`
  - local docs, benchmark file, reports, Chroma persistence, SQLite DB (runtime state).

## 5. Installation and Local Setup
Tested baseline:
- Python 3.11
- Node.js 18+ (for frontend)
- Ollama installed locally

1. Clone and enter repo.
```powershell
git clone <your-repo-url>
cd local-rag-assistant
```

2. Create Python environment and install backend dependencies.
```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

3. Start Ollama and pull local models.
```powershell
ollama serve
ollama pull llama3.2:3b
ollama pull nomic-embed-text
```

4. Start backend API.
```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

5. Start frontend.
```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

6. Open app.
- Home: `http://127.0.0.1:5173/#/`
- Dashboard: `http://127.0.0.1:5173/#/dashboard`
- History: `http://127.0.0.1:5173/#/history`

Optional hardening for write routes:
```powershell
$env:WRITE_API_KEY="replace-with-strong-key"
$env:VITE_WRITE_API_KEY="replace-with-strong-key"
```

## 6. Example Usage
Example workflow (UI):
1. Ingest one link or upload one `.pdf/.md/.txt` file in `Knowledge Ingestion`.
2. Ask a question on Home with a selected `Context Scope` (`top_k`).
3. Inspect answer + citations + latency + model + confidence.
4. Review run in History and optionally mark `Correct` or `Incorrect`.
5. Check Dashboard trends (latency, reliability, retrieval quality, eval pass, answer quality).

Equivalent query API call:
```powershell
curl -X POST http://127.0.0.1:8000/query `
  -H "Content-Type: application/json" `
  -d "{\"question\":\"What are the key capabilities of this project?\",\"top_k\":5}"
```

Expected behavior:
- If indexed context exists, answer is generated with citations.
- If no context exists, system returns: `No indexed context was found. Ingest documents first.`
- Every request is logged for operational metrics and run history.

## 7. AI Evaluation Methodology
Offline evaluation is implemented in `app/eval/harness.py` and executed via:

```powershell
python -m scripts.run_eval
```

Input dataset:
- `data/benchmarks/golden_eval.jsonl`

Output artifacts:
- JSON report: `data/reports/eval_latest.json`
- Persistent run record: `eval_runs` table (SQLite)

Core metrics tracked:
- `retrieval_hit_rate`
- `recall_at_k`
- `recall_at_5`
- `eval_pass_rate` (expected substrings present in answer)
- `groundedness_proxy` (expected terms present in retrieved context)
- `eval_coverage`
- `latency_p50_ms`, `latency_p95_ms`

Runtime quality telemetry:
- `correctness_probability` per query run (heuristic estimate from citation count/distances/reference usage).
- user feedback accuracy from `query_run_feedback`.
- calibrated 24h quality metric in `/metrics/summary`:
  - `calibrated_quality_24h` combines model confidence and user feedback using sample-weighted blending.

Regression gate:
```powershell
python -m scripts.eval_gate --report data/reports/eval_latest.json
```

Default thresholds:
- `eval_coverage >= 1.0`
- `recall_at_5 >= 0.45`
- `eval_pass_rate >= 0.50`
- `latency_p95_ms <= 20000`

## 8. Guardrails and Safety Mechanisms
Implemented safeguards:
- Grounding-first prompt contract:
  - answer with concise factual statements from context.
  - cite claims using `[n]` references mapped to retrieved chunks.
  - explicitly indicate insufficient context when applicable.
- Ingestion constraints:
  - allowed extensions: `.pdf`, `.md`, `.txt`
  - upload size limit (`INGEST_MAX_UPLOAD_BYTES`)
  - URL validation (`http/https`, host allow/block, private IP restrictions)
  - retry/backoff policy for link ingestion.
- Route hardening:
  - optional API-key guard for mutating routes (`WRITE_API_KEY`, `X-API-Key`).
- Observability:
  - request/retrieval/error logging for forensic troubleshooting.

Current state for prompt injection:
- Basic mitigation is present through controlled retrieval and grounded prompting.
- No dedicated adversarial prompt-injection detector yet.

## 9. Failure Modes and Limitations
- Retrieval inaccuracies:
  - poor chunking or weak embeddings can surface irrelevant context.
- Confidence calibration is heuristic:
  - `correctness_probability` is not a probabilistic guarantee.
- Eval method limits:
  - substring-based pass checks can over/under-estimate semantic correctness.
- Prompt sensitivity:
  - answer quality may shift with prompt wording and selected `top_k`.
- Local compute variability:
  - latency and throughput depend on host hardware and model size.
- Single-node architecture:
  - SQLite + local services are excellent for reproducibility, not horizontal scale.
- Safety depth:
  - no full policy engine, no RBAC/JWT, no dedicated rate limiter yet.

## 10. Future Improvements
- Replace SQLite state/logging with Postgres for stronger concurrency and ops.
- Add background workers/queues for ingestion and eval.
- Add model-call resilience policies (retry, timeout classes, circuit breaking).
- Expand benchmark sets (domain-specific + adversarial + drift checks).
- Add richer grounding metrics (attribution precision/faithfulness scoring).
- Add role-based auth and write-route rate limiting.
- Add load testing and SLO/alert definitions.
- Add containerized deployment profiles for reproducible environment parity.

## 11. Why This Project Matters for AI Engineering
This project demonstrates practical AI systems engineering, not just model prompting:
- End-to-end RAG architecture (ingest, retrieve, generate, cite).
- Local model ops (Ollama) and model-selection control plane.
- Observability and telemetry design (request/retrieval/query/eval signals).
- Evaluation rigor with repeatable offline harness + CI quality gate.
- Reliability and failure-awareness through history, metrics, and explicit limitations.
- Security baseline thinking (write-route protection and ingestion hardening).
- Reproducible local-first execution suitable for technical portfolio review.

## 12. License
Intended open-source license: MIT.

Before external distribution, add a `LICENSE` file (MIT text) at the repository root to formalize usage rights.
