"""Ollama model adapter for aeval."""

from __future__ import annotations

import base64
import time
from pathlib import Path

import httpx

from aeval.config import AevalConfig
from aeval.core.model import GenerateResponse, Model, ModelInfo


class OllamaModel(Model):
    """Model adapter for Ollama-served models.

    Connects to Ollama's HTTP API for model inference and discovery.
    """

    def __init__(
        self,
        model_name: str,
        *,
        host: str | None = None,
        timeout: int | None = None,
        keep_alive: str | None = None,
    ):
        config = AevalConfig.load()
        self._model_name = model_name
        self._host = (host or config.ollama.host).rstrip("/")
        self._timeout = timeout or config.ollama.timeout
        self._keep_alive = keep_alive or config.ollama.keep_alive
        self._client = httpx.Client(base_url=self._host, timeout=self._timeout)
        self._info: ModelInfo | None = None

    @property
    def name(self) -> str:
        return self._model_name

    @property
    def info(self) -> ModelInfo:
        if self._info is None:
            self._info = self._fetch_model_info()
        return self._info

    def generate(
        self,
        prompts: list[str] | str,
        *,
        system: str | None = None,
        images: list[str | list[str]] | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> list[GenerateResponse]:
        """Generate chat completions via Ollama POST /api/chat."""
        if isinstance(prompts, str):
            prompts = [prompts]

        results = []
        for i, prompt in enumerate(prompts):
            messages = []
            if system:
                messages.append({"role": "system", "content": system})

            user_msg: dict = {"role": "user", "content": prompt}

            # Handle images for multimodal models
            if images and i < len(images):
                img_data = images[i]
                if isinstance(img_data, str):
                    img_data = [img_data]
                user_msg["images"] = [_encode_image(img) for img in img_data]

            messages.append(user_msg)

            payload: dict = {
                "model": self._model_name,
                "messages": messages,
                "stream": False,
                "options": {"temperature": temperature},
            }
            if max_tokens is not None:
                payload["options"]["num_predict"] = max_tokens
            if self._keep_alive:
                payload["keep_alive"] = self._keep_alive

            start = time.time()
            resp = self._client.post("/api/chat", json=payload)
            resp.raise_for_status()
            elapsed_ms = (time.time() - start) * 1000

            data = resp.json()
            message = data.get("message", {})
            results.append(
                GenerateResponse(
                    text=message.get("content", ""),
                    model=data.get("model", self._model_name),
                    tokens_used=data.get("eval_count", 0),
                    latency_ms=elapsed_ms,
                    metadata={
                        "total_duration": data.get("total_duration"),
                        "load_duration": data.get("load_duration"),
                        "prompt_eval_count": data.get("prompt_eval_count"),
                    },
                )
            )

        return results

    def complete(
        self,
        prompts: list[str] | str,
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> list[GenerateResponse]:
        """Generate raw completions via Ollama POST /api/generate."""
        if isinstance(prompts, str):
            prompts = [prompts]

        results = []
        for prompt in prompts:
            payload: dict = {
                "model": self._model_name,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": temperature},
            }
            if max_tokens is not None:
                payload["options"]["num_predict"] = max_tokens
            if self._keep_alive:
                payload["keep_alive"] = self._keep_alive

            start = time.time()
            resp = self._client.post("/api/generate", json=payload)
            resp.raise_for_status()
            elapsed_ms = (time.time() - start) * 1000

            data = resp.json()
            results.append(
                GenerateResponse(
                    text=data.get("response", ""),
                    model=data.get("model", self._model_name),
                    tokens_used=data.get("eval_count", 0),
                    latency_ms=elapsed_ms,
                    metadata={
                        "total_duration": data.get("total_duration"),
                        "load_duration": data.get("load_duration"),
                        "prompt_eval_count": data.get("prompt_eval_count"),
                    },
                )
            )

        return results

    def health_check(self) -> bool:
        """Check if Ollama is reachable."""
        try:
            resp = self._client.get("/")
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

    def _fetch_model_info(self) -> ModelInfo:
        """Fetch model details from Ollama."""
        try:
            resp = self._client.post(
                "/api/show", json={"model": self._model_name}
            )
            resp.raise_for_status()
            data = resp.json()
            details = data.get("details", {})
            return ModelInfo(
                name=self._model_name,
                family=details.get("family", ""),
                parameter_size=details.get("parameter_size", ""),
                quantization=details.get("quantization_level", ""),
                multimodal="clip" in str(details.get("families", [])).lower(),
                digest=data.get("digest", ""),
            )
        except httpx.HTTPError:
            return ModelInfo(name=self._model_name)


def list_ollama_models(host: str | None = None) -> list[ModelInfo]:
    """List all models available in Ollama.

    Calls GET /api/tags on the Ollama API.
    """
    config = AevalConfig.load()
    base_url = (host or config.ollama.host).rstrip("/")
    timeout = config.ollama.timeout

    with httpx.Client(base_url=base_url, timeout=timeout) as client:
        resp = client.get("/api/tags")
        resp.raise_for_status()
        data = resp.json()

    models = []
    for m in data.get("models", []):
        details = m.get("details", {})
        families = details.get("families", [])
        models.append(
            ModelInfo(
                name=m.get("name", ""),
                family=details.get("family", ""),
                parameter_size=details.get("parameter_size", ""),
                quantization=details.get("quantization_level", ""),
                multimodal=any("clip" in f.lower() for f in families) if families else False,
                digest=m.get("digest", "")[:12],
            )
        )

    return models


def check_ollama_health(host: str | None = None) -> bool:
    """Check if Ollama is running and reachable."""
    config = AevalConfig.load()
    base_url = (host or config.ollama.host).rstrip("/")
    try:
        with httpx.Client(base_url=base_url, timeout=5) as client:
            resp = client.get("/")
            return resp.status_code == 200
    except httpx.HTTPError:
        return False


def _encode_image(image_path: str) -> str:
    """Encode an image file to base64 for Ollama multimodal input."""
    path = Path(image_path)
    if path.exists():
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    # Assume it's already base64-encoded
    return image_path
