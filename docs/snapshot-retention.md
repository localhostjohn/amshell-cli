# Snapshot retention

AMShell snapshot retention is deliberately preview-first.

## Preview the default policy

```powershell
amshell snapshot prune
```

The default policy keeps the newest 30 valid snapshots and displays any older snapshots that would be pruned. No files are deleted.

## Keep a different number

```powershell
amshell snapshot prune --keep 14
```

## Add an age threshold

```powershell
amshell snapshot prune --keep 14 --older-than-days 30
```

The newest 14 valid snapshots are always protected. Additional snapshots are selected only when they are at least 30 days old.

## Apply the plan

```powershell
amshell snapshot prune --keep 14 --older-than-days 30 --apply
```

`--apply` is required before AMShell deletes any snapshot files.

## Scheduling

For unattended operation, schedule snapshot creation separately from pruning and validate the preview policy first. AMShell does not create Windows Task Scheduler jobs, cron entries, or systemd timers automatically.

Example scheduled commands:

```powershell
amshell snapshot create
amshell snapshot prune --keep 30 --older-than-days 60 --apply
```

## Data handling

Snapshot files contain inventory information. Keep them in a protected local location and do not commit real operational snapshots to a public repository.
