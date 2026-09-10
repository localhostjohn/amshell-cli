from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from amshell.snapshots import apply_snapshot_prune, plan_snapshot_prune


def _write_snapshot(directory: Path, name: str, created_at: datetime) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text(
        json.dumps(
            {
                "schema": "amshell.inventory-snapshot",
                "version": 1,
                "created_at": created_at.replace(microsecond=0).isoformat(),
                "asset_count": 0,
                "assets": [],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_retention_keeps_latest_count(tmp_path: Path) -> None:
    now = datetime.now(UTC)
    paths = [
        _write_snapshot(
            tmp_path,
            f"snapshot-2026090{index}T120000000000Z.json",
            now - timedelta(days=index),
        )
        for index in range(1, 6)
    ]

    plan = plan_snapshot_prune(tmp_path, keep_latest=2)

    assert len(plan.keep) == 2
    assert len(plan.remove) == 3
    assert {item.path for item in plan.keep} == {paths[3], paths[4]}


def test_retention_age_filter_protects_recent_extra_snapshots(tmp_path: Path) -> None:
    now = datetime.now(UTC)
    _write_snapshot(tmp_path, "snapshot-20260909T120000000000Z.json", now)
    recent = _write_snapshot(
        tmp_path,
        "snapshot-20260908T120000000000Z.json",
        now - timedelta(days=1),
    )
    old = _write_snapshot(
        tmp_path,
        "snapshot-20260801T120000000000Z.json",
        now - timedelta(days=40),
    )

    plan = plan_snapshot_prune(tmp_path, keep_latest=1, older_than_days=30)

    assert [item.path for item in plan.remove] == [old]
    assert recent in {item.path for item in plan.keep}


def test_apply_prune_deletes_only_selected_snapshots(tmp_path: Path) -> None:
    now = datetime.now(UTC)
    newest = _write_snapshot(tmp_path, "snapshot-20260909T120000000000Z.json", now)
    oldest = _write_snapshot(
        tmp_path,
        "snapshot-20260801T120000000000Z.json",
        now - timedelta(days=40),
    )
    plan = plan_snapshot_prune(tmp_path, keep_latest=1)

    removed = apply_snapshot_prune(plan)

    assert removed == 1
    assert newest.exists()
    assert not oldest.exists()


def test_invalid_retention_values_are_rejected(tmp_path: Path) -> None:
    for kwargs in ({"keep_latest": 0}, {"older_than_days": -1}):
        try:
            plan_snapshot_prune(tmp_path, **kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError("Expected invalid retention policy to be rejected")
