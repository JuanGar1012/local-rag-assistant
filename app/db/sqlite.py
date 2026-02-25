import json
import sqlite3
from pathlib import Path
from statistics import median
from typing import Any


def _get_conn(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path) -> None:
    with _get_conn(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS request_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                request_id TEXT,
                method TEXT NOT NULL,
                path TEXT NOT NULL,
                status_code INTEGER NOT NULL,
                latency_ms REAL NOT NULL,
                success INTEGER NOT NULL,
                prompt_tokens INTEGER,
                completion_tokens INTEGER,
                total_tokens INTEGER,
                error TEXT
            );

            CREATE TABLE IF NOT EXISTS retrieval_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                request_id TEXT,
                source TEXT NOT NULL,
                query_text TEXT NOT NULL,
                top_k INTEGER NOT NULL,
                hit INTEGER NOT NULL,
                recall_at_k REAL NOT NULL DEFAULT 0.0,
                recall_at_5 REAL NOT NULL DEFAULT 0.0,
                citations_json TEXT NOT NULL,
                retrieved_doc_ids_json TEXT NOT NULL,
                error TEXT
            );

            CREATE TABLE IF NOT EXISTS eval_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                total_cases INTEGER NOT NULL,
                retrieval_hit_rate REAL NOT NULL,
                recall_at_k REAL NOT NULL,
                recall_at_5 REAL NOT NULL DEFAULT 0.0,
                groundedness_proxy REAL NOT NULL DEFAULT 0.0,
                eval_pass_rate REAL NOT NULL,
                eval_coverage REAL NOT NULL DEFAULT 0.0,
                latency_p50_ms REAL NOT NULL,
                latency_p95_ms REAL NOT NULL,
                metrics_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS ingestion_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                updated_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                source_type TEXT NOT NULL,
                source TEXT NOT NULL,
                status TEXT NOT NULL,
                attempt_count INTEGER NOT NULL DEFAULT 0,
                max_attempts INTEGER NOT NULL DEFAULT 1,
                latency_ms REAL,
                summary_json TEXT,
                error TEXT
            );

            CREATE TABLE IF NOT EXISTS ingested_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ingested_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                source_type TEXT NOT NULL,
                source TEXT NOT NULL,
                doc_id TEXT NOT NULL,
                UNIQUE(source, doc_id)
            );

            CREATE TABLE IF NOT EXISTS index_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                last_reset_utc TEXT,
                reset_count INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            );

            CREATE TABLE IF NOT EXISTS query_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                request_id TEXT,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                citations_json TEXT NOT NULL,
                retrieved_doc_ids_json TEXT NOT NULL,
                latency_ms REAL NOT NULL,
                top_k INTEGER,
                correctness_probability REAL,
                chat_model TEXT
            );

            CREATE TABLE IF NOT EXISTS query_run_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                query_run_id INTEGER NOT NULL UNIQUE,
                is_correct INTEGER NOT NULL,
                note TEXT,
                FOREIGN KEY(query_run_id) REFERENCES query_runs(id) ON DELETE CASCADE
            );
            """
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO index_state (id, last_reset_utc, reset_count)
            VALUES (1, NULL, 0)
            """
        )
        ingestion_cols = {row["name"] for row in conn.execute("PRAGMA table_info(ingestion_jobs)").fetchall()}
        if "attempt_count" not in ingestion_cols:
            conn.execute("ALTER TABLE ingestion_jobs ADD COLUMN attempt_count INTEGER NOT NULL DEFAULT 0")
        if "max_attempts" not in ingestion_cols:
            conn.execute("ALTER TABLE ingestion_jobs ADD COLUMN max_attempts INTEGER NOT NULL DEFAULT 1")
        if "latency_ms" not in ingestion_cols:
            conn.execute("ALTER TABLE ingestion_jobs ADD COLUMN latency_ms REAL")

        request_cols = {row["name"] for row in conn.execute("PRAGMA table_info(request_logs)").fetchall()}
        if "request_id" not in request_cols:
            conn.execute("ALTER TABLE request_logs ADD COLUMN request_id TEXT")
        if "prompt_tokens" not in request_cols:
            conn.execute("ALTER TABLE request_logs ADD COLUMN prompt_tokens INTEGER")
        if "completion_tokens" not in request_cols:
            conn.execute("ALTER TABLE request_logs ADD COLUMN completion_tokens INTEGER")
        if "total_tokens" not in request_cols:
            conn.execute("ALTER TABLE request_logs ADD COLUMN total_tokens INTEGER")

        eval_cols = {row["name"] for row in conn.execute("PRAGMA table_info(eval_runs)").fetchall()}
        if "recall_at_5" not in eval_cols:
            conn.execute("ALTER TABLE eval_runs ADD COLUMN recall_at_5 REAL NOT NULL DEFAULT 0.0")
        if "groundedness_proxy" not in eval_cols:
            conn.execute("ALTER TABLE eval_runs ADD COLUMN groundedness_proxy REAL NOT NULL DEFAULT 0.0")
        if "eval_coverage" not in eval_cols:
            conn.execute("ALTER TABLE eval_runs ADD COLUMN eval_coverage REAL NOT NULL DEFAULT 0.0")

        retrieval_cols = {row["name"] for row in conn.execute("PRAGMA table_info(retrieval_events)").fetchall()}
        if "error" not in retrieval_cols:
            conn.execute("ALTER TABLE retrieval_events ADD COLUMN error TEXT")

        query_run_cols = {row["name"] for row in conn.execute("PRAGMA table_info(query_runs)").fetchall()}
        if "top_k" not in query_run_cols:
            conn.execute("ALTER TABLE query_runs ADD COLUMN top_k INTEGER")
        if "correctness_probability" not in query_run_cols:
            conn.execute("ALTER TABLE query_runs ADD COLUMN correctness_probability REAL")
        if "chat_model" not in query_run_cols:
            conn.execute("ALTER TABLE query_runs ADD COLUMN chat_model TEXT")


def log_request(
    db_path: Path,
    *,
    method: str,
    path: str,
    status_code: int,
    latency_ms: float,
    success: bool,
    request_id: str | None = None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    total_tokens: int | None = None,
    error: str | None,
) -> None:
    params = (
        request_id,
        method,
        path,
        status_code,
        latency_ms,
        1 if success else 0,
        prompt_tokens,
        completion_tokens,
        total_tokens,
        error,
    )
    sql = """
        INSERT INTO request_logs (
            request_id, method, path, status_code, latency_ms, success,
            prompt_tokens, completion_tokens, total_tokens, error
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    try:
        with _get_conn(db_path) as conn:
            conn.execute(sql, params)
    except sqlite3.OperationalError as exc:
        if "no such table" not in str(exc).lower():
            raise
        init_db(db_path)
        with _get_conn(db_path) as conn:
            conn.execute(sql, params)


def log_retrieval_event(
    db_path: Path,
    *,
    request_id: str | None,
    source: str,
    query_text: str,
    top_k: int,
    hit: bool,
    recall_at_k: float,
    recall_at_5: float,
    citations: list[dict[str, Any]],
    retrieved_doc_ids: list[str],
    error: str | None = None,
) -> None:
    with _get_conn(db_path) as conn:
        conn.execute(
            """
            INSERT INTO retrieval_events (
                request_id, source, query_text, top_k, hit, recall_at_k, recall_at_5,
                citations_json, retrieved_doc_ids_json, error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request_id,
                source,
                query_text,
                top_k,
                1 if hit else 0,
                recall_at_k,
                recall_at_5,
                json.dumps(citations),
                json.dumps(retrieved_doc_ids),
                error,
            ),
        )


def log_eval_run(
    db_path: Path,
    *,
    total_cases: int,
    retrieval_hit_rate: float,
    recall_at_k: float,
    recall_at_5: float,
    groundedness_proxy: float,
    eval_pass_rate: float,
    eval_coverage: float,
    latency_p50_ms: float,
    latency_p95_ms: float,
    metrics: dict[str, Any],
) -> None:
    with _get_conn(db_path) as conn:
        conn.execute(
            """
            INSERT INTO eval_runs (
                total_cases, retrieval_hit_rate, recall_at_k, recall_at_5,
                groundedness_proxy, eval_pass_rate, eval_coverage,
                latency_p50_ms, latency_p95_ms, metrics_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                total_cases,
                retrieval_hit_rate,
                recall_at_k,
                recall_at_5,
                groundedness_proxy,
                eval_pass_rate,
                eval_coverage,
                latency_p50_ms,
                latency_p95_ms,
                json.dumps(metrics),
            ),
        )


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    index = (len(ordered) - 1) * percentile
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    if lower == upper:
        return ordered[lower]
    weight = index - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def request_metrics(db_path: Path, path_filter: str = "/query") -> dict[str, Any]:
    with _get_conn(db_path) as conn:
        rows = conn.execute(
            "SELECT latency_ms, success FROM request_logs WHERE path = ?",
            (path_filter,),
        ).fetchall()
    latencies = [float(row["latency_ms"]) for row in rows]
    successes = sum(int(row["success"]) for row in rows)
    total = len(rows)
    errors = total - successes
    return {
        "total_requests": total,
        "success_rate": (successes / total) if total else 0.0,
        "error_rate": (errors / total) if total else 0.0,
        "latency_p50_ms": median(latencies) if latencies else 0.0,
        "latency_p95_ms": _percentile(latencies, 0.95),
    }


def request_metrics_24h(db_path: Path, path_filter: str = "/query") -> dict[str, Any]:
    with _get_conn(db_path) as conn:
        rows = conn.execute(
            """
            SELECT latency_ms, success FROM request_logs
            WHERE path = ? AND ts_utc >= strftime('%Y-%m-%dT%H:%M:%fZ', 'now', '-24 hours')
            """,
            (path_filter,),
        ).fetchall()
    latencies = [float(row["latency_ms"]) for row in rows]
    successes = sum(int(row["success"]) for row in rows)
    total = len(rows)
    errors = total - successes
    return {
        "requests_24h": total,
        "success_rate": (successes / total) if total else 0.0,
        "error_rate": (errors / total) if total else 0.0,
        "latency_p95_ms": _percentile(latencies, 0.95),
    }


def latest_eval_metrics(db_path: Path) -> dict[str, Any]:
    with _get_conn(db_path) as conn:
        row = conn.execute("SELECT * FROM eval_runs ORDER BY id DESC LIMIT 1").fetchone()
    if row is None:
        return {}
    metrics = json.loads(str(row["metrics_json"]))
    metrics["eval_run_id"] = row["id"]
    metrics["eval_ts_utc"] = row["ts_utc"]
    metrics.setdefault("recall_at_5", row["recall_at_5"])
    metrics.setdefault("eval_pass_rate", row["eval_pass_rate"])
    metrics.setdefault("eval_coverage", row["eval_coverage"])
    metrics.setdefault("groundedness_proxy", row["groundedness_proxy"])
    return metrics


def create_ingestion_job(db_path: Path, *, source_type: str, source: str, max_attempts: int = 1) -> int:
    with _get_conn(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO ingestion_jobs (source_type, source, status, max_attempts)
            VALUES (?, ?, 'queued', ?)
            """,
            (source_type, source, max(1, max_attempts)),
        )
        return int(cursor.lastrowid)


def update_ingestion_job(
    db_path: Path,
    *,
    job_id: int,
    status: str,
    attempt_count: int | None = None,
    latency_ms: float | None = None,
    summary: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    with _get_conn(db_path) as conn:
        conn.execute(
            """
            UPDATE ingestion_jobs
            SET status = ?,
                summary_json = ?,
                error = ?,
                attempt_count = COALESCE(?, attempt_count),
                latency_ms = COALESCE(?, latency_ms),
                updated_utc = (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            WHERE id = ?
            """,
            (status, json.dumps(summary) if summary else None, error, attempt_count, latency_ms, job_id),
        )


def get_ingestion_job(db_path: Path, *, job_id: int) -> dict[str, Any] | None:
    with _get_conn(db_path) as conn:
        row = conn.execute("SELECT * FROM ingestion_jobs WHERE id = ?", (job_id,)).fetchone()
    if row is None:
        return None
    summary = json.loads(str(row["summary_json"])) if row["summary_json"] else None
    return {
        "job_id": int(row["id"]),
        "created_utc": str(row["ts_utc"]),
        "updated_utc": str(row["updated_utc"]),
        "source_type": str(row["source_type"]),
        "source": str(row["source"]),
        "status": str(row["status"]),
        "attempt_count": int(row["attempt_count"]) if row["attempt_count"] is not None else 0,
        "max_attempts": int(row["max_attempts"]) if row["max_attempts"] is not None else 1,
        "latency_ms": float(row["latency_ms"]) if row["latency_ms"] is not None else None,
        "summary": summary,
        "error": row["error"],
    }


def list_ingestion_jobs(db_path: Path, *, limit: int = 20) -> list[dict[str, Any]]:
    with _get_conn(db_path) as conn:
        rows = conn.execute("SELECT * FROM ingestion_jobs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    jobs: list[dict[str, Any]] = []
    for row in rows:
        summary = json.loads(str(row["summary_json"])) if row["summary_json"] else None
        jobs.append(
            {
                "job_id": int(row["id"]),
                "created_utc": str(row["ts_utc"]),
                "updated_utc": str(row["updated_utc"]),
                "source_type": str(row["source_type"]),
                "source": str(row["source"]),
                "status": str(row["status"]),
                "attempt_count": int(row["attempt_count"]) if row["attempt_count"] is not None else 0,
                "max_attempts": int(row["max_attempts"]) if row["max_attempts"] is not None else 1,
                "latency_ms": float(row["latency_ms"]) if row["latency_ms"] is not None else None,
                "summary": summary,
                "error": row["error"],
            }
        )
    return jobs


def ingestion_metrics(db_path: Path) -> dict[str, Any]:
    with _get_conn(db_path) as conn:
        rows = conn.execute("SELECT status, attempt_count, latency_ms FROM ingestion_jobs").fetchall()
    total = len(rows)
    if total == 0:
        return {
            "total_jobs": 0,
            "success_rate": 0.0,
            "error_rate": 0.0,
            "latency_p50_ms": 0.0,
            "latency_p95_ms": 0.0,
            "avg_attempts": 0.0,
            "retried_jobs": 0,
        }
    successes = sum(1 for row in rows if str(row["status"]) == "success")
    errors = sum(1 for row in rows if str(row["status"]) == "error")
    attempts = [int(row["attempt_count"] or 0) for row in rows]
    retried_jobs = sum(1 for a in attempts if a > 1)
    latencies = [float(row["latency_ms"]) for row in rows if row["latency_ms"] is not None]
    return {
        "total_jobs": total,
        "success_rate": successes / total,
        "error_rate": errors / total,
        "latency_p50_ms": median(latencies) if latencies else 0.0,
        "latency_p95_ms": _percentile(latencies, 0.95),
        "avg_attempts": (sum(attempts) / total) if attempts else 0.0,
        "retried_jobs": retried_jobs,
    }


def request_metrics_history(
    db_path: Path,
    *,
    hours: int = 24,
    bucket_minutes: int = 15,
    path_filter: str = "/query",
) -> list[dict[str, Any]]:
    safe_hours = max(1, min(hours, 168))
    safe_bucket = max(1, min(bucket_minutes, 60))
    with _get_conn(db_path) as conn:
        rows = conn.execute(
            """
            SELECT ts_utc, latency_ms, success
            FROM request_logs
            WHERE path = ?
              AND ts_utc >= strftime('%Y-%m-%dT%H:%M:%fZ', 'now', ?)
            ORDER BY ts_utc ASC
            """,
            (path_filter, f"-{safe_hours} hours"),
        ).fetchall()

    buckets: dict[int, dict[str, Any]] = {}
    for row in rows:
        ts = str(row["ts_utc"])
        try:
            epoch = int(ts[:19].replace("T", " ").replace("Z", "").replace("-", "").replace(":", "").replace(" ", ""))
        except Exception:
            # Fallback for malformed timestamps.
            continue
        # Bucket by minute boundary using string components to avoid timezone parsing issues.
        minute = int(ts[14:16]) if len(ts) >= 16 else 0
        bucket_minute = minute - (minute % safe_bucket)
        bucket_key = int(ts[0:4] + ts[5:7] + ts[8:10] + ts[11:13] + f"{bucket_minute:02d}")
        if bucket_key not in buckets:
            bucket_ts = f"{ts[0:14]}{bucket_minute:02d}:00Z"
            buckets[bucket_key] = {
                "bucket_utc": bucket_ts,
                "requests": 0,
                "successes": 0,
                "latencies": [],
            }
        bucket = buckets[bucket_key]
        bucket["requests"] += 1
        bucket["successes"] += int(row["success"])
        bucket["latencies"].append(float(row["latency_ms"]))
        _ = epoch  # Keep explicit local variable use for clarity.

    points: list[dict[str, Any]] = []
    for key in sorted(buckets.keys()):
        bucket = buckets[key]
        req = int(bucket["requests"])
        succ = int(bucket["successes"])
        lats = list(bucket["latencies"])
        points.append(
            {
                "bucket_utc": bucket["bucket_utc"],
                "requests": req,
                "success_rate": (succ / req) if req else 0.0,
                "error_rate": (1 - (succ / req)) if req else 0.0,
                "latency_p95_ms": _percentile(lats, 0.95),
            }
        )
    return points


def eval_metrics_history(db_path: Path, *, limit: int = 30) -> list[dict[str, Any]]:
    safe_limit = max(1, min(limit, 200))
    with _get_conn(db_path) as conn:
        rows = conn.execute(
            """
            SELECT ts_utc, recall_at_5, eval_pass_rate, eval_coverage, latency_p95_ms
            FROM eval_runs
            ORDER BY id DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()
    points = [
        {
            "ts_utc": str(row["ts_utc"]),
            "recall_at_5": float(row["recall_at_5"]),
            "eval_pass_rate": float(row["eval_pass_rate"]),
            "eval_coverage": float(row["eval_coverage"]),
            "latency_p95_ms": float(row["latency_p95_ms"]),
        }
        for row in reversed(rows)
    ]
    return points


def recent_query_history(db_path: Path, *, limit: int = 20) -> list[dict[str, Any]]:
    safe_limit = max(1, min(limit, 200))
    with _get_conn(db_path) as conn:
        rows = conn.execute(
            """
            SELECT ts_utc, query_text, top_k, hit, error
            FROM retrieval_events
            WHERE source = 'live_query'
            ORDER BY id DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()
    return [
        {
            "ts_utc": str(row["ts_utc"]),
            "question": str(row["query_text"]),
            "top_k": int(row["top_k"]),
            "hit": bool(int(row["hit"])),
            "error": str(row["error"]) if row["error"] is not None else None,
        }
        for row in rows
    ]


def record_ingested_source(db_path: Path, *, source_type: str, source: str, doc_id: str) -> None:
    with _get_conn(db_path) as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO ingested_sources (source_type, source, doc_id)
            VALUES (?, ?, ?)
            """,
            (source_type, source, doc_id),
        )


def list_ingested_sources(db_path: Path, *, limit: int = 200) -> list[dict[str, Any]]:
    safe_limit = max(1, min(limit, 1000))
    with _get_conn(db_path) as conn:
        rows = conn.execute(
            """
            SELECT id, ingested_utc, source_type, source, doc_id
            FROM ingested_sources
            ORDER BY id DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()
    return [
        {
            "id": int(row["id"]),
            "ingested_utc": str(row["ingested_utc"]),
            "source_type": str(row["source_type"]),
            "source": str(row["source"]),
            "doc_id": str(row["doc_id"]),
        }
        for row in rows
    ]


def clear_ingested_sources(db_path: Path) -> int:
    with _get_conn(db_path) as conn:
        count_row = conn.execute("SELECT COUNT(*) AS c FROM ingested_sources").fetchone()
        cleared = int(count_row["c"]) if count_row is not None else 0
        conn.execute("DELETE FROM ingested_sources")
    return cleared


def mark_index_reset(db_path: Path) -> dict[str, Any]:
    with _get_conn(db_path) as conn:
        conn.execute(
            """
            UPDATE index_state
            SET last_reset_utc = (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                reset_count = reset_count + 1
            WHERE id = 1
            """
        )
        row = conn.execute("SELECT last_reset_utc, reset_count FROM index_state WHERE id = 1").fetchone()
    return {
        "last_reset_utc": str(row["last_reset_utc"]) if row and row["last_reset_utc"] else None,
        "reset_count": int(row["reset_count"]) if row else 0,
    }


def get_index_state(db_path: Path) -> dict[str, Any]:
    with _get_conn(db_path) as conn:
        row = conn.execute("SELECT last_reset_utc, reset_count FROM index_state WHERE id = 1").fetchone()
    return {
        "last_reset_utc": str(row["last_reset_utc"]) if row and row["last_reset_utc"] else None,
        "reset_count": int(row["reset_count"]) if row else 0,
    }


def get_app_setting(db_path: Path, *, key: str) -> str | None:
    try:
        with _get_conn(db_path) as conn:
            row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    except sqlite3.OperationalError as exc:
        if "no such table" not in str(exc).lower():
            raise
        init_db(db_path)
        with _get_conn(db_path) as conn:
            row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    if row is None or row["value"] is None:
        return None
    return str(row["value"])


def set_app_setting(db_path: Path, *, key: str, value: str) -> None:
    sql = """
        INSERT INTO app_settings (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value,
            updated_utc = (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
    """
    try:
        with _get_conn(db_path) as conn:
            conn.execute(sql, (key, value))
    except sqlite3.OperationalError as exc:
        if "no such table" not in str(exc).lower():
            raise
        init_db(db_path)
        with _get_conn(db_path) as conn:
            conn.execute(sql, (key, value))


def log_query_run(
    db_path: Path,
    *,
    request_id: str | None,
    question: str,
    answer: str,
    citations: list[dict[str, Any]],
    retrieved_doc_ids: list[str],
    latency_ms: float,
    top_k: int | None = None,
    correctness_probability: float | None = None,
    chat_model: str | None = None,
) -> None:
    with _get_conn(db_path) as conn:
        conn.execute(
            """
            INSERT INTO query_runs (
                request_id, question, answer, citations_json, retrieved_doc_ids_json, latency_ms, top_k,
                correctness_probability, chat_model
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request_id,
                question,
                answer,
                json.dumps(citations),
                json.dumps(retrieved_doc_ids),
                latency_ms,
                top_k,
                correctness_probability,
                chat_model,
            ),
        )


def list_query_runs(db_path: Path, *, limit: int = 50) -> list[dict[str, Any]]:
    safe_limit = max(1, min(limit, 500))
    with _get_conn(db_path) as conn:
        rows = conn.execute(
            """
            SELECT
                qr.id,
                qr.ts_utc,
                qr.request_id,
                qr.question,
                qr.answer,
                qr.citations_json,
                qr.retrieved_doc_ids_json,
                qr.latency_ms,
                qr.top_k,
                qr.correctness_probability,
                qr.chat_model,
                qf.is_correct AS feedback_is_correct,
                qf.note AS feedback_note,
                qf.ts_utc AS feedback_ts_utc
            FROM query_runs qr
            LEFT JOIN query_run_feedback qf ON qf.query_run_id = qr.id
            ORDER BY qr.id DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()
    result: list[dict[str, Any]] = []
    for row in rows:
        result.append(
            {
                "id": int(row["id"]),
                "ts_utc": str(row["ts_utc"]),
                "request_id": str(row["request_id"]) if row["request_id"] else None,
                "question": str(row["question"]),
                "answer": str(row["answer"]),
                "citations": json.loads(str(row["citations_json"])) if row["citations_json"] else [],
                "retrieved_doc_ids": json.loads(str(row["retrieved_doc_ids_json"])) if row["retrieved_doc_ids_json"] else [],
                "latency_ms": float(row["latency_ms"]),
                "top_k": int(row["top_k"]) if row["top_k"] is not None else None,
                "correctness_probability": float(row["correctness_probability"]) if row["correctness_probability"] is not None else None,
                "chat_model": str(row["chat_model"]) if row["chat_model"] is not None else None,
                "feedback_is_correct": bool(int(row["feedback_is_correct"])) if row["feedback_is_correct"] is not None else None,
                "feedback_note": str(row["feedback_note"]) if row["feedback_note"] is not None else None,
                "feedback_ts_utc": str(row["feedback_ts_utc"]) if row["feedback_ts_utc"] is not None else None,
            }
        )
    return result


def query_run_confidence_24h(db_path: Path) -> dict[str, Any]:
    with _get_conn(db_path) as conn:
        row = conn.execute(
            """
            SELECT AVG(correctness_probability) AS avg_confidence, COUNT(*) AS n
            FROM query_runs
            WHERE ts_utc >= strftime('%Y-%m-%dT%H:%M:%fZ', 'now', '-24 hours')
              AND correctness_probability IS NOT NULL
            """
        ).fetchone()
    avg_conf = float(row["avg_confidence"]) if row and row["avg_confidence"] is not None else 0.0
    samples = int(row["n"]) if row and row["n"] is not None else 0
    return {"correctness_confidence_avg_24h": avg_conf, "confidence_samples_24h": samples}


def upsert_query_run_feedback(
    db_path: Path,
    *,
    query_run_id: int,
    is_correct: bool,
    note: str | None = None,
) -> dict[str, Any]:
    with _get_conn(db_path) as conn:
        exists = conn.execute("SELECT 1 FROM query_runs WHERE id = ?", (query_run_id,)).fetchone()
        if exists is None:
            raise ValueError("Query run not found.")
        conn.execute(
            """
            INSERT INTO query_run_feedback (query_run_id, is_correct, note)
            VALUES (?, ?, ?)
            ON CONFLICT(query_run_id) DO UPDATE SET
                is_correct = excluded.is_correct,
                note = excluded.note,
                ts_utc = (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            """,
            (query_run_id, 1 if is_correct else 0, note),
        )
        row = conn.execute(
            "SELECT query_run_id, is_correct, note, ts_utc FROM query_run_feedback WHERE query_run_id = ?",
            (query_run_id,),
        ).fetchone()
    return {
        "query_run_id": int(row["query_run_id"]) if row else query_run_id,
        "is_correct": bool(int(row["is_correct"])) if row else is_correct,
        "note": str(row["note"]) if row and row["note"] is not None else None,
        "ts_utc": str(row["ts_utc"]) if row and row["ts_utc"] is not None else None,
    }


def query_run_feedback_24h(db_path: Path) -> dict[str, Any]:
    with _get_conn(db_path) as conn:
        row = conn.execute(
            """
            SELECT AVG(CAST(is_correct AS REAL)) AS accuracy_rate, COUNT(*) AS n
            FROM query_run_feedback
            WHERE ts_utc >= strftime('%Y-%m-%dT%H:%M:%fZ', 'now', '-24 hours')
            """
        ).fetchone()
    accuracy = float(row["accuracy_rate"]) if row and row["accuracy_rate"] is not None else 0.0
    samples = int(row["n"]) if row and row["n"] is not None else 0
    return {"feedback_accuracy_rate_24h": accuracy, "feedback_samples_24h": samples}
