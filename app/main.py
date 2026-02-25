from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.metrics import router as metrics_router
from app.api.routes import router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.sqlite import init_db
from app.middleware.request_logging import RequestLoggingMiddleware

configure_logging()
settings = get_settings()

@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db(settings.sqlite_path)
    yield


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)
app.include_router(router)
app.include_router(metrics_router)
app.add_middleware(RequestLoggingMiddleware, settings=settings)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
