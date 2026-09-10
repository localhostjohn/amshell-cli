import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from typer.testing import CliRunner

from amshell import snapshot_cli
from amshell.snapshot_cli import app
from amshell.snapshots import get_snapshot_status

runner = CliRunner()


def _write_snapshot(directory: Path, created_at: datetime, name: str = "snapshot-test.json") -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    payload = {
        "schema": "amshell.inventory-snapshot",
        "version": 1,
        "created_at": created_at.replace(microsecond=0).isoformat(),
        "asset_count": 0,
        "assets": [],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_snapshot_status_is_healthy_for_recent_snapshot(tmp_path: Path) -> None:
    _write_snapshot(tmp_path, datetime.now(UTC) - timedelta(hours=2))

    result = get_snapshot_status(tmp_path, max_age_hours=24)

    assert result.healthy is True
    assert result.latest is not None
    assert result.age_hours is not None
    assert result.age_hours < 24


def test_snapshot_status_is_unhealthy_for_stale_snapshot(tmp_path: Path) -> None:
    _write_snapshot(tmp_path, datetime.now(UTC) - timedelta(hours=50))

    result = get_snapshot_status(tmp_path, max_age_hours=24)

    assert result.healthy is False
    assert result.latest is not None
    assert result.age_hours is not None
    assert result.age_hours > 24


def test_snapshot_status_is_unhealthy_when_none_exist(tmp_path: Path) -> None:
    result = get_snapshot_status(tmp_path, max_age_hours=24)

    assert result.healthy is False
    assert result.latest is None
    assert result.age_hours is None


def test_snapshot_status_rejects_invalid_threshold(tmp_path: Path) -> None:
    try:
        get_snapshot_status(tmp_path, max_age_hours=0)
    except ValueError as exc:
        assert "at least 1" in str(exc)
    else:
        raise AssertionError("Expected invalid max_age_hours to be rejected")


def test_cli_snapshot_status_returns_success_for_recent_snapshot(
    tmp_path: Path, monkeypatch
) -> None:
    _write_snapshot(tmp_path, datetime.now(UTC) - timedelta(hours=1))
    monkeypatch.setattr(snapshot_cli, "DEFAULT_SNAPSHOT_DIR", tmp_path)

    result = runner.invoke(app, ["snapshot", "status", "--max-age-hours", "24"])

    assert result.exit_code == 0
    assert "HEALTHY" in result.stdout


def test_cli_snapshot_status_returns_failure_when_no_snapshot(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(snapshot_cli, "DEFAULT_SNAPSHOT_DIR", tmp_path)

    result = runner.invoke(app, ["snapshot", "status", "--max-age-hours", "24"])

    assert result.exit_code == 1
    assert "UNHEALTHY" in result.stdout
