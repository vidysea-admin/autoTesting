# Manifest - at858-hook-utf8 (AT-858, D-103)

Contract: qa/contracts/core-invariants.md (hook output must reach the session undamaged); no contract edited
Issues: AT-858 (the session-start hook sets UTF-8 output only at the SNAPSHOT tail, so earlier lines leave as OEM/ANSI bytes)
Authority: D-103 (docs/DECISIONS.md, Approved-by: Umesh 2026-10-17) authorizes exactly qa/hooks/mc-sessionstart.ps1 and tests/test_mc_sessionstart_loop_status.py. Only those two files changed.
Status: checked-PASS (qa/verdicts/at858-hook-utf8.md, cycle 0)
Fix cycle: 0
Policy-Version: proportional-verification/2026-10-17.13
Tier: L (enforcement-path hook, checker-gated, one checker)
Dual check: no (hooks/config are tier L with one checker; no security/auth/tenancy/prod-write trigger)
Base: master 9aaf1fe5, branch wave/at858-hook-utf8 (worktree .worktrees/at858-hook-utf8)
Product commit: 209bcb86dd52330f9ede2d6e3af6c372c297603c (a manifest cannot name its own commit)
Executor: claude-sonnet-subagent (maker build), 2026-10-17/18

## What changed
- `qa/hooks/mc-sessionstart.ps1`: `[Console]::OutputEncoding = UTF8` moved from the SNAPSHOT tail to the top of the file, before the first Write-Output. The loop-status child process now gets `PYTHONIOENCODING=utf-8` and `StandardOutputEncoding = UTF8` so its non-ASCII separator is neither written in cp1252 nor decoded wrongly (found by running: with only the top-of-file move, `ticks: 1 U+00B7 last:` came out as U+FFFD). No directive text, logic or exit behaviour changed.
- `tests/test_mc_sessionstart_loop_status.py`: `_run_hook` decodes `encoding="utf-8", errors="replace"`; new `test_hook_output_is_utf8_with_the_non_ascii_separator_intact` pins `ticks: 1 \u00b7 last:` and no U+FFFD. File is 298 lines (limit 300).
- Note for the checker: AT-858 expected text asks for the encoding set OR ASCII-only; this unit forces UTF-8 and also pins a non-ASCII char, as the row's expected text says.

## Tests
Tests[AT-858]: tests/test_mc_sessionstart_loop_status.py::test_hook_output_is_utf8_with_the_non_ascii_separator_intact (the changed behaviour), plus the whole of tests/test_mc_sessionstart_loop_status.py and tests/test_mc_sessionstart_unclosed.py (same hook, same helper) -- 17 tests, under 1.5 min.

Pre-check[AT-858]: 209bcb86 `AUTOTESTER_TIMING_SCALE=4 uv run pytest tests/test_mc_sessionstart_loop_status.py tests/test_mc_sessionstart_unclosed.py` -> 17 passed, exit 0, t=74 s. `uv run ruff check src tests scripts` -> All checks passed. `uv run autotester doctor` -> exit 0 (file-too-long on the test file at 304 lines was fixed to 298 before the commit). Host was saturated by other python processes (not mine), hence TIMING_SCALE=4 (the existing AT-757 knob; the hook alone took 39 s once, 60 s test bound otherwise times out).

TDD red on base: with the original hook (git show 9aaf1fe5), the new test fails on its named assertion `the non-ASCII separator was lost or mangled` (`'ticks: 1 U+FFFD last:'`); an earlier strict-decode form failed `UnicodeDecodeError ... 0xfa`. Also on base, the two existing tests `..._on_a_healthy_log` / `..._on_an_asleep_log...` failed with a 60 s TimeoutExpired on this saturated host (environmental, not the encoding; they pass with TIMING_SCALE=4).

Falsify[AT-858]: throwaway copy of qa, tests, src, docs, scripts under the session scratchpad (outside the worktree, reusing the worktree venv with `uv run --no-sync`), fixed hook with the encoding line moved back to the SNAPSHOT tail -> `test_hook_output_is_utf8_with_the_non_ascii_separator_intact` red on `the non-ASCII separator was lost or mangled`; original base hook -> same red. Green in the worktree (17 passed). Copy not removed from scratchpad (outside repo).

Metrics: suite_runs=0 mutations=2 cycle=0 builder_min=45 check_min=0
