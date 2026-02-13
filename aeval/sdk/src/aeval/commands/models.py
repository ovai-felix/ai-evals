"""aeval models — list available Ollama models."""

from __future__ import annotations

import json

import click
from rich.console import Console
from rich.table import Table

from aeval.adapters.ollama import check_ollama_health, list_ollama_models
from aeval.config import AevalConfig

console = Console()


@click.command()
@click.option("--output", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.option("--host", default=None, help="Override Ollama host URL.")
def models_cmd(output_format: str, host: str | None):
    """List available Ollama models."""
    config = AevalConfig.load()
    ollama_host = host or config.ollama.host

    if not check_ollama_health(ollama_host):
        console.print(f"[red]Error: Ollama not reachable at {ollama_host}[/red]")
        raise SystemExit(1)

    models = list_ollama_models(ollama_host)

    if not models:
        console.print("[yellow]No models found. Pull a model with: ollama pull llama3[/yellow]")
        return

    if output_format == "json":
        data = [
            {
                "name": m.name,
                "family": m.family,
                "parameter_size": m.parameter_size,
                "quantization": m.quantization,
                "multimodal": m.multimodal,
            }
            for m in models
        ]
        click.echo(json.dumps(data, indent=2))
        return

    table = Table(title="Ollama Models")
    table.add_column("Model", style="cyan")
    table.add_column("Family", style="green")
    table.add_column("Params", justify="right")
    table.add_column("Quant", style="yellow")
    table.add_column("Multimodal", justify="center")

    for m in models:
        table.add_row(
            m.name,
            m.family,
            m.parameter_size,
            m.quantization,
            "yes" if m.multimodal else "no",
        )

    console.print(table)
