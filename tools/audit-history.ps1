param(
    [Parameter(Mandatory = $true)]
    [string]$LegacyValue,

    [string]$RepositoryPath = "."
)

$ErrorActionPreference = "Stop"

Push-Location $RepositoryPath
try {
    if (-not (Test-Path ".git") -and -not (Test-Path "HEAD")) {
        throw "RepositoryPath does not appear to be a Git repository or mirror clone."
    }

    Write-Host "AMShell history audit" -ForegroundColor Cyan
    Write-Host "Scanning all reachable refs without printing the supplied sensitive value." -ForegroundColor DarkGray

    $matches = @()

    $logMatches = git log --all -S"$LegacyValue" --format="%H" 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "git log history scan failed."
    }
    if ($logMatches) {
        $matches += $logMatches
    }

    $revList = git rev-list --all
    if ($LASTEXITCODE -ne 0) {
        throw "git rev-list failed."
    }

    foreach ($commit in $revList) {
        $grepOutput = git grep -l --fixed-strings -- "$LegacyValue" $commit 2>$null
        if ($grepOutput) {
            $matches += ($grepOutput | ForEach-Object { ($_ -split ":", 2)[0] })
        }
    }

    $matches = $matches | Sort-Object -Unique

    Write-Host ""
    if ($matches.Count -gt 0) {
        Write-Host "FAIL: The supplied value is still reachable in Git history." -ForegroundColor Red
        Write-Host "Affected commits detected: $($matches.Count)" -ForegroundColor Yellow
        $matches | ForEach-Object { Write-Host "  $_" }
        exit 1
    }

    Write-Host "PASS: No reachable Git-history match was found for the supplied value." -ForegroundColor Green
    exit 0
}
finally {
    Pop-Location
}
