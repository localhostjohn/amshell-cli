import pytest

from amshell.models import Asset


def valid_asset(**overrides) -> Asset:
    values = {
        "asset_tag": " ast001 ",
        "hostname": " astra-pc01 ",
        "device_type": "Laptop",
        "manufacturer": "ExampleCorp",
        "model": "LabBook 14",
        "serial_number": " serial001 ",
        "status": "IN-STOCK",
    }
    values.update(overrides)
    return Asset(**values)


def test_validation_normalises_identifiers() -> None:
    asset = valid_asset()

    asset.validate()

    assert asset.asset_tag == "AST001"
    assert asset.hostname == "ASTRA-PC01"
    assert asset.serial_number == "SERIAL001"
    assert asset.status == "in-stock"


def test_validation_normalises_dates() -> None:
    asset = valid_asset(
        purchase_date="2026-01-05",
        warranty_expiry="2029-01-05",
    )

    asset.validate()

    assert asset.purchase_date == "2026-01-05"
    assert asset.warranty_expiry == "2029-01-05"


def test_validation_rejects_invalid_date_format() -> None:
    asset = valid_asset(purchase_date="05/01/2026")

    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        asset.validate()


def test_validation_rejects_warranty_before_purchase() -> None:
    asset = valid_asset(
        purchase_date="2026-01-05",
        warranty_expiry="2025-12-31",
    )

    with pytest.raises(ValueError, match="earlier than purchase"):
        asset.validate()


def test_validation_rejects_missing_required_fields() -> None:
    asset = valid_asset(model="")

    with pytest.raises(ValueError, match="model"):
        asset.validate()


def test_validation_rejects_unknown_status() -> None:
    asset = valid_asset(status="lost-in-space")

    with pytest.raises(ValueError, match="Invalid status"):
        asset.validate()
