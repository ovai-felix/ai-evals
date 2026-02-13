"""aeval health — eval suite health report."""

from __future__ import annotations

import json
import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from aeval.client import OrchestratorClient
from aeval.config import AevalConfig

console = Console()


@click.command()
@click.option("--refresh", is_flag=True, help="Trigger health check refresh before reporting")
@click.option("--json-output", "as_json", is_flag=True, help="Output as JSON")
def health_cmd(refresh: bool, as_json: bool):
    """Report eval suite health — coverage, saturation, discrimination."""
    config = AevalConfig.load()
    client = OrchestratorClient(base_url=config.orchestrator_url)

    if not client.is_reachable():
        console.print("[red]Cannot reach orchestrator.[/red] Is it running?")
        console.print(f"[dim]Tried: {config.orchestrator_url}[/dim]")
        sys.exit(1)

    try:
        if refresh:
            console.print("[dim]Refreshing health metrics...[/dim]")
            result = client.refresh_health()
            console.print(f"[green]Updated {result.get('updated', 0)} evals[/green]")
            console.print()

        coverage = client.get_coverage()
        health_records = client.get_eval_health()

        if as_json:
            output = {"coverage": coverage, "evals": health_records}
            click.echo(json.dumps(output, indent=2, default=str))
            return

        _print_overview(coverage)
        _print_coverage_table(coverage, client)
        _print_watch_list(health_records)
        _print_saturated_list(health_records)

    except Exception as e:
        console.print(f"[red]Error fetching health data:[/red] {e}")
        sys.exit(1)
    finally:
        client.close()


def _print_overview(coverage: dict) -> None:
    """Print suite overview panel."""
    total = coverage.get("active_count", 0) + coverage.get("watch_count", 0) + \
            coverage.get("saturated_count", 0) + coverage.get("archived_count", 0)

    lines = [
        f"Total evals with health data: [bold]{total}[/bold]",
        f"  Active: [green]{coverage.get('active_count', 0)}[/green]  "
        f"Watch: [yellow]{coverage.get('watch_count', 0)}[/yellow]  "
        f"Saturated: [red]{coverage.get('saturated_count', 0)}[/red]  "
        f"Archived: [dim]{coverage.get('archived_count', 0)}[/dim]",
        "",
        f"Taxonomy coverage: [bold]{coverage.get('covered_nodes', 0)}/{coverage.get('total_nodes', 0)}[/bold] "
        f"leaves ({coverage.get('coverage_pct', 0)}%)",
        f"Gaps: [{'red' if coverage.get('gap_count', 0) > 0 else 'green'}]"
        f"{coverage.get('gap_count', 0)}[/] uncovered capabilities",
        f"Avg discrimination: [bold]{coverage.get('avg_discrimination', 0):.4f}[/bold]",
    ]

    console.print(Panel("\n".join(lines), title="Suite Health Overview", border_style="blue"))
    console.print()


def _print_coverage_table(coverage: dict, client: OrchestratorClient) -> None:
    """Print taxonomy coverage table."""
    try:
        taxonomy = client.get_taxonomy()
    except Exception:
        return

    table = Table(title="Taxonomy Coverage", show_lines=True)
    table.add_column("Category", style="bold")
    table.add_column("Capability", style="cyan")
    table.add_column("Evals", justify="center")
    table.add_column("Avg Disc.", justify="center")
    table.add_column("Status", justify="center")

    for category in taxonomy:
        children = category.get("children", [])
        if not children:
            continue
        for i, child in enumerate(children):
            cat_label = category["name"] if i == 0 else ""
            eval_count = child.get("eval_count", 0)
            avg_disc = child.get("avg_discrimination", 0.0)

            if eval_count == 0:
                status = "[red]GAP[/red]"
            elif avg_disc < 0.08:
                status = "[red]Saturated[/red]"
            elif avg_disc < 0.15:
                status = "[yellow]Watch[/yellow]"
            else:
                status = "[green]Active[/green]"

            disc_str = f"{avg_disc:.3f}" if eval_count > 0 else "[dim]—[/dim]"

            table.add_row(
                cat_label,
                child["name"],
                str(eval_count),
                disc_str,
                status,
            )

    console.print(table)
    console.print()


def _print_watch_list(health_records: list[dict]) -> None:
    """Print evals approaching saturation."""
    watch = [r for r in health_records if r.get("lifecycle_state") == "watch"]
    if not watch:
        return

    table = Table(title="Watch List — Approaching Saturation", show_lines=True)
    table.add_column("Eval", style="yellow")
    table.add_column("Discrimination", justify="center")
    table.add_column("Last Checked", justify="center")

    for r in watch:
        table.add_row(
            r["eval_name"],
            f"{r.get('discrimination_power', 0):.4f}",
            str(r.get("last_checked", "—"))[:19],
        )

    console.print(table)
    console.print()


def _print_saturated_list(health_records: list[dict]) -> None:
    """Print saturated evals."""
    saturated = [r for r in health_records if r.get("lifecycle_state") == "saturated"]
    if not saturated:
        return

    table = Table(title="Saturated Evals", show_lines=True)
    table.add_column("Eval", style="red")
    table.add_column("Discrimination", justify="center")
    table.add_column("Saturation Type", justify="center")
    table.add_column("Last Checked", justify="center")

    for r in saturated:
        table.add_row(
            r["eval_name"],
            f"{r.get('discrimination_power', 0):.4f}",
            r.get("saturation_type") or "—",
            str(r.get("last_checked", "—"))[:19],
        )

    console.print(table)
    console.print()
