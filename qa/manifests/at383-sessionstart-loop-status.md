# Manifest — at383-sessionstart-loop-status

**Unit:** `qa/hooks/mc-sessionstart.ps1` calls `autotester loop-status --strict` at session start
and prints its report, so a silent maker-checker loop (AT-368) announces itself at the first
moment anyone could act, without a human typing the command.
**Contract:** `qa/contracts/loop-status.md` LS4 (read-only, never in `doctor`'s verify chain) —
respected: this unit adds a caller, not a write path, and does not touch `autotester doctor`. LS5
(the session-start consumer criterion) is pending — per D-048, the checker writes it once this
unit exists.
**Gate:** `qa/gates/at383-loop-status-consumer.md`, answered **C (both)** by Umesh
2026-09-26T22:34:22+05:30. Part A (this unit): the session-start hook now. Part B (a shared sweep
routine outside this repo) is explicitly deferred, not built here.
**Authorization:** `docs/DECISIONS.md` D-048, `Changes-authorized`: "qa/hooks/mc-sessionstart.ps1:
call `autotester loop-status --strict` at session start and print its report (at383 part A). This
is an enforcement path." **Approved-by:** Umesh. Confirmed on disk before any edit.
**Date:** 2026-09-26
**Fix cycle:** 2
**Dual check:** no
**Persona walk:** skip (dev tooling / session-start hook, not a UI surface)
**Issues addressed:** AT-383, AT-622, AT-624. AT-368 stays open (its full ask — noticing *during*
an outage — is out of scope for both this unit and gate option A; nothing here runs while the app
is closed). AT-623 (the pre-existing, unbounded `autotester snapshot` call) is separately gated and
explicitly out of scope for this unit — see cycle 2 notes below.

## Fix cycle 2 (2026-09-27) — AT-622, AT-624

Cycle 1 verdict: FAIL (`qa/verdicts/at383-sessionstart-loop-status.md`), 1/2 criteria, 3/4
invariants. Two reproduced findings, both now fixed; scope stayed inside the D-048-authorised
block (`qa/hooks/mc-sessionstart.ps1` lines ~41-81) — the pre-existing, separately-gated
`autotester snapshot` call (AT-623) was not touched.

**AT-622 (medium) — timeout killed only `uv`, not its python grandchild.** Windows PowerShell
5.1/.NET Framework's `Process.Kill()` has no `entireProcessTree` overload; `uv run` always spawns
python as a child, which survived the old bare `Kill()`. Fixed by killing the whole tree on
timeout: `try { & taskkill /T /F /PID $lsProc.Id *> $null } catch {}` (same `taskkill /F /T /PID`
shape as `scripts/mutation_check.py:162`'s `kill_tree`, already precedent in this repo). Failures
from `taskkill` itself (process already gone, etc.) are swallowed — this path must still reach the
skip line and must never fail the hook, matching the pre-existing contract.

Added a real-process behavioural test,
`test_the_timeout_kills_the_real_grandchild_process_not_just_uv` (Windows-only, same
`@windows_only` skipif as the other 3 behavioural tests): copies a real `python.exe` to `uv.exe` on
a scratch PATH dir, and — because the hook's fixed `Arguments` string starts with the extensionless
token `run`, and CPython resolves an extensionless first argument as a script path relative to the
child's own working directory (which the hook sets to `$ROOT`, itself `tmp_path` in the test) —
places a script literally named `run` in `tmp_path` that spawns a REAL grandchild recording its own
pid to a file, then hangs. A new `AUTOTESTER_LOOPSTATUS_TIMEOUT_MS` env-var override (read via
`[int]::TryParse`, falling back to the real 15000ms default if unset/invalid) lets the test bound
the hang to 2s instead of waiting out the real timeout. After the hook returns, the test asserts the
grandchild pid is dead (`_alive`, imported from `test_mutation_check_judgement` rather than
redefined — C3; same real-grandchild shape as
`tests/test_flake_probe_real_process.py::test_run_once_kills_a_real_hung_process_and_its_real_grandchild`,
its direct precedent).

**AT-624 (low) — the try/catch structural test was a whole-file substring check.**
`test_the_hook_wraps_the_call_so_a_failure_cannot_propagate` used to check `'try {' in code and
'catch {' in code` over the entire file, which stayed green even with the outer wrapper removed
because the unrelated `try { ... } catch {}` timeout guard also contains those tokens. Replaced with
a structural regex (`_OUTER_TRY_RE`) anchored on the specific catch body's own message
(`"loop-status: skipped (uv/autotester unavailable)"`), asserting the `ProcessStartInfo`/`Start()`
call and its `WaitForExit` bound sit inside that exact try block's span — not merely that both
tokens appear somewhere in the file. Kept the "this fails" docstring claim, since it is now true.

**Optional (small, done): stderr tail on a non-zero exit.** When `loop-status --strict` exits
non-zero for a reason other than a timeout (e.g. the CLI itself crashes), the hook now also prints
the last non-empty line of its stderr (`  stderr: <line>`), so a tooling crash does not read
identically to a genuinely sleeping loop. Stayed inside the same block; no new failure path (the
existing `$lsStderr` `ReadToEndAsync()` task was already being started, just never read before).

### Cycle 2 tests (TDD)

`tests/test_mc_sessionstart_loop_status.py` grew from 173 to 267 lines (8 → 9 tests): one existing
test's body was replaced with the structural assertion (AT-624), one new Windows-only behavioural
test was added (AT-622), plus a `from test_mutation_check_judgement import _alive` reuse import and
one new stdlib import (`time`).

```
$ uv run pytest tests/test_mc_sessionstart_loop_status.py -v
...
tests\test_mc_sessionstart_loop_status.py .........                      [100%]
9 passed in 16.91s

$ uv run pytest tests/ -k "hook or loop_status"
................................................                         [100%]
48 passed, 1981 deselected, 1 warning in 20.91s

$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester doctor
doctor: clean
```

RAM-gated gap unchanged from cycle 1: full suite not run this cycle, per standing RAM-low
instruction — only the new/targeted test file, the `hook or loop_status` slice, ruff, and doctor.

### Cycle 2 capability coverage (C7 sabotage rows)

Falsified in a throwaway plain-file copy OUTSIDE the tracked worktree
(`C:/Users/Lenovo/AppData/Local/Temp/claude/d--autoTesting/dd410a44-7522-428c-9b91-fda96de822cd/scratchpad/at383-c2-falsify/`,
a targeted file-by-file copy of only `qa/hooks/mc-sessionstart.ps1`, `tests/test_mc_sessionstart_loop_status.py`,
`tests/test_mutation_check_judgement.py`, `tests/tests_mutation_fixtures.py`,
`tests/test_flake_probe_runner.py`, `scripts/flake_probe.py`, `scripts/mutation_check.py` — run
against the tracked worktree's own `.venv` via `uv run pytest <scratch path>`, never `git stash` and
never an edit inside the tracked worktree). Each row: patch the scratch hook copy via a Python
script asserting its anchor text matched exactly once before writing, run the targeted test, then
restore from a saved `.orig` copy.

| claim (cycle 2) | falsifying edit (scratch copy only) | check | observed |
|---|---|---|---|
| (d) On timeout the hook kills the whole process tree, not just `uv` | `try { & taskkill /T /F /PID $lsProc.Id *> $null } catch {}` → reverted to `try { $lsProc.Kill() } catch {}` | `test_the_timeout_kills_the_real_grandchild_process_not_just_uv` | PASS before. FAIL after: `AssertionError: the hook's timeout killed uv but left its real grandchild running (AT-622)` — `_alive(42772)` was `True` after the hook returned. The leftover real grandchild process (pid 42772, spawned only by this test run) was killed by hand immediately after observing the failure. |
| (e) The loop-status invocation is inside the outer try/catch whose catch prints the clean skip line | Removed the outer `try { ... } catch { Write-Output "loop-status: skipped (uv/autotester unavailable)" }` wrapper (same edit as cycle 1's row (c)), leaving only the inner timeout `try{taskkill}catch{}` | `test_the_hook_wraps_the_call_so_a_failure_cannot_propagate` (now structural) | PASS before. FAIL after: `AssertionError: no try { ... } catch { print the clean skip line } wrapper found ... ` — `_OUTER_TRY_RE` found no match once the specific catch body was gone, unlike cycle 1's loose substring check (AT-624), which stayed green under this same mutation. |

Reverted after each row from the saved `.orig`; `diff` against `.orig` confirmed byte-identical
after both rows. `git status --short` in the tracked worktree throughout cycle 2 showed only the 2
intended files (`qa/hooks/mc-sessionstart.ps1`, `tests/test_mc_sessionstart_loop_status.py`) — the
falsification copy was never inside the tracked tree.

## What changed

- **`qa/hooks/mc-sessionstart.ps1`** (lines 41-77, inserted between the existing AUTO-CONTINUE
  block and the "Living map" snapshot block — nothing before or after it was restructured, only
  added to):
  - Launches `uv run --project $ROOT autotester loop-status --strict` via
    `System.Diagnostics.Process` (not the `Start-Process` cmdlet — see "Why not Start-Process"
    below), redirecting stdout/stderr, bounded by a 15s `WaitForExit` timeout.
  - **Timed out:** kills the child process, prints `loop-status: skipped (timed out after 15s)`.
  - **uv/autotester unavailable** (e.g. `uv` not on PATH → `Process.Start()` throws
    `Win32Exception`): caught by the wrapping `try/catch`, prints
    `loop-status: skipped (uv/autotester unavailable)`.
  - **Ran to completion:** prints every non-empty line of the command's stdout (the same
    `report_lines` text `loop_status_cmd` always produces), indented two spaces. If the exit code
    is non-zero, additionally prints `LOOP UNHEALTHY (loop-status --strict exit <code>)`.
  - `--project $ROOT` pins `uv` to this project's `pyproject.toml` regardless of the hook's
    working directory; `AUTOTESTER_ROOT`, if the caller has set it (tests do), still governs which
    `qa/.last-tick` the command actually reads — `repo_root()` honours it, the CLI has no
    `--root` flag of its own.
  - The block is unconditional (runs every session start, not gated on `$backlog`/`$asleep`),
    matching the contract's framing: loop-status reports on log health in general, not only when
    other maker-checker signals already look backlogged.
  - The hook's own `exit 0` (last line) and every existing `Write-Output` line/order before this
    block are byte-identical to before. Nothing was reordered or removed.
- **`tests/test_mc_sessionstart_loop_status.py`** (new, 173 lines) — see "Tests" below.

### Why not `Start-Process`

The first implementation used the `Start-Process -PassThru` cmdlet. Two real bugs surfaced during
manual verification, not just review:
1. `-RedirectStandardOutput` and `-RedirectStandardError` pointed at the **same file** →
   `InvalidOperationException` from `Microsoft.PowerShell.Commands.StartProcessCommand` (Windows
   PowerShell refuses to redirect both streams to one file). Fixed by using two files — but that
   led into bug 2.
2. Even with separate files, `$proc.ExitCode` read back as effectively empty/`$null` immediately
   after `WaitForExit($timeoutMs)` returned true, so the healthy-log case printed
   `LOOP UNHEALTHY (loop-status --strict exit )` (blank code) — `$null -ne 0` is `$true` in
   PowerShell, so every run looked unhealthy regardless of the real exit code. Switching to
   `System.Diagnostics.Process`/`ProcessStartInfo` directly (own `.Start()`, `.WaitForExit(ms)`,
   `.StandardOutput.ReadToEndAsync()`) resolved both: exit codes and captured output are reliable,
   confirmed by the three subprocess tests below actually passing against real healthy/asleep
   logs.

## Tests (TDD)

`tests/test_mc_sessionstart_loop_status.py`, two layers (mirrors the split already established in
`tests/test_session_start_hook.py`):

- **Static, pure-Python, portable** (runs with no PowerShell at all, e.g. in a Linux CI container):
  - `test_the_hook_exists_where_the_protocol_expects_it`
  - `test_the_hook_calls_loop_status_strict` — parses the exact `$lsPsi.Arguments` line (not a
    loose "does `--strict` appear anywhere in the file" check — that string also legitimately
    appears inside the unrelated `LOOP UNHEALTHY (loop-status --strict exit ...)` message, which
    would make a loose check blind to the real invocation losing `--strict`; see the C7
    falsification below, this was caught mid-build).
  - `test_the_hook_checks_the_exit_code`
  - `test_the_hook_wraps_the_call_so_a_failure_cannot_propagate`
  - `test_the_hooks_own_exit_code_is_unconditional_zero`
- **Behavioural, real PowerShell + real `uv`** — `@windows_only`
  (`skipif(not (sys.platform == "win32" and powershell/pwsh and uv on PATH))`, the same pattern
  `test_report_export.py:145` already uses for its own Windows-only junction test):
  - `test_hook_prints_the_report_and_exits_zero_on_a_healthy_log` — writes a `qa/.last-tick` with
    one tick 1 minute old to a `tmp_path`, runs the real hook against the real repo with
    `AUTOTESTER_ROOT` pointed at `tmp_path`, asserts `ticks: 1` appears and no `LOOP UNHEALTHY`
    line, exit 0.
  - `test_hook_prints_unhealthy_line_only_on_an_asleep_log_and_still_exits_zero` — one tick 10
    hours old (past the 6h default threshold), asserts
    `LOOP UNHEALTHY (loop-status --strict exit 1)` appears and the hook itself still exits 0.
  - `test_hook_skips_cleanly_when_uv_is_unavailable` — runs the hook with `PATH`/`Path` stripped
    to `C:\Windows\System32;C:\Windows` (no `uv`), asserts
    `loop-status: skipped (uv/autotester unavailable)`, no `LOOP UNHEALTHY`, exit 0.

## How to verify (commands + actual outputs)

```
$ uv run pytest tests/test_mc_sessionstart_loop_status.py -v
...
tests\test_mc_sessionstart_loop_status.py ........                       [100%]
8 passed in 17.78s

$ uv run pytest tests/ -k "hook or loop_status"
............................................                             [100%]
44 passed, 1914 deselected, 1 warning in 37.76s

$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester doctor
doctor: clean
```

RAM-gated gap: full suite (`uv run pytest`, no target) not run this cycle, per standing RAM-low
instruction — only the new test file, the `hook or loop_status` slice, ruff, and doctor.

## Cycle 1 capability coverage (C7 sabotage rows, each claim → its falsification)

Falsified in a throwaway plain-file copy OUTSIDE the tracked worktree
(`C:/Users/Lenovo/AppData/Local/Temp/claude/d--autoTesting/dd410a44-7522-428c-9b91-fda96de822cd/scratchpad/at383-falsify/`,
`cp -r` of the worktree with `.venv` and `.git/worktrees` removed, own fresh `uv`-managed
`.venv` built there — confirmed `8 passed` against the unmodified copy before any mutation). Each
edit is a single anchored hunk, applied via a Python script that asserts the anchor matched
exactly once before writing, run, then reverted from a saved `.orig` copy; the tracked worktree
was never touched (`git status --short` in the worktree shows only the 2 intended files, before
and throughout).

| claim | falsifying edit (single anchored hunk, in the throwaway copy) | check | observed |
|---|---|---|---|
| (a) The hook actually invokes `loop-status --strict`, not just `loop-status` | `$lsPsi.Arguments` line: `"run --project ...autotester loop-status --strict"` → `"run --project ...autotester loop-status"` | `test_the_hook_calls_loop_status_strict` | PASS before. FAIL after: `assert '--strict' in 'run --project ...autotester loop-status'` |
| (b) The hook checks the exit code and prints the unhealthy line | Removed the `if ($lsProc.ExitCode -ne 0) { Write-Output ("LOOP UNHEALTHY ...") }` block entirely | `test_the_hook_checks_the_exit_code`, `test_hook_prints_unhealthy_line_only_on_an_asleep_log_and_still_exits_zero` | PASS before. FAIL after: both — the static test can't find `ExitCode`/`LOOP UNHEALTHY` in the code at all; the behavioural test runs the real hook against a real 10h-stale log and finds no `LOOP UNHEALTHY` line in its stdout |
| (c) The call is wrapped so a failure (uv unavailable) cannot break the clean-skip contract | Removed the outer `try { ... } catch { Write-Output "loop-status: skipped (uv/autotester unavailable)" }` wrapper, leaving only the inner `try{Kill()}catch{}` for the timeout path | `test_hook_skips_cleanly_when_uv_is_unavailable` | PASS before. FAIL after: with `uv` off `PATH`, `Process.Start()` throws a `Win32Exception`; Windows PowerShell 5.1's default `$ErrorActionPreference = 'Continue'` does **not** halt the script on this terminating .NET exception, so the hook still reaches its final `exit 0` — but the clean `loop-status: skipped (uv/autotester unavailable)` line never prints; instead the raw `MethodInvocationException`/`InvalidOperationException` text leaks into stdout. The exit-code contract (LS4-adjacent "never fail the hook") survives even without the wrapper, by accident of PS5.1's default error handling — the **output-cleanliness** contract does not, and that is what this test catches. |

Reverted after each row; re-ran the full 8-test file after restoring from `.orig` → `8 passed in
35.79s`, confirmed identical to the pre-mutation baseline. `git diff --stat` in the tracked
worktree immediately after all three rows showed only the 2 intended files (`qa/hooks/mc-
sessionstart.ps1`, `tests/test_mc_sessionstart_loop_status.py`) — the falsification copy was never
inside the tracked tree.

**Note on row (c):** the brief's expected observation was "the exit-0 test goes red." What was
actually observed is that the hook's exit code stays 0 (PS5.1 continues past the uncaught
exception by default) but the **clean-skip test goes red** because the raw exception text replaces
the intended skip line. Recorded honestly rather than reshaped to match the expected wording — the
try/catch is still proven necessary, just for output cleanliness under this shell's default error
handling rather than for the exit code itself, which happens to survive anyway. Flagged for the
checker to judge whether this is disclosed accurately per the C10/C7 sabotage-assertion rule.

## Live browser evidence

Not UI-touching — a PowerShell session-start hook plus its tests. Changed paths:
`qa/hooks/mc-sessionstart.ps1`, `tests/test_mc_sessionstart_loop_status.py`.

## Known limits / gaps (disclosed, not claimed)

- **Part B (the shared sweep routine) is not done.** Gate at383 answer C is explicit that B lands
  later, in `C:/Users/Lenovo/.claude/skills/checker/SKILL.md` (outside this repo's bound root, and
  outside this maker session's authority regardless), when that file is next touched. Nothing in
  this unit touches it.
- **AT-368 stays open**, as the gate itself states: this still cannot fire *during* a live outage —
  nothing in this repo runs while the app is closed. It surfaces the silence at the first session
  start after the fact, which is what gate option A promised, not the full AT-368 ask.
- Full test suite not re-run this cycle (RAM-low standing instruction) — only the new test file,
  the `hook or loop_status` slice, ruff, and doctor.
- `qa/contracts/loop-status.md` LS5 was **not** added by this unit — per D-048 that criterion is
  the checker's to write once this consumer exists, and the maker's brief for this unit explicitly
  says do not edit `qa/contracts/`.
- The behavioural (real-PowerShell) tests are Windows-only (`skipif` gated); on a non-Windows CI
  runner only the 5 static/portable tests execute. This mirrors the existing precedent
  (`test_report_export.py::test_png_embedding_refuses_a_windows_junction`), not a new pattern.
- Row (c)'s falsification surfaced a genuine PowerShell-5.1 default-error-handling nuance (see
  table note above) rather than a clean "exit code becomes non-zero" result. Disclosed above, not
  smoothed over.
- `uv` failing for a reason OTHER than "not on PATH" (e.g. installed but the `autotester` package
  itself broken) is **not** distinguished from a real unhealthy loop — it surfaces as
  `LOOP UNHEALTHY (loop-status --strict exit <n>)` with whatever stderr/stdout the failing command
  produced, not as a "skipped" line. Only a `Process.Start()`-level failure (the binary truly not
  found) hits the skip path. This reading of "tolerate uv/autotester unavailable" was a judgment
  call; flagged for the checker. Cycle 2 partially addresses the crash sub-case: the last non-empty
  stderr line is now appended to the `LOOP UNHEALTHY` output, so a crash at least carries its own
  evidence instead of reading as bare silence — it is still not distinguished from a genuinely
  sleeping loop by exit code or message shape, only by that extra line.
- **AT-623 (the pre-existing, unbounded `autotester snapshot` call) is intentionally untouched.**
  It sits in the same hook file but outside the D-048-authorised block (lines 41-81), is separately
  gated per its own issue, and the cycle-1 brief explicitly named it out of scope. The hook can
  therefore still block on that call independent of anything fixed here.
- The new `AUTOTESTER_LOOPSTATUS_TIMEOUT_MS` override is read with `[int]::TryParse`; a malformed or
  non-positive value silently falls back to the real 15000ms default rather than erroring — this
  matches the hook's overall "never fail session start on a config problem" posture but means a
  typo in that env var (nobody sets it outside this one test) fails silently rather than loudly.

## Status: checked-PASS (cycle 2, qa/verdicts/at383-sessionstart-loop-status.md df909e05)
