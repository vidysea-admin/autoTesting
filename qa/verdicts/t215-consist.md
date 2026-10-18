# Verdict - t215-consist (T-215, G11)

Cycle checked: 0
Checked: 2026-10-18 (checker, Mode A, tier M, single checker, policy proportional-verification/2026-10-18.15)
Bound: D:/autoTesting/.worktrees/t215-consist, Head 27147383 (code SHA 41847254), merge-base with int/1017 = cff3ffe6 (verified with git)

## Check plan
Diff = 4 new src modules, 2 new test files, the manifest; no UI, no auth/tenancy/prod-write, no existing module edited (every hunk is an added file, nothing removed or renamed). Tier M (new schema + oracle modules). Checks: re-run verify commands; MP23 and MP24 one falsification each in a copy outside D:/autoTesting; diff-scope read (4c); MPI1/MPI2/MPI3/MPI6 reads; ruff + doctor. Persona walk and live browser: not applicable (no surface).

## Evidence
- Verify 1: `uv run pytest tests/test_oracle_consistency.py tests/test_oracle_answer_key.py tests/test_oracle_registry.py` -> 85 passed (matches expected 85).
- Verify 2: `git diff --name-only cff3ffe6..HEAD` -> exactly the 6 src/test files plus qa/manifests/t215-consist.md; all additions. MPI3 holds (schema/multi_role_enums.py, schema/enums.py, schema/project.py, browser/session.py, registry not listed).
- Lint: `uv run ruff check src tests scripts` -> All checks passed. `uv run autotester doctor` -> 2 violations, both stale-generated (docs/MAP.md, docs/SNAPSHOT.md); no design-rule violation in the new files (the `run =` alias is how the doctor duplicate-def rule is avoided; see the low row).
- MP23 met: stale-status fixture gives one ROLE_INCONSISTENCY finding whose title names `student=vocabulary:Approved, parent=vocabulary:Pending` (oracle_consistency.py:92-105 reads the cited code); role-specific fields skipped (check_entity :107-110); only classes are placed in the title, raw text stays in the in-memory dict (read_entity :71-82).
- MP24 met: all-correct on the 7/10 key is clean, a wrong or hidden score is ANSWER_MISMATCH (oracle_answer_key.py:57-71); AnswerKeySource refuses a ref or title citing a benchmark/finding/AT-n/MPn/.work (answer_key.py:34-36,48-54) and a key whose points do not sum to documented_score (:101-103).
- MPI1 held: finding titles carry value classes, declared vocabulary labels or two numbers only; the registry reports an oracle exception by type only (oracle_context docstring; test_a_broken_port_is_errored_by_type_only_not_swallowed green). MPI2 held: fixtures are synthetic canaries, no benchmark case. MPI6 (owned part) held: the answer-key schema refuses a finding-citing source (7 variants green).

## Falsification (copies in scratchpad/t215/a and /b, outside D:/autoTesting, PYTHONPATH to the copy)
- [MP23] `if len(values) < 2:` -> `< 3` in oracle_consistency.py: named test `test_mp23_parent_sees_a_stale_status_is_a_finding_naming_each_roles_class` 1 passed in the copy before; after the edit it FAILED on `len(found) == 1` (plus 5 more in the file incl. the MPI1 canary matrix).
- [MP24] `shown[0] == expected and` -> `shown[0] <= expected and` in oracle_answer_key.py: 38 passed in the copy before; after, 4 failed: `test_mp24_a_product_showing_the_wrong_score_is_an_answer_mismatch`, `test_each_off_by_one_display_is_a_mismatch[Your score: 6/10]`, `test_run_reads_the_keys_file`, `test_through_the_registry_a_mismatch_is_counted`.
- The maker's recorded mutants (8) were not re-run beyond the floor; they are consistent with the tests read.

## Judgement calls in the manifest (all accepted)
1 inputs read from JSON under `<run_dir>/multi_role/` (invalid -> raises -> registry `errored`); 5 "7/10" read as documented_score=7 of max_score=10; 3 value classes only; 8 `run = ...` alias for the doctor duplicate-def rule: a workable CORE-REQUEST, not a defect in this unit.

## Non-blocking notes (low ledger row AT-1025)
`parse_score` takes the first number in the score element: `parse_score('Attempt 2 score 7/10')` -> `(2, None)` and `'Score: 70%'` -> `(70, None)` (command run), which would be a false ANSWER_MISMATCH on such a page. Not a criterion of MP24 as quoted; a selector that isolates the number avoids it.

VERDICT: PASS
SCOREBOARD: 2/2 criteria met, 4/4 invariants hold (MPI1, MPI2, MPI3, MPI6 owned part)
TIER: M (new schema + two stage modules, multi-file behaviour; no L trigger in the changed non-test files)
FAILURES: none
CAPABILITY-COVERAGE: 2/2 rows reproduced (one falsification per criterion, green-before in the copy, red-after on the named assertion)
LIVE-BROWSER: not-applicable (changed paths: schema/, stages/, tests/ only)
ISSUES-WRITTEN: AT-1025
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: Both criteria are evidenced by my own re-run (85 passed) and by one independent falsification each that went green then red on the named assertions; diff is additions only, inside the declared six files, and MPI3 holds. One low wording-level robustness note filed as AT-1025.
Metrics: start=2026-10-18T20:16:34Z end=2026-10-18T20:30:00Z wall_min=14 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=1 mutations=2 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-18.15 lane=normal check_s=unavailable mutants=0 defects_unit=0 defects_6c=0
slow: harness setup of the throwaway copy (missing conftest-imported helper modules, 3 re-copies) 8 min
