from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.dependencies import get_ollama
from app.main import app


class FakeOllama:
    def list_models(self) -> list[str]:
        return ["llama3.2:1b", "llama3.2:3b"]


def test_model_select_persists_active_model(tmp_path: Path) -> None:
    db = tmp_path / "app.db"

    def override_settings() -> Settings:
        return Settings(SQLITE_PATH=str(db), OLLAMA_CHAT_MODEL="llama3.2:3b")

    app.dependency_overrides[get_settings] = override_settings
    app.dependency_overrides[get_ollama] = lambda: FakeOllama()
    client = TestClient(app)

    select = client.post("/models/select", json={"chat_model": "llama3.2:1b"})
    models = client.get("/models")
    app.dependency_overrides.clear()

    assert select.status_code == 200
    assert models.status_code == 200
    payload = models.json()
    assert payload["active_chat_model"] == "llama3.2:1b"
    assert payload["chat_model"] == "llama3.2:1b"
    assert "llama3.2:1b" in payload["available_chat_models"]
