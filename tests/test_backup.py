import sqlite3
from pathlib import Path

import pytest

from amshell.backup import BackupError, create_backup, list_backups, restore_backup, verify_database
from amshell.database import AssetDatabase
from amshell.models import Asset


def make_database(path: Path, *, tag: str, serial: str, model: str) -> AssetDatabase:
    database = AssetDatabase(path)
    database.initialize()
    database.add_asset(
        Asset(
            asset_tag=tag,
            hostname=f"{tag}-PC",
            device_type="Laptop",
            manufacturer="ExampleCorp",
            model=model,
            serial_number=serial,
            location="Lab",
        )
    )
    return database


def test_create_backup_is_valid_and_listed(tmp_path: Path) -> None:
    database_path = tmp_path / "amshell.db"
    backup_dir = tmp_path / "backups"
    make_database(database_path, tag="AST001", serial="SERIAL001", model="LabBook 14")

    backup_path = create_backup(database_path, backup_dir)

    assert backup_path.exists()
    assert verify_database(backup_path)
    backups = list_backups(backup_dir)
    assert len(backups) == 1
    assert backups[0].path == backup_path
    assert backups[0].size_bytes > 0


def test_restore_replaces_database_and_creates_safety_backup(tmp_path: Path) -> None:
    database_path = tmp_path / "amshell.db"
    backup_dir = tmp_path / "backups"
    database = make_database(
        database_path,
        tag="AST001",
        serial="SERIAL001",
        model="Original Model",
    )
    source_backup = create_backup(database_path, backup_dir)

    database.update_asset("AST001", model="Changed Model", reason="Test change")
    assert database.get_asset("AST001")["model"] == "Changed Model"

    safety_backup = restore_backup(database_path, source_backup, backup_dir)

    restored = AssetDatabase(database_path)
    restored.initialize()
    assert restored.get_asset("AST001")["model"] == "Original Model"
    assert safety_backup is not None
    assert safety_backup.exists()
    assert safety_backup.name.startswith("pre-restore-")

    safety_db = AssetDatabase(safety_backup)
    safety_db.initialize()
    assert safety_db.get_asset("AST001")["model"] == "Changed Model"


def test_restore_rejects_corrupt_backup_without_touching_live_database(tmp_path: Path) -> None:
    database_path = tmp_path / "amshell.db"
    backup_dir = tmp_path / "backups"
    live = make_database(database_path, tag="AST001", serial="SERIAL001", model="Safe Model")
    corrupt = tmp_path / "corrupt.db"
    corrupt.write_bytes(b"not a sqlite database")

    with pytest.raises(BackupError, match="integrity_check"):
        restore_backup(database_path, corrupt, backup_dir)

    assert live.get_asset("AST001")["model"] == "Safe Model"
    assert verify_database(database_path)


def test_create_backup_rejects_missing_database(tmp_path: Path) -> None:
    with pytest.raises(BackupError, match="does not exist"):
        create_backup(tmp_path / "missing.db", tmp_path / "backups")


def test_verify_database_returns_false_for_corrupt_file(tmp_path: Path) -> None:
    corrupt = tmp_path / "corrupt.db"
    corrupt.write_text("not sqlite", encoding="utf-8")

    assert verify_database(corrupt) is False


def test_restore_can_create_database_when_live_file_is_missing(tmp_path: Path) -> None:
    source_path = tmp_path / "source.db"
    backup_dir = tmp_path / "backups"
    make_database(source_path, tag="AST001", serial="SERIAL001", model="Recovered Model")
    source_backup = create_backup(source_path, backup_dir)

    target_path = tmp_path / "new" / "amshell.db"
    safety_backup = restore_backup(target_path, source_backup, backup_dir)

    assert safety_backup is None
    assert verify_database(target_path)
    recovered = AssetDatabase(target_path)
    recovered.initialize()
    assert recovered.get_asset("AST001")["model"] == "Recovered Model"


def test_create_backup_rejects_corrupt_source(tmp_path: Path) -> None:
    corrupt = tmp_path / "amshell.db"
    corrupt.write_bytes(b"bad database")

    with pytest.raises(BackupError, match="integrity_check"):
        create_backup(corrupt, tmp_path / "backups")


def test_sqlite_integrity_check_is_ok_for_test_database(tmp_path: Path) -> None:
    database_path = tmp_path / "amshell.db"
    make_database(database_path, tag="AST001", serial="SERIAL001", model="LabBook 14")

    with sqlite3.connect(database_path) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"



def test_restore_rolls_back_when_final_integrity_check_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from amshell import backup as backup_module

    database_path = tmp_path / "amshell.db"
    backup_dir = tmp_path / "backups"
    database = make_database(
        database_path,
        tag="AST001",
        serial="SERIAL001",
        model="Original Model",
    )
    source_backup = create_backup(database_path, backup_dir)
    database.update_asset("AST001", model="Changed Model", reason="Test change")

    real_verify = backup_module.verify_database
    live_checks = 0

    def verify_with_one_final_failure(path: str | Path) -> bool:
        nonlocal live_checks
        candidate = Path(path)
        if candidate == database_path:
            live_checks += 1
            if live_checks == 3:
                return False
        return real_verify(path)

    monkeypatch.setattr(backup_module, "verify_database", verify_with_one_final_failure)

    with pytest.raises(BackupError, match="Automatic rollback restored"):
        restore_backup(database_path, source_backup, backup_dir)

    restored = AssetDatabase(database_path)
    assert restored.get_asset("AST001")["model"] == "Changed Model"
    assert real_verify(database_path)


def test_restore_reports_when_automatic_rollback_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from amshell import backup as backup_module

    database_path = tmp_path / "amshell.db"
    backup_dir = tmp_path / "backups"
    database = make_database(
        database_path,
        tag="AST001",
        serial="SERIAL001",
        model="Original Model",
    )
    source_backup = create_backup(database_path, backup_dir)
    database.update_asset("AST001", model="Changed Model", reason="Test change")

    real_verify = backup_module.verify_database
    live_checks = 0

    def verify_with_final_and_rollback_failure(path: str | Path) -> bool:
        nonlocal live_checks
        candidate = Path(path)
        if candidate == database_path:
            live_checks += 1
            if live_checks >= 3:
                return False
        return real_verify(path)

    monkeypatch.setattr(backup_module, "verify_database", verify_with_final_and_rollback_failure)

    with pytest.raises(BackupError, match="automatic rollback failed") as exc_info:
        restore_backup(database_path, source_backup, backup_dir)

    assert "Safety backup remains available at:" in str(exc_info.value)
    assert any(path.name.startswith("pre-restore-") for path in backup_dir.glob("*.db"))


def test_restore_removes_new_database_when_final_check_fails_without_prior_live_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from amshell import backup as backup_module

    source_path = tmp_path / "source.db"
    backup_dir = tmp_path / "backups"
    make_database(source_path, tag="AST001", serial="SERIAL001", model="Recovered Model")
    source_backup = create_backup(source_path, backup_dir)
    target_path = tmp_path / "new" / "amshell.db"

    real_verify = backup_module.verify_database

    def verify_with_target_failure(path: str | Path) -> bool:
        if Path(path) == target_path:
            return False
        return real_verify(path)

    monkeypatch.setattr(backup_module, "verify_database", verify_with_target_failure)

    with pytest.raises(BackupError, match="removed the newly created live database"):
        restore_backup(target_path, source_backup, backup_dir)

    assert not target_path.exists()
