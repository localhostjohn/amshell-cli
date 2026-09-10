# Snapshot automation

AMShell can be scheduled externally to create recurring inventory snapshots. AMShell does not install scheduled tasks, cron entries, systemd timers, or other host automation automatically.

## Health check

Use:

```powershell
amshell snapshot status
```

The default freshness threshold is 36 hours. Override it with:

```powershell
amshell snapshot status --max-age-hours 24
```

The command reports the newest valid snapshot, its creation time and age. It exits with code 0 when the newest snapshot is within the allowed age, and code 1 when snapshots are missing or stale. This makes it suitable for scheduled-task monitoring and external alerting.

## Suggested daily workflow

A simple daily sequence is:

```powershell
amshell snapshot create
amshell snapshot prune --keep 30 --older-than-days 30 --apply
amshell snapshot status --max-age-hours 36
```

The prune command is intentionally preview-first when run manually. In an already-reviewed scheduler wrapper, `--apply` may be used explicitly.

## Windows Task Scheduler example

See `examples/scheduling/windows-task-snapshot.ps1`.

Create a normal Task Scheduler task that launches PowerShell and calls the reviewed local script. Use an account and working directory that can access the AMShell installation, database and snapshot directory. Test the script interactively before scheduling it.

AMShell does not create or modify the task on your behalf.

## cron example

See `examples/scheduling/cron-snapshot.sh`.

A daily cron entry could call the reviewed wrapper from the AMShell working directory. Ensure the scheduled environment has the expected `PATH`, permissions and current directory.

AMShell does not create or modify the crontab.

## Operational considerations

Snapshot files contain inventory data. Keep them outside public repositories and protect them in the same way as the underlying asset database. Check `amshell snapshot status` after scheduling and periodically verify that retention is behaving as expected.