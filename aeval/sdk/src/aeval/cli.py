"""aeval CLI entrypoint."""

import click

from aeval.commands.init import init_cmd
from aeval.commands.models import models_cmd
from aeval.commands.run import run_cmd
from aeval.commands.compare import compare_cmd
from aeval.commands.status import status_cmd
from aeval.commands.health import health_cmd
from aeval.commands.registry import registry_cmd
from aeval.commands.results import results_cmd
from aeval.commands.ci import ci_cmd
from aeval.commands.contamination import contamination_cmd


@click.group()
@click.version_option(package_name="aeval")
def cli():
    """aeval — AI Evaluation Pipeline.

    Write evals like pytest, run them against any Ollama model,
    get scores with confidence intervals, and compare models.
    """
    pass


cli.add_command(init_cmd, "init")
cli.add_command(models_cmd, "models")
cli.add_command(run_cmd, "run")
cli.add_command(compare_cmd, "compare")
cli.add_command(status_cmd, "status")
cli.add_command(health_cmd, "health")
cli.add_command(registry_cmd, "registry")
cli.add_command(results_cmd, "results")
cli.add_command(ci_cmd, "ci")
cli.add_command(contamination_cmd, "contamination-check")


if __name__ == "__main__":
    cli()
