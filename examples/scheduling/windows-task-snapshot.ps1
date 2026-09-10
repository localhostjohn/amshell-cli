# Example AMShell scheduled snapshot wrapper for Windows Task Scheduler.
# Review paths before use. This script does not install a scheduled task.

$ErrorActionPreference = "Stop"

$Amshell = "amshell"

& $Amshell snapshot create
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

& $Amshell snapshot prune --keep 30 --older-than-days 30 --apply
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

& $Amshell snapshot status --max-age-hours 36
exit $LASTEXITCODE
