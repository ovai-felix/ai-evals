"""aeval status — check system health."""

from __future__ import annotations

import click
from rich.console import Console

from aeval.adapters.ollama import check_ollama_health, list_ollama_models
from aeval.config import AevalConfig

console = Console()


@click.command()
def status_cmd():
    """Check system health — Ollama and orchestrator connectivity."""
    config = AevalConfig.load()

    console.print()

    # Check Orchestrator
    try:
        from aeval.client import OrchestratorClient

        client = OrchestratorClient(config.orchestrator_url)
        if client.is_reachable():
            health = client.health()
            parts = []
            if health.get("db"):
                parts.append("DB ✓")
            if health.get("redis"):
                parts.append("Redis ✓")
            detail = f" ({', '.join(parts)})" if parts else ""
            console.print(
                f"[green]Orchestrator:  ✓ running ({config.orchestrator_url}){detail}[/green]"
            )
        else:
            console.print(
                f"[yellow]Orchestrator:  ✗ not reachable ({config.orchestrator_url})[/yellow]"
            )
        client.close()
    except Exception:
        console.print(
            f"[yellow]Orchestrator:  ✗ not reachable ({config.orchestrator_url})[/yellow]"
        )

    # Check Ollama
    if check_ollama_health(config.ollama.host):
        models = list_ollama_models(config.ollama.host)
        console.print(
            f"[green]Ollama:        ✓ running ({config.ollama.host}, "
            f"{len(models)} models)[/green]"
        )
    else:
        console.print(
            f"[red]Ollama:        ✗ not reachable ({config.ollama.host})[/red]"
        )

    console.print()
