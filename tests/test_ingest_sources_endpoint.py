from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.db.sqlite import init_db, record_ingested_source
from app.main import app


def test_ingest_sources_endpoint_smoke(tmp_path: Path) -> None:
    db = tmp_path / "app.db"
    init_db(db)
    record_ingested_source(db, source_type="link", source="https://example.com/a", doc_id="a_doc")
    record_ingested_source(db, source_type="upload", source="notes.md", doc_id="notes_doc")

    def override_settings() -> Settings:
        return Settings(SQLITE_PATH=str(db))

    app.dependency_overrides[get_settings] = override_settings
    client = TestClient(app)
    response = client.get("/ingest/sources?limit=10")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_sources"] == 2
    assert isinstance(payload["items"], list)
    assert payload["items"][0]["source"]
