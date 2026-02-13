"""aeval ci — CI/CD integration for eval pipelines.

Exit codes:
  0 — All evals pass, no regressions detected.
  1 — Regression detected or threshold failure.
  2 — System error (cannot reach services, eval not found, etc.).
"""

from __future__ import annotations

import json
import sys
from datetime import datetime

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from aeval.commands.run import _resolve_eval, _resolve_model
from aeval.core.eval import load_eval_file
from aeval.core.suite import get_suite
from aeval.stats.significance import significance_test

console = Console()

# Exit codes
EXIT_PASS = 0
EXIT_REGRESSION = 1
EXIT_SYSTEM_ERROR = 2


@click.command("ci")
@click.option("--suite", "suite_name", required=True, help="Eval suite to run (e.g., pre-merge, smoke, full).")
@click.option("--model", "-m", "model_spec", required=True, help="Model to evaluate (e.g., ollama:brain-analyst-ft).")
@click.option(
    "--fail-on",
    type=click.Choice(["regression", "threshold", "any"]),
    default="any",
    help="What triggers failure: regression (vs baseline), threshold, or any.",
)
@click.option("--baseline-model", default=None, help="Baseline model for regression detection (e.g., ollama:llama3).")
@click.option(
    "--report",
    type=click.Choice(["console", "github-pr-comment", "json"]),
    default="console",
    help="Output format.",
)
@click.option("--threshold", type=float, default=None, help="Override pass/fail threshold for all evals.")
@click.option("--local", is_flag=True, default=False, help="Force local execution (bypass orchestrator).")
def ci_cmd(
    suite_name: str,
    model_spec: str,
    fail_on: str,
    baseline_model: str | None,
    report: str,
    threshold: float | None,
    local: bool,
):
    """Run eval suite for CI/CD — exit 0 (pass), 1 (regression), 2 (error).

    Runs all evals in a suite, optionally compares against a baseline model
    for regression detection, and returns structured exit codes for CI pipelines.

    \b
    Examples:
      aeval ci --suite pre-merge --model ollama:brain-analyst-ft --fail-on regression
      aeval ci --suite smoke --model ollama:llama3 --report json
      aeval ci --suite safety --model ollama:brain-analyst-ft --baseline-model ollama:llama3
    """
    # Resolve suite
    suite = get_suite(suite_name)
    if suite is None:
        console.print(f"[red]Error: Suite not found: {suite_name}[/red]", style="bold")
        sys.exit(EXIT_SYSTEM_ERROR)

    # Resolve eval definitions
    definitions = []
    for eval_name in suite.evals:
        defn = _resolve_eval(eval_name)
        if defn is None:
            console.print(f"[red]Error: Eval not found: {eval_name}[/red]")
            sys.exit(EXIT_SYSTEM_ERROR)
        if threshold is not None:
            defn.threshold = threshold
        definitions.append(defn)

    # Resolve model
    try:
        model = _resolve_model(model_spec)
    except Exception as e:
        console.print(f"[red]Error: Cannot connect to model {model_spec}: {e}[/red]")
        sys.exit(EXIT_SYSTEM_ERROR)

    # Optionally resolve baseline model
    baseline = None
    if baseline_model:
        try:
            baseline = _resolve_model(baseline_model)
        except Exception as e:
            console.print(f"[red]Error: Cannot connect to baseline model {baseline_model}: {e}[/red]")
            sys.exit(EXIT_SYSTEM_ERROR)

    # Run evals
    results = []
    baseline_results = []

    model_display = model_spec.removeprefix("ollama:")

    for defn in definitions:
        try:
            result = defn.run(model)
            results.append(result)
        except Exception as e:
            console.print(f"[red]Error running {defn.name}: {e}[/red]")
            sys.exit(EXIT_SYSTEM_ERROR)

        # Run baseline if provided
        if baseline:
            try:
                b_result = defn.run(baseline)
                baseline_results.append(b_result)
            except Exception as e:
                console.print(f"[red]Error running baseline {defn.name}: {e}[/red]")
                sys.exit(EXIT_SYSTEM_ERROR)

    # Analyze results
    analysis = _analyze_results(
        results=results,
        baseline_results=baseline_results if baseline else None,
        fail_on=fail_on,
    )

    # Output
    if report == "json":
        _output_json(analysis, suite_name, model_spec, baseline_model)
    elif report == "github-pr-comment":
        _output_github_comment(analysis, suite_name, model_spec, baseline_model)
    else:
        _output_console(analysis, suite_name, model_spec, baseline_model)

    sys.exit(analysis["exit_code"])


def _analyze_results(
    results: list,
    baseline_results: list | None,
    fail_on: str,
) -> dict:
    """Analyze eval results and determine pass/fail."""
    evals = []
    any_threshold_fail = False
    any_regression = False

    for i, result in enumerate(results):
        entry = {
            "eval_name": result.eval_name,
            "score": result.score,
            "passed": result.passed,
            "threshold": result.threshold,
            "num_tasks": result.num_tasks,
            "ci_lower": result.ci.lower if result.ci else None,
            "ci_upper": result.ci.upper if result.ci else None,
            "regression": False,
            "delta": None,
            "significant": None,
            "p_value": None,
            "effect_size": None,
        }

        # Threshold check
        if result.passed is False:
            any_threshold_fail = True

        # Regression check (vs baseline)
        if baseline_results and i < len(baseline_results):
            b = baseline_results[i]
            entry["baseline_score"] = b.score
            entry["delta"] = result.score - b.score

            # Significance test
            task_scores = [t.score for t in result.task_results]
            baseline_scores = [t.score for t in b.task_results]

            if len(task_scores) >= 2 and len(baseline_scores) >= 2:
                sig = significance_test(task_scores, baseline_scores)
                entry["significant"] = sig["significant"]
                entry["p_value"] = sig["p_value"]
                entry["effect_size"] = sig.get("effect_size")

                # Regression = significant decrease
                if sig["significant"] and entry["delta"] < 0:
                    entry["regression"] = True
                    any_regression = True

        evals.append(entry)

    # Determine exit code
    if fail_on == "regression":
        exit_code = EXIT_REGRESSION if any_regression else EXIT_PASS
    elif fail_on == "threshold":
        exit_code = EXIT_REGRESSION if any_threshold_fail else EXIT_PASS
    else:  # "any"
        exit_code = EXIT_REGRESSION if (any_regression or any_threshold_fail) else EXIT_PASS

    return {
        "exit_code": exit_code,
        "passed": exit_code == EXIT_PASS,
        "any_threshold_fail": any_threshold_fail,
        "any_regression": any_regression,
        "evals": evals,
    }


def _output_console(analysis: dict, suite: str, model: str, baseline: str | None):
    """Rich console output for CI results."""
    model_display = model.removeprefix("ollama:")
    status = "[green]PASS[/green]" if analysis["passed"] else "[red]FAIL[/red]"

    console.print()
    console.print(Panel(
        f"Suite: [bold]{suite}[/bold]  Model: [bold]{model_display}[/bold]  Result: {status}",
        title="aeval CI",
        border_style="green" if analysis["passed"] else "red",
    ))

    table = Table(show_lines=True)
    table.add_column("Eval", style="cyan")
    table.add_column("Score", justify="right")
    table.add_column("Threshold", justify="right")
    table.add_column("Pass?", justify="center")
    if baseline:
        table.add_column("Baseline", justify="right")
        table.add_column("Delta", justify="right")
        table.add_column("Regression?", justify="center")

    for e in analysis["evals"]:
        row = [
            e["eval_name"],
            f"{e['score']:.3f}",
            f"{e['threshold']:.2f}" if e["threshold"] else "—",
            "[green]PASS[/green]" if e["passed"] else ("[red]FAIL[/red]" if e["passed"] is False else "—"),
        ]
        if baseline:
            delta = e.get("delta")
            if delta is not None:
                sign = "+" if delta >= 0 else ""
                delta_color = "green" if delta >= 0 else "red"
                row.append(f"{e.get('baseline_score', 0):.3f}")
                row.append(f"[{delta_color}]{sign}{delta:.3f}[/{delta_color}]")
            else:
                row.append("—")
                row.append("—")

            if e["regression"]:
                row.append("[bold red]YES[/bold red]")
            else:
                row.append("[green]no[/green]")

        table.add_row(*row)

    console.print(table)
    console.print()

    if analysis["any_regression"]:
        console.print("[bold red]Regressions detected. CI pipeline should block merge.[/bold red]")
    if analysis["any_threshold_fail"]:
        console.print("[bold red]Threshold failures detected.[/bold red]")
    if analysis["passed"]:
        console.print("[bold green]All checks passed.[/bold green]")
    console.print()


def _output_json(analysis: dict, suite: str, model: str, baseline: str | None):
    """JSON output for programmatic consumption."""
    output = {
        "suite": suite,
        "model": model,
        "baseline_model": baseline,
        "passed": analysis["passed"],
        "exit_code": analysis["exit_code"],
        "any_threshold_fail": analysis["any_threshold_fail"],
        "any_regression": analysis["any_regression"],
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "evals": [],
    }
    for e in analysis["evals"]:
        entry = {
            "eval_name": e["eval_name"],
            "score": e["score"],
            "threshold": e["threshold"],
            "passed": e["passed"],
            "num_tasks": e["num_tasks"],
        }
        if e.get("ci_lower") is not None:
            entry["ci"] = {"lower": e["ci_lower"], "upper": e["ci_upper"]}
        if e.get("delta") is not None:
            entry["baseline_score"] = e.get("baseline_score")
            entry["delta"] = e["delta"]
            entry["regression"] = e["regression"]
            entry["significant"] = e.get("significant")
            entry["p_value"] = e.get("p_value")
            entry["effect_size"] = e.get("effect_size")
        output["evals"].append(entry)

    click.echo(json.dumps(output, indent=2))


def _output_github_comment(analysis: dict, suite: str, model: str, baseline: str | None):
    """Markdown output suitable for GitHub PR comments."""
    model_display = model.removeprefix("ollama:")
    verdict = "PASS" if analysis["passed"] else "FAIL"
    badge = "white_check_mark" if analysis["passed"] else "x"

    lines = [
        f"## :{badge}: Model Evaluation — {verdict}",
        "",
        f"**Suite:** `{suite}` | **Model:** `{model_display}`"
        + (f" | **Baseline:** `{baseline.removeprefix('ollama:')}`" if baseline else ""),
        "",
        "| Eval | Score | Threshold | Pass |"
        + (" Baseline | Delta | Regression |" if baseline else ""),
        "|------|------:|----------:|:----:|"
        + ("--------:|------:|:----------:|" if baseline else ""),
    ]

    for e in analysis["evals"]:
        passed_icon = "white_check_mark" if e["passed"] else ("x" if e["passed"] is False else "—")
        row = f"| {e['eval_name']} | {e['score']:.3f} | {e['threshold']:.2f if e['threshold'] else '—'} | :{passed_icon}: |"
        if baseline:
            delta = e.get("delta")
            if delta is not None:
                sign = "+" if delta >= 0 else ""
                reg_icon = "rotating_light" if e["regression"] else "white_check_mark"
                row += f" {e.get('baseline_score', 0):.3f} | {sign}{delta:.3f} | :{reg_icon}: |"
            else:
                row += " — | — | — |"
        lines.append(row)

    lines.append("")
    if analysis["any_regression"]:
        lines.append("> :warning: **Regressions detected.** This PR should not be merged until regressions are addressed.")
    elif analysis["any_threshold_fail"]:
        lines.append("> :warning: **Threshold failures detected.** Review eval results before merging.")
    else:
        lines.append("> :tada: All evaluations passed. Model is ready for merge.")

    lines.append("")
    lines.append(f"*Generated by `aeval ci` at {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}*")

    click.echo("\n".join(lines))
