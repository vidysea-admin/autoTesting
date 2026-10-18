# Verdict - doctor-oracle-exempt

Cycle checked: 0
Policy-Version: proportional-verification/2026-10-18.15
Checked: HEAD e5e0c493 (code state 7f0afd31), base 4dea50b3 = `git merge-base HEAD int/1017`, clean tree.

## Plan (step 0)
Diff: src/autotester/doctor.py (+13/-5, two design-rule checks), tests/test_doctor_oracle_exempt.py (new), docs/MAP.md, docs/SNAPSHOT.md (generated), manifest. Logic changed in a validator = protected change -> L. No UI, no prompt, no data artifact, no security trigger (Dual check: no is right). Checks: re-run verify commands; diff read (4c); probe the exemption boundary in a temp repo; one falsification per criterion in copies outside the worktree.

VERDICT: PASS
SCOREBOARD: 2/2 criteria met (DOE1, DOE2), I* design rules hold (doctor clean, doctor.py 296 lines)
TIER: L (validator edit = protected change, src/autotester/doctor.py:111,133)
FAILURES: none
CAPABILITY-COVERAGE: 2/2 rows reproduced
LIVE-BROWSER: not-applicable (src/autotester/doctor.py, tests, generated docs)
ISSUES-WRITTEN: AT-1222
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)

## Evidence (all run by the checker)
- `uv run pytest tests/test_doctor_oracle_exempt.py tests/test_doctor.py` -> 54 passed. `uv run ruff check src tests scripts` -> All checks passed. `uv run autotester doctor` -> `doctor: clean`.
- DOE1 probe (temp repos, PYTHONPATH=worktree src): stages/foo_copy.py, oracle_notreal_copy, oracle_mailbox_copy, oracle_copy_lint_v2 -> drift-filename red; stages/oracle_copy_lint.py -> clean. Only copy_lint contains a banned hint among the 13 enum stems, so the exemption is exactly that name.
- DOE2 probe: run in two non-oracle modules -> 1 duplicate-concept; run in stages/oracle_notreal.py + a.py -> red; oracle_<enum> run alongside a.py or zzz.py -> clean in either order (order-independent: the oracle `run` is never recorded); another name (helper) in two oracle modules -> red; run in two oracle modules -> clean.
- Diff read (4c): doctor.py:27 ORACLE_STEMS from the OracleName enum (no hand list), :111 stem guard, :132-139 oracle flag + `continue` for name `run`. Nothing removed from the two rules besides the exempted case; no file outside the declared scope.
- Falsification DOE1 (copy f1 of HEAD, outside D:/autoTesting): 14 passed green; widening `path.stem not in ORACLE_STEMS` to `not path.stem.startswith("oracle_")` -> 4 failed on `test_every_other_banned_name_stays_red[oracle_notreal_copy|oracle_copy_lint_copy|oracle_copy_lint_v2|oracle_tenant_new]`.
- Falsification DOE2 (copy f2): 14 passed green; widening `path.stem in ORACLE_STEMS` to `startswith("oracle_")` -> 1 failed on `test_run_outside_a_real_oracle_module_still_collides[stages/oracle_notreal.py]`.

## Judgement notes (non-blocking, filed as AT-1222, low)
- The DOE1 stem exemption is not scoped to stages/: probe `src/autotester/schema/oracle_copy_lint.py` is clean (doctor.py:111 checks only `path.stem`). The DOE2 exemption is scoped by `path.parent.name == "stages"` (doctor.py:132), so `x/stages/oracle_mailbox.py` is also exempt. Both match criterion text (brief: "exactly the stems", "stages/oracle_*.py") and the real tree has one stages/, so not a FAIL; neither case is pinned by a test.
- New test file instead of tests/test_doctor.py: acceptable (the existing file is at the 300-line cap, no near-duplicate of existing tests).

EXPLANATION: Both exemptions are derived from the OracleName enum and nothing wider by stem; every probe of foo_copy, oracle_notreal_copy, run in non-oracle modules and other names in oracle modules stayed red, and both falsifications went red on the named assertions. Only the directory scoping is looser than the contract wording (low, AT-1222).
Metrics: start=2026-10-19 end=2026-10-19 wall_min=12 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=2 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-18.15 lane=normal check_s=720 mutants=0 defects_unit=0 defects_6c=0
