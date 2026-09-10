#!/usr/bin/env sh
# Example AMShell scheduled snapshot wrapper for cron.
# Review PATH and working directory before use. This script does not install cron entries.

set -eu

AMShell="${AMSHELL_BIN:-amshell}"

"$AMShell" snapshot create
"$AMShell" snapshot prune --keep 30 --older-than-days 30 --apply
"$AMShell" snapshot status --max-age-hours 36
