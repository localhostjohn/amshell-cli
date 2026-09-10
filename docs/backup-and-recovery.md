# Backup and Recovery

AMShell stores its local inventory in SQLite. The backup and restore workflow is designed to demonstrate safe operational recovery rather than simple file copying.

## Create a backup

```powershell
amshell backup
```

AMShell:

1. Confirms that the live database exists.
2. Runs SQLite `PRAGMA integrity_check` against the live database.
3. Uses SQLite's backup API to create a consistent backup in `backups/`.
4. Runs `integrity_check` against the completed backup.
5. Refuses the operation if either integrity check fails.

Backups use timestamped filenames such as:

```text
backups/amshell-20260909T201530123456Z.db
```

The `backups/` directory is excluded from Git.

## List backups

```powershell
amshell backup list
```

This displays the local backup path, size and modification timestamp.

## Verify a backup

```powershell
amshell backup verify backups/amshell-20260909T201530123456Z.db
```

The command opens the selected database read-only and runs SQLite `PRAGMA integrity_check`.

A failed integrity check returns a non-zero exit code and the backup should not be used for restore.

## Restore a backup

```powershell
amshell restore backups/amshell-20260909T201530123456Z.db
```

The restore workflow is intentionally conservative:

1. Verify the selected backup before touching the live database.
2. Verify the current live database when it exists.
3. Create a timestamped `pre-restore-*` safety backup of the current live database.
4. Copy the selected backup to a temporary file in the live database directory.
5. Verify the temporary restored copy.
6. Atomically replace the live database with the verified temporary copy.
7. Remove stale SQLite WAL/SHM sidecar files if present.
8. Verify the final restored live database.

Use `--yes` only when an interactive confirmation is not appropriate:

```powershell
amshell restore backups/amshell-20260909T201530123456Z.db --yes
```

## Failure behaviour

AMShell refuses a restore when:

- the selected backup is missing;
- the selected backup fails SQLite integrity checking;
- the current live database is corrupt and therefore cannot be safely captured as an automatic pre-restore backup;
- the temporary restored copy fails validation;
- the final restored database fails validation.

A corrupt selected backup is rejected before the live database is changed.

## Scope

This workflow protects the local AMShell SQLite database only. It is not a substitute for an organisation's enterprise backup, retention, encryption, disaster-recovery or records-management controls.

Public repository examples must not contain real organisational asset databases or recovery copies.
