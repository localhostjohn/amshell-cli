# Changelog

All notable AMShell changes are recorded here.

The project follows semantic versioning for release tags and uses PEP 440-compatible Python package versions.

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

- Current examples use fictional Astra lab data.
- Operational databases, exports, backups and snapshots are excluded from source control.
- Public-release readiness now explicitly requires Git-history verification for previously committed sensitive values, including the known legacy serial-number concern.

## Pre-v2 prototype

Earlier commits represent the original AMShell learning prototype. They are retained while the repository remains private. Before any future change to public visibility, repository history must be reviewed and, if necessary, rewritten according to `docs/release-readiness.md`.
