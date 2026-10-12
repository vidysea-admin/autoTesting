# Verdict - t179a-lead-tester-core, coordinator A, repair check (cycle 2, re-run after BLOCKED-PROCESS)

Date: 2026-10-12 | Bound to .worktrees/chk-t179a-A (detached) | Head f54af1ac9ed38eb48d7c1160d47640eb4b474784 (code cc7f29ed, maker head 86d240a9; later commits are qa-only) | Base 16aaa402
Cycle checked: 2
Policy-Version: proportional-verification/2026-10-10.9

VERDICT: PASS
SCOREBOARD: 3/3 claimed criteria met (AL2 in part as claimed, AL3 met for crawl/run_case, AL6 met for the tool boundary as claimed); AL1/AL4/AL5/AL7 HELD by the manifest (not judged)
TIER: L
FAILURES: none
ISSUES-WRITTEN: none

## AL6 (the earlier FAIL: a secret split by TAB or LF leaked into the stage result)
Own test written blind (`.work/test_chk_al6.py`, not committed): the fake secret (RAW canary) split at 5 cut points by 6 separators (TAB, LF, TAB+LF, space-TAB-space, LF LF, CRLF), placed in 3 stage-result fields (error, hitl_prompt, evidence label), driven through `tools.dispatch` on `run_case`. Asserted: outcome `ok=False` (withheld), neither half nor its JSON-escaped form in the outcome, none in the stored results, none in any file under the data dir. Result: 90 passed. Plus a split secret in the tool CALL arguments (TAB, LF): refused, zero sessions. Plus a clean result still released. 93 passed.
Falsification: with `_carries_credential` swapped for the old shape (gate on `json.dumps(data)`), the same 90 split rows FAIL (90 failed). So the test discriminates and the cycle-2 fix (`tools._carries_credential` walking decoded strings) is what closes it.

## AL3
Own probes (`.work/test_chk_al3.py`, 9 passed): (a) raw secret in a call arg refused with `RefusalClass.SECRET`, no session, no stage call; (b) crawl with no approval and crawl asking 5000 actions against a 10-action grant both refuse `APPROVAL` before any session; (c) READ_ONLY run_case refuses CLICK "Place order"/"Save", PRESS_KEY, FILL, NAVIGATE to a delete URL with a query, NAVIGATE off-domain, each with zero sessions and zero stage calls; a plain in-domain NAVIGATE still runs. The suite also holds the 32-row READ_ONLY table and the real-`BrowserSession.goto` destination-seam oracle (C1 repair), green.

## AL2
Read tools.py: each handler calls the existing function named by `ToolSpec.wraps` (`explore.run_crawl`, `execute.run_case`, `store.load_portal_persona`, `catalog.catalog`, `grade.grade`); no parallel implementation. `autotester doctor`: clean. `report` and `capture_network` HELD, as claimed.

## Gate (own run, head f54af1ac, suite slot free at start, Windows)
- `uv run pytest -o addopts=` (full): 23 failed, 4188 passed, 163 skipped (1458 s).
- Baseline: the same suite on merge-base 16aaa402 (clean worktree): 22 failed, 3797 passed, 163 skipped. The 22 base failures are the same 22 test ids on the branch (5 symlink tests need the Windows symlink privilege, WinError 1314; 16 test_ui_intake/origin_guard "asyncio.run() cannot be called from a running event loop", order-dependent pollution that also reproduces on the base; 1 serial_entry_mix_live, 0 PNGs). Branch minus base = 391 new passes, 0 new failures except `test_core.py::test_env_creation_is_coordinated_across_processes`, a multi-process timing flake (`_queue.Empty`) that passes when re-run on the branch. The branch's agent tests alone plus ui_intake/origin_guard: 504 passed (the branch does not cause the pollution). The branch diff touches no ui, core, discover or report_export file.
- `uv run ruff check src tests scripts`: All checks passed.
- `uv run autotester doctor`: clean.

## Notes
The 22 environment/pollution failures are pre-existing on master's base and should be filed by the maker/owner; they are not this unit's. No product issues written. LIVE-BROWSER: not-applicable (no UI surface).
