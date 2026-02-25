import logging
from typing import Any

import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)


class OllamaClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client = httpx.Client(timeout=settings.OLLAMA_TIMEOUT_SECONDS)

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        payload = {"model": self.settings.OLLAMA_EMBED_MODEL, "input": texts}
        response = self._client.post(f"{self.settings.OLLAMA_BASE_URL}/api/embed", json=payload)
        if response.status_code == 404:
            # Compatibility fallback for older Ollama versions.
            legacy_embeddings: list[list[float]] = []
            for text in texts:
                legacy_resp = self._client.post(
                    f"{self.settings.OLLAMA_BASE_URL}/api/embeddings",
                    json={"model": self.settings.OLLAMA_EMBED_MODEL, "prompt": text},
                )
                legacy_resp.raise_for_status()
                legacy_embeddings.append(legacy_resp.json()["embedding"])
            return legacy_embeddings
        response.raise_for_status()
        data = response.json()
        embeddings = data.get("embeddings")
        if not isinstance(embeddings, list):
            raise RuntimeError("Ollama embed response missing embeddings list.")
        return embeddings

    def list_models(self) -> list[str]:
        response = self._client.get(f"{self.settings.OLLAMA_BASE_URL}/api/tags")
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        models = data.get("models")
        if not isinstance(models, list):
            return []
        names: list[str] = []
        for item in models:
            if isinstance(item, dict) and isinstance(item.get("name"), str):
                names.append(str(item["name"]))
        return names

    def generate_with_meta(self, prompt: str, *, model: str | None = None) -> dict[str, Any]:
        response = self._client.post(
            f"{self.settings.OLLAMA_BASE_URL}/api/generate",
            json={
                "model": model or self.settings.OLLAMA_CHAT_MODEL,
                "prompt": prompt,
                "stream": False,
            },
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        text = data.get("response")
        if not isinstance(text, str):
            raise RuntimeError("Ollama generate response missing response text.")
        prompt_tokens = data.get("prompt_eval_count")
        completion_tokens = data.get("eval_count")
        total_tokens: int | None = None
        if isinstance(prompt_tokens, int) and isinstance(completion_tokens, int):
            total_tokens = prompt_tokens + completion_tokens
        return {
            "text": text.strip(),
            "prompt_tokens": prompt_tokens if isinstance(prompt_tokens, int) else None,
            "completion_tokens": completion_tokens if isinstance(completion_tokens, int) else None,
            "total_tokens": total_tokens,
        }

    def generate(self, prompt: str, *, model: str | None = None) -> str:
        return str(self.generate_with_meta(prompt, model=model)["text"])

    def healthcheck(self) -> bool:
        try:
            response = self._client.get(f"{self.settings.OLLAMA_BASE_URL}/api/tags")
            response.raise_for_status()
            return True
        except Exception:
            logger.exception("Ollama healthcheck failed")
            return False
