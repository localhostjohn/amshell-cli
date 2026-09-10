from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime


@dataclass(frozen=True, slots=True)
class OperationalReport:
    generated_at: str
    filters: dict[str, str]
    asset_count: int
    status_counts: dict[str, int]
    type_counts: dict[str, int]
    warranty_expired: int
    warranty_expiring_90_days: int
    assets: tuple[dict[str, object], ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "schema": "amshell.operational-report",
            "version": 1,
            "generated_at": self.generated_at,
            "filters": self.filters,
            "summary": {
                "asset_count": self.asset_count,
                "status_counts": self.status_counts,
                "type_counts": self.type_counts,
                "warranty_expired": self.warranty_expired,
                "warranty_expiring_90_days": self.warranty_expiring_90_days,
            },
            "assets": list(self.assets),
        }


def _matches(value: object, expected: str | None) -> bool:
    if expected is None:
        return True
    return str(value or "").strip().casefold() == expected.strip().casefold()


def build_operational_report(
    rows: Iterable[Mapping[str, object]],
    *,
    status: str | None = None,
    device_type: str | None = None,
    today: date | None = None,
) -> OperationalReport:
    report_date = today or datetime.now(UTC).date()
    filters: dict[str, str] = {}
    if status:
        filters["status"] = status
    if device_type:
        filters["device_type"] = device_type

    selected: list[dict[str, object]] = []
    status_counts: Counter[str] = Counter()
    type_counts: Counter[str] = Counter()
    expired = 0
    expiring = 0

    for row in rows:
        if not _matches(row["status"], status):
            continue
        if not _matches(row["device_type"], device_type):
            continue

        asset = {
            "asset_tag": row["asset_tag"],
            "hostname": row["hostname"],
            "device_type": row["device_type"],
            "manufacturer": row["manufacturer"],
            "model": row["model"],
            "serial_number": row["serial_number"],
            "status": row["status"],
            "location": row["location"],
            "assigned_to": row["assigned_to"],
            "purchase_date": row["purchase_date"],
            "warranty_expiry": row["warranty_expiry"],
        }
        selected.append(asset)
        status_counts[str(row["status"])] += 1
        type_counts[str(row["device_type"])] += 1

        expiry_text = str(row["warranty_expiry"] or "").strip()
        if expiry_text:
            expiry = date.fromisoformat(expiry_text)
            remaining = (expiry - report_date).days
            if remaining < 0:
                expired += 1
            elif remaining <= 90:
                expiring += 1

    return OperationalReport(
        generated_at=datetime.now(UTC).replace(microsecond=0).isoformat(),
        filters=filters,
        asset_count=len(selected),
        status_counts=dict(sorted(status_counts.items())),
        type_counts=dict(sorted(type_counts.items())),
        warranty_expired=expired,
        warranty_expiring_90_days=expiring,
        assets=tuple(selected),
    )
