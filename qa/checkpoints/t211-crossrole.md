# Checkpoint - t211-crossrole (checker, cycle 0)

Environment: Windows 11, worktree .venv, uv.lock sha256 d7ff32b5ab4a. Checked code 4425f762 (HEAD cff3ffe6). Attribution: checker claude-sonnet-subagent, verdict qa/verdicts/t211-crossrole.md.

| check | command / scope | code + test hashes (blob7) | result |
|---|---|---|---|
| affected tests | `uv run pytest tests/test_cross_role_runner.py tests/test_oracle_registry.py tests/test_cross_role_schema.py` (56 collected) | runner 7e0f305, registry a294f63, test_runner 2521d1a, test_registry 49d506c, test_schema 85c5cdc | 56 passed |
| ruff | `uv run ruff check src tests scripts` | same tree | pass |
| doctor | `uv run autotester doctor` | same tree | 2 violations, both stale-generated (MAP, SNAPSHOT) |
| MPI3 | `git diff --name-only 36a87037..4425f762` | - | enums file absent |
| falsify MP13 | copy m13: window +2.5 s; node ...::test_mp13_same_view_fails_at_window_1_with_window_and_last_observation | runner 7e0f305 | green before, red after |
| falsify MP14 | copy m14: early break + guard removed; node ...::test_mp14_absent_passes_only_after_the_full_window_with_no_match | runner 7e0f305 | green before, red after |
| falsify MP15 | copy m15: NOT_BUILT -> NOT_RUN; node ...::test_mp15_one_absent_module_is_reported_not_built_and_not_omitted | registry a294f63 | green before, red after |
| timing probes | fake clock boundaries, slow observe, real SystemClock x30, non-Observation port, phone-shaped text | runner 7e0f305 | see verdict; findings AT-1211, AT-1212 |
