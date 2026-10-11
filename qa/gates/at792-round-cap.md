# HUMAN_GATE: D-014 round cap on the ingest/reconcile seam (at792-stale-rc2-test)

**Asked:** 2026-10-11 by the maker. **Answered:** 2026-10-11 by Umesh, option A (D-082): the D-014
cap is waived for at792-stale-rc2-test, at733-bounded and t178-failure-bundle-fb4-fb5 only. D-014
itself is unchanged.

## What is blocked

`wave/at792-stale-rc2-test` (worktree `.worktrees/at792-stale-rc2-test`) repairs one stale test,
`tests/test_reconcile_schema.py::test_rc2_ingest_video_keeps_narration_on_screen_text_and_exit_screen`,
by passing it a transcript that contains the narration. No assertion changes and no product file
changes. The test is one of the four reds in the full suite on master (AT-792).

The Stop hook counted 6 earlier PASSes on this seam (at433, at465-466, t060, t135, t162-drive-2b,
t172). D-014 caps a non-security seam at 2. This unit is not security class, and no decision entry
waives the cap, so the maker may not open another round on its own.

## What happened

The maker merged the branch into master (424f120a) before the manifest lint had passed, then
reverted that merge (354bd31f). Master is back to its earlier content. Nothing was pushed.

## The question

Choose one:

- **A. Waive the cap for this one test-only repair.** Needs a `docs/DECISIONS.md` entry with
  `Approved-by: Umesh`. Then one checker judges the branch and it merges on PASS.
- **B. File, don't fix.** AT-792 stays open, and the red test is recorded in
  `qa/checkpoints/baseline-reds.md` as a known red, so it does not block the push gate.

Maker's recommendation: A. The diff is 5 lines in one test file, and leaving a known-stale test red
hides any real regression in the same file.

## Second unit on the same question: at733-bounded (added 2026-10-11)

`wave/at733-bounded` (code b07cc727, manifest 32c18947) holds a checker PASS for RU5
(`qa/verdicts/at733-bounded.md`, master 5e5dd272): a failed wipe of the entry case's browser
profile now ends the case ERRORED and names the path, where before the case ran on the leftover
profile and could PASS. The checker counted 2 earlier PASSes on the `_run_entry_case` seam
(at044, at574), or 3 if at567-file-splits is counted. The unit is not security class, so merging
it would be the 3rd or 4th PASS on a seam D-014 caps at 2. It is NOT merged.

Same choice, per unit: **A** waive (decision entry with `Approved-by: Umesh`, then the maker
merges at the PASSed commit) or **B** leave the branch unmerged and AT-733 open.

Maker's recommendation: A. AT-733 is a false-PASS path in real runs, and the fix is already
independently checked.

## Third unit on the same question: t178-failure-bundle-fb4-fb5 (added 2026-10-11)

`wave/t178-failure-bundle-fb4-fb5` (a7d3fa6c) has checker B PASS and checker A with every criterion
met and only its full suite left. Checker A ruled the unit security class only for the two
`failure_bundle` files (path containment, `stages/failure_bundle.py:211-212`); the rest of its diff
is not. A counted earlier PASSes per seam: `schema/case.py` 5, `stages/expand.py` 4,
`core/project_store.py` 15+, `core/paths.py` 12, `cli.py` 11+, `ui/routes_runs.py` 14+,
`ui/routes_learn.py` 4. Seven seams are over the cap of 2. It is NOT merged.

**Update, same day:** cycle 0 failed in A's full suite (two unregistered CLI advice sites). Fix
cycle 1 is at 297207ff and holds a dual PASS: A `qa/verdicts/t178-failure-bundle-fb4-fb5.r1.a.md`
(full suite on 297207ff: 3457 passed, 4 failed, none new), B
`qa/verdicts/t178-failure-bundle-fb4-fb5.r1.b.md`. The commit to merge is now 297207ff. It is
still NOT merged.

Same choice: **A** waive (decision entry with `Approved-by: Umesh`, then merge at the PASSed commit
297207ff) or **B** leave unmerged and FB4/FB5 unmet.

Maker's recommendation: A, and a wider question for the owner: with shared files at 11 to 15 PASSes,
a cap of 2 per seam now stops almost every unit that touches `cli.py`, `project_store.py` or
`routes_runs.py`. The cap may need to be per unit rather than per file; that is a D-014 change and
yours to decide.
