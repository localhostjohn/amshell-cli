from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime

ASSET_STATUSES = ("in-stock", "assigned", "repair", "loan", "retired", "disposed")


def normalize_date(value: str, field_name: str) -> str:
    value = value.strip()
    if not value:
        return ""
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise ValueError(f"{field_name} must use YYYY-MM-DD format.") from exc


@dataclass(slots=True)
class Asset:
    asset_tag: str
    device_type: str
    manufacturer: str
    model: str
    serial_number: str
    hostname: str = ""
    status: str = "in-stock"
    location: str = ""
    assigned_to: str = ""
    purchase_date: str = ""
    warranty_expiry: str = ""
    notes: str = ""
    id: int | None = None
    created_at: str | None = None
    updated_at: str | None = None

    def validate(self) -> None:
        self.asset_tag = self.asset_tag.strip().upper()
        self.serial_number = self.serial_number.strip().upper()
        self.device_type = self.device_type.strip()
        self.manufacturer = self.manufacturer.strip()
        self.model = self.model.strip()
        self.hostname = self.hostname.strip().upper()
        self.status = self.status.strip().lower()
        self.location = self.location.strip()
        self.assigned_to = self.assigned_to.strip()
        self.purchase_date = normalize_date(self.purchase_date, "Purchase date")
        self.warranty_expiry = normalize_date(self.warranty_expiry, "Warranty expiry")
        self.notes = self.notes.strip()

        required = {
            "asset tag": self.asset_tag,
            "device type": self.device_type,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "serial number": self.serial_number,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError(f"Missing required field(s): {', '.join(missing)}")
        if self.status not in ASSET_STATUSES:
            raise ValueError(
                f"Invalid status '{self.status}'. Choose one of: {', '.join(ASSET_STATUSES)}"
            )
        if (
            self.purchase_date
            and self.warranty_expiry
            and date.fromisoformat(self.warranty_expiry)
            < date.fromisoformat(self.purchase_date)
        ):
            raise ValueError("Warranty expiry cannot be earlier than purchase date.")


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
