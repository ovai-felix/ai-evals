"""HTTP client for the aeval orchestrator API."""

from __future__ import annotations

from typing import Any

import httpx


class OrchestratorClient:
    """Client for communicating with the aeval orchestrator service."""

    def __init__(self, base_url: str = "http://localhost:8081"):
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(base_url=self._base_url, timeout=30)

    def is_reachable(self) -> bool:
        """Check if the orchestrator is reachable."""
        try:
            resp = self._client.get("/api/v1/health", timeout=3)
            return resp.status_code == 200
        except (httpx.HTTPError, httpx.ConnectError):
            return False

    def health(self) -> dict[str, Any]:
        """Get orchestrator health status."""
        resp = self._client.get("/api/v1/health")
        resp.raise_for_status()
        return resp.json()

    def submit_run(
        self,
        eval_name: str,
        model: str,
        *,
        threshold: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Submit an eval run to the orchestrator."""
        payload: dict[str, Any] = {
            "eval_name": eval_name,
            "model": model,
        }
        if threshold is not None:
            payload["threshold"] = threshold
        if metadata:
            payload["metadata"] = metadata

        resp = self._client.post("/api/v1/runs", json=payload)
        resp.raise_for_status()
        return resp.json()

    def get_run(self, run_id: str) -> dict[str, Any]:
        """Get run details including per-task results."""
        resp = self._client.get(f"/api/v1/runs/{run_id}")
        resp.raise_for_status()
        return resp.json()

    def list_runs(
        self,
        *,
        eval_name: str | None = None,
        model: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List runs with optional filters."""
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if eval_name:
            params["eval_name"] = eval_name
        if model:
            params["model"] = model
        if status:
            params["status"] = status

        resp = self._client.get("/api/v1/runs", params=params)
        resp.raise_for_status()
        return resp.json()

    def query_results(
        self,
        *,
        eval_name: str | None = None,
        model: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Query completed results."""
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if eval_name:
            params["eval_name"] = eval_name
        if model:
            params["model"] = model

        resp = self._client.get("/api/v1/results", params=params)
        resp.raise_for_status()
        return resp.json()

    def get_taxonomy(self) -> list[dict[str, Any]]:
        """Get the full capability taxonomy tree."""
        resp = self._client.get("/api/v1/taxonomy")
        resp.raise_for_status()
        return resp.json()

    def get_eval_health(
        self, *, lifecycle_state: str | None = None
    ) -> list[dict[str, Any]]:
        """Get eval health records."""
        params: dict[str, Any] = {}
        if lifecycle_state:
            params["lifecycle_state"] = lifecycle_state
        resp = self._client.get("/api/v1/health/evals", params=params)
        resp.raise_for_status()
        return resp.json()

    def get_coverage(self) -> dict[str, Any]:
        """Get taxonomy coverage summary."""
        resp = self._client.get("/api/v1/health/coverage")
        resp.raise_for_status()
        return resp.json()

    def refresh_health(self) -> dict[str, Any]:
        """Trigger health check refresh for all evals."""
        resp = self._client.post("/api/v1/health/refresh")
        resp.raise_for_status()
        return resp.json()

    def generate_evals(
        self,
        *,
        taxonomy_node: str | None = None,
        method: str | None = None,
        count: int = 5,
    ) -> dict[str, Any]:
        """Generate candidate eval tasks via LLM."""
        payload: dict[str, Any] = {"count": count}
        if taxonomy_node:
            payload["taxonomy_node"] = taxonomy_node
        if method:
            payload["method"] = method
        resp = self._client.post("/api/v1/intelligence/generate", json=payload)
        resp.raise_for_status()
        return resp.json()

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()


class RegistryClient:
    """Client for communicating with the aeval registry service."""

    def __init__(self, base_url: str = "http://localhost:8082"):
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(base_url=self._base_url, timeout=30)

    def is_reachable(self) -> bool:
        """Check if the registry service is reachable."""
        try:
            resp = self._client.get("/api/v1/health", timeout=3)
            return resp.status_code == 200
        except (httpx.HTTPError, httpx.ConnectError):
            return False

    def search(self, query: str) -> list[dict[str, Any]]:
        """Search for evals by name, tag, or description."""
        resp = self._client.get("/api/v1/search", params={"q": query})
        resp.raise_for_status()
        return resp.json()

    def list_evals(self) -> list[dict[str, Any]]:
        """List all evals in the registry."""
        resp = self._client.get("/api/v1/evals")
        resp.raise_for_status()
        return resp.json()

    def get_eval(self, name: str) -> dict[str, Any]:
        """Get details for a single eval."""
        resp = self._client.get(f"/api/v1/evals/{name}")
        resp.raise_for_status()
        return resp.json()

    def list_suites(self) -> list[dict[str, Any]]:
        """List all available suites."""
        resp = self._client.get("/api/v1/suites")
        resp.raise_for_status()
        return resp.json()

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()
