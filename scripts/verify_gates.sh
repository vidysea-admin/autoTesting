#!/usr/bin/env bash
# Run the project's verify gates with the REAL exit code of each (AT-692).
# A bare `cmd | tail` reports tail's status, so a failing suite looks green.
# Usage: scripts/verify_gates.sh LOGFILE CMD [ARGS...]   (prints the last 15 lines, exits with CMD's status)
set -o pipefail
log="${1:?log file}"; shift
"$@" 2>&1 | tee "$log" | tail -15
status=${PIPESTATUS[0]}
echo "[verify exit code: $status]"
exit "$status"
