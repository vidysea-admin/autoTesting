# Checkpoint - t179a-lead-tester-core, cycle 1, coordinator A (blind dual check)

Verdict: qa/verdicts/t179a-lead-tester-core.r1.a.md (FAIL, C1). Cycle checked: 1. Policy-Version: proportional-verification/2026-10-10.9.
Code under check: c489e201 (code 67a94fb1), Repair base 638d788a, master at check time f6003e87.
Environment fingerprint: Windows 11, uv venv inside `git archive` copies on C: (head, base; merge clone), python from `uv sync --frozen` of uv.lock at c489e201. Hashes: guards.py/tools.py as archived (CRLF in archive; identical to c489e201 with --strip-trailing-cr).
Original attribution: coordinator A (claude-sonnet-5-5) with sub-checkers; evidence dir qa/evidence/t179a-lead-tester-core-r1-A/.

| Check | Command + scope | Result |
|---|---|---|
| AL3c attack table | scripts/al3c-attack/attack.py (229 rows, dispatch + spies, data-root hash) | all refused rows refused (typed, 0 sessions, 0 run_case); no bypass |
| Login carve-out | scripts/login-carveout/run_rows.py (94 rows) | narrow as stated; looser items = P5 |
| ALLOW_WRITES/TEST_ACCOUNT differential | policy-differential/differential.py on base and head (357 rows each) | 42 NAVIGATE rows narrowed per policy; 13 accepted by check_destination -> FAIL C1 |
| C1 reproduction | policy-differential/supplement_head.py (coordinator re-run) | NARROWS rows reproduced |
| F2/F3/F4/F5 | scripts/dispatch-hardening (520+77, 482, 1333 rows; mutant) | F4 clean; F5 mutant dies; leaks P2, P3, label P6 |
| ruff / doctor / limits | `ruff check src tests scripts` 0; `autotester doctor` clean; ast limits | clean; max file 283, max fn 27 |
| Affected tests | agent 131; execute/safety 92; schema/doctor/typing/loop 87; scanner set 182 (all `-o addopts=`) | all passed |
| Falsification | rows 1-3 (+4 coverage note) in own copies | all red after, restored |
| Trial merge | clone of D:/autoTesting at f6003e87 + merge c489e201 | clean; agent 131, advice 33, doctor 40, surface 49, ruff, doctor clean |
| Full suite | not run (criterion open) | owed to next passing check |
