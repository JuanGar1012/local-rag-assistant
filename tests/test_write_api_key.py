from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.dependencies import get_ollama, get_store
from app.main import app
from app.rag.vector_store import ChromaVectorStore


class FakeOllama:
    def list_models(self) -> list[str]:
        return ["llama3.2:1b", "llama3.2:3b"]


def test_write_endpoints_require_api_key_when_configured(tmp_path: Path) -> None:
    db = tmp_path / "app.db"

    def override_settings() -> Settings:
        return Settings(
            SQLITE_PATH=str(db),
            CHROMA_DIR=str(tmp_path / "chroma"),
            WRITE_API_KEY="secret-key",
        )

    def override_store() -> ChromaVectorStore:
        return ChromaVectorStore(override_settings())

    app.dependency_overrides[get_settings] = override_settings
    app.dependency_overrides[get_store] = override_store
    app.dependency_overrides[get_ollama] = lambda: FakeOllama()
    client = TestClient(app)

    no_key = client.post("/ingest/reset", json={"confirm": True})
    bad_key = client.post("/models/select", json={"chat_model": "llama3.2:1b"}, headers={"X-API-Key": "nope"})
    good_key = client.post("/models/select", json={"chat_model": "llama3.2:1b"}, headers={"X-API-Key": "secret-key"})

    app.dependency_overrides.clear()

    assert no_key.status_code == 401
    assert bad_key.status_code == 401
    assert good_key.status_code == 200
