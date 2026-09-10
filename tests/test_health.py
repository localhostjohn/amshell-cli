from __future__ import annotations

import os
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from amshell.backup import create_backup
from amshell.database import AssetDatabase
from amshell.health import run_health_checks
from amshell.models import Asset


def test_doctor_reports_healthy_database_and_recent_backup(tmp_path: Path) -> None:
    database_path = tmp_path / "data" / "amshell.db"
    backup_dir = tmp_path / "backups"
    database = AssetDatabase(database_path)
    database.initialize()
    database.add_asset(
        Asset(
            asset_tag="AST001",
            hostname="astra-lab-01",
            device_type="Laptop",
            manufacturer="Astra",
            model="LabBook",
            serial_number="ASTRA-SERIAL-001",
            status="in-stock",
        )
    )
    create_backup(database_path, backup_dir)

    report = run_health_checks(database_path, backup_dir, max_backup_age_days=7)

    statuses = {check.name: check.status for check in report.checks}
    assert statuses["Database"] == "PASS"
    assert statuses["Schema"] == "PASS"
    assert statuses["Inventory"] == "PASS"
    assert statuses["Backup"] == "PASS"
    assert report.has_failures is False


def test_doctor_warns_when_inventory_is_empty(tmp_path: Path) -> None:
    database_path = tmp_path / "amshell.db"
    database = AssetDatabase(database_path)
    database.initialize()

    report = run_health_checks(database_path, tmp_path / "backups")

    inventory_check = next(check for check in report.checks if check.name == "Inventory")
    assert inventory_check.status == "WARN"
    assert "empty" in inventory_check.detail


def test_doctor_fails_when_database_is_missing(tmp_path: Path) -> None:
    report = run_health_checks(
        tmp_path / "missing.db",
        tmp_path / "backups",
        max_backup_age_days=7,
    )

    statuses = {check.name: check.status for check in report.checks}
    assert statuses["Database"] == "FAIL"
    assert statuses["Schema"] == "FAIL"
    assert statuses["Inventory"] == "FAIL"
    assert statuses["Backup"] == "WARN"
    assert report.has_failures is True


def test_doctor_warns_when_backup_is_stale(tmp_path: Path) -> None:
    database_path = tmp_path / "amshell.db"
    backup_dir = tmp_path / "backups"
    database = AssetDatabase(database_path)
    database.initialize()
    backup = create_backup(database_path, backup_dir)

    stale_time = datetime.now(UTC) - timedelta(days=10)
    timestamp = stale_time.timestamp()
    os.utime(backup, (timestamp, timestamp))

    report = run_health_checks(database_path, backup_dir, max_backup_age_days=7)

    backup_check = next(check for check in report.checks if check.name == "Backup")
    assert backup_check.status == "WARN"
    assert "10 day(s) old" in backup_check.detail
    assert "verified backup" in backup_check.detail


def test_doctor_fails_when_latest_backup_is_corrupt(tmp_path: Path) -> None:
    database_path = tmp_path / "amshell.db"
    backup_dir = tmp_path / "backups"
    database = AssetDatabase(database_path)
    database.initialize()
    backup = create_backup(database_path, backup_dir)
    backup.write_bytes(b"not a sqlite database")

    report = run_health_checks(database_path, backup_dir)

    backup_check = next(check for check in report.checks if check.name == "Backup")
    assert backup_check.status == "FAIL"
    assert "integrity_check" in backup_check.detail
    assert report.has_failures is True


def test_doctor_fails_for_incomplete_asset_schema(tmp_path: Path) -> None:
    database_path = tmp_path / "broken-schema.db"
    database_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE assets (id INTEGER PRIMARY KEY)")

    report = run_health_checks(database_path, tmp_path / "backups")

    schema_check = next(check for check in report.checks if check.name == "Schema")
    assert schema_check.status == "FAIL"
    assert "Missing required asset column" in schema_check.detail


def test_doctor_fails_when_asset_history_schema_is_missing(tmp_path: Path) -> None:
    database_path = tmp_path / "missing-history.db"
    database = AssetDatabase(database_path)
    database.initialize()

    with sqlite3.connect(database_path) as connection:
        connection.execute("DROP TABLE asset_history")

    report = run_health_checks(database_path, tmp_path / "backups")

    schema_check = next(check for check in report.checks if check.name == "Schema")
    assert schema_check.status == "FAIL"
    assert "asset_history" in schema_check.detail
