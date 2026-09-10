from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .discovery.windows import WindowsDevice


@dataclass(frozen=True, slots=True)
class DriftField:
    name: str
    stored: str
    observed: str
    matches: bool


@dataclass(frozen=True, slots=True)
class InventoryComparison:
    asset_tag: str
    fields: tuple[DriftField, ...]
    identity_match: bool
    os_caption: str
    os_version: str
    total_memory_gb: float
    processor: str

    @property
    def drifted_fields(self) -> tuple[DriftField, ...]:
        return tuple(field for field in self.fields if not field.matches)

    @property
    def has_drift(self) -> bool:
        return bool(self.drifted_fields)

    def safe_updates(self) -> dict[str, str]:
        """Return discovery-backed fields that may be reconciled automatically.

        The BIOS serial number is an identity anchor and is never changed by the
        automated comparison path. If it does not match, no automatic updates
        are considered safe.
        """
        if not self.identity_match:
            return {}
        allowed = {"hostname", "manufacturer", "model"}
        return {
            field.name: field.observed
            for field in self.drifted_fields
            if field.name in allowed
        }


def _normalized(field: str, value: object) -> str:
    text = str(value or "").strip()
    if field in {"hostname", "serial_number"}:
        return text.upper()
    return text.casefold()


def compare_asset_to_windows_device(
    asset: Mapping[str, object], device: WindowsDevice
) -> InventoryComparison:
    """Compare one stored asset with read-only local Windows discovery data."""
    observed = {
        "hostname": device.hostname,
        "manufacturer": device.manufacturer,
        "model": device.model,
        "serial_number": device.serial_number,
    }

    fields: list[DriftField] = []
    for field_name, observed_value in observed.items():
        stored_value = str(asset[field_name] or "")
        fields.append(
            DriftField(
                name=field_name,
                stored=stored_value,
                observed=observed_value,
                matches=(
                    _normalized(field_name, stored_value)
                    == _normalized(field_name, observed_value)
                ),
            )
        )

    serial_field = next(field for field in fields if field.name == "serial_number")
    return InventoryComparison(
        asset_tag=str(asset["asset_tag"]),
        fields=tuple(fields),
        identity_match=serial_field.matches,
        os_caption=device.os_caption,
        os_version=device.os_version,
        total_memory_gb=device.total_memory_gb,
        processor=device.processor,
    )
