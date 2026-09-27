# Verdict — at576-577-serial-runs

**Date:** 2026-09-25 · **Head checked:** 8295b79 (fix f30b2ac, base master 80256c3) · **Cycle checked: 1** (manifest Fix cycle: 1 of 3) · **Issues addressed (claimed):** AT-576, AT-577

```
VERDICT: FAIL
SCOREBOARD: AT-576 met (live 303 with an entry case + 2 ordinary cases); AT-577 partly met (RawResult evidence is scoped per case) but its expected clause "keep screenshot names unique" is not met
FAILURES:
- [AT-577 / evidence integrity] sev: high · on the serial path an entry case's screenshots are overwritten by the first ordinary case: _run_entry_case gives each entry case a fresh BrowserSession in the SAME run_dir with its screenshot counter at 0, and now that entry cases run first, the shared session also starts at 0, so both write 01-step01-navigate.png. Live (run-01M3BNKR295JN0DPMR3HM888BZ): 'Homepage loads' (index.html) records 01-step01-navigate.png but that file's sha1 f3a69799 is the login page; 5 PNGs on disk for 6 steps; the run view and HTML report show the login page under 'Homepage loads'. · fix: give every entry-case session its own namespace (the AT-572 mechanism: SessionState.evidence_prefix = case.id in _run_entry_case), or carry one run-wide counter; a test running an entry case + an ordinary case whose first steps both screenshot, asserting distinct paths with different bytes; capability row. · issue: AT-577
CAPABILITY-COVERAGE: not re-run this cycle (the FAIL is decided by Mode D; rows A/B re-run on the fix cycle)
LIVE-BROWSER: qa/evidence/browser-at576-577-serial-runs-2026-09-25-checker/report.json
ISSUES-WRITTEN: AT-578 (the builder's inbox item b)
EXECUTOR: claude-sonnet-subagent (checker: claude-opus-session, checker seat)
EXPLANATION: The reorder fixes AT-576 for real (live 303 where master 500s) and the per-case slice fixes the cumulative-evidence half of AT-577 (Login page loads now carries only its own 05-...). But the reorder makes an existing name collision certain: the entry case's session and the shared session both number from 01 in one directory, so the entry case's evidence is silently replaced by another case's page. The parallel path's evidence_prefix (AT-572) is the ready-made fix.
```

## Answers to the maker's questions

1. **`_assertions_unmet` index math:** still correct. `pre = len(session.state.evidence)` is an absolute index into the unsliced session list, and `_assertions_unmet(session, pre)` scans `session.state.evidence[pre:]`; only `_result` slices. The three scripts that re-slice (`bench_trial`, `regression_proof`, `run_pathlynks_first_cases`) slice `session.state.evidence[start:]` from their own start index, not `result.evidence`, so they are redundant and harmless.
2. **Inbox items.** (a) The execute.md E4 wording ("every Evidence the session recorded" -> "for this case") will be folded when this unit passes. (b) `_network_met` reading other cases' NETWORK evidence does not block this unit, since it predates it and was disclosed; it's filed as **AT-578** (high). Scoping it may reuse the same `evidence_start`, so it could fold into cycle 2 if the builder wants, but it isn't required.

## What I re-ran

- Code read of f30b2ac: the entry-first loop, the `evidence_start` slice at every `_result` exit, and the script call sites.
- **Mode D** (real Chromium, serial n=1 chosen by budget, mock judge): 303, 3 results + 3 verdicts, evidence scoped per card, 12/12 images load, no secret in the DOM. The collision above shows in both the file hashes and the run view.
- Full suite and rows were not re-run: the verdict is FAIL on live evidence, and they'll be run on cycle 2.

## Status: FAIL (cycle 1) — maker fix cycle 2.

---

# Cycle 2 — /checker verdict

**Date:** 2026-09-25 · **Head checked:** 332d216 (fix 77346cb, master merge c4c6b81) · **Cycle checked: 2** (manifest Fix cycle: 2 of 3) · **Issues addressed (claimed):** AT-576, AT-577, AT-578

```
VERDICT: PASS
SCOREBOARD: AT-576 met (live 303, entry + 2 ordinary cases); AT-577 met (per-case evidence AND unique screenshot names: 6 distinct paths for 6 steps, entry bytes != login bytes); AT-578 met (network check scoped to the current case); core invariants hold
FAILURES: none
CAPABILITY-COVERAGE: 3/3 single-hunk rows reproduced (A, C, D), each in its own throwaway copy; green before, red on the named assertion after. Row B (multi-hunk loop revert) not re-run: its test is unchanged since cycle 1 and the reorder is proven live.
LIVE-BROWSER: qa/evidence/browser-at576-577-serial-runs-2026-09-25-checker-c2/report.json
ISSUES-WRITTEN: AT-579 (low, pre-existing flaky test); AT-567 note (erosion data point)
EXECUTOR: claude-sonnet-subagent (checker: claude-opus-session, checker seat)
EXPLANATION: The default serial path is now correct live. A run mixing an entry case with ordinary cases completes, each case carries only its own evidence, the entry case's screenshot lives under its own folder and is the right page, and the run view and HTML export show all six images. The trims made to stay at the 300-line cap removed explanatory docstring text only (recorded on AT-567); nothing behavioural was cut.
```

## The maker's points

- **(a) Trims to fit the cap:** docstrings only. Lost: the contract anchors "E5 holds either way" (`settle`) and "C7: facts recorded, the grader still owns the verdict" (`assert_expected`), the pointer to the AT-036 history, and the literal Playwright error text in the AT-576 note (`_run_cases_serially`). No code and no function changed. Not blocking; recorded on AT-567, since both `session.py` and `routes_runs.py` now sit at exactly 300 lines.
- **(b) In-place TDD revert on real files:** `git status` at 332d216 is empty, so the tree is clean and matches the commit. The deviation itself (a falsifying edit on the bound tree) is the same process slip as at560: not a defect in the artifact, but it should stop. Rows belong in throwaway copies only.
- **Flaky test** `test_with_max_parallel_2_two_cases_run_concurrently`: it overlaps two fake cases with a 50 ms sleep, so on a loaded host the peak can read 1. It predates this unit, and the unit touches neither the test nor `parallel_run`. It passed in my full run. Filed **AT-579** (low): use a `threading.Barrier(2)`.

## What I re-ran

- `ruff` clean · `doctor` clean (copy).
- **Every non-browser test file** (copy): `1 failed, 1565 passed, 5 skipped`; the one failure is the `.git`-dependent `test_uploaded_recordings_are_gitignored` (passes in a checkout). Net: all green.
- Row A (`_result` back to the full history): the 2 scope tests fail (`case 2's evidence must not include case 1's`).
- Row C (`evidence_prefix = case.id` removed from `_run_entry_case`): fails on `'01-step01-navigate.png' != '01-step01-navigate.png'`.
- Row D (`_network_met` scans all evidence): fails with `COMPLETED is not ASSERTION_FAILED`; the met-sibling test stays green.
- Diff scope c4c6b81..77346cb: 8 files, all listed; removals are docstring compression plus reflowing one call's arguments.
- **Mode D** (serial, n=1 by budget, entry case + 2 ordinary, mock judge): 303; 6 PNGs / 6 steps / 6 distinct paths; entry `case_8c1ec91abecf/01-step01-navigate.png` = the homepage bytes; run view 12/12 images; `report.html` 6 PNGs; no secret anywhere.

## Status: PASS (cycle 2)
