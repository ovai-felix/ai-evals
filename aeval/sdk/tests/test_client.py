"""Tests for OrchestratorClient."""

from unittest.mock import patch, MagicMock

import httpx
import pytest

from aeval.client import OrchestratorClient


@pytest.fixture
def client():
    return OrchestratorClient("http://localhost:8081")


class TestIsReachable:
    def test_reachable(self, client):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch.object(client._client, "get", return_value=mock_resp):
            assert client.is_reachable() is True

    def test_unreachable_connection_error(self, client):
        with patch.object(
            client._client, "get", side_effect=httpx.ConnectError("refused")
        ):
            assert client.is_reachable() is False

    def test_unreachable_timeout(self, client):
        with patch.object(
            client._client, "get", side_effect=httpx.ReadTimeout("timeout")
        ):
            assert client.is_reachable() is False


class TestHealth:
    def test_health(self, client):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status": "healthy",
            "db": True,
            "redis": True,
            "ollama": True,
        }
        mock_resp.raise_for_status = MagicMock()
        with patch.object(client._client, "get", return_value=mock_resp):
            result = client.health()
            assert result["status"] == "healthy"
            assert result["db"] is True


class TestSubmitRun:
    def test_submit_run(self, client):
        mock_resp = MagicMock()
        mock_resp.status_code = 202
        mock_resp.json.return_value = {
            "id": "abc-123",
            "status": "pending",
            "message": "Run submitted successfully",
        }
        mock_resp.raise_for_status = MagicMock()
        with patch.object(client._client, "post", return_value=mock_resp) as mock_post:
            result = client.submit_run("factuality-test", "gemma3:4b", threshold=0.7)
            assert result["id"] == "abc-123"
            assert result["status"] == "pending"
            mock_post.assert_called_once_with(
                "/api/v1/runs",
                json={
                    "eval_name": "factuality-test",
                    "model": "gemma3:4b",
                    "threshold": 0.7,
                },
            )

    def test_submit_run_minimal(self, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"id": "xyz", "status": "pending", "message": "ok"}
        mock_resp.raise_for_status = MagicMock()
        with patch.object(client._client, "post", return_value=mock_resp) as mock_post:
            client.submit_run("reasoning-test", "llama3")
            call_args = mock_post.call_args
            payload = call_args[1]["json"]
            assert "threshold" not in payload
            assert "metadata" not in payload


class TestGetRun:
    def test_get_run(self, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "id": "abc-123",
            "eval_name": "factuality-test",
            "model_name": "gemma3:4b",
            "status": "completed",
            "score": 0.8,
            "results": [],
        }
        mock_resp.raise_for_status = MagicMock()
        with patch.object(client._client, "get", return_value=mock_resp):
            result = client.get_run("abc-123")
            assert result["score"] == 0.8


class TestListRuns:
    def test_list_runs(self, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [
            {"id": "1", "eval_name": "test", "status": "completed"},
        ]
        mock_resp.raise_for_status = MagicMock()
        with patch.object(client._client, "get", return_value=mock_resp) as mock_get:
            result = client.list_runs(eval_name="test", limit=10)
            assert len(result) == 1
            call_args = mock_get.call_args
            assert call_args[1]["params"]["eval_name"] == "test"
            assert call_args[1]["params"]["limit"] == 10

    def test_list_runs_no_filters(self, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = MagicMock()
        with patch.object(client._client, "get", return_value=mock_resp) as mock_get:
            client.list_runs()
            params = mock_get.call_args[1]["params"]
            assert "eval_name" not in params
            assert "model" not in params
            assert "status" not in params


class TestQueryResults:
    def test_query_results(self, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [
            {"id": "1", "eval_name": "test", "status": "completed", "score": 0.9},
        ]
        mock_resp.raise_for_status = MagicMock()
        with patch.object(client._client, "get", return_value=mock_resp):
            result = client.query_results(eval_name="test")
            assert result[0]["score"] == 0.9
