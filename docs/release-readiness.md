# AMShell v2 release readiness

This checklist is the release gate for the v2 release candidate and for producing a public AMShell distribution.

For the detailed sanitisation workflow and clean-history alternative, see [Git history remediation](history-remediation.md).

## Release-candidate gate

Before tagging `v2.0.0-rc1`:

- `pyproject.toml` and `amshell.__version__` agree on `2.0.0rc1`.
- `ruff check amshell tests` passes.
- `pytest -q` passes on Python 3.11, 3.12 and 3.13.
- A clean non-editable `pip install .` succeeds.
- `amshell --help`, `amshell backup --help`, `amshell doctor --help` and `amshell snapshot --help` run successfully after the clean install.
- README command documentation matches the actual CLI surface.
- `CHANGELOG.md` describes the release candidate.
- Example inventory data contains fictional Astra lab values only.
- No local database, backup, export, snapshot, environment or credential file is tracked.

## Public-release security gate

**Do not expose the private development archive directly.** Produce the public distribution from a verified clean-history repository, or complete a full history rewrite and re-audit first.

A sensitive value removed from a current branch can still exist in historical Git blobs, tags, branches, pull-request refs, local clones or forks. The private AMShell development archive has a known legacy-history concern, so checking only current files is insufficient when reusing that archive's history.

Perform the history review from a fresh mirror clone:

```bash
git clone --mirror <AMShell repository URL> AMShell-audit.git
cd AMShell-audit.git
```

Search all reachable history for the exact known legacy serial number and any other known sensitive strings:

```bash
git log --all -S"<KNOWN_LEGACY_SERIAL>" --oneline
git grep -n "<KNOWN_LEGACY_SERIAL>" $(git rev-list --all)
```

Also inspect historical asset-data file types and obvious sensitive terms:

```bash
git log --all --name-only -- "*.csv" "*.json" "*.db" "*.sqlite" "*.sqlite3"
git log --all -G"serial|password|token|secret|nhsbsa|nhs\.uk" --oneline --all
```

The commands above are review aids, not a guarantee that every possible sensitive value will be detected. Review unexpected matches manually.

### If the legacy serial is found

Keep the repository private. Rewrite history with a purpose-built tool such as `git filter-repo`, removing or replacing the affected blob/value across all relevant refs. Then force-push the rewritten refs deliberately, expire/re-clone local copies, and repeat the full history scan from a fresh mirror clone.

Do not publish the old serial value in issues, commits, pull requests, documentation or screenshots while performing the remediation.

### Public-visibility decision

For an in-place history rewrite, only consider public visibility when:

- the exact legacy value produces no matches in a fresh full-history scan;
- current tracked files contain no employer/internal data or credentials;
- fictional examples have been reviewed manually;
- any obsolete remote branches/tags containing sensitive history have been removed or rewritten;
- collaborators know that old clones must not be pushed back after a history rewrite.

## Release tagging

Once CI is green and the release-candidate gate is complete, create the Git tag using the conventional repository tag form:

```bash
git tag -a v2.0.0-rc1 -m "AMShell v2.0.0-rc1"
git push origin v2.0.0-rc1
```

The Python package version remains PEP 440 compatible as `2.0.0rc1`; the Git tag uses the more readable `v2.0.0-rc1` form.

## Final v2.0.0

Promote to `2.0.0` only after the release candidate has been exercised in the lab, no release-blocking defects remain, documentation still reflects the command surface, and the security gate has been revisited before any public-visibility change.
