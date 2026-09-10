# JSON inventory export

AMShell can export the local inventory to a versioned JSON document:

```bash
amshell export-json exports/assets.json
```

The export is designed for automation, reporting, lab integrations and future migration tooling. It does not replace the SQLite database and is not imported automatically.

## Contract

The current document shape is:

```json
{
  "schema": "amshell.inventory",
  "version": 1,
  "exported_at": "2026-09-09T20:10:00+00:00",
  "asset_count": 1,
  "assets": []
}
```

`schema` identifies the AMShell export family and `version` allows future format changes to be handled explicitly instead of silently breaking integrations.

Each exported asset contains the current inventory fields, including asset tag, hostname, device type, manufacturer, model, serial number, lifecycle status, location, assignment, purchase/warranty dates, notes and record timestamps.

## Safety

The export is local only. AMShell does not upload JSON data or contact external services.

JSON exports may contain sensitive operational inventory information. The `exports/` directory is excluded from Git, and real organisational inventories should not be committed to a public repository.
