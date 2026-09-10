# Historical inventory snapshots

AMShell can create local, versioned point-in-time inventory snapshots and compare them later.

## Create a snapshot

```powershell
amshell snapshot create
```

Snapshots are written beneath `snapshots/` using a UTC timestamped filename. The directory is intended to remain local and should not contain employer or production inventory in a public repository.

## List snapshots

```powershell
amshell snapshot list
```

The list shows the snapshot path, creation time, and asset count. Files that fail snapshot validation are ignored by listing/status/retention discovery rather than causing a later metadata exception.

## Compare snapshots

```powershell
amshell snapshot diff snapshots/snapshot-OLD.json snapshots/snapshot-NEW.json
```

The comparison reports:

- assets added since the older snapshot;
- assets removed since the older snapshot;
- existing asset tags whose stored fields changed;
- the individual fields that changed for each asset.

Snapshot comparison is keyed by `asset_tag`.

## Scheduler-friendly design

AMShell does not automatically install scheduled tasks or cron jobs. The `snapshot create` command is deliberately non-interactive so it can be invoked later by an administrator-controlled scheduler.

Examples of future deployment patterns include Windows Task Scheduler or cron/systemd timers, but scheduling remains outside AMShell's automatic behaviour.

## Data handling

Snapshots can contain serial numbers, hostnames, assignments, locations, warranty information, and notes. Treat populated snapshots as operational inventory data. Do not commit real organisational snapshots to a public repository.

## Snapshot validation

When loading a snapshot, AMShell validates the payload before it is used for diffing, status or retention logic. A valid snapshot must have:

- the supported AMShell snapshot schema and version;
- a timezone-aware ISO 8601 `created_at` value;
- a non-negative integer `asset_count` matching the number of asset records;
- an `assets` list containing mapping objects;
- every required exported asset field as a string;
- a non-empty, unique `asset_tag` for each record.

Malformed snapshots are rejected with a controlled `ValueError`. This prevents corrupt or manually edited JSON from surfacing as unexpected `KeyError`, `TypeError` or datetime parsing failures deeper in snapshot operations.
