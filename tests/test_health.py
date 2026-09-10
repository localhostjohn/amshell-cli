from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from amshell.backup import create_backup
from amshell.database import AssetDatabase
from amshell.health import run_health_checks


def test_doctor_reports_healthy_database_and_recent_backup(tmp_path: Path) -> None:
    database_path = tmp_path / "data" / "amshell.db"
    backup_dir = tmp_path / "backups"
    database = AssetDatabase(database_path)
    database.initialize()
    create_backup(database_path, backup_dir)

    report = run_health_checks(database_path, backup_dir, max_backup_age_days=7)

    statuses = {check.name: check.status for check in report.checks}
    assert statuses["Database"] == "PASS"
    assert statuses["Schema"] == "PASS"
    assert statuses["Backup"] == "PASS"
    assert report.has_failures is False


def test_doctor_fails_when_database_is_missing(tmp_path: Path) -> None:
    report = run_health_checks(
        tmp_path / "missing.db",
        tmp_path / "backups",
        max_backup_age_days=7,
    )

    statuses = {check.name: check.status for check in report.checks}
    assert statuses["Database"] == "FAIL"
    assert statuses["Schema"] == "FAIL"
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


def test_doctor_fails_for_incomplete_schema(tmp_path: Path) -> None:
    database_path = tmp_path / "broken-schema.db"
    database_path.parent.mkdir(parents=True, exist_ok=True)

    import sqlite3

    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE assets (id INTEGER PRIMARY KEY)")

    report = run_health_checks(database_path, tmp_path / "backups")

    schema_check = next(check for check in report.checks if check.name == "Schema")
    assert schema_check.status == "FAIL"
    assert "Missing required asset column" in schema_check.detail
