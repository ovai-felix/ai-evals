"""aeval run — run an eval against a model."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from aeval.core.eval import get_eval, load_eval_file
from aeval.core.model import Model

console = Console()


def _resolve_model(model_spec: str) -> Model:
    """Resolve a model spec like 'ollama:llama3' into a Model instance."""
    if model_spec.startswith("ollama:"):
        model_name = model_spec[len("ollama:"):]
        return Model.from_ollama(model_name)
    # Default to ollama
    return Model.from_ollama(model_spec)


def _resolve_eval(eval_name: str):
    """Find and load an eval by name or file path."""
    # Check if it's registered already
    definition = get_eval(eval_name)
    if definition:
        return definition

    # Try loading as a file path
    path = Path(eval_name)
    if path.exists() and path.suffix == ".py":
        definitions = load_eval_file(str(path))
        if definitions:
            return definitions[0]

    # Search in evals directory (including core/)
    evals_dir = Path.cwd() / "evals"
    if evals_dir.exists():
        for candidate in evals_dir.rglob("*.py"):
            if candidate.stem == eval_name or candidate.stem.replace("_", "-") == eval_name:
                definitions = load_eval_file(str(candidate))
                if definitions:
                    return definitions[0]

    # Try with .py extension
    py_path = Path(eval_name + ".py")
    if py_path.exists():
        definitions = load_eval_file(str(py_path))
        if definitions:
            return definitions[0]

    return None


def _try_orchestrator(eval_name: str, model_spec: str, threshold: float | None) -> bool:
    """Try to submit the run to the orchestrator. Returns True if successful."""
    try:
        from aeval.client import OrchestratorClient
        from aeval.config import AevalConfig

        config = AevalConfig.load()
        client = OrchestratorClient(config.orchestrator_url)

        if not client.is_reachable():
            return False

        result = client.submit_run(
            eval_name=eval_name,
            model=model_spec,
            threshold=threshold,
        )
        client.close()

        console.print()
        console.print(f"  [green]Run submitted to orchestrator[/green]")
        console.print(f"  Run ID: {result['id']}")
        console.print(f"  Status: {result['status']}")
        console.print()
        console.print("[dim]  Track with: aeval results --run-id " + result['id'] + "[/dim]")
        console.print()
        return True
    except Exception:
        return False


@click.command()
@click.argument("eval_name", required=False, default=None)
@click.option("--model", "-m", "model_spec", required=True, help="Model to evaluate (e.g., ollama:llama3).")
@click.option("--output", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.option("--threshold", type=float, default=None, help="Pass/fail threshold.")
@click.option("--local", is_flag=True, default=False, help="Force local execution (bypass orchestrator).")
@click.option("--suite", "suite_name", default=None, help="Run a named suite of evals (e.g., smoke, standard, full).")
def run_cmd(eval_name: str | None, model_spec: str, output_format: str, threshold: float | None, local: bool, suite_name: str | None):
    """Run an eval against a model.

    EVAL_NAME is the eval name or path to eval .py file.
    Use --suite to run a named group of evals instead.

    If the orchestrator is running, the eval is submitted for async execution.
    Use --local to force local (standalone) execution.
    """
    if suite_name:
        _run_suite(suite_name, model_spec, output_format, threshold, local)
        return

    if eval_name is None:
        console.print("[red]Error: Provide EVAL_NAME or use --suite.[/red]")
        raise SystemExit(1)

    # Dual-mode: try orchestrator first unless --local
    if not local:
        if _try_orchestrator(eval_name, model_spec, threshold):
            return

    # Fall through to local execution
    _run_locally(eval_name, model_spec, output_format, threshold)


def _run_suite(suite_name: str, model_spec: str, output_format: str, threshold: float | None, local: bool):
    """Run all evals in a named suite."""
    from aeval.core.suite import get_suite

    suite = get_suite(suite_name)
    if suite is None:
        console.print(f"[red]Error: Suite not found: {suite_name}[/red]")
        console.print("[dim]Use 'aeval registry suites' to list available suites.[/dim]")
        raise SystemExit(1)

    console.print()
    console.print(f"  [bold]Suite: {suite.name}[/bold]")
    if suite.description:
        console.print(f"  {suite.description}")
    console.print(f"  Evals: {len(suite.evals)}")
    console.print()

    suite_results = []
    any_failed = False

    for eval_name in suite.evals:
        console.print(f"  [bold]--- {eval_name} ---[/bold]")

        if not local:
            if _try_orchestrator(eval_name, model_spec, threshold):
                suite_results.append({"eval": eval_name, "status": "submitted"})
                continue

        # Local execution
        definition = _resolve_eval(eval_name)
        if not definition:
            console.print(f"  [yellow]Skipping {eval_name}: eval not found[/yellow]")
            suite_results.append({"eval": eval_name, "status": "not_found"})
            continue

        if threshold is not None:
            definition.threshold = threshold

        try:
            model = _resolve_model(model_spec)
        except Exception as e:
            console.print(f"  [red]Error: Could not connect to model: {e}[/red]")
            raise SystemExit(1)

        model_display = model_spec.removeprefix("ollama:")
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task(
                    f"Running {definition.name} on {model_display}...", total=None
                )
                result = definition.run(model)
        except Exception as e:
            console.print(f"  [red]Error running {eval_name}: {e}[/red]")
            suite_results.append({"eval": eval_name, "status": "error", "error": str(e)})
            any_failed = True
            continue

        # Display result
        _display_result(result, output_format)

        suite_results.append({
            "eval": eval_name,
            "status": "completed",
            "score": result.score,
            "passed": result.passed,
        })

        if result.passed is False:
            any_failed = True

    # Suite summary
    console.print()
    console.print("  [bold]Suite Summary[/bold]")
    console.print(f"  Suite: {suite.name}")
    for sr in suite_results:
        status_str = sr["status"]
        if status_str == "completed":
            score = sr.get("score", 0)
            passed = sr.get("passed")
            if passed is True:
                status_str = f"[green]PASS[/green] ({score:.3f})"
            elif passed is False:
                status_str = f"[red]FAIL[/red] ({score:.3f})"
            else:
                status_str = f"({score:.3f})"
        elif status_str == "submitted":
            status_str = "[blue]submitted[/blue]"
        elif status_str == "not_found":
            status_str = "[yellow]not found[/yellow]"
        elif status_str == "error":
            status_str = f"[red]error[/red]"
        console.print(f"    {sr['eval']}: {status_str}")
    console.print()

    if any_failed:
        sys.exit(1)


def _run_locally(eval_name: str, model_spec: str, output_format: str, threshold: float | None):
    """Run an eval locally (standalone mode)."""
    # Resolve eval
    definition = _resolve_eval(eval_name)
    if not definition:
        console.print(f"[red]Error: Eval not found: {eval_name}[/red]")
        console.print("[dim]Provide a registered eval name or path to a .py file.[/dim]")
        raise SystemExit(1)

    if threshold is not None:
        definition.threshold = threshold

    # Resolve model
    try:
        model = _resolve_model(model_spec)
    except Exception as e:
        console.print(f"[red]Error: Could not connect to model: {e}[/red]")
        raise SystemExit(1)

    # Run eval
    model_display = model_spec.removeprefix("ollama:")
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task(
                f"Running {definition.name} on {model_display}...", total=None
            )
            result = definition.run(model)
    except Exception as e:
        err_name = type(e).__name__
        if "Timeout" in err_name or "timeout" in str(e).lower():
            console.print(
                f"[red]Error: Request timed out talking to Ollama.[/red]\n"
                f"  The model may be loading into VRAM (especially after a model swap).\n"
                f"  Try again, or increase timeout in aeval.yaml (current: {model._timeout}s)."
            )
        else:
            console.print(f"[red]Error running eval: {e}[/red]")
        raise SystemExit(2)

    # Output results
    if output_format == "json":
        _output_json(result)
    else:
        _display_result(result, output_format)

    if result.passed is False:
        sys.exit(1)


def _display_result(result, output_format: str):
    """Display an eval result in table format."""
    if output_format == "json":
        _output_json(result)
        return

    console.print()
    # Score with CI
    score_str = f"  score: {result.score:.3f}"
    if result.ci:
        score_str += f" (±{result.ci.margin:.3f}, {result.ci.level:.0%} CI)"
    console.print(score_str)

    # Baseline delta
    if result.baseline_delta is not None:
        sign = "+" if result.baseline_delta >= 0 else ""
        delta_str = f"  vs. baseline: {sign}{result.baseline_delta:.3f}"
        if result.p_value is not None:
            sig = "significant" if result.significant else "not significant"
            delta_str += f" (p={result.p_value:.3f}, {sig})"
        console.print(delta_str)

    # Pass/fail
    if result.passed is not None:
        status = "[green]PASS[/green]" if result.passed else "[red]FAIL[/red]"
        threshold_str = f" (threshold: {result.threshold:.2f})" if result.threshold else ""
        console.print(f"  Status: {status}{threshold_str}")

    # Task count
    console.print(f"  Tasks: {result.num_tasks}")
    console.print()


def _output_json(result):
    """Output an eval result as JSON."""
    data = {
        "eval_name": result.eval_name,
        "model_name": result.model_name,
        "score": result.score,
        "num_tasks": result.num_tasks,
        "passed": result.passed,
        "threshold": result.threshold,
    }
    if result.ci:
        data["ci"] = {
            "lower": result.ci.lower,
            "upper": result.ci.upper,
            "level": result.ci.level,
        }
    if result.baseline_delta is not None:
        data["baseline_delta"] = result.baseline_delta
    if result.p_value is not None:
        data["p_value"] = result.p_value
        data["significant"] = result.significant
    click.echo(json.dumps(data, indent=2))
