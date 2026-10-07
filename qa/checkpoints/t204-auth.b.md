# Checkpoint (coordinator B) — t204-auth, cycle 0

Verdict: FAIL (qa/verdicts/t204-auth.b.md). Written 2026-10-07 by coordinator B only; A's files not read.
Bound tree for judging: detached worktree `D:/autoTesting/.worktrees/t204-b` at f7380803 (code d87b2181, base 7782df41). Dependency lock hash: uv.lock at f7380803. Environment: Windows 11, Python from the worktree .venv, argon2-cffi 25.1.0, TestClient (no server) except the browser walk (uvicorn 127.0.0.1:8766, scratch AUTOTESTER_ROOT / AUTOTESTER_AUTH_DIR).

| Check | Command / scope | Code hashes | Result | Attribution |
|---|---|---|---|---|
| Route enumeration + matcher fuzz | scratchpad/matrix/enum_routes.py, fuzz_match.py; 74 pairs; 32,550 cases | f7380803 src/ | 74/74 rows, 0 disagreements | sub-checker 1 |
| Authorization matrix | matrix/matrix.py; 19 keys x routes x {holder, key-only, control, unauth, zero-perm} | f7380803 | 0 mismatches | sub-checker 1 |
| Credential display | matrix/secret_leak.py | f7380803 | no value without credentials.view | sub-checker 1 |
| Escalation probes | matrix/escalation.py | f7380803 | groups.manage-only and users.manage-only reach admin (by contract text) | sub-checker 1 |
| Credential WRITE path | scratchpad/own/xtenant.py | f7380803 | FAIL: dev writes GEMINI_API_KEY, VICTIM_PASSWORD, AUTOTESTER_APPROVAL_KEY via /env/add | coordinator |
| AU15 parity | scratchpad/own/au15.py | f7380803 | admin == developer refusal | coordinator |
| Hash, sessions, rate limit, audit, CLI, storage | scratchpad/data/sc_*.py | f7380803 | PASS with low defects (P10, P11) | sub-checker 2 |
| doctor / ruff | `autotester doctor`; `ruff check src tests scripts` | f7380803 | `doctor: clean`; `All checks passed!` | sub-checker 2 |
| Falsification rows 1-22 + 10b + 16b | scratchpad/t204_falsify_b.py, one copy per row, node per row, copy's `autotester.__file__` confirmed | f7380803 | all RED except row 10 (declared survivor, accepted) | sub-checker 3 |
| Extra mutants | E15 E21s E13 E9 E3a E3b E8 E10 E16 (RED); P1 P2 P3 E2 E22 (SURVIVE); P4 (RED) | f7380803 | see verdict section 3 | sub-checker 3 |
| Browser walk AU26 | Playwright, 127.0.0.1:8766, 4 contexts; D:/autoTesting/qa/evidence/browser-t204-auth-2026-10-07-checker-b/ | f7380803 | PASS with medium/low findings | sub-checker 4 |
| Diff scope 4c | `git diff 7782df41 f7380803` | f7380803 | removals are the documented moves (router list, card helpers) | coordinator |
| Full suite | NOT RUN | - | suite_runs=0: `.work/suite.lock` held by t203-hosting cycle 1 from 19:29:29; and the verdict is FAIL, the suite is owed to the repair check on the fixed tree. Deselect `tests/test_crawl_inventory_live.py` (pre-existing hang). Trigger: tests/conftest.py edit | - | - |

## Remaining for the repair check (cycle 1, failed-criteria list for side B)

- AU21 write path (P1): re-run `xtenant.py`-style probe plus the matrix on the fixed tree.
- AU23 (P2): `.dockerignore` evaluated against a planted `.auth/auth.sqlite3`.
- AU25: the one full suite, once, on the fixed tree.
- AU24 Linux run and the AU1 DECISIONS entry stay external.
- Keep (unchanged inputs): all other rows above keep their recorded results unless the fix diff touches their files.
