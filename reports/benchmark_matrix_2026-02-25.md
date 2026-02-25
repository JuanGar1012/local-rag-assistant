# Benchmark Matrix - 2026-02-25

## Purpose
Track measurable tradeoffs across model, context scope, latency, retrieval quality, and answer quality.

## Environment
- Host: local workstation
- Runtime: Ollama + Chroma + SQLite
- API: FastAPI
- UI: React/Vite
- Benchmark source: `data/benchmarks/golden_eval.jsonl`

## Run Matrix

| Run ID | Chat Model | Embed Model | top_k | Dataset | Eval Coverage | Recall@5 | Eval Pass Rate | Latency P95 (ms) | Calibrated Quality (24h) | Notes |
|---|---|---|---:|---|---:|---:|---:|---:|---:|---|
| R1 | llama3.2:3b | nomic-embed-text | 3 | golden_eval | - | - | - | - | - | baseline |
| R2 | llama3.2:3b | nomic-embed-text | 6 | golden_eval | - | - | - | - | - | broader context |
| R3 | llama3.2:3b | nomic-embed-text | 10 | golden_eval | - | - | - | - | - | stress latency |
| R4 | llama3.2:1b | nomic-embed-text | 3 | golden_eval | - | - | - | - | - | smaller model |

## How to Populate
1. Run eval:
```powershell
python -m scripts.run_eval
```
2. Pull metrics:
```powershell
python -m scripts.metrics_report
```
3. Read values from:
- `data/reports/eval_latest.json`
- `GET /metrics/summary`
- Dashboard/History run metadata

## Interpretation Guide
- Prefer higher `Recall@5` and `Eval Pass Rate`.
- Keep `Latency P95` within your demo target.
- Use `Calibrated Quality` to reflect both system confidence and human feedback.
- Document tradeoff decisions in `Notes`.
