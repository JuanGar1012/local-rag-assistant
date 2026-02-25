from fastapi.testclient import TestClient

from app.main import app


def test_models_endpoint_smoke() -> None:
    client = TestClient(app)
    response = client.get("/models")
    assert response.status_code == 200
    payload = response.json()
    assert "chat_model" in payload
    assert "embed_model" in payload
    assert payload["chat_model"]
    assert payload["embed_model"]
