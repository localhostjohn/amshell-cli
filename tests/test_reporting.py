from datetime import date

from amshell.reporting import build_operational_report


def _row(**overrides):
    row = {
        "asset_tag": "AST001",
        "hostname": "ASTRA-PC01",
        "device_type": "Laptop",
        "manufacturer": "Astra Labs",
        "model": "Model A",
        "serial_number": "LAB001",
        "status": "assigned",
        "location": "Lab",
        "assigned_to": "User One",
        "purchase_date": "2025-01-01",
        "warranty_expiry": "2027-01-01",
    }
    row.update(overrides)
    return row


def test_report_filters_status_and_type():
    rows = [
        _row(),
        _row(asset_tag="AST002", device_type="Desktop", status="in-stock"),
    ]

    report = build_operational_report(
        rows,
        status="assigned",
        device_type="laptop",
        today=date(2026, 9, 9),
    )

    assert report.asset_count == 1
    assert report.status_counts == {"assigned": 1}
    assert report.type_counts == {"Laptop": 1}
    assert report.assets[0]["asset_tag"] == "AST001"


def test_report_counts_expired_and_expiring_warranties():
    rows = [
        _row(asset_tag="AST001", warranty_expiry="2026-09-01"),
        _row(asset_tag="AST002", warranty_expiry="2026-10-01"),
        _row(asset_tag="AST003", warranty_expiry="2027-06-01"),
    ]

    report = build_operational_report(rows, today=date(2026, 9, 9))

    assert report.warranty_expired == 1
    assert report.warranty_expiring_90_days == 1


def test_report_json_contract_is_versioned():
    report = build_operational_report([_row()], today=date(2026, 9, 9))

    payload = report.as_dict()

    assert payload["schema"] == "amshell.operational-report"
    assert payload["version"] == 1
    assert payload["summary"]["asset_count"] == 1
