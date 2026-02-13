"""aeval registry — browse and manage the eval registry."""

from __future__ import annotations

from pathlib import Path

import click
import yaml
from rich.console import Console
from rich.table import Table

console = Console()


def _get_registry_client():
    """Try to create a RegistryClient connected to the service."""
    try:
        from aeval.client import RegistryClient
        from aeval.config import AevalConfig

        config = AevalConfig.load()
        client = RegistryClient(config.registry_url)
        if client.is_reachable():
            return client
        client.close()
    except Exception:
        pass
    return None


def _scan_local_registry() -> list[dict]:
    """Scan registry-data/ directory for local eval metadata."""
    registry_dir = Path.cwd() / "registry-data"
    if not registry_dir.exists():
        return []

    evals = []
    for meta_file in sorted(registry_dir.rglob("meta.yaml")):
        try:
            with open(meta_file) as f:
                meta = yaml.safe_load(f) or {}
            meta["_dir"] = str(meta_file.parent)
            evals.append(meta)
        except Exception:
            continue
    return evals


@click.group()
def registry_cmd():
    """Browse and manage the eval registry."""
    pass


@registry_cmd.command("search")
@click.argument("query")
def search_cmd(query: str):
    """Search for evals by name, tag, or description."""
    client = _get_registry_client()

    if client:
        try:
            results = client.search(query)
            client.close()
        except Exception:
            results = _local_search(query)
    else:
        results = _local_search(query)

    if not results:
        console.print(f"[yellow]No evals found matching '{query}'.[/yellow]")
        return

    table = Table(title=f"Search: {query}")
    table.add_column("Name", style="bold")
    table.add_column("Version")
    table.add_column("Category")
    table.add_column("Description")
    table.add_column("Tags")

    for e in results:
        table.add_row(
            e.get("name", ""),
            e.get("version", ""),
            e.get("category", ""),
            e.get("description", "")[:60],
            ", ".join(e.get("tags", [])),
        )

    console.print(table)


@registry_cmd.command("list")
def list_cmd():
    """List all evals in the registry."""
    client = _get_registry_client()

    if client:
        try:
            evals = client.list_evals()
            client.close()
        except Exception:
            evals = _scan_local_registry()
    else:
        evals = _scan_local_registry()

    if not evals:
        console.print("[yellow]No evals found in registry.[/yellow]")
        return

    table = Table(title="Registry Evals")
    table.add_column("Name", style="bold")
    table.add_column("Version")
    table.add_column("Category")
    table.add_column("Description")
    table.add_column("Tags")

    for e in evals:
        table.add_row(
            e.get("name", ""),
            e.get("version", ""),
            e.get("category", ""),
            e.get("description", "")[:60],
            ", ".join(e.get("tags", [])),
        )

    console.print(table)


@registry_cmd.command("info")
@click.argument("eval_name")
def info_cmd(eval_name: str):
    """Show detailed info for a specific eval."""
    client = _get_registry_client()

    info = None
    if client:
        try:
            info = client.get_eval(eval_name)
            client.close()
        except Exception:
            pass

    if info is None:
        # Fallback to local
        for e in _scan_local_registry():
            if e.get("name") == eval_name:
                info = e
                break

    if info is None:
        console.print(f"[red]Eval not found: {eval_name}[/red]")
        raise SystemExit(1)

    console.print()
    console.print(f"  [bold]{info.get('name', '')}[/bold]")
    console.print(f"  Version:     {info.get('version', '')}")
    console.print(f"  Category:    {info.get('category', '')}")
    console.print(f"  Description: {info.get('description', '')}")
    console.print(f"  Tags:        {', '.join(info.get('tags', []))}")
    console.print(f"  Threshold:   {info.get('threshold', 'N/A')}")
    console.print(f"  Dataset:     {info.get('dataset', 'N/A')}")
    console.print()


@registry_cmd.command("publish")
@click.argument("eval_path")
@click.option("--name", help="Override eval name.")
@click.option("--version", "eval_version", default="1.0", help="Eval version.")
def publish_cmd(eval_path: str, name: str | None, eval_version: str):
    """Publish an eval to the registry (local only for now)."""
    path = Path(eval_path)
    if not path.exists():
        console.print(f"[red]File not found: {eval_path}[/red]")
        raise SystemExit(1)

    # Load the eval to get its metadata
    from aeval.core.eval import load_eval_file

    definitions = load_eval_file(str(path))
    if not definitions:
        console.print(f"[red]No eval definitions found in {eval_path}[/red]")
        raise SystemExit(1)

    defn = definitions[0]
    eval_name = name or defn.name

    # Create registry-data directory
    registry_dir = Path.cwd() / "registry-data" / eval_name
    registry_dir.mkdir(parents=True, exist_ok=True)

    # Write meta.yaml
    meta = {
        "name": eval_name,
        "version": eval_version,
        "description": defn.description,
        "tags": defn.tags,
        "threshold": defn.threshold,
        "category": defn.metadata.get("category", ""),
    }

    meta_path = registry_dir / "meta.yaml"
    with open(meta_path, "w") as f:
        yaml.dump(meta, f, default_flow_style=False)

    # Copy eval file
    import shutil
    shutil.copy2(path, registry_dir / "eval.py")

    console.print(f"  [green]Published {eval_name} v{eval_version} to registry-data/[/green]")


@registry_cmd.command("suites")
def suites_cmd():
    """List available eval suites."""
    client = _get_registry_client()

    suites = None
    if client:
        try:
            suites = client.list_suites()
            client.close()
        except Exception:
            pass

    if suites is None:
        # Fallback to local suites.yaml
        from aeval.core.suite import list_suites
        suite_list = list_suites()
        suites = [
            {"name": s.name, "description": s.description, "evals": s.evals, "timeout": s.timeout}
            for s in suite_list
        ]

    if not suites:
        console.print("[yellow]No suites found.[/yellow]")
        return

    table = Table(title="Eval Suites")
    table.add_column("Name", style="bold")
    table.add_column("Description")
    table.add_column("Evals")
    table.add_column("Timeout")

    for s in suites:
        evals_str = ", ".join(s.get("evals", []))
        table.add_row(
            s.get("name", ""),
            s.get("description", ""),
            evals_str,
            s.get("timeout", "30m"),
        )

    console.print(table)


def _local_search(query: str) -> list[dict]:
    """Search local registry-data by name, tags, or description."""
    query_lower = query.lower()
    results = []
    for e in _scan_local_registry():
        name = e.get("name", "").lower()
        desc = e.get("description", "").lower()
        tags = [t.lower() for t in e.get("tags", [])]
        category = e.get("category", "").lower()

        if (
            query_lower in name
            or query_lower in desc
            or query_lower in category
            or any(query_lower in t for t in tags)
        ):
            results.append(e)
    return results
