from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .exporting import ASSET_EXPORT_FIELDS

SNAPSHOT_SCHEMA = "amshell.inventory-snapshot"
SNAPSHOT_VERSION = 1


@dataclass(frozen=True, slots=True)
class SnapshotInfo:
    path: Path
    created_at: str
    asset_count: int


@dataclass(frozen=True, slots=True)
class SnapshotDiff:
    added: tuple[str, ...]
    removed: tuple[str, ...]
    changed: dict[str, tuple[str, ...]]

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.removed or self.changed)


@dataclass(frozen=True, slots=True)
class SnapshotPrunePlan:
    keep: tuple[SnapshotInfo, ...]
    remove: tuple[SnapshotInfo, ...]


@dataclass(frozen=True, slots=True)
class SnapshotStatus:
    healthy: bool
    latest: SnapshotInfo | None
    age_hours: float | None
    detail: str


def _snapshot_timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")


def create_snapshot(
    rows: Iterable[Mapping[str, object]],
    snapshot_dir: str | Path = "snapshots",
) -> Path:
    directory = Path(snapshot_dir)
    directory.mkdir(parents=True, exist_ok=True)
    assets = [{field: row[field] for field in ASSET_EXPORT_FIELDS} for row in rows]
    created_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    payload = {
        "schema": SNAPSHOT_SCHEMA,
        "version": SNAPSHOT_VERSION,
        "created_at": created_at,
        "asset_count": len(assets),
        "assets": assets,
    }
    destination = directory / f"snapshot-{_snapshot_timestamp()}.json"
    destination.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return destination


def load_snapshot(path: str | Path) -> dict[str, object]:
    snapshot_path = Path(path)
    try:
        payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unable to read snapshot: {snapshot_path}") from exc

    if not isinstance(payload, dict):
        raise TypeError(f"Snapshot root object is invalid: {snapshot_path}")
    if payload.get("schema") != SNAPSHOT_SCHEMA or payload.get("version") != SNAPSHOT_VERSION:
        raise ValueError(f"Unsupported AMShell snapshot format: {snapshot_path}")

    created_at = payload.get("created_at")
    if not isinstance(created_at, str) or not created_at.strip():
        raise ValueError(f"Snapshot created_at is invalid: {snapshot_path}")
    try:
        created = datetime.fromisoformat(created_at)
    except ValueError as exc:
        raise ValueError(f"Snapshot created_at is invalid: {snapshot_path}") from exc
    if created.tzinfo is None:
        raise ValueError(f"Snapshot created_at must include a timezone: {snapshot_path}")

    asset_count = payload.get("asset_count")
    if isinstance(asset_count, bool) or not isinstance(asset_count, int) or asset_count < 0:
        raise ValueError(f"Snapshot asset_count is invalid: {snapshot_path}")

    assets = payload.get("assets")
    if not isinstance(assets, list):
        raise TypeError(f"Snapshot assets are invalid: {snapshot_path}")
    if asset_count != len(assets):
        raise ValueError(f"Snapshot asset_count does not match assets: {snapshot_path}")

    seen_tags: set[str] = set()
    for index, asset in enumerate(assets):
        if not isinstance(asset, dict):
            raise TypeError(f"Snapshot asset {index} is invalid: {snapshot_path}")

        missing = [field for field in ASSET_EXPORT_FIELDS if field not in asset]
        if missing:
            raise ValueError(
                f"Snapshot asset {index} is missing required field(s): {', '.join(missing)}"
            )

        for field in ASSET_EXPORT_FIELDS:
            if not isinstance(asset[field], str):
                raise TypeError(
                    f"Snapshot asset {index} field '{field}' must be a string: {snapshot_path}"
                )

        asset_tag = asset["asset_tag"].strip()
        if not asset_tag:
            raise ValueError(f"Snapshot asset {index} has an empty asset_tag: {snapshot_path}")
        if asset_tag in seen_tags:
            raise ValueError(f"Snapshot contains duplicate asset_tag '{asset_tag}': {snapshot_path}")
        seen_tags.add(asset_tag)

    return payload


def list_snapshots(snapshot_dir: str | Path = "snapshots") -> list[SnapshotInfo]:
    directory = Path(snapshot_dir)
    if not directory.exists():
        return []

    results: list[SnapshotInfo] = []
    for path in sorted(directory.glob("snapshot-*.json"), reverse=True):
        try:
            payload = load_snapshot(path)
        except (TypeError, ValueError):
            continue
        results.append(
            SnapshotInfo(
                path=path,
                created_at=str(payload["created_at"]),
                asset_count=int(payload["asset_count"]),
            )
        )
    return results


def get_snapshot_status(
    snapshot_dir: str | Path = "snapshots",
    *,
    max_age_hours: int = 36,
) -> SnapshotStatus:
    if max_age_hours < 1:
        raise ValueError("max_age_hours must be at least 1.")

    snapshots = list_snapshots(snapshot_dir)
    if not snapshots:
        return SnapshotStatus(
            healthy=False,
            latest=None,
            age_hours=None,
            detail="No valid snapshots were found.",
        )

    latest = snapshots[0]
    created = datetime.fromisoformat(latest.created_at)
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    age_hours = max(0.0, (datetime.now(UTC) - created.astimezone(UTC)).total_seconds() / 3600)
    healthy = age_hours <= max_age_hours
    detail = (
        f"Latest snapshot is {age_hours:.1f} hours old."
        if healthy
        else f"Latest snapshot is stale at {age_hours:.1f} hours old."
    )
    return SnapshotStatus(
        healthy=healthy,
        latest=latest,
        age_hours=age_hours,
        detail=detail,
    )


def plan_snapshot_prune(
    snapshot_dir: str | Path = "snapshots",
    *,
    keep_latest: int = 30,
    older_than_days: int | None = None,
) -> SnapshotPrunePlan:
    if keep_latest < 1:
        raise ValueError("keep_latest must be at least 1.")
    if older_than_days is not None and older_than_days < 0:
        raise ValueError("older_than_days must be zero or greater.")

    snapshots = list_snapshots(snapshot_dir)
    protected = snapshots[:keep_latest]
    candidates = snapshots[keep_latest:]

    if older_than_days is not None:
        cutoff = datetime.now(UTC) - timedelta(days=older_than_days)
        remove = []
        keep_extra = []
        for item in candidates:
            created = datetime.fromisoformat(item.created_at)
            if created <= cutoff:
                remove.append(item)
            else:
                keep_extra.append(item)
        return SnapshotPrunePlan(
            keep=(*protected, *keep_extra),
            remove=tuple(remove),
        )

    return SnapshotPrunePlan(keep=tuple(protected), remove=tuple(candidates))


def apply_snapshot_prune(plan: SnapshotPrunePlan) -> int:
    removed = 0
    for item in plan.remove:
        item.path.unlink(missing_ok=True)
        removed += 1
    return removed


def diff_snapshots(older: str | Path, newer: str | Path) -> SnapshotDiff:
    older_payload = load_snapshot(older)
    newer_payload = load_snapshot(newer)

    older_assets = {
        str(asset["asset_tag"]): asset
        for asset in older_payload["assets"]
        if isinstance(asset, dict) and "asset_tag" in asset
    }
    newer_assets = {
        str(asset["asset_tag"]): asset
        for asset in newer_payload["assets"]
        if isinstance(asset, dict) and "asset_tag" in asset
    }

    older_tags = set(older_assets)
    newer_tags = set(newer_assets)
    added = tuple(sorted(newer_tags - older_tags))
    removed = tuple(sorted(older_tags - newer_tags))

    changed: dict[str, tuple[str, ...]] = {}
    for asset_tag in sorted(older_tags & newer_tags):
        fields = tuple(
            field
            for field in ASSET_EXPORT_FIELDS
            if older_assets[asset_tag].get(field) != newer_assets[asset_tag].get(field)
        )
        if fields:
            changed[asset_tag] = fields

    return SnapshotDiff(added=added, removed=removed, changed=changed)
