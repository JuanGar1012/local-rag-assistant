import re
import time
from fastapi import APIRouter, BackgroundTasks, Depends, File, Header, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

from app.core.config import Settings, get_settings
from app.db.sqlite import (
    clear_ingested_sources,
    create_ingestion_job,
    get_app_setting,
    get_index_state,
    get_ingestion_job,
    list_ingested_sources,
    list_ingestion_jobs,
    list_query_runs,
    log_retrieval_event,
    log_query_run,
    mark_index_reset,
    recent_query_history,
    record_ingested_source,
    set_app_setting,
    upsert_query_run_feedback,
    update_ingestion_job,
)
from app.dependencies import get_ollama, get_query_service, get_store
from app.rag.ingest_service import fetch_link_text, validate_ingest_url
from app.rag.ingestion import ingest_document_texts, source_to_doc_id, text_from_bytes
from app.rag.ollama_client import OllamaClient
from app.rag.vector_store import ChromaVectorStore
from app.services.query_service import QueryService

router = APIRouter()


def require_write_access(
    settings: Settings = Depends(get_settings),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    configured_key = settings.WRITE_API_KEY.strip()
    if not configured_key:
        return
    if x_api_key is None or x_api_key.strip() != configured_key:
        raise HTTPException(status_code=401, detail="Missing or invalid X-API-Key.")


class QueryRequest(BaseModel):
    question: str = Field(min_length=3, description="User question.")
    top_k: int | None = Field(default=None, ge=1, le=15)


class Citation(BaseModel):
    rank: int
    doc_id: str
    source: str
    chunk_index: int
    distance: float
    text_preview: str


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
    retrieved_doc_ids: list[str]
    latency_ms: float
    correctness_probability: float
    chat_model: str
    embed_model: str


class IngestLinkRequest(BaseModel):
    url: str = Field(min_length=10)


class IngestJobAccepted(BaseModel):
    job_id: int
    status: str


class IngestJobStatus(BaseModel):
    job_id: int
    created_utc: str
    updated_utc: str
    source_type: str
    source: str
    status: str
    attempt_count: int
    max_attempts: int
    latency_ms: float | None = None
    summary: dict[str, int] | None = None
    error: str | None = None


class IngestJobListResponse(BaseModel):
    jobs: list[IngestJobStatus]


class ResetIngestionRequest(BaseModel):
    confirm: bool = Field(default=False, description="Must be true to execute reset.")


class ResetIngestionResponse(BaseModel):
    status: str
    vector_count: int
    sources_cleared: int
    last_reset_utc: str | None = None
    reset_count: int
    message: str


class IngestedSourceItem(BaseModel):
    id: int
    ingested_utc: str
    source_type: str
    source: str
    doc_id: str


class IngestedSourcesResponse(BaseModel):
    total_sources: int
    last_reset_utc: str | None = None
    reset_count: int
    items: list[IngestedSourceItem]


class QueryHistoryItem(BaseModel):
    ts_utc: str
    question: str
    top_k: int
    hit: bool
    error: str | None = None


class QueryHistoryResponse(BaseModel):
    items: list[QueryHistoryItem]


class QueryRunItem(BaseModel):
    id: int
    ts_utc: str
    request_id: str | None = None
    question: str
    answer: str
    citations: list[dict[str, object]]
    retrieved_doc_ids: list[str]
    latency_ms: float
    top_k: int | None = None
    correctness_probability: float | None = None
    chat_model: str | None = None
    feedback_is_correct: bool | None = None
    feedback_note: str | None = None
    feedback_ts_utc: str | None = None


class QueryRunsResponse(BaseModel):
    items: list[QueryRunItem]


class QueryRunFeedbackRequest(BaseModel):
    is_correct: bool
    note: str | None = Field(default=None, max_length=400)


class QueryRunFeedbackResponse(BaseModel):
    query_run_id: int
    is_correct: bool
    note: str | None = None
    ts_utc: str | None = None


class ModelsResponse(BaseModel):
    chat_model: str
    active_chat_model: str
    default_chat_model: str
    available_chat_models: list[str]
    embed_model: str
    ollama_base_url: str


class ModelSelectRequest(BaseModel):
    chat_model: str = Field(min_length=1)


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/models", response_model=ModelsResponse)
def models(
    settings: Settings = Depends(get_settings),
    ollama: OllamaClient = Depends(get_ollama),
) -> ModelsResponse:
    available: list[str] = []
    try:
        available = ollama.list_models()
    except Exception:
        available = []
    active = get_app_setting(settings.sqlite_path, key="active_chat_model") or settings.OLLAMA_CHAT_MODEL
    return ModelsResponse(
        chat_model=active,
        active_chat_model=active,
        default_chat_model=settings.OLLAMA_CHAT_MODEL,
        available_chat_models=available,
        embed_model=settings.OLLAMA_EMBED_MODEL,
        ollama_base_url=settings.OLLAMA_BASE_URL,
    )


@router.post("/models/select", response_model=ModelsResponse)
def select_model(
    payload: ModelSelectRequest,
    _: None = Depends(require_write_access),
    settings: Settings = Depends(get_settings),
    ollama: OllamaClient = Depends(get_ollama),
) -> ModelsResponse:
    requested = payload.chat_model.strip()
    if not requested:
        raise HTTPException(status_code=400, detail="chat_model cannot be empty.")
    available: list[str] = []
    try:
        available = ollama.list_models()
    except Exception:
        available = []
    if available and requested not in available:
        raise HTTPException(status_code=400, detail=f"Model not found in local Ollama tags: {requested}")
    set_app_setting(settings.sqlite_path, key="active_chat_model", value=requested)
    return ModelsResponse(
        chat_model=requested,
        active_chat_model=requested,
        default_chat_model=settings.OLLAMA_CHAT_MODEL,
        available_chat_models=available,
        embed_model=settings.OLLAMA_EMBED_MODEL,
        ollama_base_url=settings.OLLAMA_BASE_URL,
    )


@router.post("/query", response_model=QueryResponse)
def query(
    payload: QueryRequest,
    request: Request,
    query_service: QueryService = Depends(get_query_service),
) -> QueryResponse:
    k = payload.top_k or query_service.settings.TOP_K
    active_chat_model = get_app_setting(query_service.settings.sqlite_path, key="active_chat_model") or query_service.settings.OLLAMA_CHAT_MODEL
    try:
        result = query_service.run_query(
            question=payload.question,
            top_k=payload.top_k,
            request_id=getattr(request.state, "request_id", None),
            chat_model=active_chat_model,
        )
    except Exception as exc:
        log_retrieval_event(
            query_service.settings.sqlite_path,
            request_id=getattr(request.state, "request_id", None),
            source="live_query",
            query_text=payload.question,
            top_k=k,
            hit=False,
            recall_at_k=0.0,
            recall_at_5=0.0,
            citations=[],
            retrieved_doc_ids=[],
            error=str(exc),
        )
        raise HTTPException(status_code=500, detail=f"Query failed: {exc}") from exc
    token_usage = result.get("token_usage", {})
    request.state.prompt_tokens = token_usage.get("prompt_tokens")
    request.state.completion_tokens = token_usage.get("completion_tokens")
    request.state.total_tokens = token_usage.get("total_tokens")
    log_query_run(
        query_service.settings.sqlite_path,
        request_id=getattr(request.state, "request_id", None),
        question=payload.question,
        answer=str(result.get("answer", "")),
        citations=result.get("citations", []),
        retrieved_doc_ids=result.get("retrieved_doc_ids", []),
        latency_ms=float(result.get("latency_ms", 0.0)),
        top_k=k,
        correctness_probability=float(result.get("correctness_probability", 0.0)),
        chat_model=str(result.get("chat_model", query_service.settings.OLLAMA_CHAT_MODEL)),
    )
    return QueryResponse(**result)


@router.get("/query/history", response_model=QueryHistoryResponse)
def query_history(limit: int = 20, settings: Settings = Depends(get_settings)) -> QueryHistoryResponse:
    items = recent_query_history(settings.sqlite_path, limit=limit)
    return QueryHistoryResponse(items=[QueryHistoryItem(**item) for item in items])


@router.get("/query/runs", response_model=QueryRunsResponse)
def query_runs(limit: int = 50, settings: Settings = Depends(get_settings)) -> QueryRunsResponse:
    items = list_query_runs(settings.sqlite_path, limit=limit)
    return QueryRunsResponse(items=[QueryRunItem(**item) for item in items])


@router.post("/query/runs/{run_id}/feedback", response_model=QueryRunFeedbackResponse)
def query_run_feedback(
    run_id: int,
    payload: QueryRunFeedbackRequest,
    _: None = Depends(require_write_access),
    settings: Settings = Depends(get_settings),
) -> QueryRunFeedbackResponse:
    try:
        row = upsert_query_run_feedback(
            settings.sqlite_path,
            query_run_id=run_id,
            is_correct=payload.is_correct,
            note=(payload.note or "").strip() or None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return QueryRunFeedbackResponse(**row)


def _run_upload_ingest_job(
    *,
    job_id: int,
    filename: str,
    raw: bytes,
    settings: Settings,
    store: ChromaVectorStore,
    ollama: OllamaClient,
) -> None:
    started = time.perf_counter()
    update_ingestion_job(settings.sqlite_path, job_id=job_id, status="running", attempt_count=1)
    try:
        text = text_from_bytes(filename, raw)
        doc_id = source_to_doc_id(filename)
        summary = ingest_document_texts(settings, store, ollama, docs=[(doc_id, filename, text)])
        latency_ms = (time.perf_counter() - started) * 1000
        update_ingestion_job(
            settings.sqlite_path,
            job_id=job_id,
            status="success",
            attempt_count=1,
            latency_ms=latency_ms,
            summary=summary,
        )
        record_ingested_source(settings.sqlite_path, source_type="upload", source=filename, doc_id=doc_id)
    except Exception as exc:
        latency_ms = (time.perf_counter() - started) * 1000
        update_ingestion_job(
            settings.sqlite_path,
            job_id=job_id,
            status="error",
            attempt_count=1,
            latency_ms=latency_ms,
            error=str(exc),
        )


def _run_link_ingest_job(
    *,
    job_id: int,
    url: str,
    settings: Settings,
    store: ChromaVectorStore,
    ollama: OllamaClient,
) -> None:
    started = time.perf_counter()
    max_attempts = max(1, settings.INGEST_LINK_MAX_RETRIES + 1)
    attempt = 0
    last_error: str | None = None
    while attempt < max_attempts:
        attempt += 1
        update_ingestion_job(settings.sqlite_path, job_id=job_id, status="running", attempt_count=attempt)
        try:
            _, text = fetch_link_text(url, settings)
            doc_id = source_to_doc_id(url)
            summary = ingest_document_texts(settings, store, ollama, docs=[(doc_id, url, text)])
            latency_ms = (time.perf_counter() - started) * 1000
            update_ingestion_job(
                settings.sqlite_path,
                job_id=job_id,
                status="success",
                attempt_count=attempt,
                latency_ms=latency_ms,
                summary=summary,
            )
            record_ingested_source(settings.sqlite_path, source_type="link", source=url, doc_id=doc_id)
            return
        except Exception as exc:
            last_error = str(exc)
            if attempt >= max_attempts:
                break
            backoff = settings.INGEST_LINK_BACKOFF_SECONDS * (2 ** (attempt - 1))
            time.sleep(backoff)
    latency_ms = (time.perf_counter() - started) * 1000
    update_ingestion_job(
        settings.sqlite_path,
        job_id=job_id,
        status="error",
        attempt_count=attempt,
        latency_ms=latency_ms,
        error=last_error or "Unknown link ingestion error",
    )


@router.post("/ingest/upload", response_model=IngestJobAccepted, status_code=202)
async def ingest_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    _: None = Depends(require_write_access),
    settings: Settings = Depends(get_settings),
    store: ChromaVectorStore = Depends(get_store),
    ollama: OllamaClient = Depends(get_ollama),
) -> IngestJobAccepted:
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty upload.")
    if len(raw) > settings.INGEST_MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"Upload too large. Limit is {settings.INGEST_MAX_UPLOAD_BYTES} bytes.")
    filename = file.filename or "upload.txt"
    if not re.search(r"\.(pdf|md|txt)$", filename.lower()):
        raise HTTPException(status_code=400, detail="Unsupported upload extension. Use .pdf, .md, or .txt.")
    job_id = create_ingestion_job(settings.sqlite_path, source_type="upload", source=filename, max_attempts=1)
    background_tasks.add_task(
        _run_upload_ingest_job,
        job_id=job_id,
        filename=filename,
        raw=raw,
        settings=settings,
        store=store,
        ollama=ollama,
    )
    return IngestJobAccepted(job_id=job_id, status="queued")


@router.post("/ingest/link", response_model=IngestJobAccepted, status_code=202)
def ingest_link(
    background_tasks: BackgroundTasks,
    payload: IngestLinkRequest,
    _: None = Depends(require_write_access),
    settings: Settings = Depends(get_settings),
    store: ChromaVectorStore = Depends(get_store),
    ollama: OllamaClient = Depends(get_ollama),
) -> IngestJobAccepted:
    try:
        validate_ingest_url(payload.url, settings)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Rejected link: {exc}") from exc
    max_attempts = max(1, settings.INGEST_LINK_MAX_RETRIES + 1)
    job_id = create_ingestion_job(settings.sqlite_path, source_type="link", source=payload.url, max_attempts=max_attempts)
    background_tasks.add_task(
        _run_link_ingest_job,
        job_id=job_id,
        url=payload.url,
        settings=settings,
        store=store,
        ollama=ollama,
    )
    return IngestJobAccepted(job_id=job_id, status="queued")


@router.get("/ingest/jobs/{job_id}", response_model=IngestJobStatus)
def ingestion_job_status(job_id: int, settings: Settings = Depends(get_settings)) -> IngestJobStatus:
    row = get_ingestion_job(settings.sqlite_path, job_id=job_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Ingestion job not found.")
    return IngestJobStatus(**row)


@router.get("/ingest/jobs", response_model=IngestJobListResponse)
def ingestion_job_list(limit: int = 20, settings: Settings = Depends(get_settings)) -> IngestJobListResponse:
    safe_limit = max(1, min(limit, 100))
    jobs = list_ingestion_jobs(settings.sqlite_path, limit=safe_limit)
    return IngestJobListResponse(jobs=[IngestJobStatus(**job) for job in jobs])


@router.post("/ingest/reset", response_model=ResetIngestionResponse)
def ingestion_reset(
    payload: ResetIngestionRequest,
    _: None = Depends(require_write_access),
    settings: Settings = Depends(get_settings),
    store: ChromaVectorStore = Depends(get_store),
) -> ResetIngestionResponse:
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="Reset requires confirm=true.")
    count = store.reset_collection()
    sources_cleared = clear_ingested_sources(settings.sqlite_path)
    state = mark_index_reset(settings.sqlite_path)
    return ResetIngestionResponse(
        status="ok",
        vector_count=count,
        sources_cleared=sources_cleared,
        last_reset_utc=state["last_reset_utc"],
        reset_count=int(state["reset_count"]),
        message="Vector index reset completed.",
    )


@router.get("/ingest/sources", response_model=IngestedSourcesResponse)
def ingestion_sources(limit: int = 100, settings: Settings = Depends(get_settings)) -> IngestedSourcesResponse:
    items = list_ingested_sources(settings.sqlite_path, limit=limit)
    state = get_index_state(settings.sqlite_path)
    return IngestedSourcesResponse(
        total_sources=len(items),
        last_reset_utc=state["last_reset_utc"],
        reset_count=int(state["reset_count"]),
        items=[IngestedSourceItem(**item) for item in items],
    )
