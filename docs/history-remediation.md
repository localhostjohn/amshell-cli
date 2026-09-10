# Git history remediation

This guide supports the AMShell public-release security gate.

The current v2 tree uses fictional Astra lab data, but the private repository contains a legacy pre-v2 `assets.csv` object in historical commits. Do not make the repository public until a fresh post-remediation audit is clean.

## Preferred release strategy

The lowest-risk portfolio option is to create a new clean-history repository from the current sanitised v2 tree and publish that repository instead of exposing the legacy private repository.

This avoids carrying old commit objects, obsolete branches, historical pull-request refs, and other legacy metadata into the public portfolio.

Keep the existing `localhostjohn/AMShell` repository private as the development archive.

## Option A - clean-history public repository

Recommended public repository name: `localhostjohn/amshell-cli`.

The helper script can prepare the clean workspace without publishing anything:

```powershell
.\tools\prepare-public-release.ps1 -Destination "AMShell-public"
```

If the empty public repository already exists, you can also wire its remote during preparation:

```powershell
.\tools\prepare-public-release.ps1 `
  -Destination "AMShell-public" `
  -NewRepositoryUrl "https://github.com/localhostjohn/amshell-cli.git"
```

The script clones the private source, removes its Git metadata, creates a new `main` branch and one clean initial commit. It never pushes automatically.

Manual equivalent, from a trusted workstation:

```powershell
git clone https://github.com/localhostjohn/AMShell.git AMShell-public
cd AMShell-public
Remove-Item -Recurse -Force .git
git init
git branch -M main
git add .
git commit -m "AMShell v2.0.0-rc1"
```

Create a new empty GitHub repository, then add its remote and push:

```powershell
git remote add origin <NEW_REPOSITORY_URL>
git push -u origin main
```

Before changing visibility, run the current-tree review and confirm that only fictional/personal lab data is present.

## Option B - rewrite the existing private repository

Only use this approach if preserving the repository identity is important.

Install `git-filter-repo` locally and make a fresh mirror clone:

```powershell
python -m pip install git-filter-repo
git clone --mirror https://github.com/localhostjohn/AMShell.git AMShell-rewrite.git
cd AMShell-rewrite.git
```

Remove the historical legacy asset CSV path from all rewritten refs:

```powershell
git filter-repo --path assets.csv --invert-paths --force
```

`git filter-repo` may remove the `origin` remote as a safety measure. Inspect the rewritten history before restoring the remote.

Run the audit script from a separate clean checkout or copy it outside the mirror first:

```powershell
.\tools\audit-history.ps1 -LegacyValue "<KNOWN_LEGACY_VALUE>" -RepositoryPath "C:\path\to\AMShell-rewrite.git"
```

Do not paste the actual legacy value into issues, PRs, screenshots, documentation, or shell-history you intend to publish.

After the rewritten mirror is verified:

```powershell
git remote add origin https://github.com/localhostjohn/AMShell.git
git push --force --mirror origin
```

A force-mirror push is destructive. Existing clones become stale and must not be pushed back unchanged.

## Post-rewrite verification

Delete the local audit clone and perform a fresh mirror clone from GitHub:

```powershell
cd ..
Remove-Item -Recurse -Force AMShell-rewrite.git

git clone --mirror https://github.com/localhostjohn/AMShell.git AMShell-verify.git
```

Run the history audit again against `AMShell-verify.git`.

Also review historical data-file paths:

```powershell
git -C AMShell-verify.git log --all --name-only -- "*.csv" "*.json" "*.db" "*.sqlite" "*.sqlite3"
```

Only close the public-release blocker when the fresh clone has no match for the known legacy value and the current tracked tree contains no employer/internal data or credentials.

## Important GitHub caveat

History rewriting changes commit IDs. Old local clones, forks, cached pages, and provider-managed pull-request refs may retain references to old objects. For the strongest publication boundary, prefer a newly created clean-history public repository.

If the existing repository itself must become public after sensitive-history rewriting, review GitHub's current sensitive-data removal guidance and consider GitHub Support where old cached views or pull-request references need purging.
