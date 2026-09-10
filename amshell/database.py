from __future__ import annotations

import csv
import sqlite3
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from .models import Asset, utc_now

EDITABLE_FIELDS = (
    "hostname",
    "device_type",
    "manufacturer",
    "model",
    "serial_number",
    "location",
    "assigned_to",
    "purchase_date",
    "warranty_expiry",
    "notes",
)


class AssetDatabase:
    def __init__(self, path: str | Path = "data/amshell.db") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        with self.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS assets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    asset_tag TEXT NOT NULL UNIQUE,
                    hostname TEXT NOT NULL DEFAULT '',
                    device_type TEXT NOT NULL,
                    manufacturer TEXT NOT NULL,
                    model TEXT NOT NULL,
                    serial_number TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL,
                    location TEXT NOT NULL DEFAULT '',
                    assigned_to TEXT NOT NULL DEFAULT '',
                    purchase_date TEXT NOT NULL DEFAULT '',
                    warranty_expiry TEXT NOT NULL DEFAULT '',
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS asset_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    asset_id INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    old_value TEXT,
                    new_value TEXT,
                    reason TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(asset_id) REFERENCES assets(id) ON DELETE CASCADE
                );
                """
            )
            columns = {row["name"] for row in db.execute("PRAGMA table_info(assets)")}
            if "purchase_date" not in columns:
                db.execute("ALTER TABLE assets ADD COLUMN purchase_date TEXT NOT NULL DEFAULT ''")
            if "warranty_expiry" not in columns:
                db.execute("ALTER TABLE assets ADD COLUMN warranty_expiry TEXT NOT NULL DEFAULT ''")

    def add_asset(self, asset: Asset) -> Asset:
        asset.validate()
        now = utc_now()
        try:
            with self.connect() as db:
                cursor = db.execute(
                    """
                    INSERT INTO assets (
                        asset_tag, hostname, device_type, manufacturer, model,
                        serial_number, status, location, assigned_to,
                        purchase_date, warranty_expiry, notes, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        asset.asset_tag,
                        asset.hostname,
                        asset.device_type,
                        asset.manufacturer,
                        asset.model,
                        asset.serial_number,
                        asset.status,
                        asset.location,
                        asset.assigned_to,
                        asset.purchase_date,
                        asset.warranty_expiry,
                        asset.notes,
                        now,
                        now,
                    ),
                )
                asset.id = int(cursor.lastrowid)
                asset.created_at = now
                asset.updated_at = now
                db.execute(
                    """
                    INSERT INTO asset_history
                    (asset_id, event_type, new_value, reason, created_at)
                    VALUES (?, 'created', ?, ?, ?)
                    """,
                    (asset.id, asset.status, "Asset added to inventory", now),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError("Asset tag and serial number must both be unique.") from exc
        return asset

    def get_asset(self, asset_tag: str) -> sqlite3.Row | None:
        with self.connect() as db:
            return db.execute(
                "SELECT * FROM assets WHERE asset_tag = ?",
                (asset_tag.strip().upper(),),
            ).fetchone()

    def list_assets(
        self, *, status: str | None = None, device_type: str | None = None
    ) -> list[sqlite3.Row]:
        clauses: list[str] = []
        params: list[str] = []
        if status:
            clauses.append("status = ?")
            params.append(status.strip().lower())
        if device_type:
            clauses.append("LOWER(device_type) = LOWER(?)")
            params.append(device_type.strip())
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        with self.connect() as db:
            return db.execute(
                f"SELECT * FROM assets{where} ORDER BY asset_tag",
                params,
            ).fetchall()

    def search(self, term: str) -> list[sqlite3.Row]:
        pattern = f"%{term.strip()}%"
        with self.connect() as db:
            return db.execute(
                """
                SELECT * FROM assets
                WHERE asset_tag LIKE ? OR hostname LIKE ? OR device_type LIKE ?
                   OR manufacturer LIKE ? OR model LIKE ? OR serial_number LIKE ?
                   OR assigned_to LIKE ? OR location LIKE ?
                ORDER BY asset_tag
                """,
                (pattern,) * 8,
            ).fetchall()

    def update_asset(
        self,
        asset_tag: str,
        *,
        hostname: str | None = None,
        device_type: str | None = None,
        manufacturer: str | None = None,
        model: str | None = None,
        serial_number: str | None = None,
        location: str | None = None,
        assigned_to: str | None = None,
        purchase_date: str | None = None,
        warranty_expiry: str | None = None,
        notes: str | None = None,
        reason: str = "Manual asset update",
    ) -> list[tuple[str, str, str]]:
        row = self.get_asset(asset_tag)
        if row is None:
            raise ValueError(f"Asset '{asset_tag}' was not found.")

        requested = {
            "hostname": hostname,
            "device_type": device_type,
            "manufacturer": manufacturer,
            "model": model,
            "serial_number": serial_number,
            "location": location,
            "assigned_to": assigned_to,
            "purchase_date": purchase_date,
            "warranty_expiry": warranty_expiry,
            "notes": notes,
        }
        updates = {field: value for field, value in requested.items() if value is not None}
        if not updates:
            raise ValueError("No editable fields were supplied.")

        candidate = Asset(
            asset_tag=row["asset_tag"],
            hostname=updates.get("hostname", row["hostname"]),
            device_type=updates.get("device_type", row["device_type"]),
            manufacturer=updates.get("manufacturer", row["manufacturer"]),
            model=updates.get("model", row["model"]),
            serial_number=updates.get("serial_number", row["serial_number"]),
            status=row["status"],
            location=updates.get("location", row["location"]),
            assigned_to=updates.get("assigned_to", row["assigned_to"]),
            purchase_date=updates.get("purchase_date", row["purchase_date"]),
            warranty_expiry=updates.get("warranty_expiry", row["warranty_expiry"]),
            notes=updates.get("notes", row["notes"]),
        )
        candidate.validate()

        normalized = {field: getattr(candidate, field) for field in EDITABLE_FIELDS}
        changes = [
            (field, str(row[field]), normalized[field])
            for field in updates
            if str(row[field]) != normalized[field]
        ]
        if not changes:
            return []

        now = utc_now()
        assignments = ", ".join(f"{field} = ?" for field, _, _ in changes)
        values = [new_value for _, _, new_value in changes]
        values.extend((now, row["id"]))

        try:
            with self.connect() as db:
                db.execute(
                    f"UPDATE assets SET {assignments}, updated_at = ? WHERE id = ?",
                    values,
                )
                for field, old_value, new_value in changes:
                    db.execute(
                        """
                        INSERT INTO asset_history
                        (asset_id, event_type, old_value, new_value, reason, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            row["id"],
                            f"field-change:{field}",
                            old_value,
                            new_value,
                            reason.strip(),
                            now,
                        ),
                    )
        except sqlite3.IntegrityError as exc:
            raise ValueError("The updated serial number must be unique.") from exc

        return changes

    def set_status(self, asset_tag: str, new_status: str, reason: str = "") -> None:
        row = self.get_asset(asset_tag)
        if row is None:
            raise ValueError(f"Asset '{asset_tag}' was not found.")
        probe = Asset(
            asset_tag=row["asset_tag"],
            hostname=row["hostname"],
            device_type=row["device_type"],
            manufacturer=row["manufacturer"],
            model=row["model"],
            serial_number=row["serial_number"],
            status=new_status,
            location=row["location"],
            assigned_to=row["assigned_to"],
            purchase_date=row["purchase_date"],
            warranty_expiry=row["warranty_expiry"],
            notes=row["notes"],
        )
        probe.validate()
        now = utc_now()
        with self.connect() as db:
            db.execute(
                "UPDATE assets SET status = ?, updated_at = ? WHERE id = ?",
                (probe.status, now, row["id"]),
            )
            db.execute(
                """
                INSERT INTO asset_history
                (asset_id, event_type, old_value, new_value, reason, created_at)
                VALUES (?, 'status-change', ?, ?, ?, ?)
                """,
                (row["id"], row["status"], probe.status, reason.strip(), now),
            )

    def history(self, asset_tag: str) -> list[sqlite3.Row]:
        asset = self.get_asset(asset_tag)
        if asset is None:
            raise ValueError(f"Asset '{asset_tag}' was not found.")
        with self.connect() as db:
            return db.execute(
                """
                SELECT event_type, old_value, new_value, reason, created_at
                FROM asset_history
                WHERE asset_id = ?
                ORDER BY id
                """,
                (asset["id"],),
            ).fetchall()

    def summary(self) -> list[sqlite3.Row]:
        with self.connect() as db:
            return db.execute(
                "SELECT status, COUNT(*) AS count FROM assets GROUP BY status ORDER BY status"
            ).fetchall()

    def warranty_report(self, days: int = 90) -> list[dict[str, object]]:
        if days < 0:
            raise ValueError("Warranty window must be zero or greater.")
        today = datetime.now(UTC).date()
        cutoff = today + timedelta(days=days)
        with self.connect() as db:
            rows = db.execute(
                """
                SELECT asset_tag, hostname, manufacturer, model, status,
                       purchase_date, warranty_expiry
                FROM assets
                WHERE warranty_expiry != ''
                ORDER BY warranty_expiry, asset_tag
                """
            ).fetchall()

        report: list[dict[str, object]] = []
        for row in rows:
            expiry = date.fromisoformat(row["warranty_expiry"])
            if expiry <= cutoff:
                age_days = None
                if row["purchase_date"]:
                    age_days = (today - date.fromisoformat(row["purchase_date"])).days
                report.append(
                    {
                        "asset_tag": row["asset_tag"],
                        "hostname": row["hostname"],
                        "manufacturer": row["manufacturer"],
                        "model": row["model"],
                        "status": row["status"],
                        "warranty_expiry": row["warranty_expiry"],
                        "days_remaining": (expiry - today).days,
                        "age_days": age_days,
                    }
                )
        return report

    def export_csv(self, destination: str | Path) -> int:
        rows = self.list_assets()
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        fields = [
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
        ]
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for row in rows:
                writer.writerow({field: row[field] for field in fields})
        return len(rows)

    def import_csv(self, source: str | Path) -> tuple[int, list[str]]:
        added = 0
        errors: list[str] = []
        with Path(source).open("r", newline="", encoding="utf-8-sig") as handle:
            for line_number, row in enumerate(csv.DictReader(handle), start=2):
                try:
                    self.add_asset(
                        Asset(
                            asset_tag=row.get("asset_tag", ""),
                            hostname=row.get("hostname", ""),
                            device_type=row.get("device_type", ""),
                            manufacturer=row.get("manufacturer", ""),
                            model=row.get("model", ""),
                            serial_number=row.get("serial_number", ""),
                            status=row.get("status", "in-stock") or "in-stock",
                            location=row.get("location", ""),
                            assigned_to=row.get("assigned_to", ""),
                            purchase_date=row.get("purchase_date", ""),
                            warranty_expiry=row.get("warranty_expiry", ""),
                            notes=row.get("notes", ""),
                        )
                    )
                    added += 1
                except (KeyError, ValueError) as exc:
                    errors.append(f"Line {line_number}: {exc}")
        return added, errors
