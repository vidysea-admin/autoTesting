# Verdict — at383-sessionstart-loop-status

**Date:** 2026-09-27
**Cycle checked:** 1
**Checker:** /checker (standing checker session: orchestrator plus 3 fresh-context lenses — rows/scope/authorisation, live hook in 7 states, config/security audit). The decisive finding was reproduced by the orchestrator itself.
**Contract:** qa/contracts/loop-status.md LS1-LS4; authorisation D-048 (Changes-authorized: qa/hooks/mc-sessionstart.ps1, Approved-by: Umesh); gate qa/gates/at383-loop-status-consumer.md answered C; issue AT-383 (part A)
**Branch / code commit:** wave/at383-sessionstart-loop-status · 0f7e31d (manifest 1a382a9), base cfb905a

```
VERDICT: FAIL
SCOREBOARD: 1/2 criteria met (print the loop-status --strict report at session start: met in all 7 live states; a bounded call that cannot leave anything behind: NOT met), 3/4 invariants hold (LS1-LS3 behaviour live-confirmed; LS4 read-only/not in doctor holds; D-048 scope holds; C7 is weakened by an overclaiming static test)
FAILURES:
- [manifest "kills the child" / hook safety] sev: medium · on timeout, `$lsProc.Kill()` kills only `uv`. Windows PowerShell 5.1 has no Kill(entireProcessTree), and `uv run` starts python as a child, so the python grandchild keeps running after the kill. Reproduced by the checker with the same ProcessStartInfo shape: the uv pid exited while the python pid was still alive 1.5s later · kill the tree (`taskkill /T /F /PID <uv pid>` or a Job Object), and add a test with a real grandchild asserted dead after the timeout (the AT-494 shape), plus a sabotage row · issue: AT-622
- [C7] sev: low · test_the_hook_wraps_the_call_so_a_failure_cannot_propagate is a whole-file `'try {'`/`'catch {'` substring check. It stays green when the outer try/catch is removed, because the unrelated Kill() try/catch satisfies it, so its docstring's "this fails" is false · assert the structure, or drop the claim · issue: AT-624
CAPABILITY-COVERAGE: 3/3 manifest rows reproduced (a: dropping --strict kills test_the_hook_calls_loop_status_strict; b: removing the exit-code block kills 2 tests; c: removing the outer try/catch kills only the Windows behavioural test, as the manifest's own table says). The extra static-test gap is filed as AT-624.
LIVE-BROWSER: not-applicable (changed paths: qa/hooks/mc-sessionstart.ps1, tests/; no UI surface). The hook itself was run live instead; see below.
ISSUES-WRITTEN: AT-622, AT-623 (pre-existing, not charged), AT-624
EXECUTOR: maker builder (checker: claude-opus orchestrator + subagents)
EXPLANATION: The feature does what the gate asked. Each of the 7 live states printed the right report and exit code, and the diff is exactly the D-048 authorisation. But the unit's own claim that a hang is killed is only half true: the python underneath uv survives. On an enforcement path that runs every session, that is the defect class of AT-494/AT-518, and a test can pin it.
```

**Re-ran:**
- `uv run ruff check src tests scripts`: clean.
- `uv run autotester doctor`: clean.
- `-k "hook or loop_status"`: 44 passed. `tests/test_mc_sessionstart_loop_status.py`: 8/8.
- Diff scope `cfb905a..HEAD`: 3 files, all insertions. The existing hook lines are byte-identical before and after the inserted block.
- Full suite: not run for cycle 1. The unit already fails on a reproduced defect, so cycle 2 runs it.

**Live hook runs** (copies of the real hook, with AUTOTESTER_ROOT set to scratch trees; the real qa/ was never read or written). Every run below exited 0.

| State | Result | Time |
|---|---|---|
| healthy | report, no UNHEALTHY line | 3-5.6s |
| asleep, 8h | SLEEP row + `LOOP UNHEALTHY (loop-status --strict exit 1)` | |
| paused | paused row, no UNHEALTHY line (LS1) | |
| uv off PATH | `loop-status: skipped (uv/autotester unavailable)` | 1.66s |
| hang, block isolated | `skipped (timed out after 15s)` | 15.9s |
| all-future | CORRUPT row + UNHEALTHY (LS1) | |
| out-of-order with a credible tick | CORRUPT row, no UNHEALTHY line (LS3) | |

The healthy path adds about 1.5-2s to session start.

**Security audit cleared:**
- Command injection: `$ROOT` is quoted and there is no shell (UseShellExecute=false).
- Env leakage: loop-status prints no environment values.
- Deadlock: stdout and stderr are read via ReadToEndAsync before WaitForExit.
- A failure cannot break session start.

**Questions for cycle 2, not failures:**
- A CLI that crashes (uv resolves, but autotester exits 1 with a traceback) prints the same `LOOP UNHEALTHY (… exit 1)` line as a sleeping loop, and the stderr is dropped. The manifest disclosed this. It fails loud, which is the safe side, but printing the last stderr line would stop a tooling failure from reading as an outage.
- `uv run` without `--no-sync` can reach the network or write `.venv` at session start. That matches the pre-existing snapshot call, and is noted against LS4's spirit.
- The whole hook still blocks for about 82s when uv itself hangs. That comes from the pre-existing, unbounded `uv run autotester snapshot` call, not this unit; filed as AT-623.

---

# Verdict — at383-sessionstart-loop-status, cycle 2

**Date:** 2026-09-27
**Cycle checked:** 2
**Checker:** /checker session (bound to `d:/autoTesting`). Branch commits: merge-master 45cbc79, code a3dc2ed, manifest 71f07e3.

```
VERDICT: PASS
SCOREBOARD: all cycle-1 FAIL lines closed (AT-622 tree kill, AT-624 structural try/catch assertion); all criteria met, core invariants hold
FAILURES: none
CAPABILITY-COVERAGE: all rows (a-e) reproduced in the checker's own throwaway copies
LIVE-BROWSER: not-applicable (changed paths: qa/hooks/mc-sessionstart.ps1, tests/test_mc_sessionstart_loop_status.py, manifest; session-start hook, no UI)
ISSUES-WRITTEN: AT-625 (low: the AUTOTESTER_LOOPSTATUS_TIMEOUT_MS seam has no upper clamp; filed at 02021fa, non-blocking)
EXECUTOR: manifest's Executor (checker: this session plus parallel lens subagents)
EXPLANATION: On timeout the hook now kills the whole tree with `taskkill /T /F`. The checker drove a real `uv` → python grandchild through the hook's own path and confirmed the grandchild is dead afterwards, which is the exact repro of the cycle-1 FAIL. The try/catch test now asserts structure (_OUTER_TRY_RE), and removing the outer wrapper turns it red. The full suite is green.
```

## What the checker re-ran

- **Row lenses, each in its own scratch copy:** rows a–e all reproduced. Every falsifying edit turned its named test red, and the assertion that fired was the named one.
- **AT-622 (tree kill):** a real hung grandchild launched through the hook's `uv run` path was confirmed dead after the timeout. Removing `taskkill /T` brings back the orphan and turns the behavioural test red.
- **AT-624 (structural test):** removing only the outer try/catch now turns the static test red, where cycle 1 stayed green.
- **Live lens:** all 7 loop-status states render correctly. With `taskkill` missing from PATH the hook still returns within its bound and prints the skip line. The stderr tail is surfaced on failure.
- **Scope lens:** the diff stays within D-048's authorization for this enforcement path, and nothing was deleted or renamed outside the claims.
- **Full `uv run pytest`:** **1991 passed, 6 skipped, 32 xfailed, 0 failed** (12:27).

## Carried forward (not charged to this unit)

- **AT-623** (unbounded `uv run autotester snapshot` call, pre-existing): gated for Umesh at `qa/gates/at623-snapshot-call-timeout.md`.
- **AT-625** (low): the timeout environment seam has no upper clamp. Separate unit.

## After merge

The checker flips AT-383, AT-622 and AT-624 to fixed once ancestry is confirmed. Their regression check is `uv run pytest tests/test_mc_sessionstart_loop_status.py`.
