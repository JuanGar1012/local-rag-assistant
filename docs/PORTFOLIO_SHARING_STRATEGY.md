# Portfolio Sharing Strategy (Zero-Cost + Production Path)

## Why this project is local-first
This project is intentionally designed for **zero API cost**:
- Inference runs with local Ollama models.
- Embeddings are generated locally.
- Retrieval and app data stay local by default.

This allows anyone reviewing the project to clone and run it without paid model APIs.

## Recommended portfolio presentation

## 1) Primary CTA: Run Locally
Use this as your main call-to-action for recruiters/hiring managers:

```text
Clone -> Install deps -> Pull models -> Run backend/frontend -> Try included prompts
```

Keep this flow in README and on your portfolio page so interaction is real (not static).

## 2) Secondary CTA: Guided Demo
Link to:
- `docs/DEMO_SCRIPT.md` (structured walkthrough)
- short demo video/GIF clips
- architecture + ADR docs

This gives non-technical reviewers a fast way to understand value.

## 3) What to emphasize in portfolio copy
- End-to-end RAG engineering (ingestion, retrieval, generation, traceability).
- Runtime model selection and quality instrumentation.
- Evaluation gate + security baseline + production roadmap.

## Suggested portfolio blurb
Built a local-first RAG platform (FastAPI, Ollama, Chroma, SQLite, React) with ingestion jobs, citation traceability, model switching, calibrated quality metrics, and CI evaluation gates. Designed for zero-cost reproducibility today and clear production migration tomorrow.

## Production-readiness roadmap (for hiring managers)
Point reviewers to:
- `PRODUCTION_READY_ADDONS.md` (checklist and phased roadmap)
- `docs/SECURITY_BASELINE.md`
- `docs/EVAL_PROTOCOL.md`
- `docs/ARCHITECTURE.md`

This shows you can ship local-first now while planning realistic production evolution.

## If reviewers ask: "Why not host a public live demo?"
Use this answer:
- Public hosting of live inference shifts compute cost to the project owner.
- This project intentionally prioritizes zero-cost reproducibility.
- The architecture and docs include a concrete path to production deployment when required.
