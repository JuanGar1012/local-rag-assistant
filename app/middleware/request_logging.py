import logging
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.config import Settings
from app.db.sqlite import log_request

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: Settings) -> None:  # type: ignore[no-untyped-def]
        super().__init__(app)
        self.settings = settings

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        request.state.request_id = str(uuid.uuid4())
        start = time.perf_counter()
        status_code = 500
        error: str | None = None
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception as exc:
            error = str(exc)
            logger.exception("Unhandled request error", extra={"path": request.url.path, "method": request.method})
            raise
        finally:
            latency_ms = (time.perf_counter() - start) * 1000
            success = status_code < 500 and error is None
            log_request(
                self.settings.sqlite_path,
                request_id=getattr(request.state, "request_id", None),
                method=request.method,
                path=request.url.path,
                status_code=status_code,
                latency_ms=latency_ms,
                success=success,
                prompt_tokens=getattr(request.state, "prompt_tokens", None),
                completion_tokens=getattr(request.state, "completion_tokens", None),
                total_tokens=getattr(request.state, "total_tokens", None),
                error=error,
            )
