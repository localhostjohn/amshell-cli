# Operational Reporting

AMShell can generate read-only operational inventory reports from the local SQLite database.

## Commands

```powershell
amshell report
amshell report --status repair
amshell report --type Laptop
amshell report --status assigned --type Laptop
amshell report --format json
```

## Table output

The default table report includes:

- total assets in the selected scope;
- lifecycle counts;
- expired warranty count;
- warranties expiring within 90 days;
- asset tag, hostname, type, model, status, assignment and warranty date.

## JSON output

`--format json` emits a versioned machine-readable report:

```json
{
  "schema": "amshell.operational-report",
  "version": 1,
  "generated_at": "2026-09-09T20:00:00+00:00",
  "filters": {},
  "summary": {},
  "assets": []
}
```

This output can be redirected to a file or consumed by another local automation workflow.

## Safety

Reporting is read-only. It does not update asset records, lifecycle status, audit history or backups.

Reports may include asset identifiers, serial numbers, assignments and locations. Treat exported output as operational data and do not publish real inventory information in public repositories.
