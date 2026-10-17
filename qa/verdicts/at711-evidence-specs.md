# Verdict - at711-evidence-specs
Cycle checked: 0
Policy-Version: proportional-verification/2026-10-15.12
Bound root: D:/autoTesting/.worktrees/at711-evidence-specs (base fcedc9f4 = git merge-base HEAD master; head 9bf1c95f, code commit 6a0052cf)

## Check plan
Tier M (new public functions in a shared ledger module; no UI, no security/auth/tenancy/prod-write). Lane: normal (no adapter lane, cycle 0 M tier).
Criterion C1 = AT-711 `expected`: a capability row names the tree it ran on and the checker refuses a row whose recorded HEAD is not the submitted commit; non-clean digest = disclosure, not disqualification. Issue text: "the criterion must be the COMPARISON, not the recording".
Steps: re-run manifest verify commands; read full diff (4c); falsify C1 in throwaway copies outside the worktree; judge wiring question.

## Result
VERDICT: PASS
SCOREBOARD: 1/1 criteria met, 0/0 invariants violated (doctor clean covers file/function size, one-concept-one-place)
TIER: M (new public functions evidence_specs.py:166-243 in a shared ledger module)
FAILURES: none
CAPABILITY-COVERAGE: 2/2 rows reproduced by checker (manifest rows 1 and 3 name the same comparison; checker re-did the wrong-commit row and the manifest-only row, see FALSIFY)
LIVE-BROWSER: not-applicable (src/autotester/ledger/evidence_specs.py, tests/test_evidence_spec_tombstones.py)
ISSUES-WRITTEN: AT-1012 (medium, guard not wired), AT-1013 (low, empty submitted matches anything)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)

## Evidence (all run by the checker)
- `uv run pytest tests/test_evidence_spec_tombstones.py` in the worktree -> 18 passed, 1 warning (2.79 s).
- `uv run ruff check src tests scripts` -> All checks passed!
- `uv run autotester doctor` -> doctor: clean.
- Diff read in full (`git diff fcedc9f4..HEAD -- src tests`): additions only in evidence_specs.py (+87) and the test file (+95, one import block edited; no assertion removed or weakened, no skip/xfail). No file outside the declared scope.
- FALSIFY (floor, 1 per criterion, throwaway copies under the session scratchpad, imported via PYTHONPATH, `autotester.__file__` verified inside the copy; named test GREEN in the copy first):
  - `test_a_row_on_a_clean_tree_at_the_wrong_commit_is_refused`: green (1 passed) -> after inserting `return True` at the top of `_head_covers` (evidence_specs.py:~201) red on `assert [] == ['capability-...ree-mismatch']`.
  - extra, same cycle: `test_a_row_recorded_at_the_code_commit_survives_a_manifest_only_follow_up`: green -> after making the manifest-only branch `return False` red on the unexpected `capability-row-tree-mismatch` Violation.
  Neither is an import/setup failure.

## Judgement on the maker's hint (wiring)
AT-711 `expected` says the checker "refuses any row whose recorded state does not match the submitted commit" and that the criterion is the comparison, not the recording. `check_capability_row_tree` IS that comparison: it diffs the recorded head against a submitted commit (equal/prefix, or only `qa/manifests/` paths between them), refuses a row with no marker, and keeps a dirty digest as disclosure (`tree_disclosures`). Both the stale-commit-clean case (the maker's refinement) and the missing-marker case go red under real git in tests. The issue does not name `doctor.run` or a checker step, and wiring it into doctor now would flag every existing manifest (none carries a `tree:` marker), which needs a forward-only cut-over decision that is not in the issue text. So: capability met, enforcement not wired; this is not a FAIL of the criterion as stated. Filed as AT-1012 (medium) so the wiring is a tracked candidate, not forgotten.

## Non-blocking findings
- AT-1013 (low): `_head_covers` is a no-op for an empty submitted string (`"x".startswith("")` is True); probed: `check_capability_row_tree(manifest, "", Path("."))` -> [].
- Wording: none.

EXPLANATION: The comparison AT-711 asks for exists, is real-git tested for the dirty-at-head, clean-at-wrong-commit, no-marker and manifest-only-follow-up cases, and reddens under two independent breakages. It is not called by doctor or any checker step, which the issue text does not require and which would break all current manifests; tracked as AT-1012.
Metrics: start=2026-10-17 end=2026-10-17 wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=2 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-15.12 lane=normal check_s=unavailable mutants=0 defects_unit=0 defects_6c=0
