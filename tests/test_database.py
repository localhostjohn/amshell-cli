from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from amshell.database import AssetDatabase
from amshell.models import Asset


def make_db(tmp_path: Path) -> AssetDatabase:
    database = AssetDatabase(tmp_path / "amshell.db")
    database.initialize()
    return database


def sample_asset(tag: str = "AST001", serial: str = "SERIAL001") -> Asset:
    return Asset(
        asset_tag=tag,
        hostname="ASTRA-PC01",
        device_type="Laptop",
        manufacturer="ExampleCorp",
        model="LabBook 14",
        serial_number=serial,
        location="Lab",
    )


def test_add_and_get_asset(tmp_path: Path) -> None:
    database = make_db(tmp_path)
    database.add_asset(sample_asset())

    row = database.get_asset("ast001")

    assert row is not None
    assert row["asset_tag"] == "AST001"
    assert row["serial_number"] == "SERIAL001"
    assert row["status"] == "in-stock"


def test_duplicate_asset_tag_is_rejected(tmp_path: Path) -> None:
    database = make_db(tmp_path)
    database.add_asset(sample_asset())

    with pytest.raises(ValueError, match="unique"):
        database.add_asset(sample_asset(serial="SERIAL002"))


def test_duplicate_serial_is_rejected(tmp_path: Path) -> None:
    database = make_db(tmp_path)
    database.add_asset(sample_asset())

    with pytest.raises(ValueError, match="unique"):
        database.add_asset(sample_asset(tag="AST002"))


def test_status_change_creates_history(tmp_path: Path) -> None:
    database = make_db(tmp_path)
    database.add_asset(sample_asset())

    database.set_status("AST001", "repair", "Battery fault")

    row = database.get_asset("AST001")
    assert row["status"] == "repair"
    events = database.history("AST001")
    assert len(events) == 2
    assert events[-1]["event_type"] == "status-change"
    assert events[-1]["old_value"] == "in-stock"
    assert events[-1]["new_value"] == "repair"
    assert events[-1]["reason"] == "Battery fault"


def test_update_asset_records_each_field_change(tmp_path: Path) -> None:
    database = make_db(tmp_path)
    database.add_asset(sample_asset())

    changes = database.update_asset(
        "AST001",
        hostname="astra-pc02",
        assigned_to="Lab User",
        location="Bench 2",
        reason="Device reassigned",
    )

    assert changes == [
        ("hostname", "ASTRA-PC01", "ASTRA-PC02"),
        ("location", "Lab", "Bench 2"),
        ("assigned_to", "", "Lab User"),
    ]
    row = database.get_asset("AST001")
    assert row["hostname"] == "ASTRA-PC02"
    assert row["assigned_to"] == "Lab User"
    assert row["location"] == "Bench 2"

    events = database.history("AST001")
    assert [event["event_type"] for event in events[-3:]] == [
        "field-change:hostname",
        "field-change:location",
        "field-change:assigned_to",
    ]
    assert all(event["reason"] == "Device reassigned" for event in events[-3:])


def test_update_asset_allows_clearing_optional_field(tmp_path: Path) -> None:
    database = make_db(tmp_path)
    asset = sample_asset()
    asset.assigned_to = "Lab User"
    database.add_asset(asset)

    changes = database.update_asset(
        "AST001",
        assigned_to="",
        reason="Returned to stock",
    )

    assert changes == [("assigned_to", "Lab User", "")]
    assert database.get_asset("AST001")["assigned_to"] == ""


def test_update_asset_rejects_duplicate_serial(tmp_path: Path) -> None:
    database = make_db(tmp_path)
    database.add_asset(sample_asset())
    database.add_asset(sample_asset(tag="AST002", serial="SERIAL002"))

    with pytest.raises(ValueError, match="serial number must be unique"):
        database.update_asset("AST002", serial_number="SERIAL001")

    assert database.get_asset("AST002")["serial_number"] == "SERIAL002"


def test_update_asset_requires_a_field(tmp_path: Path) -> None:
    database = make_db(tmp_path)
    database.add_asset(sample_asset())

    with pytest.raises(ValueError, match="No editable fields"):
        database.update_asset("AST001")


def test_warranty_dates_are_audited(tmp_path: Path) -> None:
    database = make_db(tmp_path)
    database.add_asset(sample_asset())

    changes = database.update_asset(
        "AST001",
        purchase_date="2026-01-01",
        warranty_expiry="2029-01-01",
        reason="Procurement record added",
    )

    assert changes == [
        ("purchase_date", "", "2026-01-01"),
        ("warranty_expiry", "", "2029-01-01"),
    ]
    events = database.history("AST001")
    assert events[-2]["event_type"] == "field-change:purchase_date"
    assert events[-1]["event_type"] == "field-change:warranty_expiry"


def test_warranty_report_includes_expired_and_expiring_assets(tmp_path: Path) -> None:
    database = make_db(tmp_path)
    today = datetime.now(UTC).date()

    expired = sample_asset(tag="AST001", serial="SERIAL001")
    expired.purchase_date = (today - timedelta(days=900)).isoformat()
    expired.warranty_expiry = (today - timedelta(days=5)).isoformat()
    database.add_asset(expired)

    expiring = sample_asset(tag="AST002", serial="SERIAL002")
    expiring.purchase_date = (today - timedelta(days=600)).isoformat()
    expiring.warranty_expiry = (today + timedelta(days=30)).isoformat()
    database.add_asset(expiring)

    later = sample_asset(tag="AST003", serial="SERIAL003")
    later.warranty_expiry = (today + timedelta(days=180)).isoformat()
    database.add_asset(later)

    report = database.warranty_report(90)

    assert [row["asset_tag"] for row in report] == ["AST001", "AST002"]
    assert report[0]["days_remaining"] == -5
    assert report[1]["days_remaining"] == 30
    assert report[0]["age_days"] == 900


def test_warranty_report_rejects_negative_window(tmp_path: Path) -> None:
    database = make_db(tmp_path)

    with pytest.raises(ValueError, match="zero or greater"):
        database.warranty_report(-1)


def test_search_matches_model_and_hostname(tmp_path: Path) -> None:
    database = make_db(tmp_path)
    database.add_asset(sample_asset())

    assert len(database.search("LabBook")) == 1
    assert len(database.search("ASTRA-PC01")) == 1
    assert database.search("does-not-exist") == []


def test_export_and_import_round_trip(tmp_path: Path) -> None:
    source = make_db(tmp_path / "source")
    asset = sample_asset()
    asset.purchase_date = "2026-01-01"
    asset.warranty_expiry = "2029-01-01"
    source.add_asset(asset)
    csv_path = tmp_path / "assets.csv"

    assert source.export_csv(csv_path) == 1

    target = make_db(tmp_path / "target")
    added, errors = target.import_csv(csv_path)

    assert added == 1
    assert errors == []
    imported = target.get_asset("AST001")
    assert imported is not None
    assert imported["purchase_date"] == "2026-01-01"
    assert imported["warranty_expiry"] == "2029-01-01"
