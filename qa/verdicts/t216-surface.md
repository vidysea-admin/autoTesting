# Verdict - t216-surface (T-216, MP25 MP26)
Date: 2026-10-18 · Cycle checked: 0 · Checker: Mode A, single, bound to d:/autoTesting/.worktrees/t216-surface
Policy-Version: proportional-verification/2026-10-18.15 · Checked: base cff3ffe6 (merge-base with int/1017 confirmed), code d601de49, HEAD 2ffefb6a (adds only the manifest)

## Check plan
Diff = 3 new src files + 3 test files, no deletions (numstat 0 removed), no UI. Tier M. Steps: re-run verify commands; MP25 matrix and MP26 fixture probes of my own; one falsification per criterion in copies of git archive d601de49 outside the worktree; MPI1/MPI3 reads; step 4c diff scope.

VERDICT: PASS
SCOREBOARD: 2/2 criteria met, 4/4 invariants hold (MPI1, MPI2, MPI3, MPI6 as held by the manifest)
TIER: M (new public oracle modules + a shared schema file; no L trigger in the changed non-test files)
FAILURES: none
CAPABILITY-COVERAGE: 6/6 rows evidenced by 2 floor falsifications by me (MP25, MP26) plus the builder's recorded 6 (same files, not re-run: floor is 1 per criterion)
LIVE-BROWSER: not-applicable (src/autotester/schema, src/autotester/stages, tests only)
ISSUES-WRITTEN: AT-1025 (medium), AT-1026 (low)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)

## Evidence
- Verify cmd: `uv run pytest tests/test_oracle_copy_lint.py tests/test_oracle_responsive.py tests/test_oracle_registry.py` -> 41 passed (matches manifest expected 41). ruff: All checks passed.
- MP25 own probe (scratchpad/probe216.py): misspelt Pathlynks/Vidysea/Moodle/"Acme Learning" variants (delete, insert, swap, case, spacing) reported with count; correct use clean; forbidden string counted case-insensitively (2 for 2); timestamps in -05:00, Z, PST, JST, EST, GMT+9, +0900, UTC-8, EDT reported per zone by offset, display-zone forms (+05:30, IST, GMT+5:30) and no-zone/AM-PM-only text clean; mail body cited as a message (/mail/{id}). Titles cite rule id and slug only.
- MP26 own probe (probe216b.py): 520 px page at 375 = finding; control right=420 and left=-30 = findings (count 1); page 376 / control right 376 within the 1 px tolerance = clean, 377 = finding. Masking engine absent in my env -> screenshot withheld with fixed reason, no png written; port screenshot error -> withheld "screenshot_failed", no png, error text not copied. Masked-file-written path is the unit test (OCR faked) through leak_evidence.store_masked_screenshot (leak_evidence.py:87-101).
- Falsification MP25 (copy, green before): test_every_cell_of_the_rule_matrix_is_reported; edit oracle_copy_lint.py:116 `key != shown` -> `False` -> RED on set equality (tz-display zone-offset and zone-pst cells missing).
- Falsification MP26 (copy, green before): test_overflow_at_375_is_a_finding_with_a_masked_screenshot; edit oracle_responsive.py:56 -> `return False, off` -> RED `assert 0 == 1` (len(found)). Both restored by discarding the copies; bound tree untouched.
- MPI1: finding fields are rule id, slug of label, fixed phrase, zone/count, templatised URL; no matched text (oracle_copy_lint.py:125-138, oracle_responsive.py:75-90); SurfaceText repr=False (lint_rule.py:130); screenshots only via store_masked_screenshot. MPI2: fixtures synthetic matrix (test_oracle_copy_lint.py:1-60). MPI3: `git diff --name-only cff3ffe6..d601de49` lists neither multi_role_enums.py nor enums.py.
- Step 4c: 6 added files, all listed in What changed, 0 lines removed, nothing renamed.
- Doctor: 3 violations, exactly the manifest's: drift-filename on oracle_copy_lint.py (doctor.py:25 substring rule vs OracleName.COPY_LINT) and stale MAP/SNAPSHOT. CORE-REQUEST (doctor-oracle-exempt unit), not a FAIL of this unit.

## Non-blocking findings (ledger)
- AT-1025 medium: brand terms under 5 letters get tolerance 0 (oracle_copy_lint.py:75-77), so 'Zoho'->'Zohu' is not reported; disclosed (call 7), shipped matrix terms are longer.
- AT-1026 low: IANA zone names and unknown abbreviations are ignored silently ('09:00 America/New_York' with display IST = clean).
- CORE-REQUESTs 1-4 in the manifest stand for the maker; PASS here does not close MP25/MP26 against a live T-210 session (fakes only, per manifest).

EXPLANATION: Both criteria are met on my own probes and tests; each falsification went green then red on the named assertion, and the diff adds six files without removing anything. The two limits above are disclosed design choices outside the shipped matrix, so they are ledger rows, not FAILs.
slow: protocol read and probe authoring 4 min (wall 9 min: over the 5-min target, under the 10-min hard checkpoint)
Metrics: start=2026-10-18T20:17:50Z end=2026-10-18T20:26:55Z wall_min=9 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=2 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-18.15 lane=normal check_s=545 mutants=0 defects_unit=0 defects_6c=0
