from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.table import Table

from .cli import app, console, db
from .comparison import compare_asset_to_windows_device
from .discovery.windows import DiscoveryError, discover_local_windows_device
from .exporting import export_inventory_json
from .health import run_health_checks
from .reporting import build_operational_report


@app.command()
def compare(
    asset_tag: str,
    update: bool = typer.Option(
        False,
        "--update",
        help="Reconcile safe descriptive fields when the serial identity check passes.",
    ),
) -> None:
    """Compare a stored asset with read-only local Windows discovery data."""
    database = db()
    asset = database.get_asset(asset_tag)
    if asset is None:
        console.print(f"[red]Asset not found:[/red] {asset_tag}")
        raise typer.Exit(1)

    try:
        device = discover_local_windows_device()
    except DiscoveryError as exc:
        console.print(f"[red]Comparison failed:[/red] {exc}")
        raise typer.Exit(1) from exc

    comparison = compare_asset_to_windows_device(asset, device)
    table = Table(title=f"Inventory Comparison: {comparison.asset_tag}")
    table.add_column("Field")
    table.add_column("Stored")
    table.add_column("Observed")
    table.add_column("Result")
    for field in comparison.fields:
        table.add_row(
            field.name.replace("_", " ").title(),
            field.stored,
            field.observed,
            "MATCH" if field.matches else "DRIFT",
        )
    console.print(table)

    live = Table(title="Live Windows Observations", show_header=False)
    live.add_column("Field")
    live.add_column("Value")
    live.add_row("Operating System", comparison.os_caption)
    live.add_row("OS Version", comparison.os_version)
    live.add_row("Memory", f"{comparison.total_memory_gb:.1f} GB")
    live.add_row("Processor", comparison.processor)
    console.print(live)

    if not comparison.identity_match:
        console.print(
            "[red]Identity mismatch:[/red] the discovered BIOS serial does not match "
            "the stored asset. Automatic updates are blocked."
        )
        if update:
            raise typer.Exit(1)
        return

    if not comparison.has_drift:
        console.print("[green]No stored hardware drift detected.[/green]")
        return

    safe_updates = comparison.safe_updates()
    if not update:
        if safe_updates:
            console.print(
                "[yellow]Safe descriptive drift detected.[/yellow] "
                "Run with --update to reconcile hostname/manufacturer/model."
            )
        return

    if not safe_updates:
        console.print("[yellow]No automatically reconcilable fields were found.[/yellow]")
        return

    try:
        changes = database.update_asset(
            asset_tag,
            reason="Local Windows inventory drift reconciliation",
            **safe_updates,
        )
    except ValueError as exc:
        console.print(f"[red]Reconciliation failed:[/red] {exc}")
        raise typer.Exit(1) from exc

    updated = Table(title=f"Reconciled {comparison.asset_tag}")
    updated.add_column("Field")
    updated.add_column("Old")
    updated.add_column("New")
    for field, old_value, new_value in changes:
        updated.add_row(field.replace("_", " ").title(), old_value, new_value)
    console.print(updated)


@app.command("export-json")
def export_json(destination: Path) -> None:
    """Export the current inventory in a versioned JSON format."""
    try:
        count = export_inventory_json(db().list_assets(), destination)
    except OSError as exc:
        console.print(f"[red]JSON export failed:[/red] {exc}")
        raise typer.Exit(1) from exc
    console.print(f"[green]Exported {count} asset(s) as JSON:[/green] {destination}")


@app.command()
def doctor(
    max_backup_age_days: int = typer.Option(
        7,
        "--max-backup-age",
        min=0,
        help="Warn when the newest local backup is older than this many days.",
    ),
) -> None:
    """Run operational health checks for the local AMShell installation."""
    from .cli import DEFAULT_BACKUP_DIR, DEFAULT_DB

    health_report = run_health_checks(
        DEFAULT_DB,
        DEFAULT_BACKUP_DIR,
        max_backup_age_days=max_backup_age_days,
    )
    table = Table(title="AMShell Doctor")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Detail")
    for check in health_report.checks:
        table.add_row(check.name, check.status, check.detail)
    console.print(table)

    if health_report.has_failures:
        raise typer.Exit(1)


@app.command()
def report(
    status: str | None = typer.Option(None, help="Filter by lifecycle status."),
    device_type: str | None = typer.Option(None, "--type", help="Filter by device type."),
    output_format: str = typer.Option(
        "table",
        "--format",
        help="Output format: table or json.",
    ),
) -> None:
    """Generate a read-only operational inventory report."""
    normalized_format = output_format.strip().lower()
    if normalized_format not in {"table", "json"}:
        console.print("[red]Error:[/red] --format must be 'table' or 'json'.")
        raise typer.Exit(2)

    operational_report = build_operational_report(
        db().list_assets(),
        status=status,
        device_type=device_type,
    )

    if normalized_format == "json":
        console.print_json(json.dumps(operational_report.as_dict()))
        return

    summary = Table(title="AMShell Operational Report")
    summary.add_column("Metric")
    summary.add_column("Value", justify="right")
    summary.add_row("Assets", str(operational_report.asset_count))
    summary.add_row("Expired warranties", str(operational_report.warranty_expired))
    summary.add_row(
        "Warranties expiring within 90 days",
        str(operational_report.warranty_expiring_90_days),
    )
    console.print(summary)

    lifecycle = Table(title="Lifecycle Counts")
    lifecycle.add_column("Status")
    lifecycle.add_column("Assets", justify="right")
    for name, count in operational_report.status_counts.items():
        lifecycle.add_row(name, str(count))
    console.print(lifecycle)

    assets = Table(title="Assets")
    for heading in ("Tag", "Hostname", "Type", "Model", "Status", "Assigned To", "Warranty"):
        assets.add_column(heading)
    for asset in operational_report.assets:
        assets.add_row(
            str(asset["asset_tag"]),
            str(asset["hostname"]),
            str(asset["device_type"]),
            f"{asset['manufacturer']} {asset['model']}",
            str(asset["status"]),
            str(asset["assigned_to"]),
            str(asset["warranty_expiry"]),
        )
    console.print(assets)


if __name__ == "__main__":
    app()
