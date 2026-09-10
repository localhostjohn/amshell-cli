from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

import amshell.cli as cli_module
from amshell.app import app
from amshell.database import AssetDatabase
from amshell.models import Asset

runner = CliRunner()


def test_cli_init_creates_database(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "data" / "amshell.db"
    monkeypatch.setattr(cli_module, "DEFAULT_DB", database_path)

    result = runner.invoke(app, ["init"])

    assert result.exit_code == 0
    assert database_path.exists()
    assert "database ready" in result.stdout.lower()


def test_cli_export_json_writes_versioned_inventory(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "data" / "amshell.db"
    monkeypatch.setattr(cli_module, "DEFAULT_DB", database_path)
    database = AssetDatabase(database_path)
    database.initialize()
    database.add_asset(
        Asset(
            asset_tag="AST001",
            hostname="ASTRA-PC01",
            device_type="Laptop",
            manufacturer="ExampleCorp",
            model="LabBook 14",
            serial_number="SERIAL001",
        )
    )
    destination = tmp_path / "exports" / "assets.json"

    result = runner.invoke(app, ["export-json", str(destination)])

    assert result.exit_code == 0
    assert "exported 1 asset" in result.stdout.lower()
    payload = json.loads(destination.read_text(encoding="utf-8"))
    assert payload["asset_count"] == 1
    assert payload["assets"][0]["asset_tag"] == "AST001"


def test_cli_report_json_filters_inventory(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "data" / "amshell.db"
    monkeypatch.setattr(cli_module, "DEFAULT_DB", database_path)
    database = AssetDatabase(database_path)
    database.initialize()
    database.add_asset(
        Asset(
            asset_tag="AST001",
            hostname="ASTRA-PC01",
            device_type="Laptop",
            manufacturer="ExampleCorp",
            model="LabBook 14",
            serial_number="SERIAL001",
            status="assigned",
        )
    )
    database.add_asset(
        Asset(
            asset_tag="AST002",
            hostname="ASTRA-PC02",
            device_type="Desktop",
            manufacturer="ExampleCorp",
            model="LabDesk",
            serial_number="SERIAL002",
            status="in-stock",
        )
    )

    result = runner.invoke(app, ["report", "--status", "assigned", "--format", "json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["summary"]["asset_count"] == 1
    assert payload["assets"][0]["asset_tag"] == "AST001"


def test_cli_report_rejects_unknown_format(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "data" / "amshell.db"
    monkeypatch.setattr(cli_module, "DEFAULT_DB", database_path)

    result = runner.invoke(app, ["report", "--format", "xml"])

    assert result.exit_code == 2
    assert "table" in result.stdout.lower()
    assert "json" in result.stdout.lower()


def test_cli_show_missing_asset_returns_error(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "data" / "amshell.db"
    monkeypatch.setattr(cli_module, "DEFAULT_DB", database_path)

    result = runner.invoke(app, ["show", "AST999"])

    assert result.exit_code == 1
    assert "asset not found" in result.stdout.lower()
