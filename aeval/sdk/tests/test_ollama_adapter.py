"""Tests for Ollama adapter (mocked HTTP)."""

from unittest.mock import patch, MagicMock

import httpx
import pytest

from aeval.core.model import ModelInfo
from aeval.adapters.ollama import OllamaModel, list_ollama_models, check_ollama_health


def _mock_response(status_code: int, **kwargs) -> httpx.Response:
    """Create a mock httpx.Response that supports raise_for_status()."""
    request = httpx.Request("GET", "http://test")
    return httpx.Response(status_code, request=request, **kwargs)


@pytest.fixture
def mock_config():
    """Patch config loading to avoid needing aeval.yaml."""
    with patch("aeval.adapters.ollama.AevalConfig") as mock:
        config = MagicMock()
        config.ollama.host = "http://localhost:11434"
        config.ollama.timeout = 30
        config.ollama.keep_alive = "5m"
        mock.load.return_value = config
        yield config


class TestOllamaModel:
    def test_generate_single_prompt(self, mock_config):
        model = OllamaModel("llama3", host="http://localhost:11434", timeout=30)

        mock_resp = _mock_response(
            200,
            json={
                "model": "llama3",
                "message": {"role": "assistant", "content": "Paris"},
                "eval_count": 5,
                "total_duration": 1000000,
            },
        )

        with patch.object(model._client, "post", return_value=mock_resp) as mock_post:
            results = model.generate("What is the capital of France?")

        assert len(results) == 1
        assert results[0].text == "Paris"
        assert results[0].model == "llama3"
        assert results[0].tokens_used == 5

        call_args = mock_post.call_args
        assert call_args[0][0] == "/api/chat"
        payload = call_args[1]["json"]
        assert payload["model"] == "llama3"
        assert payload["stream"] is False

    def test_generate_multiple_prompts(self, mock_config):
        model = OllamaModel("llama3", host="http://localhost:11434", timeout=30)

        mock_resp = _mock_response(
            200,
            json={
                "model": "llama3",
                "message": {"role": "assistant", "content": "Answer"},
                "eval_count": 3,
            },
        )

        with patch.object(model._client, "post", return_value=mock_resp):
            results = model.generate(["Q1", "Q2", "Q3"])

        assert len(results) == 3

    def test_generate_with_system(self, mock_config):
        model = OllamaModel("llama3", host="http://localhost:11434", timeout=30)

        mock_resp = _mock_response(
            200,
            json={"model": "llama3", "message": {"content": "ok"}},
        )

        with patch.object(model._client, "post", return_value=mock_resp) as mock_post:
            model.generate("hi", system="You are helpful")

        payload = mock_post.call_args[1]["json"]
        messages = payload["messages"]
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are helpful"

    def test_complete(self, mock_config):
        model = OllamaModel("llama3", host="http://localhost:11434", timeout=30)

        mock_resp = _mock_response(
            200,
            json={"model": "llama3", "response": "completed text", "eval_count": 10},
        )

        with patch.object(model._client, "post", return_value=mock_resp) as mock_post:
            results = model.complete("Continue this: ")

        assert len(results) == 1
        assert results[0].text == "completed text"
        assert mock_post.call_args[0][0] == "/api/generate"

    def test_health_check_success(self, mock_config):
        model = OllamaModel("llama3", host="http://localhost:11434", timeout=30)

        mock_resp = _mock_response(200, text="Ollama is running")
        with patch.object(model._client, "get", return_value=mock_resp):
            assert model.health_check() is True

    def test_health_check_failure(self, mock_config):
        model = OllamaModel("llama3", host="http://localhost:11434", timeout=30)

        with patch.object(model._client, "get", side_effect=httpx.ConnectError("refused")):
            assert model.health_check() is False

    def test_name_property(self, mock_config):
        model = OllamaModel("brain-analyst-ft", host="http://localhost:11434", timeout=30)
        assert model.name == "brain-analyst-ft"


class TestListModels:
    def test_list_models(self, mock_config):
        mock_resp = _mock_response(
            200,
            json={
                "models": [
                    {
                        "name": "llama3:latest",
                        "digest": "abc123def456",
                        "details": {
                            "family": "llama",
                            "parameter_size": "8.0B",
                            "quantization_level": "Q4_0",
                            "families": ["llama"],
                        },
                    },
                    {
                        "name": "llava:7b",
                        "digest": "xyz789",
                        "details": {
                            "family": "llama",
                            "parameter_size": "7.0B",
                            "quantization_level": "Q4_0",
                            "families": ["llama", "clip"],
                        },
                    },
                ]
            },
        )

        with patch("aeval.adapters.ollama.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            models = list_ollama_models("http://localhost:11434")

        assert len(models) == 2
        assert models[0].name == "llama3:latest"
        assert models[0].family == "llama"
        assert models[0].multimodal is False
        assert models[1].name == "llava:7b"
        assert models[1].multimodal is True


class TestHealthCheck:
    def test_healthy(self, mock_config):
        mock_resp = _mock_response(200, text="Ollama is running")

        with patch("aeval.adapters.ollama.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            assert check_ollama_health("http://localhost:11434") is True

    def test_unhealthy(self, mock_config):
        with patch("aeval.adapters.ollama.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.side_effect = httpx.ConnectError("refused")
            mock_client_cls.return_value = mock_client

            assert check_ollama_health("http://localhost:11434") is False
