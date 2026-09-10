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

The list shows the snapshot path, creation time, and asset count.

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
