from pathlib import Path

from amshell.models import Asset
from amshell.snapshots import create_snapshot, diff_snapshots, list_snapshots, load_snapshot


def _asset(tag: str, hostname: str, status: str = "in-stock") -> dict[str, object]:
    asset = Asset(
        asset_tag=tag,
        hostname=hostname,
        device_type="Laptop",
        manufacturer="ExampleCorp",
        model="LabBook 14",
        serial_number=f"SERIAL-{tag}",
        status=status,
    )
    asset.validate()
    asset.created_at = "2026-09-09T20:00:00+00:00"
    asset.updated_at = "2026-09-09T20:00:00+00:00"
    return {
        "asset_tag": asset.asset_tag,
        "hostname": asset.hostname,
        "device_type": asset.device_type,
        "manufacturer": asset.manufacturer,
        "model": asset.model,
        "serial_number": asset.serial_number,
        "status": asset.status,
        "location": asset.location,
        "assigned_to": asset.assigned_to,
        "purchase_date": asset.purchase_date,
        "warranty_expiry": asset.warranty_expiry,
        "notes": asset.notes,
        "created_at": asset.created_at,
        "updated_at": asset.updated_at,
    }


def test_create_and_list_snapshot(tmp_path: Path) -> None:
    path = create_snapshot([_asset("AST001", "ASTRA-PC01")], tmp_path)
    payload = load_snapshot(path)

    assert payload["schema"] == "amshell.inventory-snapshot"
    assert payload["version"] == 1
    assert payload["asset_count"] == 1
    assert payload["assets"][0]["asset_tag"] == "AST001"

    snapshots = list_snapshots(tmp_path)
    assert len(snapshots) == 1
    assert snapshots[0].asset_count == 1


def test_diff_snapshots_reports_added_removed_and_changed(tmp_path: Path) -> None:
    older = create_snapshot(
        [_asset("AST001", "ASTRA-PC01"), _asset("AST002", "ASTRA-PC02")],
        tmp_path / "older",
    )
    newer = create_snapshot(
        [
            _asset("AST001", "ASTRA-RENAMED", status="assigned"),
            _asset("AST003", "ASTRA-PC03"),
        ],
        tmp_path / "newer",
    )

    result = diff_snapshots(older, newer)

    assert result.added == ("AST003",)
    assert result.removed == ("AST002",)
    assert result.changed["AST001"] == ("hostname", "status")
    assert result.has_changes is True


def test_diff_identical_snapshots_has_no_changes(tmp_path: Path) -> None:
    rows = [_asset("AST001", "ASTRA-PC01")]
    older = create_snapshot(rows, tmp_path / "older")
    newer = create_snapshot(rows, tmp_path / "newer")

    result = diff_snapshots(older, newer)

    assert result.has_changes is False
    assert result.added == ()
    assert result.removed == ()
    assert result.changed == {}


def test_load_snapshot_rejects_invalid_format(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text('{"schema":"other","version":1,"assets":[]}', encoding="utf-8")

    try:
        load_snapshot(path)
    except ValueError as exc:
        assert "Unsupported AMShell snapshot format" in str(exc)
    else:
        raise AssertionError("Expected invalid snapshot to be rejected")
