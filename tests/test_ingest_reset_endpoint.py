from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.dependencies import get_store
from app.main import app
from app.rag.models import Chunk
from app.rag.vector_store import ChromaVectorStore
from app.db.sqlite import init_db, record_ingested_source


def test_ingest_reset_endpoint_clears_vectors(tmp_path: Path) -> None:
    settings = Settings(CHROMA_DIR=str(tmp_path / "chroma_reset_test"))
    db = tmp_path / "app.db"
    init_db(db)
    store = ChromaVectorStore(settings)
    store.upsert_chunks(
        [
            Chunk(
                chunk_id="doc::chunk::0",
                text="sample",
                metadata={"doc_id": "doc", "source": "doc.txt", "chunk_index": 0},
            )
        ],
        [[0.1, 0.2, 0.3]],
    )
    assert store.count() == 1
    record_ingested_source(db, source_type="link", source="https://example.com", doc_id="doc")

    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_settings] = lambda: Settings(SQLITE_PATH=str(db), CHROMA_DIR=str(tmp_path / "chroma_reset_test"))
    client = TestClient(app)
    response = client.post("/ingest/reset", json={"confirm": True})
    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["vector_count"] == 0
    assert payload["sources_cleared"] == 1
    assert payload["reset_count"] == 1
    assert store.count() == 0
