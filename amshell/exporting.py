from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from pathlib import Path

EXPORT_SCHEMA = "amshell.inventory"
EXPORT_VERSION = 1

ASSET_EXPORT_FIELDS = (
    "asset_tag",
    "hostname",
    "device_type",
    "manufacturer",
    "model",
    "serial_number",
    "status",
    "location",
    "assigned_to",
    "purchase_date",
    "warranty_expiry",
    "notes",
    "created_at",
    "updated_at",
)


def build_inventory_export(rows: Iterable[Mapping[str, object]]) -> dict[str, object]:
    assets = [{field: row[field] for field in ASSET_EXPORT_FIELDS} for row in rows]
    return {
        "schema": EXPORT_SCHEMA,
        "version": EXPORT_VERSION,
        "exported_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "asset_count": len(assets),
        "assets": assets,
    }


def export_inventory_json(
    rows: Iterable[Mapping[str, object]], destination: str | Path
) -> int:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_inventory_export(rows)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return int(payload["asset_count"])
