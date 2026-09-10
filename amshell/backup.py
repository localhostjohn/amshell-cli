from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


class BackupError(RuntimeError):
    """Raised when a backup or restore operation cannot be completed safely."""


@dataclass(frozen=True, slots=True)
class BackupInfo:
    path: Path
    size_bytes: int
    modified_at: str


def verify_database(path: str | Path) -> bool:
    """Return True only when SQLite reports the database integrity check as OK."""
    database_path = Path(path)
    if not database_path.is_file():
        return False

    try:
        uri = f"file:{database_path.resolve().as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True) as connection:
            result = connection.execute("PRAGMA integrity_check").fetchone()
    except sqlite3.DatabaseError:
        return False

    return bool(result and result[0] == "ok")


def _timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")


def create_backup(
    database_path: str | Path,
    backup_dir: str | Path = "backups",
    *,
    prefix: str = "amshell",
) -> Path:
    """Create and verify a consistent SQLite backup using the SQLite backup API."""
    source_path = Path(database_path)
    if not source_path.is_file():
        raise BackupError(f"Database does not exist: {source_path}")
    if not verify_database(source_path):
        raise BackupError("Source database failed SQLite integrity_check.")

    destination_dir = Path(backup_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / f"{prefix}-{_timestamp()}.db"

    try:
        with sqlite3.connect(source_path) as source, sqlite3.connect(destination) as target:
            source.backup(target)
    except sqlite3.DatabaseError as exc:
        destination.unlink(missing_ok=True)
        raise BackupError(f"SQLite backup failed: {exc}") from exc

    if not verify_database(destination):
        destination.unlink(missing_ok=True)
        raise BackupError("Created backup failed SQLite integrity_check.")

    return destination


def list_backups(backup_dir: str | Path = "backups") -> list[BackupInfo]:
    directory = Path(backup_dir)
    if not directory.exists():
        return []

    backups: list[BackupInfo] = []
    for path in sorted(directory.glob("*.db"), key=lambda item: item.stat().st_mtime, reverse=True):
        stat = path.stat()
        modified = datetime.fromtimestamp(stat.st_mtime, UTC).replace(microsecond=0).isoformat()
        backups.append(BackupInfo(path=path, size_bytes=stat.st_size, modified_at=modified))
    return backups


def restore_backup(
    database_path: str | Path,
    backup_path: str | Path,
    backup_dir: str | Path = "backups",
) -> Path | None:
    """Restore a verified backup atomically, taking a safety backup first when possible."""
    live_path = Path(database_path)
    source_backup = Path(backup_path)

    if not source_backup.is_file():
        raise BackupError(f"Backup does not exist: {source_backup}")
    if not verify_database(source_backup):
        raise BackupError("Selected backup failed SQLite integrity_check; restore refused.")

    safety_backup: Path | None = None
    if live_path.is_file():
        if not verify_database(live_path):
            raise BackupError(
                "Current database failed SQLite integrity_check; automatic pre-restore backup refused."
            )
        safety_backup = create_backup(live_path, backup_dir, prefix="pre-restore")

    live_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=".amshell-restore-",
            suffix=".db",
            dir=live_path.parent,
            delete=False,
        ) as temp_handle:
            temp_path = Path(temp_handle.name)

        shutil.copy2(source_backup, temp_path)
        if not verify_database(temp_path):
            raise BackupError("Temporary restored copy failed SQLite integrity_check.")

        os.replace(temp_path, live_path)
        temp_path = None
        Path(f"{live_path}-wal").unlink(missing_ok=True)
        Path(f"{live_path}-shm").unlink(missing_ok=True)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)

    if not verify_database(live_path):
        raise BackupError("Restored database failed final SQLite integrity_check.")

    return safety_backup
