"""aeval init — initialize project configuration."""

from __future__ import annotations

import shutil
from pathlib import Path

import click
from rich.console import Console

from aeval.adapters.ollama import check_ollama_health, list_ollama_models

console = Console()


@click.command()
@click.option(
    "--ollama-host",
    default="http://localhost:11434",
    help="Ollama API host URL.",
)
def init_cmd(ollama_host: str):
    """Initialize aeval project — create aeval.yaml, detect Ollama."""
    config_path = Path.cwd() / "aeval.yaml"

    if config_path.exists():
        console.print("[yellow]aeval.yaml already exists. Skipping creation.[/yellow]")
    else:
        # Copy from example or create fresh
        example = Path(__file__).parent.parent.parent.parent.parent / "aeval.yaml.example"
        if example.exists():
            shutil.copy(example, config_path)
        else:
            config_path.write_text(
                f"ollama:\n"
                f"  host: {ollama_host}\n"
                f"  timeout: 120\n"
                f"  keep_alive: 5m\n"
                f"\n"
                f"judge_model: ollama:gpt-oss:20b\n"
                f"datasets_dir: ./datasets\n"
                f"evals_dir: ./evals\n"
            )
        console.print("[green]Created aeval.yaml[/green]")

    # Create directories
    for dirname in ["datasets", "evals"]:
        d = Path.cwd() / dirname
        d.mkdir(exist_ok=True)

    # Detect Ollama
    console.print()
    if check_ollama_health(ollama_host):
        models = list_ollama_models(ollama_host)
        console.print(
            f"[green]Ollama:        ✓ detected at {ollama_host} "
            f"({len(models)} models available)[/green]"
        )
    else:
        console.print(
            f"[red]Ollama:        ✗ not reachable at {ollama_host}[/red]\n"
            f"  Install Ollama: https://ollama.ai\n"
            f"  Or set --ollama-host to your Ollama instance."
        )

    console.print()
    console.print("[dim]Run 'aeval models' to list available models.[/dim]")
    console.print("[dim]Run 'aeval run <eval> --model ollama:<name>' to run an eval.[/dim]")
