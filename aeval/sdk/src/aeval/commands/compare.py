"""aeval compare — compare two or more models on an eval."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from aeval.commands.run import _resolve_eval, _resolve_model
from aeval.core.eval import load_eval_file
from aeval.stats.significance import significance_test

console = Console()


def _collect_eval_files(eval_names: list[str]) -> list:
    """Resolve multiple eval names to definitions."""
    definitions = []
    for name in eval_names:
        defn = _resolve_eval(name)
        if defn:
            definitions.append(defn)
        else:
            console.print(f"[yellow]Warning: Eval not found: {name}[/yellow]")
    return definitions


@click.command()
@click.argument("models", nargs=-1, required=True)
@click.option("--eval", "-e", "eval_names", multiple=True, help="Eval(s) to run.")
@click.option("--suite", "suite_name", default=None, help="Run a named suite of evals instead of --eval.")
@click.option("--output", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.option("--format", "report_format", type=click.Choice(["default", "alignment-tax"]), default="default",
              help="Report format: default table or alignment-tax report.")
def compare_cmd(models: tuple[str, ...], eval_names: tuple[str, ...], suite_name: str | None, output_format: str, report_format: str):
    """Compare two or more models on eval(s).

    MODELS are model specs (e.g., ollama:llama3 ollama:brain-analyst-ft).
    """
    if len(models) < 2:
        console.print("[red]Error: Need at least 2 models to compare.[/red]")
        raise SystemExit(1)

    # Resolve eval names from suite or --eval
    resolved_eval_names: list[str] = list(eval_names)
    if suite_name:
        from aeval.core.suite import get_suite
        suite = get_suite(suite_name)
        if suite is None:
            console.print(f"[red]Error: Suite not found: {suite_name}[/red]")
            raise SystemExit(1)
        resolved_eval_names = suite.evals

    if not resolved_eval_names:
        console.print("[red]Error: Specify at least one eval with --eval or --suite.[/red]")
        raise SystemExit(1)

    # Resolve evals
    definitions = _collect_eval_files(resolved_eval_names)
    if not definitions:
        console.print("[red]Error: No valid evals found.[/red]")
        raise SystemExit(1)

    # Resolve models
    model_instances = {}
    for spec in models:
        try:
            model_instances[spec] = _resolve_model(spec)
        except Exception as e:
            console.print(f"[red]Error connecting to {spec}: {e}[/red]")
            raise SystemExit(1)

    # Run all evals across all models
    # results[eval_name][model_spec] = EvalResult
    all_results: dict[str, dict[str, object]] = {}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for defn in definitions:
            all_results[defn.name] = {}
            for spec, model in model_instances.items():
                display = spec.removeprefix("ollama:")
                task = progress.add_task(
                    f"Running {defn.name} on {display}...", total=None
                )
                result = defn.run(model)
                all_results[defn.name][spec] = result
                progress.remove_task(task)

    # Output
    if output_format == "json":
        _output_json(all_results, models)
    elif report_format == "alignment-tax":
        _output_alignment_tax(all_results, models)
    else:
        _output_table(all_results, models)


def _output_table(all_results: dict, models: tuple[str, ...]):
    """Render comparison as a rich table."""
    model_labels = [m.removeprefix("ollama:") for m in models]

    table = Table(title="Model Comparison")
    table.add_column("Eval", style="cyan")
    for label in model_labels:
        table.add_column(label, justify="right")
    table.add_column("Delta", justify="right")
    table.add_column("Sig?", justify="center")

    for eval_name, model_results in all_results.items():
        row = [eval_name]
        scores = []
        task_score_lists = []

        for spec in models:
            result = model_results[spec]
            row.append(f"{result.score:.3f}")
            scores.append(result.score)
            task_score_lists.append([t.score for t in result.task_results])

        # Delta (first vs second model)
        delta = scores[0] - scores[1]
        sign = "+" if delta >= 0 else ""
        row.append(f"{sign}{delta:.3f}")

        # Significance test (between first two models)
        if len(task_score_lists[0]) >= 2 and len(task_score_lists[1]) >= 2:
            sig_result = significance_test(task_score_lists[0], task_score_lists[1])
            if sig_result["significant"]:
                row.append("[bold green]**yes**[/bold green]")
            else:
                row.append("[dim]no[/dim]")
        else:
            row.append("[dim]—[/dim]")

        table.add_row(*row)

    console.print()
    console.print(table)
    console.print()


def _output_json(all_results: dict, models: tuple[str, ...]):
    """Output comparison as JSON."""
    data = {"comparisons": []}
    for eval_name, model_results in all_results.items():
        entry = {"eval": eval_name, "models": {}}
        task_score_lists = []

        for spec in models:
            result = model_results[spec]
            entry["models"][spec] = {
                "score": result.score,
                "num_tasks": result.num_tasks,
            }
            if result.ci:
                entry["models"][spec]["ci"] = {
                    "lower": result.ci.lower,
                    "upper": result.ci.upper,
                }
            task_score_lists.append([t.score for t in result.task_results])

        # Significance between first two models
        if len(models) >= 2 and len(task_score_lists[0]) >= 2 and len(task_score_lists[1]) >= 2:
            sig_result = significance_test(task_score_lists[0], task_score_lists[1])
            entry["significance"] = sig_result

        data["comparisons"].append(entry)

    click.echo(json.dumps(data, indent=2))


def _output_alignment_tax(all_results: dict, models: tuple[str, ...]):
    """Render an alignment tax report: what improved, degraded, net assessment.

    Compares the first model (fine-tuned) against the second model (baseline).
    """
    from rich.panel import Panel

    if len(models) < 2:
        console.print("[red]Alignment tax requires exactly 2 models.[/red]")
        return

    model_a = models[0].removeprefix("ollama:")
    model_b = models[1].removeprefix("ollama:")

    improved = []
    degraded = []
    unchanged = []

    for eval_name, model_results in all_results.items():
        result_a = model_results[models[0]]
        result_b = model_results[models[1]]
        delta = result_a.score - result_b.score

        task_scores_a = [t.score for t in result_a.task_results]
        task_scores_b = [t.score for t in result_b.task_results]

        sig = None
        if len(task_scores_a) >= 2 and len(task_scores_b) >= 2:
            sig = significance_test(task_scores_a, task_scores_b)

        entry = {
            "eval": eval_name,
            "score_a": result_a.score,
            "score_b": result_b.score,
            "delta": delta,
            "significant": sig["significant"] if sig else False,
            "p_value": sig["p_value"] if sig else None,
            "effect_size": sig.get("effect_size") if sig else None,
        }

        if sig and sig["significant"]:
            if delta > 0:
                improved.append(entry)
            else:
                degraded.append(entry)
        else:
            unchanged.append(entry)

    # Header
    console.print()
    console.print(Panel(
        f"[bold]Alignment Tax Report[/bold]\n"
        f"Fine-tuned: [cyan]{model_a}[/cyan]  vs  Baseline: [cyan]{model_b}[/cyan]",
        border_style="blue",
    ))

    # Improvements
    if improved:
        table = Table(title="Improvements", show_lines=True, border_style="green")
        table.add_column("Eval", style="cyan")
        table.add_column(model_a, justify="right")
        table.add_column(model_b, justify="right")
        table.add_column("Delta", justify="right", style="green")
        table.add_column("Effect Size", justify="right")

        for e in sorted(improved, key=lambda x: x["delta"], reverse=True):
            effect = f"{e['effect_size']:.2f}" if e["effect_size"] is not None else "—"
            table.add_row(
                e["eval"],
                f"{e['score_a']:.3f}",
                f"{e['score_b']:.3f}",
                f"+{e['delta']:.3f}",
                effect,
            )
        console.print(table)

    # Degradations (alignment tax)
    if degraded:
        table = Table(title="Degradations (Alignment Tax)", show_lines=True, border_style="red")
        table.add_column("Eval", style="cyan")
        table.add_column(model_a, justify="right")
        table.add_column(model_b, justify="right")
        table.add_column("Delta", justify="right", style="red")
        table.add_column("Effect Size", justify="right")

        for e in sorted(degraded, key=lambda x: x["delta"]):
            effect = f"{e['effect_size']:.2f}" if e["effect_size"] is not None else "—"
            table.add_row(
                e["eval"],
                f"{e['score_a']:.3f}",
                f"{e['score_b']:.3f}",
                f"{e['delta']:.3f}",
                effect,
            )
        console.print(table)

    # Unchanged
    if unchanged:
        table = Table(title="Unchanged (No Significant Difference)", show_lines=True, border_style="dim")
        table.add_column("Eval", style="cyan")
        table.add_column(model_a, justify="right")
        table.add_column(model_b, justify="right")
        table.add_column("Delta", justify="right")

        for e in unchanged:
            sign = "+" if e["delta"] >= 0 else ""
            table.add_row(
                e["eval"],
                f"{e['score_a']:.3f}",
                f"{e['score_b']:.3f}",
                f"{sign}{e['delta']:.3f}",
            )
        console.print(table)

    # Net assessment
    console.print()
    total_evals = len(improved) + len(degraded) + len(unchanged)
    net_delta = sum(e["delta"] for e in improved + degraded + unchanged) / total_evals if total_evals else 0

    assessment_lines = [
        f"Improved: [green]{len(improved)}[/green] evals",
        f"Degraded: [red]{len(degraded)}[/red] evals",
        f"Unchanged: [dim]{len(unchanged)}[/dim] evals",
        "",
        f"Net avg delta: {'[green]+' if net_delta >= 0 else '[red]'}{net_delta:.4f}{'[/green]' if net_delta >= 0 else '[/red]'}",
    ]

    if degraded:
        tax = sum(abs(e["delta"]) for e in degraded)
        assessment_lines.append(f"Alignment tax (total degradation): [red]{tax:.4f}[/red]")

    if not degraded:
        assessment_lines.append("")
        assessment_lines.append("[bold green]No alignment tax detected — pure improvement.[/bold green]")
    elif not improved:
        assessment_lines.append("")
        assessment_lines.append("[bold red]No improvements — all changes are regressions.[/bold red]")
    else:
        gain = sum(e["delta"] for e in improved)
        cost = sum(abs(e["delta"]) for e in degraded)
        ratio = gain / cost if cost > 0 else float("inf")
        assessment_lines.append(f"Gain/cost ratio: [bold]{ratio:.2f}x[/bold]")
        if ratio >= 2.0:
            assessment_lines.append("[green]Strong net improvement despite alignment tax.[/green]")
        elif ratio >= 1.0:
            assessment_lines.append("[yellow]Marginal improvement — review degradations carefully.[/yellow]")
        else:
            assessment_lines.append("[red]Alignment tax exceeds improvements. Consider targeted fine-tuning.[/red]")

    console.print(Panel("\n".join(assessment_lines), title="Net Assessment", border_style="blue"))
    console.print()
