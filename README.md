# Local RAG Support Copilot (Zero-Cost)

Local-only RAG backend for portfolio metrics and demo UX.

## Why these dependencies

- `Ollama`: local LLM + embeddings, no paid APIs.
- `Chroma`: local persistent vector store with low setup.
- `SQLite`: embedded logging + eval store.
- `FastAPI`: typed APIs with simple deployment.

## Project structure

```text
app/
  api/{routes.py,metrics.py}
  core/{config.py,logging.py}
  db/sqlite.py
  eval/harness.py
  metrics/summary.py
  middleware/request_logging.py
  rag/{ingestion.py,ingest_service.py,ollama_client.py,pipeline.py,vector_store.py}
  services/query_service.py
  dependencies.py
  main.py
scripts/
  ingest.py
  run_eval.py
  metrics_report.py
data/
  docs/
  benchmarks/golden_eval.jsonl
  reports/{eval_latest.json,metrics-summary.json}
tests/
  test_db_schema_metrics.py
  test_metrics_endpoint.py
```

## 1) Install (PowerShell)

```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

## 2) Start Ollama and pull models

```powershell
ollama serve
```

In another terminal:

```powershell
ollama pull llama3.2:3b
ollama pull nomic-embed-text
```

## 3) Run ingestion

```powershell
python -m scripts.ingest
```

Expected snippet:

```text
{'docs': 2, 'chunks': 4, 'vector_count': 4}
```

## 4) Run API

```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Recommended smoke check (no shell quoting issues):

```powershell
python -m scripts.smoke_api
```

PowerShell helper:

```powershell
.\scripts\smoke_api.ps1
```

## 5) Query API

```powershell
curl -X POST http://127.0.0.1:8000/query `
  -H "Content-Type: application/json" `
  -d "{\"question\":\"What metrics does this project expose?\",\"top_k\":5}"
```

## 6) Run offline eval

```powershell
python -m scripts.run_eval
```

Outputs:
- `data/reports/eval_latest.json`
- `eval_runs` rows in SQLite

## 7) Check metrics summary endpoint

```powershell
python -m scripts.smoke_api
```

Trend history endpoint:

```powershell
irm 'http://127.0.0.1:8000/metrics/history?hours=24&bucket_minutes=15'
```

Expected payload shape:

```json
{
  "updated_at": "2026-02-24T00:00:00+00:00",
  "latency_p95_ms": 920.4,
  "success_rate": 0.98,
  "error_rate": 0.02,
  "requests_24h": 154,
  "recall_at_5": 0.87,
  "eval_pass_rate": 0.81,
  "eval_coverage": 1.0
}
```

## 8) Generate metrics artifact for portfolio

```powershell
python -m scripts.metrics_report
```

Artifact:
- `data/reports/metrics-summary.json`

## Optional ingestion endpoints

Upload:

```powershell
curl -X POST http://127.0.0.1:8000/ingest/upload -F "file=@data/docs/project_notes.txt"
```

Link:

```powershell
curl -X POST http://127.0.0.1:8000/ingest/link `
  -H "Content-Type: application/json" `
  -d "{\"url\":\"https://example.com\"}"
```

Job status:

```powershell
curl http://127.0.0.1:8000/ingest/jobs/1
```

## Ingestion hardening config

- `INGEST_MAX_UPLOAD_BYTES`
- `INGEST_ALLOWED_HOSTS`
- `INGEST_BLOCKED_HOSTS`
- `INGEST_ALLOW_PRIVATE_IPS`
- `INGEST_LINK_MAX_RETRIES`
- `INGEST_LINK_BACKOFF_SECONDS`

## Write endpoint auth (optional but recommended)

Set an API key to protect write routes:

```powershell
$env:WRITE_API_KEY="replace-with-strong-key"
```

When configured, send header:

```text
X-API-Key: <your-key>
```

Frontend (optional):

```powershell
$env:VITE_WRITE_API_KEY="replace-with-strong-key"
```

Protected write routes include ingestion reset/upload/link, model selection, and query feedback updates.

## Tests

```powershell
pytest -q
```

## Eval quality gate

Run quality thresholds against `data/reports/eval_latest.json`:

```powershell
python -m scripts.eval_gate --report data/reports/eval_latest.json
```

Protocol and thresholds:
- `docs/EVAL_PROTOCOL.md`
- `docs/SECURITY_BASELINE.md`
- `PRODUCTION_READY_ADDONS.md`

## Architecture and ADRs

- `docs/ARCHITECTURE.md`
- `docs/ADR/0001-runtime-model-selection.md`
- `docs/ADR/0002-quality-calibration-and-eval-gate.md`

## Portfolio Positioning

- `docs/PORTFOLIO_SHARING_STRATEGY.md` (how to present this as zero-cost local-first + production-minded)
- `docs/DEMO_SCRIPT.md` (live walkthrough flow)

## Frontend portfolio cards

The frontend now polls `GET /metrics/summary` every 60s and renders:

- Response Latency (`latency_p95_ms`)
- Retrieval Quality (`recall_at_5`)
- System Reliability (`success_rate`)
- Eval Coverage (`eval_coverage`)

Presentation dashboard also visualizes trends from `GET /metrics/history`:

- Query latency trend
- Reliability trend
- Retrieval match trend
- Eval pass trend

UI routes:

- Home view: `http://127.0.0.1:5173/#/`
- Dashboard view: `http://127.0.0.1:5173/#/dashboard`

Frontend styling stack:

- Tailwind CSS (utility-first responsive UI)
- Mobile-first layouts with responsive breakpoints

If pulling latest changes, refresh frontend deps:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```
