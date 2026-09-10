# AMShell Doctor

`amshell doctor` runs local operational checks against the AMShell installation.

```powershell
amshell doctor
```

Use a different backup freshness threshold when needed:

```powershell
amshell doctor --max-backup-age 14
```

## Checks

- **Database** — verifies that the local SQLite database exists and passes `PRAGMA integrity_check`.
- **Schema** — verifies that the required `assets` columns are present.
- **Backup** — checks whether a local backup exists and whether the newest backup is within the configured age threshold.
- **Windows Discovery** — reports whether the current operating system supports AMShell's local PowerShell/CIM discovery feature.

## Status meanings

- `PASS` — the check completed successfully.
- `WARN` — AMShell can continue, but an operational capability or recommended safeguard needs attention.
- `FAIL` — a core local requirement failed. The command exits with a non-zero status when any FAIL result is present.

The doctor command is read-only. It does not create backups, modify inventory records, repair databases, or change the host operating system.
