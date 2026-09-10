# Changelog

All notable AMShell changes are recorded here.

The project follows semantic versioning for release tags and uses PEP 440-compatible Python package versions.

## Unreleased

### Changed

- Hardened `amshell doctor` to verify the newest backup's SQLite integrity before reporting backup freshness.
- Extended schema health checks to validate the `asset_history` table as well as `assets`.
- Added an inventory health check that warns when a valid database contains no assets.

## [2.0.0rc1] - 2026-09-10

### Added

- Installable Typer/Rich CLI backed by local SQLite persistence.
- Validated asset records with lifecycle states and serial-number uniqueness.
- Audited asset creation, field edits and lifecycle transitions.
- Search, inventory summaries, warranty reporting and approximate asset age.
- CSV import/export and versioned JSON export.
- Read-only local Windows discovery through constrained PowerShell/CIM queries.
- Stored-vs-observed inventory comparison with identity-gated safe reconciliation.
- Verified SQLite backup, backup listing, integrity verification and safety-first restore.
- `amshell doctor` operational health checks.
- Read-only operational reporting with table and JSON output.
- Point-in-time historical inventory snapshots.
- Snapshot diffing, preview-first retention/pruning and snapshot freshness status.
- Windows Task Scheduler and cron examples for recurring snapshot workflows.
- Pytest and Ruff CI across Python 3.11, 3.12 and 3.13.
- Packaged CLI smoke testing using a non-editable `pip install .` installation.

### Changed

- Replaced the original CSV-oriented prototype with a structured local application and SQLite data model.
- Expanded project documentation around recovery, health checks, reporting, snapshots, drift comparison and operational boundaries.
- Standardised package/runtime version metadata on `2.0.0rc1`.

### Security

- Public examples use fictional Astra lab data.
- Operational databases, exports, backups and snapshots are excluded from source control.
- The public repository was created with clean Git history rather than inheriting the private prototype history.

## Pre-v2 prototype

The original AMShell prototype remains only in the separate private development archive. The public `amshell-cli` repository starts from the sanitised v2 release-candidate tree and does not inherit the prototype's Git history.
