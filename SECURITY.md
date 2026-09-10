# Security

AMShell is a local learning and portfolio project for managing fictional or explicitly authorised IT asset data.

## Data handling

- The default SQLite database is stored locally under `data/` and is excluded from Git.
- Local CSV/JSON exports, backups, snapshots and environment files are excluded from Git.
- Do not commit real organisational asset inventories, serial numbers, usernames, internal locations or other confidential operational data.
- Public examples in this repository use fictional Astra lab data only.
- Treat terminal output and screenshots from `amshell discover`, `amshell show`, exports and reports as potentially sensitive because they can contain real device identifiers.

## Credentials

AMShell does not require credentials, cloud APIs or external services for its current feature set. Do not add production credentials, API keys, tokens, passwords or connection strings to the repository.

## Git history and public visibility

Deleting or replacing sensitive data in a branch does not remove it from historical Git objects. The private AMShell development archive contains a known legacy-history concern and is not the intended public distribution.

Public releases should be produced from a verified clean-history repository or from history that has been deliberately rewritten and re-audited according to [docs/release-readiness.md](docs/release-readiness.md). The clean public distribution must contain only fictional or explicitly authorised data.

Do not reproduce sensitive legacy values in issues, pull requests, commit messages, changelogs, remediation documents or screenshots.

## Reporting a security issue

If you identify a security issue in the code or repository contents, report it privately to the repository owner rather than publishing sensitive exploit or data-exposure details in a public issue.

## Scope

The current application is intended for local lab and portfolio use. It has not undergone independent security review and should not be treated as a production enterprise asset-management platform.
