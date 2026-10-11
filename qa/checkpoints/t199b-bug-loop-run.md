# Checkpoint - t199b-bug-loop-run (cycle 0)

Attribution: single checker coordinator (claude-sonnet-subagent) + sub-checkers A (store/TB6/compat) and B (sheet plan). Verdict: qa/verdicts/t199b-bug-loop-run.md.
Code identity: head d196c26e; `src/` tree baf2d16ac1855680713f5fb94c1d443a04d9ba9b and `tests/` tree 007369471b8c4ad9899dc123081ce82bc2d39eb3, identical at 0d263eab, 50676d85, d196c26e.
Dependency lock: uv.lock identical at d196c26e and master f6003e87 (no diff). Env: Windows 11, CPython 3.11 venv on C: synced from uv.lock, `autotester.__file__` inside the copy; no conftest/fixture change (tests/bug_run_fixture.py and tests/sheet_fake.py are new helpers).
Data snapshot: none (synthetic tmp stores only). Build/deploy id: n/a (no browser/live check).

| Check | Command / scope | Result |
|---|---|---|
| Affected tests | pytest -p no:xdist -o addopts= over 21 files (test_bug_run, _idempotent, _sheet_plan, _bug_store_hardening, _bug_store, _bug_loop, _bug_store_concurrency, _issues, _pinned_regression, _schema, _doctor, _cli_advice_resolves, _cli_surface, _grade, _grade_assertion_rule, _grade_evidence, _score, _migrate_stamp_legacy_rubrics, _coverage_wiring, _unified_report, _ai_report, _failure_bundle) | 537 passed, 3 skipped (qa/evidence/t199b-bug-loop-run/affected.txt) |
| Lint / design | ruff check src tests scripts; autotester doctor | All checks passed; doctor: clean |
| TB3 probe | probe tb3.py (own run dirs) | all expected |
| TB4 probe | tb4.py, tb4k.py | met; P-T1 reproduced |
| TB6 / store / compat / ripple | A: p1*.py p2*.py p3*.py p4*.py | TB6 met; P-S1, P-S6, P-S7, P-S8 |
| TB9/10/11/13/live | B: p1-p5.py | met; P-S2..P-S5, P-S9 |
| Falsification | 7 edits (TB3, TB4 me; TB6 A; TB9, TB10, TB11, TB13 B) | all red on the intended assertion, copies discarded |
| Trial merge | d196c26e into master 822dca2b, throwaway clone | 1 conflict, docs/MAP.md (generated; `autotester map`); ruff/doctor clean; 271 passed |

Reuse note: the builder's Pre-check lines carry no `blobs=` and several have t<30 s, so none was reused; the same tree was re-run.
Full-suite trigger: none for this unit; shared models `schema/verdict.py` (added property) and `schema/tracked_bug.py` -> covered by the 6c full suite.
