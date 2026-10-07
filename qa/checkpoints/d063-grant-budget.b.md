# Checkpoint B — d063-grant-budget (coordinator B, cycle 0)

Environment fingerprint: Windows 11, worktree .venv (cpython 3.11), HEAD a4bd0a60a3f2b9a76028b0ec1d46f91a8d63dae0, uv.lock sha256 188681b3a300c36f..., no browser/deploy/data snapshot.
Attribution: coordinator B; sub-checkers via Agent (ids in the dispatching transcript only), scratch C:/Users/Lenovo/AppData/Local/Temp/d063-checkerB.

| check | command + scope | result | attribution |
|---|---|---|---|
| lint | `uv run ruff check src tests scripts` | pass | coordinator |
| doctor | `uv run autotester doctor` | exit 1, 1 violation (stale docs/MAP.md) | coordinator |
| full suite | `uv --directory <root> run pytest` (2320 collected) at HEAD a4bd0a60 | 1 failed (test_goal_contract_registration, merge drift), 2314 passed, 5 skipped, 14 xfailed, 1589 s | coordinator |
| falsification R1-R5 + R1b/R1c + M1-M3 | single node per row in throwaway copy, PYTHONPATH=<copy>/src | R1 literal not red; R1b/R1c, R2-R5, M1, M3 red; M2 survives; all restored | sub-checker 1 |
| falsification R6-R9, G1-G4 | single node per row in throwaway copy | R6-R9, G2-G4 red; G1 survives | sub-checker 2 |
| G1 re-run by coordinator | copy g1b, `if False:` at approve_cmd bound check, pytest test_approve_cli+test_approval_signing+test_consent | 59 passed (survives) | coordinator |
| security probes | grant scope/bounds/placeholders/key creation/end-to-end preflight, scratch dirs | findings P5,P6,P9,P13; no scope-widening defect | sub-checker 3 |
| budget/exact-host review | probes with fakes | findings P4,P7,P8,P10; exact-host no defect | sub-checker 4 |
| diff scope 4c | `git diff bd2fe8f4 --stat/--` | no deletions of symbols/assertions | coordinator |

Remaining: none mandatory. Verdict FAIL (P1).

## Cycle 1 (coordinator B), head b90618c9; src/uv.lock/pyproject/conftest identical to a4bd0a60

Environment fingerprint: Windows 11, worktree .venv cpython 3.11, copies under scratchpad c1/m1..m4 (git archive HEAD), PYTHONPATH=<copy>/src:<copy>/scripts.

| check | command + scope | result | attribution |
|---|---|---|---|
| diff identity | git diff --name-only a4bd0a60 HEAD -- src pyproject.toml uv.lock | empty (tests + qa only) | coordinator |
| C3 CLI bounds | copy c1: tests/test_approve_cli_bounds.py (10 collected) | 10 passed | coordinator |
| C3 if False mutant | copy m1, cli_crawl.py:256 | 2 failed (nan, inf), 8 passed | coordinator |
| C3 defaults mutant | copy m4, --production default True | 1 failed, 9 passed | coordinator |
| Row 1 scope | copy c1 green 13 passed; copy m2 `True for d in ref.domains` | 1 failed [scope] DID NOT RAISE, 12 passed | coordinator |
| F3 production | copy m3 consent.py:85 production=True | 2 failed ([valid],[unused]), 11 passed | coordinator |
| bound-tree affected tests | approve_cli_bounds, approve_cli, consent, approval_signing | 69 passed | coordinator |
| lint / doctor | ruff src tests scripts / autotester doctor | pass / 1 violation (stale MAP, as cycle 0) | coordinator |

Reused from cycle 0 by identity: lint, full suite, falsification R2-R9/M1-M3/G2-G4, security and budget/exact-host probes. Remaining: none. Verdict PASS (B side).

## Cycle 2 (coordinator B, tip 1fd229b1)
Environment fingerprint: Windows 11, detached worktree .venv cpython 3.11 (removed after), HEAD 1fd229b1963d784d06ad029fa65ec7945e89cfb2, uv sync clean; no browser build id (local uvicorn on 127.0.0.1:8765 from the bound src), no data snapshot.
| check | command + scope | result | attribution |
|---|---|---|---|
| lint | uv run ruff check src tests scripts | pass | coordinator B |
| doctor | uv run autotester doctor | doctor: clean | coordinator B |
| full suite | uv run pytest (2409 collected incl. xfail/skip) at 1fd229b1 | 1 failed (tests/test_goal_done_checks.py, T-197..T-201 done_check, master fe6eb98a state, .goal/ unchanged by branch), 2388 passed, 6 skipped, 14 xfailed, 2223 s | coordinator B |
| falsification | 31 single-hunk mutants, own isolated copy each (scratchpad b/mutants4.py, mutants5.py) | 26 killed, 5 survived (C9, C10, C12, D4b, X1) | coordinator B |
| real browser | scratchpad b/browser_probe.py, Chromium | same-origin accepted, cross-site and Origin null refused | coordinator B |
Result: PASS, verdict qa/verdicts/d063-grant-budget.b.md.
