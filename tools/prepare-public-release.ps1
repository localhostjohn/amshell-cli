param(
    [string]$SourceRepository = "https://github.com/localhostjohn/AMShell.git",
    [string]$Destination = "AMShell-public",
    [string]$NewRepositoryUrl
)

$ErrorActionPreference = "Stop"

$destinationPath = Join-Path (Get-Location) $Destination

if (Test-Path $destinationPath) {
    throw "Destination already exists: $destinationPath"
}

Write-Host "Creating clean AMShell public-release workspace..." -ForegroundColor Cyan
git clone $SourceRepository $Destination
if ($LASTEXITCODE -ne 0) {
    throw "Repository clone failed."
}

Push-Location $destinationPath
try {
    if (-not (Test-Path ".git")) {
        throw "Expected cloned Git metadata was not found."
    }

    Remove-Item -Recurse -Force ".git"

    git init
    if ($LASTEXITCODE -ne 0) {
        throw "git init failed."
    }

    git branch -M main
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to create main branch."
    }

    git add .
    if ($LASTEXITCODE -ne 0) {
        throw "git add failed."
    }

    git commit -m "AMShell v2.0.0-rc1"
    if ($LASTEXITCODE -ne 0) {
        throw "Initial clean-history commit failed. Check your Git user.name/user.email configuration."
    }

    if ($NewRepositoryUrl) {
        git remote add origin $NewRepositoryUrl
        if ($LASTEXITCODE -ne 0) {
            throw "Unable to add the new repository remote."
        }
    }

    Write-Host ""
    Write-Host "Clean-history workspace created successfully." -ForegroundColor Green
    Write-Host "Path: $destinationPath"
    Write-Host "Branch: main"
    Write-Host "History: one initial commit"
    Write-Host ""
    Write-Host "Nothing has been pushed." -ForegroundColor Yellow
    Write-Host "Review the working tree before publication."

    if ($NewRepositoryUrl) {
        Write-Host ""
        Write-Host "After review, push explicitly with:" -ForegroundColor Cyan
        Write-Host "  git push -u origin main"
    }
    else {
        Write-Host ""
        Write-Host "Create an empty GitHub repository, then run:" -ForegroundColor Cyan
        Write-Host "  git remote add origin <NEW_REPOSITORY_URL>"
        Write-Host "  git push -u origin main"
    }
}
finally {
    Pop-Location
}
