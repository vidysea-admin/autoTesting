# Verdict: at792-stale-rc2-test

Date: 2026-10-11 · Cycle checked: 0 · Head: e346c6d1 (worktree .worktrees/at792-stale-rc2-test, branch wave/at792-stale-rc2-test) · Policy-Version: proportional-verification/2026-10-10.9
Bound to D:/autoTesting. Manifest lint: exit 0. D-014 round cap waived (docs/DECISIONS.md D-082 item 3, qa/gates/at792-round-cap.md).

## Check plan

Test-only diff to one stale test, dispatched as the fix for open issue AT-792, so it gets one checker at tier S. Plan: (1) diff scope against the true unit base, (2) before/after assertion comparison, (3) run the file on the branch (expect green) and on master (expect red), (4) compare to contract RC2/RC3, (5) falsification in copies outside the worktree. No UI, no full suite, no importer tests (no product file changed).

Unit base: `git merge-base HEAD master` returns 1379689c, which is not the real base, because master contains the unit's earlier merge (424f120a) and its revert (354bd31f). The real base is f96b136c (first parent of 424f120a; verified an ancestor of HEAD). All diff reads use f96b136c..HEAD. master does not contain the unit's test change.

VERDICT: PASS
SCOREBOARD: 2/2 criteria met (RC2 repaired and still tested; RC3 reject-path untouched), 0/0 invariants touched
TIER: S (one test function plus the manifest; no product, conftest, fixture or contract file; not a protected test change)
FAILURES: none
CAPABILITY-COVERAGE: 2/2 falsification rows reproduced by the checker (narration, exit_screen)
LIVE-BROWSER: not-applicable (tests/test_reconcile_schema.py, qa/manifests/*.md)
ISSUES-WRITTEN: none (AT-792 stays open until the maker merges and closes it)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)

## Evidence

1. Diff scope (`git diff f96b136c..HEAD --stat`): `qa/manifests/at792-stale-rc2-test.md` and `tests/test_reconcile_schema.py` (+4/-1) only. Nothing deleted or renamed. No product file, conftest, fixture, contract or ledger touched.
2. Assertions before/after (I read the diff): the 4 assertion statements are byte-identical: `step.narration == "type your email here"`, `step.on_screen_text == "Email"`, `home = next(s for s in spec.screens if s.name == "Home")`, `flow.exit_screen == home.id`. Only setup changed: before `ingest_video(source, "p", MockProvider(...))`; after the same call plus `transcript=said`, where `said = Transcript(source_id=source.id, segments=[TranscriptSegment(start=0, end=3, text="First, type your email here, then continue.")])`. No assertion weakened, deleted, skipped or xfailed. `test_rc2_absent_evidence_is_none_not_empty_or_invented` is untouched. `Transcript` and `TranscriptSegment` were already imported (file line 17).
3. Branch run: `uv run --directory <worktree> pytest -p no:xdist -o addopts= tests/test_reconcile_schema.py` -> 19 passed, exit 0 (branch-run.txt).
4. Master run (5da362ea, D:/autoTesting), same command -> 1 failed, 18 passed. The failing node is the RC2 test: `AssertionError: assert None == 'type your email here'` at tests/test_reconcile_schema.py:125, the AT-792 failure (master-run.txt).
5. Contract (qa/contracts/reconcile.md, quoted in the manifest): RC2 needs narration, on_screen_text and exit_screen to round-trip through `ingest_video`, all present and equal; the test still checks exactly that. RC3 is enforced inside `ingest_video` (src/autotester/stages/ingest.py:270-272 builds `heard` only from a passed transcript, then `verify_narration`, src/autotester/stages/reconcile.py:136-141, drops a narration that is not a transcript quote). I read both lines. A real video ingest has a transcript, so the old test passed an input RC3 now correctly rejects: product right, test stale. The new transcript contains "type your email here" as a substring, so the test exercises RC2 preservation plus the RC3 keep-path. The RC3 reject-path is guarded elsewhere (tests/test_reconcile.py::test_rc3_narration_not_in_transcript_is_rejected_and_the_step_kept; not re-run, no product file changed).
6. Falsification (two throwaway copies of `git archive e346c6d1` outside the repo, `PYTHONPATH=<copy>/src`, confirmed importing the copy's autotester; both GREEN before the edit, falsify-green-before.txt):
   - copy a, ingest.py:171 `narration=s.narration or None` changed to `narration=None`: RED, `assert None == 'type your email here'`.
   - copy b, ingest.py:181 `exit_screen=screen_ids.get(exit_name, exit_name) if exit_name else None` changed to `exit_screen=None`: RED, `assert None == 'scr_f0949f19fb5a'` (the `flow.exit_screen == home.id` assertion).
   Both reds are on the named assertion, not an import error (falsify-red-after.txt). Copies deleted afterwards.
7. The manifest's Pre-check (`d9972cbb ... -> 19 passed`) reproduces on e346c6d1; the test file is unchanged between d9972cbb and HEAD (only manifest commits above it).

## Explanation

The test was repaired by supplying the transcript a real video ingest has, with every assertion unchanged, and it still fails when RC2's narration or exit_screen preservation breaks (two copies). Master is red on this node with the AT-792 message and the branch is green.

For the maker: master already contains 1379689c and d9972cbb through the reverted merge, so a plain `git merge wave/at792-stale-rc2-test` brings in only e346c6d1 (a manifest line) and NOT the test fix. Revert 354bd31f (revert the revert) or cherry-pick d9972cbb, then confirm the node is green on master.

Metrics: start=2026-10-11T03:28:00Z end=2026-10-11T03:38:30Z wall_min=10 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=2 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=630 mutants=0 defects_unit=0 defects_6c=0
slow: master pytest run 58 s (collecting against the full tree) and one discarded branch run from the wrong cwd; the lane was off (adapter lane.enabled not set), so the normal check applied
