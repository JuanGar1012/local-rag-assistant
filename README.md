# Local RAG Assistant

Local-first and zero-cost by design.

This is a portfolio-grade AI application that runs entirely on your machine with FastAPI + Ollama + Chroma + SQLite + React/Vite. It demonstrates end-to-end RAG engineering, evaluation rigor, observability, and product UX without paid APIs or cloud services.

## 1. Project Overview
This system ingests local files or links, retrieves relevant context, and generates cited answers using local LLMs. It is designed to solve a real AI engineering problem: turning a basic "chat with docs" demo into a measurable, auditable, and reproducible system.

Why this is useful:
- Shows full AI system lifecycle: ingestion, retrieval, generation, evaluation, and monitoring.
- Produces traceable outputs with citations and run history.
- Supports fast local experimentation for model and retrieval tuning.

What makes it different:
- Fully local runtime (Ollama, Chroma, SQLite).
- No paid API keys.
- No mandatory cloud dependencies.

## 2. Key Capabilities
- Retrieval-Augmented Generation (RAG) with citations.
  - Solves grounding and answer traceability.
- Knowledge ingestion from links and files (`.pdf`, `.md`, `.txt`).
  - Solves "bring your own data" workflows.
- Ingestion job lifecycle (`queued/running/success/error`) with retry/backoff for links.
  - Solves operational visibility for data pipelines.
- Query run history with question, answer, citations, latency, model, and context scope.
  - Solves reproducibility and debugging.
- Answer quality loop with confidence + human feedback (`Correct`/`Incorrect`).
  - Solves iterative quality calibration.
- Metrics summary + history dashboard.
  - Solves reliability and performance monitoring.
- Runtime model selection from local Ollama tags.
  - Solves controlled model experimentation.
- Offline evaluation harness + CI quality gate.
  - Solves regression prevention.

## 3. System Architecture
Core layers:
- UI layer: React/Vite frontend for query, ingestion, dashboard, and history.
- API layer: FastAPI endpoints for query, ingestion, metrics, model control, and feedback.
- Orchestration layer: Query service + RAG pipeline.
- Model layer: Ollama local chat + embedding models.
- Retrieval layer: Chroma vector store with persistent local index.
- State/telemetry layer: SQLite for requests, retrieval events, eval runs, and query runs.
- Evaluation layer: offline benchmark runner and threshold gate.

```text
User (Browser)
    |
    v
React UI (Home / Dashboard / History)
    |
    v
FastAPI API
  /query
  /ingest/*
  /metrics/*
  /models/*
  /query/runs/*
    |
    v
QueryService + RAGPipeline
  1) Embed question (Ollama embed model)
  2) Retrieve top-k chunks (Chroma)
  3) Build grounded prompt
  4) Generate answer (Ollama chat model)
  5) Return citations + latency + confidence
    |
    +--> SQLite (logs, runs, feedback, eval history)
    +--> Metrics APIs
    +--> Offline eval runner + report
```

Layer purpose:
- API: typed interfaces and route orchestration.
- Retrieval/Generation: relevance and grounded response generation.
- Persistence: audit trail and observability.
- Evaluation: measurable quality and regression control.

## 4. Repository Structure
- `app/`: backend application code.
  - `api/`: REST endpoints.
  - `rag/`: ingestion, chunking, retrieval, generation logic.
  - `services/`: query orchestration.
  - `db/`: SQLite schema and data access.
  - `metrics/`: summary/history builders.
  - `eval/`: evaluation harness.
  - `middleware/`: request logging and telemetry.
- `frontend/`: React/Vite user interface.
- `scripts/`: CLI helpers (`ingest`, `run_eval`, `metrics_report`, `eval_gate`, `smoke_api`).
- `tests/`: backend and endpoint tests.
- `docs/`: architecture, security baseline, eval protocol, ADRs, demo script.
- `data/`: local docs, benchmark file, and generated reports.

## 5. Installation and Local Setup
Requirements:
- Python 3.11
- Node.js 18+
- Ollama installed locally

1. Clone and enter repository.
```powershell
git clone <your-repo-url>
cd local-rag-assistant
```

2. Backend setup.
```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

3. Start local model runtime and pull models.
```powershell
ollama serve
ollama pull llama3.2:3b
ollama pull nomic-embed-text
```

4. Start backend.
```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

5. Start frontend.
```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

6. Open:
- `http://127.0.0.1:5173/#/` (Home)
- `http://127.0.0.1:5173/#/dashboard` (Metrics dashboard)
- `http://127.0.0.1:5173/#/history` (Query runs)

Optional write-route protection:
```powershell
$env:WRITE_API_KEY="replace-with-strong-key"
$env:VITE_WRITE_API_KEY="replace-with-strong-key"
```

## 6. Example Usage
Typical flow:
1. Upload a file or ingest a public link in `Knowledge Ingestion`.
2. Ask a question and set `Context Scope` (top-k retrieval size).
3. Review answer with citations and latency/model/confidence metadata.
4. Mark answer as `Correct` or `Incorrect` in History.
5. Check Dashboard trends for speed, reliability, retrieval quality, eval pass rate, and answer quality.

API example:
```powershell
curl -X POST http://127.0.0.1:8000/query `
  -H "Content-Type: application/json" `
  -d "{\"question\":\"What are this project's key capabilities?\",\"top_k\":5}"
```

Expected behavior:
- With indexed context: grounded answer + citations.
- Without indexed context: explicit fallback message.
- Every run is logged for analysis.

## 7. AI Evaluation Methodology
Evaluation command:
```powershell
python -m scripts.run_eval
```

Benchmark input:
- `data/benchmarks/golden_eval.jsonl`

Outputs:
- `data/reports/eval_latest.json`
- `eval_runs` table in SQLite

Tracked metrics:
- `retrieval_hit_rate`
- `recall_at_k`
- `recall_at_5`
- `eval_pass_rate`
- `groundedness_proxy`
- `eval_coverage`
- `latency_p50_ms`
- `latency_p95_ms`

Quality gate:
```powershell
python -m scripts.eval_gate --report data/reports/eval_latest.json
```

Default thresholds:
- `eval_coverage >= 1.0`
- `recall_at_5 >= 0.45`
- `eval_pass_rate >= 0.50`
- `latency_p95_ms <= 20000`

Runtime quality calibration:
- Per-run `correctness_probability` heuristic.
- Human feedback (`Correct`/`Incorrect`) on stored runs.
- Aggregated 24h blended metric: `calibrated_quality_24h`.

## 8. Guardrails and Safety Mechanisms
Implemented:
- Grounding-oriented prompt design with citation references.
- "Insufficient context" behavior when retrieval is weak.
- File type and upload size restrictions for ingestion.
- URL safety validation (scheme, host policy, private IP controls).
- Retry/backoff for link ingestion failures.
- Optional API key protection on write routes.
- Request/retrieval/error telemetry for troubleshooting.

Current limitations:
- No dedicated prompt-injection classifier.
- No policy engine for fine-grained safety controls yet.

## 9. Failure Modes and Limitations
- Retrieval can return weak context if chunking/embedding quality is poor.
- Confidence score is heuristic, not calibrated probability theory.
- Eval pass checks are substring-based and can miss semantic nuance.
- Latency depends on local hardware and selected model size.
- Local single-node architecture is not horizontally scalable.
- Auth/rate-limit depth is baseline (not enterprise-grade yet).

## 10. Future Improvements
- Postgres for multi-user/concurrent production state.
- Worker queue for ingestion and eval.
- Stronger model-call resilience (timeouts/retries/circuit breaker).
- Broader benchmark suites (domain + adversarial cases).
- Richer faithfulness and attribution metrics.
- Role-based access control and rate limiting.
- Load testing + SLOs + incident response playbooks.
- Containerized deployment profiles.

## 11. Why This Project Matters for AI Engineering
This project demonstrates:
- LLM systems design (RAG architecture end to end).
- Practical retrieval engineering (chunking, vector search, citations).
- AI evaluation rigor (offline harness + quality gates).
- Reliability thinking (metrics, history, failure awareness).
- AI product engineering (usable UX, model selection, feedback loop).
- Reproducible local-first development with production-minded roadmap.

## 12. License
This project is licensed under the MIT License.

See [LICENSE](./LICENSE) for full text.
