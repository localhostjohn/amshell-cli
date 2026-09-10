from __future__ import annotations

import json
from pathlib import Path

from amshell.database import AssetDatabase
from amshell.exporting import EXPORT_SCHEMA, EXPORT_VERSION, export_inventory_json
from amshell.models import Asset


def make_db(tmp_path: Path) -> AssetDatabase:
    database = AssetDatabase(tmp_path / "amshell.db")
    database.initialize()
    return database


def test_json_export_has_versioned_schema_and_assets(tmp_path: Path) -> None:
    database = make_db(tmp_path)
    database.add_asset(
        Asset(
            asset_tag="AST001",
            hostname="ASTRA-PC01",
            device_type="Laptop",
            manufacturer="ExampleCorp",
            model="LabBook 14",
            serial_number="SERIAL001",
            status="assigned",
            assigned_to="Lab User",
        )
    )
    destination = tmp_path / "exports" / "inventory.json"

    count = export_inventory_json(database.list_assets(), destination)

    assert count == 1
    payload = json.loads(destination.read_text(encoding="utf-8"))
    assert payload["schema"] == EXPORT_SCHEMA
    assert payload["version"] == EXPORT_VERSION
    assert payload["asset_count"] == 1
    assert payload["exported_at"].endswith("+00:00")
    assert payload["assets"][0]["asset_tag"] == "AST001"
    assert payload["assets"][0]["assigned_to"] == "Lab User"


def test_json_export_empty_inventory_is_valid(tmp_path: Path) -> None:
    database = make_db(tmp_path)
    destination = tmp_path / "inventory.json"

    assert export_inventory_json(database.list_assets(), destination) == 0

    payload = json.loads(destination.read_text(encoding="utf-8"))
    assert payload["asset_count"] == 0
    assert payload["assets"] == []
