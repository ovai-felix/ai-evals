"""aeval results — query results from the orchestrator."""

from __future__ import annotations

import json

import click
from rich.console import Console
from rich.table import Table

from aeval.client import OrchestratorClient
from aeval.config import AevalConfig

console = Console()


@click.command()
@click.option("--run-id", default=None, help="Show results for a specific run ID.")
@click.option("--eval", "eval_name", default=None, help="Filter by eval name.")
@click.option("--model", default=None, help="Filter by model name.")
@click.option("--last", is_flag=True, help="Show the most recent completed run.")
@click.option("--output", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.option("--limit", default=20, help="Max results to show.")
def results_cmd(
    run_id: str | None,
    eval_name: str | None,
    model: str | None,
    last: bool,
    output_format: str,
    limit: int,
):
    """Query eval results from the orchestrator.

    Requires the orchestrator to be running (docker compose up).
    """
    config = AevalConfig.load()
    client = OrchestratorClient(config.orchestrator_url)

    if not client.is_reachable():
        console.print("[red]Error: Orchestrator not reachable at "
                       f"{config.orchestrator_url}[/red]")
        console.print("[dim]Start it with: docker compose up -d[/dim]")
        raise SystemExit(1)

    try:
        if run_id:
            _show_run_detail(client, run_id, output_format)
        elif last:
            _show_last_run(client, eval_name, model, output_format)
        else:
            _show_run_list(client, eval_name, model, limit, output_format)
    finally:
        client.close()


def _show_run_detail(client: OrchestratorClient, run_id: str, output_format: str):
    """Show detailed results for a specific run."""
    try:
        run = client.get_run(run_id)
    except Exception:
        console.print(f"[red]Error: Run not found: {run_id}[/red]")
        raise SystemExit(1)

    if output_format == "json":
        click.echo(json.dumps(run, indent=2, default=str))
        return

    console.print()
    console.print(f"  Run:    {run['id']}")
    console.print(f"  Eval:   {run['eval_name']}")
    console.print(f"  Model:  {run['model_name']}")
    console.print(f"  Status: {_status_badge(run['status'])}")

    if run.get("score") is not None:
        score_str = f"  Score:  {run['score']:.3f}"
        ci = run.get("ci")
        if ci:
            margin = (ci["upper"] - ci["lower"]) / 2
            score_str += f" (±{margin:.3f}, {ci.get('level', 0.95):.0%} CI)"
        console.print(score_str)

    if run.get("passed") is not None:
        status = "[green]PASS[/green]" if run["passed"] else "[red]FAIL[/red]"
        threshold_str = f" (threshold: {run['threshold']:.2f})" if run.get("threshold") else ""
        console.print(f"  Result: {status}{threshold_str}")

    if run.get("num_tasks"):
        console.print(f"  Tasks:  {run['num_tasks']}")

    # Show per-task results table
    results = run.get("results", [])
    if results:
        console.print()
        table = Table(show_header=True, padding=(0, 1))
        table.add_column("Task", style="dim")
        table.add_column("Score", justify="right")
        table.add_column("Passed")
        table.add_column("Prediction", max_width=40, no_wrap=True)
        table.add_column("Reference", max_width=30, no_wrap=True)

        for r in results:
            passed_str = ""
            if r.get("passed") is not None:
                passed_str = "[green]✓[/green]" if r["passed"] else "[red]✗[/red]"
            table.add_row(
                r["task_id"],
                f"{r['score']:.3f}",
                passed_str,
                r.get("prediction", "")[:40],
                r.get("reference", "")[:30],
            )
        console.print(table)

    console.print()


def _show_last_run(
    client: OrchestratorClient,
    eval_name: str | None,
    model: str | None,
    output_format: str,
):
    """Show the most recent completed run."""
    runs = client.query_results(eval_name=eval_name, model=model, limit=1)
    if not runs:
        console.print("[yellow]No completed runs found.[/yellow]")
        raise SystemExit(0)

    _show_run_detail(client, runs[0]["id"], output_format)


def _show_run_list(
    client: OrchestratorClient,
    eval_name: str | None,
    model: str | None,
    limit: int,
    output_format: str,
):
    """Show a list of runs."""
    runs = client.query_results(eval_name=eval_name, model=model, limit=limit)

    if output_format == "json":
        click.echo(json.dumps(runs, indent=2, default=str))
        return

    if not runs:
        console.print("[yellow]No completed runs found.[/yellow]")
        return

    console.print()
    table = Table(show_header=True, padding=(0, 1))
    table.add_column("ID", style="dim", max_width=8, no_wrap=True)
    table.add_column("Eval")
    table.add_column("Model")
    table.add_column("Score", justify="right")
    table.add_column("Tasks", justify="right")
    table.add_column("Passed")
    table.add_column("Submitted")

    for run in runs:
        passed_str = ""
        if run.get("passed") is not None:
            passed_str = "[green]PASS[/green]" if run["passed"] else "[red]FAIL[/red]"
        score_str = f"{run['score']:.3f}" if run.get("score") is not None else "-"
        tasks_str = str(run.get("num_tasks", "-"))
        submitted = run.get("submitted_at", "")
        if isinstance(submitted, str) and len(submitted) > 16:
            submitted = submitted[:16]

        table.add_row(
            str(run["id"])[:8],
            run["eval_name"],
            run["model_name"],
            score_str,
            tasks_str,
            passed_str,
            str(submitted),
        )

    console.print(table)
    console.print()


def _status_badge(status: str) -> str:
    colors = {
        "pending": "yellow",
        "running": "blue",
        "completed": "green",
        "failed": "red",
    }
    color = colors.get(status, "white")
    return f"[{color}]{status}[/{color}]"
