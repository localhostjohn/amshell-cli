from __future__ import annotations

import platform
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .backup import list_backups, verify_database

REQUIRED_ASSET_COLUMNS = {
    "id",
    "asset_tag",
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
}


@dataclass(frozen=True, slots=True)
class HealthCheck:
    name: str
    status: str
    detail: str


@dataclass(frozen=True, slots=True)
class HealthReport:
    checks: tuple[HealthCheck, ...]

    @property
    def has_failures(self) -> bool:
        return any(check.status == "FAIL" for check in self.checks)

    @property
    def warning_count(self) -> int:
        return sum(check.status == "WARN" for check in self.checks)


def _schema_check(database_path: Path) -> HealthCheck:
    try:
        uri = f"file:{database_path.resolve().as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True) as connection:
            rows = connection.execute("PRAGMA table_info(assets)").fetchall()
    except sqlite3.DatabaseError as exc:
        return HealthCheck("Schema", "FAIL", f"Unable to inspect schema: {exc}")

    columns = {str(row[1]) for row in rows}
    missing = sorted(REQUIRED_ASSET_COLUMNS - columns)
    if missing:
        return HealthCheck(
            "Schema",
            "FAIL",
            f"Missing required asset column(s): {', '.join(missing)}",
        )
    return HealthCheck("Schema", "PASS", "Required assets table columns are present.")


def _backup_check(backup_dir: Path, max_age_days: int) -> HealthCheck:
    backups = list_backups(backup_dir)
    if not backups:
        return HealthCheck("Backup", "WARN", "No local database backups were found.")

    newest = backups[0]
    try:
        modified = datetime.fromisoformat(newest.modified_at)
    except ValueError:
        return HealthCheck("Backup", "WARN", f"Latest backup timestamp is invalid: {newest.path}")

    age = datetime.now(UTC) - modified.astimezone(UTC)
    age_days = max(0, age.days)
    if age_days > max_age_days:
        return HealthCheck(
            "Backup",
            "WARN",
            f"Latest backup is {age_days} day(s) old: {newest.path}",
        )
    return HealthCheck(
        "Backup",
        "PASS",
        f"Latest backup is {age_days} day(s) old: {newest.path}",
    )


def run_health_checks(
    database_path: str | Path,
    backup_dir: str | Path,
    *,
    max_backup_age_days: int = 7,
) -> HealthReport:
    database = Path(database_path)
    backups = Path(backup_dir)
    checks: list[HealthCheck] = []

    if not database.is_file():
        checks.append(HealthCheck("Database", "FAIL", f"Database does not exist: {database}"))
        checks.append(HealthCheck("Schema", "FAIL", "Schema cannot be checked without a database."))
    elif not verify_database(database):
        checks.append(HealthCheck("Database", "FAIL", "SQLite integrity_check failed."))
        checks.append(HealthCheck("Schema", "FAIL", "Schema check skipped because integrity failed."))
    else:
        checks.append(HealthCheck("Database", "PASS", "SQLite integrity_check returned OK."))
        checks.append(_schema_check(database))

    checks.append(_backup_check(backups, max_backup_age_days))

    if platform.system() == "Windows":
        checks.append(
            HealthCheck(
                "Windows Discovery",
                "PASS",
                "Local PowerShell/CIM discovery is supported on this host.",
            )
        )
    else:
        checks.append(
            HealthCheck(
                "Windows Discovery",
                "WARN",
                "Local Windows discovery is unavailable on this operating system.",
            )
        )

    return HealthReport(tuple(checks))
