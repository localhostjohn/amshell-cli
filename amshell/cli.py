from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .backup import BackupError, create_backup, list_backups, restore_backup, verify_database
from .database import AssetDatabase
from .discovery.windows import DiscoveryError, discover_local_windows_device
from .models import ASSET_STATUSES, Asset

app = typer.Typer(help="AMShell - IT asset inventory and lifecycle management from the command line.")
backup_app = typer.Typer(help="Create, list and verify local SQLite backups.")
app.add_typer(backup_app, name="backup")
console = Console()
DEFAULT_DB = Path("data/amshell.db")
DEFAULT_BACKUP_DIR = Path("backups")


def db() -> AssetDatabase:
    database = AssetDatabase(DEFAULT_DB)
    database.initialize()
    return database


def print_assets(rows) -> None:
    table = Table(title="AMShell Asset Inventory")
    for heading in (
        "Tag",
        "Hostname",
        "Type",
        "Manufacturer",
        "Model",
        "Serial",
        "Status",
        "Assigned To",
    ):
        table.add_column(heading)
    for row in rows:
        table.add_row(
            row["asset_tag"],
            row["hostname"],
            row["device_type"],
            row["manufacturer"],
            row["model"],
            row["serial_number"],
            row["status"],
            row["assigned_to"],
        )
    console.print(table)


@app.command()
def init() -> None:
    """Create the local AMShell database."""
    db()
    console.print(f"[green]AMShell database ready:[/green] {DEFAULT_DB}")


@app.command("list")
def list_assets(
    status: str | None = typer.Option(None, help="Filter by lifecycle status."),
    device_type: str | None = typer.Option(
        None, "--type", help="Filter by device type."
    ),
) -> None:
    """List assets in the local inventory."""
    rows = db().list_assets(status=status, device_type=device_type)
    print_assets(rows)


@app.command()
def add(
    asset_tag: str = typer.Option(..., prompt=True),
    device_type: str = typer.Option(..., "--type", prompt=True),
    manufacturer: str = typer.Option(..., prompt=True),
    model: str = typer.Option(..., prompt=True),
    serial_number: str = typer.Option(..., "--serial", prompt=True),
    hostname: str = typer.Option("", prompt=True),
    status: str = typer.Option(
        "in-stock", help=f"One of: {', '.join(ASSET_STATUSES)}"
    ),
    location: str = typer.Option(""),
    assigned_to: str = typer.Option("", "--assigned-to"),
    purchase_date: str = typer.Option("", help="Purchase date in YYYY-MM-DD format."),
    warranty_expiry: str = typer.Option("", help="Warranty expiry in YYYY-MM-DD format."),
    notes: str = typer.Option(""),
) -> None:
    """Add an asset to the inventory."""
    try:
        asset = db().add_asset(
            Asset(
                asset_tag=asset_tag,
                hostname=hostname,
                device_type=device_type,
                manufacturer=manufacturer,
                model=model,
                serial_number=serial_number,
                status=status,
                location=location,
                assigned_to=assigned_to,
                purchase_date=purchase_date,
                warranty_expiry=warranty_expiry,
                notes=notes,
            )
        )
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    console.print(f"[green]Added[/green] {asset.asset_tag} ({asset.model})")


@app.command()
def show(asset_tag: str) -> None:
    """Show full details for one asset."""
    row = db().get_asset(asset_tag)
    if row is None:
        console.print(f"[red]Asset not found:[/red] {asset_tag}")
        raise typer.Exit(1)
    table = Table(title=row["asset_tag"], show_header=False)
    table.add_column("Field", style="bold")
    table.add_column("Value")
    for field in (
        "hostname",
        "device_type",
        "manufacturer",
        "model",
        "serial_number",
        "status",
        "location",
        "assigned_to",
        "purchase_date",
        "warranty_expiry",
        "notes",
        "created_at",
        "updated_at",
    ):
        table.add_row(field.replace("_", " ").title(), str(row[field]))
    console.print(table)


@app.command()
def edit(
    asset_tag: str,
    hostname: str | None = typer.Option(None),
    device_type: str | None = typer.Option(None, "--type"),
    manufacturer: str | None = typer.Option(None),
    model: str | None = typer.Option(None),
    serial_number: str | None = typer.Option(None, "--serial"),
    location: str | None = typer.Option(None),
    assigned_to: str | None = typer.Option(None, "--assigned-to"),
    purchase_date: str | None = typer.Option(None, help="YYYY-MM-DD or empty to clear."),
    warranty_expiry: str | None = typer.Option(None, help="YYYY-MM-DD or empty to clear."),
    notes: str | None = typer.Option(None),
    reason: str = typer.Option("Manual asset update", help="Reason recorded in audit history."),
) -> None:
    """Edit approved asset fields and record each change in audit history."""
    try:
        changes = db().update_asset(
            asset_tag,
            hostname=hostname,
            device_type=device_type,
            manufacturer=manufacturer,
            model=model,
            serial_number=serial_number,
            location=location,
            assigned_to=assigned_to,
            purchase_date=purchase_date,
            warranty_expiry=warranty_expiry,
            notes=notes,
            reason=reason,
        )
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc

    if not changes:
        console.print("[yellow]No values changed.[/yellow]")
        return

    table = Table(title=f"Updated {asset_tag.upper()}")
    table.add_column("Field")
    table.add_column("Old")
    table.add_column("New")
    for field, old_value, new_value in changes:
        table.add_row(field.replace("_", " ").title(), old_value, new_value)
    console.print(table)


@app.command()
def search(term: str) -> None:
    """Search tags, hostnames, hardware details, assignment and location."""
    print_assets(db().search(term))


@app.command()
def status(
    asset_tag: str,
    new_status: str,
    reason: str = typer.Option("", prompt=True),
) -> None:
    """Change an asset lifecycle status and record the event."""
    try:
        db().set_status(asset_tag, new_status, reason)
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    console.print(f"[green]Updated[/green] {asset_tag.upper()} -> {new_status.lower()}")


@app.command()
def history(asset_tag: str) -> None:
    """Show audit history for an asset."""
    try:
        rows = db().history(asset_tag)
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    table = Table(title=f"History: {asset_tag.upper()}")
    for heading in ("Time", "Event", "Old", "New", "Reason"):
        table.add_column(heading)
    for row in rows:
        table.add_row(
            row["created_at"],
            row["event_type"],
            row["old_value"] or "",
            row["new_value"] or "",
            row["reason"],
        )
    console.print(table)


@app.command()
def summary() -> None:
    """Show asset counts by lifecycle status."""
    rows = db().summary()
    table = Table(title="AMShell Summary")
    table.add_column("Status")
    table.add_column("Assets", justify="right")
    total = 0
    for row in rows:
        total += row["count"]
        table.add_row(row["status"], str(row["count"]))
    table.add_section()
    table.add_row("Total", str(total))
    console.print(table)


@app.command()
def warranty(
    days: int = typer.Option(
        90,
        min=0,
        help="Show expired or expiring warranties within this many days.",
    ),
) -> None:
    """Show expired and soon-to-expire warranties."""
    try:
        rows = db().warranty_report(days)
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc

    table = Table(title=f"Warranty Report: next {days} day(s)")
    for heading in (
        "Tag",
        "Hostname",
        "Model",
        "Status",
        "Warranty Expiry",
        "Days Remaining",
        "Approx. Age",
    ):
        table.add_column(heading)

    for row in rows:
        remaining = int(row["days_remaining"])
        remaining_text = f"expired {abs(remaining)}d ago" if remaining < 0 else f"{remaining}d"
        age_days = row["age_days"]
        age_text = "" if age_days is None else f"{int(age_days) / 365.25:.1f}y"
        table.add_row(
            str(row["asset_tag"]),
            str(row["hostname"]),
            f"{row['manufacturer']} {row['model']}",
            str(row["status"]),
            str(row["warranty_expiry"]),
            remaining_text,
            age_text,
        )
    console.print(table)


@backup_app.callback(invoke_without_command=True)
def backup_create(ctx: typer.Context) -> None:
    """Create a verified backup when no backup subcommand is supplied."""
    if ctx.invoked_subcommand is not None:
        return
    try:
        path = create_backup(DEFAULT_DB, DEFAULT_BACKUP_DIR)
    except BackupError as exc:
        console.print(f"[red]Backup failed:[/red] {exc}")
        raise typer.Exit(1) from exc
    console.print(f"[green]Backup created and verified:[/green] {path}")


@backup_app.command("list")
def backup_list() -> None:
    """List local AMShell database backups."""
    rows = list_backups(DEFAULT_BACKUP_DIR)
    table = Table(title="AMShell Backups")
    table.add_column("Backup")
    table.add_column("Size", justify="right")
    table.add_column("Modified")
    for item in rows:
        table.add_row(str(item.path), f"{item.size_bytes:,} B", item.modified_at)
    console.print(table)


@backup_app.command("verify")
def backup_verify(path: Path) -> None:
    """Run SQLite integrity_check against a backup file."""
    if verify_database(path):
        console.print(f"[green]Backup integrity check passed:[/green] {path}")
        return
    console.print(f"[red]Backup integrity check failed:[/red] {path}")
    raise typer.Exit(1)


@app.command()
def restore(
    backup_path: Path,
    yes: bool = typer.Option(False, "--yes", help="Skip the interactive restore confirmation."),
) -> None:
    """Restore a verified backup after creating a safety backup of the live database."""
    if not yes and not typer.confirm(
        f"Restore {backup_path} over {DEFAULT_DB}? A safety backup will be created first."
    ):
        console.print("Restore cancelled.")
        return

    try:
        safety_backup = restore_backup(DEFAULT_DB, backup_path, DEFAULT_BACKUP_DIR)
    except BackupError as exc:
        console.print(f"[red]Restore failed:[/red] {exc}")
        raise typer.Exit(1) from exc

    console.print(f"[green]Restore completed and verified:[/green] {DEFAULT_DB}")
    if safety_backup is not None:
        console.print(f"[dim]Pre-restore safety backup: {safety_backup}[/dim]")


@app.command()
def discover(
    add_to_inventory: bool = typer.Option(
        False,
        "--add",
        help="After discovery, prompt for an asset tag and add the local device.",
    ),
) -> None:
    """Discover read-only hardware and OS details from the local Windows host."""
    try:
        device = discover_local_windows_device()
    except DiscoveryError as exc:
        console.print(f"[red]Discovery failed:[/red] {exc}")
        raise typer.Exit(1) from exc

    table = Table(title="Local Windows Device", show_header=False)
    table.add_column("Field", style="bold")
    table.add_column("Value")
    values = (
        ("Hostname", device.hostname),
        ("Manufacturer", device.manufacturer),
        ("Model", device.model),
        ("Serial Number", device.serial_number),
        ("Operating System", device.os_caption),
        ("OS Version", device.os_version),
        ("Memory", f"{device.total_memory_gb:.1f} GB"),
        ("Processor", device.processor),
    )
    for field, value in values:
        table.add_row(field, value)
    console.print(table)

    if not add_to_inventory:
        console.print("[dim]Read-only discovery complete; inventory was not changed.[/dim]")
        return

    asset_tag = typer.prompt("Asset tag")
    device_type = typer.prompt("Device type", default="Laptop")
    try:
        asset = db().add_asset(
            Asset(
                asset_tag=asset_tag,
                hostname=device.hostname,
                device_type=device_type,
                manufacturer=device.manufacturer,
                model=device.model,
                serial_number=device.serial_number,
                status="in-stock",
                notes=(
                    f"Discovered locally by AMShell; {device.os_caption} "
                    f"{device.os_version}; {device.total_memory_gb:.1f} GB RAM; "
                    f"{device.processor}"
                ),
            )
        )
    except ValueError as exc:
        console.print(f"[red]Could not add discovered device:[/red] {exc}")
        raise typer.Exit(1) from exc
    console.print(f"[green]Added discovered device:[/green] {asset.asset_tag}")


@app.command("import-csv")
def import_csv(source: Path) -> None:
    """Import sanitised asset records from CSV."""
    database = db()
    try:
        added, errors = database.import_csv(source)
    except OSError as exc:
        console.print(f"[red]Import failed:[/red] {exc}")
        raise typer.Exit(1) from exc
    console.print(f"[green]Imported {added} asset(s).[/green]")
    for error in errors:
        console.print(f"[yellow]{error}[/yellow]")


@app.command("export-csv")
def export_csv(destination: Path) -> None:
    """Export the current inventory to CSV."""
    count = db().export_csv(destination)
    console.print(f"[green]Exported {count} asset(s):[/green] {destination}")


if __name__ == "__main__":
    app()
