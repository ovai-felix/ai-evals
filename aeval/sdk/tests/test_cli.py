"""Tests for CLI commands."""

from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from aeval.cli import cli
from aeval.core.model import ModelInfo


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_config():
    with patch("aeval.adapters.ollama.AevalConfig") as mock:
        config = MagicMock()
        config.ollama.host = "http://localhost:11434"
        config.ollama.timeout = 30
        config.ollama.keep_alive = "5m"
        mock.load.return_value = config
        yield config


class TestModelsCommand:
    def test_models_table(self, runner, mock_config):
        mock_models = [
            ModelInfo(
                name="llama3:latest",
                family="llama",
                parameter_size="8.0B",
                quantization="Q4_0",
                multimodal=False,
            ),
            ModelInfo(
                name="llava:7b",
                family="llama",
                parameter_size="7.0B",
                quantization="Q4_0",
                multimodal=True,
            ),
        ]

        with patch("aeval.commands.models.check_ollama_health", return_value=True), \
             patch("aeval.commands.models.list_ollama_models", return_value=mock_models):
            result = runner.invoke(cli, ["models"])

        assert result.exit_code == 0
        assert "llama3" in result.output
        assert "llava" in result.output

    def test_models_json(self, runner, mock_config):
        mock_models = [
            ModelInfo(name="llama3", family="llama", parameter_size="8.0B"),
        ]

        with patch("aeval.commands.models.check_ollama_health", return_value=True), \
             patch("aeval.commands.models.list_ollama_models", return_value=mock_models):
            result = runner.invoke(cli, ["models", "--output", "json"])

        assert result.exit_code == 0
        assert '"name": "llama3"' in result.output

    def test_models_ollama_unreachable(self, runner, mock_config):
        with patch("aeval.commands.models.check_ollama_health", return_value=False):
            result = runner.invoke(cli, ["models"])

        assert result.exit_code == 1
        assert "not reachable" in result.output


class TestInitCommand:
    def test_init_creates_config(self, runner, tmp_path, mock_config):
        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch("aeval.commands.init.check_ollama_health", return_value=True), \
                 patch("aeval.commands.init.list_ollama_models", return_value=[]):
                result = runner.invoke(cli, ["init"])

            assert result.exit_code == 0
            assert "Created aeval.yaml" in result.output


class TestStatusCommand:
    def test_status_healthy(self, runner, mock_config):
        mock_orch_client = MagicMock()
        mock_orch_client.is_reachable.return_value = False
        with patch("aeval.commands.status.check_ollama_health", return_value=True), \
             patch("aeval.commands.status.list_ollama_models", return_value=[ModelInfo(name="m")]), \
             patch("aeval.commands.status.AevalConfig") as mock_cfg, \
             patch("aeval.client.OrchestratorClient", return_value=mock_orch_client):
            mock_cfg.load.return_value = MagicMock(
                ollama=MagicMock(host="http://localhost:11434"),
                orchestrator_url="http://localhost:8081",
            )
            result = runner.invoke(cli, ["status"])

        assert result.exit_code == 0
        assert "✓" in result.output

    def test_status_unhealthy(self, runner, mock_config):
        mock_orch_client = MagicMock()
        mock_orch_client.is_reachable.return_value = False
        with patch("aeval.commands.status.check_ollama_health", return_value=False), \
             patch("aeval.commands.status.AevalConfig") as mock_cfg, \
             patch("aeval.client.OrchestratorClient", return_value=mock_orch_client):
            mock_cfg.load.return_value = MagicMock(
                ollama=MagicMock(host="http://localhost:11434"),
                orchestrator_url="http://localhost:8081",
            )
            result = runner.invoke(cli, ["status"])

        assert result.exit_code == 0
        assert "✗" in result.output

    def test_status_orchestrator_healthy(self, runner, mock_config):
        mock_orch_client = MagicMock()
        mock_orch_client.is_reachable.return_value = True
        mock_orch_client.health.return_value = {"status": "healthy", "db": True, "redis": True, "ollama": True}
        with patch("aeval.commands.status.check_ollama_health", return_value=True), \
             patch("aeval.commands.status.list_ollama_models", return_value=[]), \
             patch("aeval.commands.status.AevalConfig") as mock_cfg, \
             patch("aeval.client.OrchestratorClient", return_value=mock_orch_client):
            mock_cfg.load.return_value = MagicMock(
                ollama=MagicMock(host="http://localhost:11434"),
                orchestrator_url="http://localhost:8081",
            )
            result = runner.invoke(cli, ["status"])

        assert result.exit_code == 0
        assert "Orchestrator" in result.output
        assert "✓" in result.output


class TestResultsCommand:
    def test_results_orchestrator_unreachable(self, runner, mock_config):
        mock_client = MagicMock()
        mock_client.is_reachable.return_value = False
        with patch("aeval.commands.results.AevalConfig") as mock_cfg, \
             patch("aeval.commands.results.OrchestratorClient", return_value=mock_client):
            mock_cfg.load.return_value = MagicMock(orchestrator_url="http://localhost:8081")
            result = runner.invoke(cli, ["results"])

        assert result.exit_code == 1
        assert "not reachable" in result.output

    def test_results_last(self, runner, mock_config):
        mock_client = MagicMock()
        mock_client.is_reachable.return_value = True
        mock_client.query_results.return_value = [{
            "id": "abc-123",
            "eval_name": "factuality-test",
            "model_name": "gemma3:4b",
            "status": "completed",
            "score": 0.8,
        }]
        mock_client.get_run.return_value = {
            "id": "abc-123",
            "eval_name": "factuality-test",
            "model_name": "gemma3:4b",
            "status": "completed",
            "score": 0.8,
            "passed": True,
            "threshold": 0.7,
            "num_tasks": 5,
            "ci": {"lower": 0.6, "upper": 1.0, "level": 0.95},
            "results": [],
        }
        with patch("aeval.commands.results.AevalConfig") as mock_cfg, \
             patch("aeval.commands.results.OrchestratorClient", return_value=mock_client):
            mock_cfg.load.return_value = MagicMock(orchestrator_url="http://localhost:8081")
            result = runner.invoke(cli, ["results", "--last"])

        assert result.exit_code == 0
        assert "factuality-test" in result.output
        assert "0.800" in result.output

    def test_results_json(self, runner, mock_config):
        mock_client = MagicMock()
        mock_client.is_reachable.return_value = True
        mock_client.query_results.return_value = [{
            "id": "abc-123",
            "eval_name": "factuality-test",
            "model_name": "gemma3:4b",
            "status": "completed",
            "score": 0.8,
        }]
        mock_client.get_run.return_value = {
            "id": "abc-123",
            "eval_name": "factuality-test",
            "model_name": "gemma3:4b",
            "status": "completed",
            "score": 0.8,
            "results": [],
        }
        with patch("aeval.commands.results.AevalConfig") as mock_cfg, \
             patch("aeval.commands.results.OrchestratorClient", return_value=mock_client):
            mock_cfg.load.return_value = MagicMock(orchestrator_url="http://localhost:8081")
            result = runner.invoke(cli, ["results", "--last", "--output", "json"])

        assert result.exit_code == 0
        assert '"eval_name"' in result.output

    def test_results_no_runs(self, runner, mock_config):
        mock_client = MagicMock()
        mock_client.is_reachable.return_value = True
        mock_client.query_results.return_value = []
        with patch("aeval.commands.results.AevalConfig") as mock_cfg, \
             patch("aeval.commands.results.OrchestratorClient", return_value=mock_client):
            mock_cfg.load.return_value = MagicMock(orchestrator_url="http://localhost:8081")
            result = runner.invoke(cli, ["results", "--last"])

        assert result.exit_code == 0
        assert "No completed runs" in result.output


class TestRunOrchestratorDetection:
    def test_run_delegates_to_orchestrator(self, runner, mock_config):
        """When orchestrator is reachable, run submits there."""
        mock_client = MagicMock()
        mock_client.is_reachable.return_value = True
        mock_client.submit_run.return_value = {
            "id": "run-abc-123",
            "status": "pending",
            "message": "ok",
        }
        with patch("aeval.client.OrchestratorClient", return_value=mock_client), \
             patch("aeval.config.AevalConfig.load") as mock_load:
            mock_load.return_value = MagicMock(orchestrator_url="http://localhost:8081")
            result = runner.invoke(cli, ["run", "factuality-test", "-m", "ollama:gemma3:4b"])

        assert result.exit_code == 0
        assert "submitted to orchestrator" in result.output
        assert "run-abc-123" in result.output

    def test_run_local_flag_skips_orchestrator(self, runner, mock_config, tmp_path):
        """--local flag forces local execution, skipping orchestrator."""
        # With --local, it should try to resolve eval locally (and fail since no eval file)
        result = runner.invoke(cli, ["run", "nonexistent-eval", "-m", "ollama:llama3", "--local"])
        assert result.exit_code == 1
        assert "Eval not found" in result.output

    def test_run_falls_through_when_orchestrator_unreachable(self, runner, mock_config):
        """When orchestrator is not reachable, falls through to local execution."""
        mock_client = MagicMock()
        mock_client.is_reachable.return_value = False
        with patch("aeval.client.OrchestratorClient", return_value=mock_client), \
             patch("aeval.config.AevalConfig.load") as mock_load:
            mock_load.return_value = MagicMock(orchestrator_url="http://localhost:8081")
            # Will fall through to local and fail on eval resolution
            result = runner.invoke(cli, ["run", "nonexistent-eval", "-m", "ollama:llama3"])

        assert result.exit_code == 1
        assert "Eval not found" in result.output


class TestVersionFlag:
    def test_version(self, runner):
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output
