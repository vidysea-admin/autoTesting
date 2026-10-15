# Verdict - infra-trio

**Cycle checked:** 1
**Head checked:** 1156642f
**Verdict:** PASS-WITH-ADVISORY (AT-692 PASS; AT-820 guard is a weak tripwire, not a ban)

## Evidence
- tests/test_infra_trio.py 4 passed; ruff clean; doctor clean; merge-tree vs master clean (no conflicts).
- AT-692 scripts/verify_gates.sh: a fake `pytest` printing "1 failed" and exiting 1 -> script exit 1 with "[verify exit code: 1]". Also correct: missing command 127, killed child 137, exit 4 with 100k lines of output, unwritable log path (exit code still preserved, tee error only). No args exits non-zero. PASS.
- AT-676: no code in this branch; accepted as already shipped.

## AT-820 advisory (non-blocking, record as issue)
The `HOST_WIDE` regex is trivially bypassed. Verified NOT matched: `Stop-Process -Force -Name chrome`, `Get-Process -Name python | Stop-Process`, `Get-Process chrome | Stop-Process`, `taskkill /FI "IMAGENAME eq x"`, `taskkill /IM` at end of line, `wmic process ... delete`, `psutil.process_iter()` + `.kill()`, string concatenation. The scan also skips `.bat/.cmd` and `src/**/*.ps1|sh`. Current src/ and scripts/ contain no host-wide kills (grep confirmed: only own-proc `proc.kill()` and `taskkill /F /T /PID <own pid>`), so nothing is broken today. Suggest a follow-up: ban `taskkill` unless followed by `/PID`, ban `Stop-Process` without `-Id`, ban `psutil.process_iter`/`wmic`, scan all extensions.
