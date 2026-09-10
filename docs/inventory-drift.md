# Inventory drift comparison

AMShell can compare one stored asset record with read-only inventory discovered from the **local Windows host**.

## Read-only comparison

```powershell
amshell compare AST001
```

AMShell compares:

- Hostname
- Manufacturer
- Model
- BIOS serial number

It also displays live observations for Windows edition/version, memory and processor. These live observations are informational only in the current data model.

## Identity protection

The BIOS serial number is treated as the hardware identity anchor.

If the discovered serial number does not match the stored asset record, AMShell reports an identity mismatch and blocks automatic reconciliation. The comparison command never changes the serial number automatically.

This prevents a local machine from silently overwriting a different asset record.

## Controlled reconciliation

When the serial identity check passes, AMShell can reconcile safe descriptive drift:

```powershell
amshell compare AST001 --update
```

Only these discovery-backed fields can be updated automatically:

- Hostname
- Manufacturer
- Model

Each actual update goes through the existing audited edit path and records the old value, new value, reason and timestamp in `asset_history`.

## Scope and safety

- Discovery remains local-only and read-only.
- No remote host or credential input is accepted.
- The default comparison command does not change the database.
- `--update` is explicit.
- Serial-number mismatches block automatic updates.
- OS, processor and memory observations are not written to the asset record in this version.

This feature is intended for personal lab and authorised inventory validation only.
