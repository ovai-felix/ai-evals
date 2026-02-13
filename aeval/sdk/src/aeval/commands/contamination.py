"""aeval contamination-check — detect eval dataset contamination from training data."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from aeval.core.contamination import check_all_datasets

console = Console()


@click.command("contamination-check")
@click.option(
    "--training-manifest",
    required=True,
    type=click.Path(exists=True),
    help="Path to training data manifest JSON (contains content hashes).",
)
@click.option(
    "--datasets-dir",
    default=None,
    type=click.Path(exists=True),
    help="Directory containing eval datasets. Defaults to registry-data/.",
)
@click.option(
    "--threshold",
    default=0.05,
    type=float,
    help="Contamination rate above which an eval is flagged (default: 5%).",
)
@click.option("--output", "output_format", type=click.Choice(["table", "json"]), default="table")
def contamination_cmd(
    training_manifest: str,
    datasets_dir: str | None,
    threshold: float,
    output_format: str,
):
    """Check eval datasets for contamination against training data.

    Compares SHA-256 hashes of eval prompts against a training data manifest
    to detect potential data leakage. Evals with contamination rate above
    the threshold are flagged.

    \b
    Manifest format (JSON):
      {"files": [{"path": "data.jsonl", "hash": "abc123..."}, ...]}
      or: {"hashes": ["abc123...", ...]}
      or: ["abc123...", ...]

    \b
    Examples:
      aeval contamination-check --training-manifest ./manifest.json
      aeval contamination-check --training-manifest ./manifest.json --datasets-dir ./datasets
    """
    # Find datasets
    dataset_paths, eval_names = _find_datasets(datasets_dir)

    if not dataset_paths:
        console.print("[yellow]No eval datasets found.[/yellow]")
        console.print("[dim]Provide --datasets-dir or ensure registry-data/ exists.[/dim]")
        sys.exit(1)

    # Run contamination check
    report = check_all_datasets(
        manifest_path=training_manifest,
        dataset_paths=dataset_paths,
        eval_names=eval_names,
        threshold=threshold,
    )

    # Output
    if output_format == "json":
        _output_json(report)
    else:
        _output_table(report)

    # Exit with error if any contamination found
    if report.any_contaminated:
        sys.exit(1)


def _find_datasets(datasets_dir: str | None) -> tuple[list[str], list[str]]:
    """Find eval dataset files to check."""
    paths: list[str] = []
    names: list[str] = []

    search_dirs = []
    if datasets_dir:
        search_dirs.append(Path(datasets_dir))
    else:
        # Default search locations
        for candidate in [
            Path.cwd() / "registry-data",
            Path.cwd() / "datasets",
            Path("/app/registry-data"),
        ]:
            if candidate.exists():
                search_dirs.append(candidate)

    for search_dir in search_dirs:
        # Look for JSONL/JSON files
        for pattern in ("**/*.jsonl", "**/*.json"):
            for f in search_dir.glob(pattern):
                if f.name in ("meta.yaml", "package.json"):
                    continue
                # Try to infer eval name from parent dir
                eval_name = f.parent.name if f.parent != search_dir else f.stem
                paths.append(str(f))
                names.append(eval_name)

    return paths, names


def _output_table(report):
    """Rich table output for contamination report."""
    console.print()
    console.print(f"[bold]Contamination Check[/bold]")
    console.print(f"Manifest: {report.manifest_path} ({report.manifest_entries:,} entries)")
    console.print()

    table = Table(show_lines=True)
    table.add_column("Eval", style="cyan")
    table.add_column("Dataset", style="dim")
    table.add_column("Items", justify="right")
    table.add_column("Contaminated", justify="right")
    table.add_column("Rate", justify="right")
    table.add_column("Status", justify="center")

    for r in report.results:
        rate_str = f"{r.contamination_rate:.1%}"
        if r.flagged:
            status = "[bold red]FLAGGED[/bold red]"
            rate_style = f"[red]{rate_str}[/red]"
        elif r.contaminated_items > 0:
            status = "[yellow]warning[/yellow]"
            rate_style = f"[yellow]{rate_str}[/yellow]"
        else:
            status = "[green]clean[/green]"
            rate_style = f"[green]{rate_str}[/green]"

        table.add_row(
            r.eval_name,
            Path(r.dataset_path).name,
            str(r.total_items),
            str(r.contaminated_items),
            rate_style,
            status,
        )

    console.print(table)
    console.print()

    clean = report.clean_count
    flagged = report.contaminated_count
    total = len(report.results)
    console.print(f"Results: {clean}/{total} clean, {flagged}/{total} flagged")

    if report.any_contaminated:
        console.print("[bold red]Contamination detected! Flagged evals should be reviewed or replaced.[/bold red]")
    else:
        console.print("[green]No contamination detected.[/green]")
    console.print()


def _output_json(report):
    """JSON output for contamination report."""
    output = {
        "manifest_path": report.manifest_path,
        "manifest_entries": report.manifest_entries,
        "any_contaminated": report.any_contaminated,
        "results": [
            {
                "eval_name": r.eval_name,
                "dataset_path": r.dataset_path,
                "total_items": r.total_items,
                "contaminated_items": r.contaminated_items,
                "contamination_rate": r.contamination_rate,
                "flagged": r.flagged,
            }
            for r in report.results
        ],
    }
    click.echo(json.dumps(output, indent=2))
