# Verdict - at697-committed-fresh

**Verdict:** PASS
**Status:** PASS
**Cycle checked:** 0
**Reviewed SHA:** 92649717 (code d0774e62; base 82275231 = git merge-base HEAD int/1017)
**Policy-Version:** proportional-verification/2026-10-17.13

## Plan
Tier M, one criterion C1 = AT-697 / qa/contracts/living-ledger.md:26-33 (L1 "Committed == disk == fresh"). Checks: re-run verify commands; read the full diff; end-to-end stale-commit scenario in a copy; one falsification in a copy outside the worktree; judge the advisory.py edit.

## Independent checks
- `uv run pytest tests/test_committed_fresh.py tests/test_doctor.py` -> 48 passed (matches manifest).
- `uv run ruff check src tests scripts` -> All checks passed!
- `uv run autotester doctor` -> exit 1 with exactly 2 violations, both `decision-citation-dangling` on qa/manifests/at697-committed-fresh.md:15 and :31 citing D-104. Base-lag, not a defect: `git grep "^## D-104" int/1017 -- docs/DECISIONS.md` finds the entry. No `stale-generated`, `stale-committed` or `committed-leg-skipped` finding on the real worktree.
- Size rules: doctor.py 287 lines, committed_fresh.py 89, test file 145; module docstring states the one job; `check_generated_fresh` untouched (diff read in full).

## Contract comparison (C1)
- Contract Verify: stale committed MAP.md regenerated on disk uncommitted -> doctor non-zero naming the committed blob; commit it -> clean. Reproduced end to end in a scratchpad copy (git repo from `git archive`, driver doctor.run + doctor.blocking): after the stale commit plus uncommitted regeneration, `stale-generated docs/MAP.md` is ABSENT (disk leg passes) while `stale-committed docs/MAP.md` is reported and blocking; after committing the regeneration the MAP finding is gone. (SNAPSHOT findings in that copy are noise from a partial copy without qa/.)
- No-commit / non-git: `_skip_reason` returns a reason, violation `committed-leg-skipped` is emitted and named; test line 124-134 asserts it is reported and non-blocking. Never a silent pass.
- Normalisation: `_lf` applied to both sides (committed_fresh.py:86-87 area, `_compare`); fixtures use `git clone -c core.autocrlf=true` (shape C, as the row demands), test_fixture_really_checks_out_crlf asserts CRLF really on disk.

## Falsification (floor, 1 for C1, copy outside the worktree)
`_compare` made to `return []` before reading the blob: unmutated copy 8 passed; mutated copy 3 failed (test_stale_committed_map_regenerated_on_disk_is_named, test_doctor_run_wires_the_committed_leg, test_untracked_generated_file_in_a_committed_repo_is_stale), 5 passed. Red on the named assertion, not an import error. Restored (copy only; the worktree was never edited).

## advisory.py edit (hint 2)
Necessary for the criterion: a non-git or pre-first-commit tree must report the leg skipped without going red; `committed-leg-skipped` in NON_BLOCKING does exactly that and is covered by test line 134. In scope of the issue's "skipped and named". Not an enforcement path.

## Findings (non-blocking, no FAIL)
- low (wording): the warning summary for `committed-leg-skipped` is labelled "(D-087, non-blocking)" (advisory.py warning_summary), a cosmetic mismatch the maker already noted.
- low (test): as the maker states in the manifest, the clone fixtures cannot by themselves falsify `_lf` because the fresh side is read with universal newlines; the CRLF-blob test is the real normalisation falsifier and is sensitive. Not a defect.

Invariants: none-touched (no schema, credential or enforcement-path change).

Metrics: start=2026-10-18T02:10:00Z end=2026-10-18T02:35:00Z wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=1 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-17.13 lane=normal check_s=unavailable mutants=0 defects_unit=0 defects_6c=0
