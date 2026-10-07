# Checkpoint B - t151-target-discovery (cycle 1)

Verdict: FAIL (see qa/verdicts/t151-target-discovery.b.md). Remaining for repair checker: one full `uv run pytest` (my run did not finish within the wall limit).

Common identity: HEAD 182437925380a793b1a89eb923f8c74ba27e3d03; HEAD:src/autotester/stages 4c3681f075f78c6719111db0b43be902dc5ea49d; HEAD:src/autotester/schema 74ac1b7253a50329c705cef275ea4836f3a47e8d; HEAD:tests/test_discover.py e76b6b61f37678116f1d033fc8cda10441cfd876; HEAD:uv.lock e9bfb8868a57dfc95ee37fc12243eb3efdc61c78; HEAD:pyproject.toml 3cd649dfb048d568b45f2299bc99b49204cc7818; HEAD:providers/mock.py db5cf9bf0b55942a55a3d806f8ffde8162b87220. Environment: win32, bound .venv python, no conftest/fixture changes in diff. Attribution: coordinator B + sub-checkers (Sonnet), scratch under C:/Users/Lenovo/AppData/Local/Temp/claude/checker-b-t151/.

| check | command / scope | result |
|---|---|---|
| lint | uv run ruff check src tests scripts | All checks passed |
| unit | uv run pytest tests/test_discover.py (63 collected) | 63 passed |
| doctor | uv run autotester doctor | 5 D-065 dangling-citation violations only (expected, D-065 on master) |
| obsidian grep | grep -rniE obsidian pyproject.toml | exit 1 |
| full suite | uv run pytest (2283 collected) | NOT COMPLETED at wall limit; seen failures: test_citations dangling (D-065), 3 mc_sessionstart hook timeouts under load |
| falsification | R1a R2a R2b R4a2 R4b R5a R5b R6a R6b R7 R8 R9a R9b R9c R10 R11a R11b R12(cyclic) | KILLED, each green-before in copy, restored green |
| falsification | reader line+1, exec swallowed, .txt admitted, alias check removed (non-cyclic) | SURVIVED (own copies S1-S4) |
| security probes | secrets, path escape, approval, YAML, no-exec, classify injection | held; P2 and P3 reproduced by me |
| prompt rubric | 7-item read-only rubric + probes | satisfied; no blocking defect |

# Cycle 2 (repair checker B, 2026-10-07)

Verdict: FAIL (see qa/verdicts/t151-target-discovery.b.md). Cycle-1 file archived as qa/verdicts/t151-target-discovery.b.r1-1.md.

Common identity: HEAD a9307c2ef42eb2085d18f9203c81546581e6168c (base 2fae2504). HEAD:src/autotester/stages de502a0996a4a40e198bc2282f1cbe5cce0bd2c9; HEAD:src/autotester/schema 426172318a34f4982ea50dadadf6413f7cde9bb0; HEAD:tests/test_discover.py e76b6b61f37678116f1d033fc8cda10441cfd876; HEAD:tests/test_discover_hardening.py c51e02c502aaa9a3dab1f085c75b11e83fb58496; HEAD:uv.lock e9bfb8868a57dfc95ee37fc12243eb3efdc61c78; HEAD:pyproject.toml 3cd649dfb048d568b45f2299bc99b49204cc7818; HEAD:tests/conftest.py e5ff4b8402fdf0b9f1dde251bd25c70401c39139; HEAD:providers/mock.py db5cf9bf0b55942a55a3d806f8ffde8162b87220. Environment: win32, python 3.11 (uv), detached worktree D:/autoTesting/.worktrees/t151-b-suite .venv (80 packages, pyyaml 6.0.3). Attribution: coordinator B alone (no sub-checkers), scratch C:/Users/Lenovo/AppData/Local/Temp/claude/checker-b-t151/ (falsify.py, probe.py, x17.py, rows/, rows2/).

| check | command / scope | result |
|---|---|---|
| lint | ruff check src tests scripts (suite worktree venv) | All checks passed |
| doctor | autotester doctor | doctor: clean |
| obsidian grep | grep -rniE obsidian pyproject.toml | exit 1 |
| flood probe | probe.py: "#a " x 20000 default limits; import flood 3000 lines; multi-file | reader and scan both end in signal_budget, complete=False, signals <= 2000 |
| falsification | 16 rows R01-R16 (one isolated copy per row, named nodes only) | all green -> red (named assertion) -> green, copy restored byte-identical; twice (rows/, rows2/) |
| falsification | X17 scan _emit deadline-in-loop (not in table) | SURVIVES: 3 named + all 90 of test_discover.py+test_discover_hardening.py pass; checker probe test fails 501 scrub calls vs <50 on mutant, passes on baseline |
| full suite | uv run pytest, PID 57552, detached worktree, no -q/-x, started 2026-10-07T09:21:36+05:30 | 4 failed, 2286 passed, 6 skipped, 14 xfailed in 4963.90s (1:22:43); failures: test_crawl_inventory_live (wall_clock_s), test_mc_sessionstart_loop_status x2, test_redact_wrap_perf (3.95s vs 3s); none in files touched by the diff |

# Cycle 3 (narrow, X17 only, repair checker B, 2026-10-07)

Verdict: PASS (qa/verdicts/t151-target-discovery.b.md). Common identity: HEAD a0820901096333f803a4f208a694ba7265e21b44; HEAD:src/autotester/stages/discover.py 9253e1b7d102cbea336f05c1f2fb270fd9867252; HEAD:tests/test_discover_hardening.py a366641df8d7fe22070e63333fd00888bc038dc8; HEAD:uv.lock e9bfb8868a57dfc95ee37fc12243eb3efdc61c78; HEAD:src/autotester/stages 497e66b8a6a53ebbbeb797e7f5c180ed9a4c91e0.

| check | command / scope | result |
|---|---|---|
| X17 falsification | named node, copy of HEAD, discover.py line 208 -> if False | 1 passed -> 1 failed (500 < 50) -> 1 passed, restored byte-identical; all 91 discover tests under mutant: 1 failed, 90 passed |
| affected tests | tests/test_discover.py + tests/test_discover_hardening.py (copy of HEAD) | 91 passed |
| lint | ruff check src tests scripts | All checks passed |
| doctor | autotester doctor | doctor: clean |
| full suite | uv run pytest, worktree, no -q/-x | 2 failed, 2291 passed, 5 skipped, 14 xfailed in 2256.38s; both failures reproduce on a git archive of master 478cc5fb (dashboard sync; live_case 403) |
