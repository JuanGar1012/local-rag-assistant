import pytest

from app.core.config import Settings
from app.rag.ingest_service import validate_ingest_url


def test_validate_ingest_url_blocks_localhost() -> None:
    settings = Settings()
    with pytest.raises(ValueError):
        validate_ingest_url("http://localhost:8000/docs", settings)


def test_validate_ingest_url_allowlist() -> None:
    settings = Settings(INGEST_ALLOWED_HOSTS="example.com")
    validate_ingest_url("https://example.com/docs", settings)
    with pytest.raises(ValueError):
        validate_ingest_url("https://not-example.com/docs", settings)
