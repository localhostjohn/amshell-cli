from __future__ import annotations

from pathlib import Path

import typer
from rich.table import Table

from .app import app
from .cli import console, db
from .snapshots import (
    apply_snapshot_prune,
    create_snapshot,
    diff_snapshots,
    get_snapshot_status,
    list_snapshots,
    plan_snapshot_prune,
)

snapshot_app = typer.Typer(help="Create, list, compare, monitor and prune historical snapshots.")
app.add_typer(snapshot_app, name="snapshot")
DEFAULT_SNAPSHOT_DIR = Path("snapshots")


@snapshot_app.command("create")
def snapshot_create() -> None:
    """Create a versioned point-in-time inventory snapshot."""
    try:
        path = create_snapshot(db().list_assets(), DEFAULT_SNAPSHOT_DIR)
    except OSError as exc:
        console.print(f"[red]Snapshot failed:[/red] {exc}")
        raise typer.Exit(1) from exc
    console.print(f"[green]Snapshot created:[/green] {path}")


@snapshot_app.command("list")
def snapshot_list() -> None:
    """List valid local historical snapshots."""
    rows = list_snapshots(DEFAULT_SNAPSHOT_DIR)
    table = Table(title="AMShell Historical Snapshots")
    table.add_column("Snapshot")
    table.add_column("Created")
    table.add_column("Assets", justify="right")
    for item in rows:
        table.add_row(str(item.path), item.created_at, str(item.asset_count))
    console.print(table)


@snapshot_app.command("status")
def snapshot_status(
    max_age_hours: int = typer.Option(
        36,
        "--max-age-hours",
        min=1,
        help="Fail when the newest valid snapshot is older than this many hours.",
    ),
) -> None:
    """Check whether recurring snapshot production appears healthy."""
    try:
        status = get_snapshot_status(
            DEFAULT_SNAPSHOT_DIR,
            max_age_hours=max_age_hours,
        )
    except ValueError as exc:
        console.print(f"[red]Snapshot status check invalid:[/red] {exc}")
        raise typer.Exit(2) from exc

    table = Table(title="Snapshot Automation Status")
    table.add_column("Status")
    table.add_column("Latest Snapshot")
    table.add_column("Created")
    table.add_column("Age")
    table.add_column("Detail")
    table.add_row(
        "HEALTHY" if status.healthy else "UNHEALTHY",
        str(status.latest.path) if status.latest else "-",
        status.latest.created_at if status.latest else "-",
        f"{status.age_hours:.1f}h" if status.age_hours is not None else "-",
        status.detail,
    )
    console.print(table)

    if not status.healthy:
        raise typer.Exit(1)


@snapshot_app.command("diff")
def snapshot_diff(older: Path, newer: Path) -> None:
    """Compare two historical snapshots by asset tag and stored fields."""
    try:
        result = diff_snapshots(older, newer)
    except (TypeError, ValueError) as exc:
        console.print(f"[red]Snapshot comparison failed:[/red] {exc}")
        raise typer.Exit(1) from exc

    summary = Table(title="Snapshot Difference")
    summary.add_column("Change")
    summary.add_column("Assets")
    summary.add_row("Added", ", ".join(result.added) or "-")
    summary.add_row("Removed", ", ".join(result.removed) or "-")
    summary.add_row("Changed", ", ".join(result.changed) or "-")
    console.print(summary)

    if result.changed:
        details = Table(title="Changed Asset Fields")
        details.add_column("Asset")
        details.add_column("Fields")
        for asset_tag, fields in result.changed.items():
            details.add_row(asset_tag, ", ".join(fields))
        console.print(details)

    if not result.has_changes:
        console.print("[green]No inventory changes between snapshots.[/green]")


@snapshot_app.command("prune")
def snapshot_prune(
    keep_latest: int = typer.Option(
        30,
        "--keep",
        min=1,
        help="Always keep at least this many newest valid snapshots.",
    ),
    older_than_days: int | None = typer.Option(
        None,
        "--older-than-days",
        min=0,
        help="Only prune additional snapshots at least this many days old.",
    ),
    apply: bool = typer.Option(
        False,
        "--apply",
        help="Delete the selected snapshots. Without this flag, only preview the plan.",
    ),
) -> None:
    """Preview or apply the local snapshot retention policy."""
    try:
        plan = plan_snapshot_prune(
            DEFAULT_SNAPSHOT_DIR,
            keep_latest=keep_latest,
            older_than_days=older_than_days,
        )
    except ValueError as exc:
        console.print(f"[red]Retention policy invalid:[/red] {exc}")
        raise typer.Exit(2) from exc

    table = Table(title="Snapshot Retention Plan")
    table.add_column("Action")
    table.add_column("Snapshot")
    table.add_column("Created")
    for item in plan.keep:
        table.add_row("KEEP", str(item.path), item.created_at)
    for item in plan.remove:
        table.add_row("PRUNE", str(item.path), item.created_at)
    console.print(table)

    if not plan.remove:
        console.print("[green]No snapshots are eligible for pruning.[/green]")
        return

    if not apply:
        console.print(
            f"[yellow]Preview only:[/yellow] {len(plan.remove)} snapshot(s) would be removed. "
            "Re-run with --apply to delete them."
        )
        return

    removed = apply_snapshot_prune(plan)
    console.print(f"[green]Pruned {removed} snapshot(s).[/green]")


if __name__ == "__main__":
    app()
