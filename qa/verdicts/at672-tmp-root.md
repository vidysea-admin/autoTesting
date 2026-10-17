# Verdict - at672-tmp-root

**Verdict: PASS**
**Checker:** Mode A, fresh context. **Date:** 2026-10-17. **Cycle checked: 0** (manifest Fix cycle 0).
**Bound root:** D:/autoTesting/.worktrees/at672-tmp-root (code 6899f3df, head e14a283c, base fcedc9f4 = merge-base with master).
**Criterion C1 (AT-672):** pytest temp files must not land on the system volume. **Tier:** L (conftest edit), single checker.
Policy-Version: proportional-verification/2026-10-15.12

## Plan
Logic changed in tests/conftest.py (`pytest_configure`) + one new test. Checks: manifest verifies, sample of other test files proving conftest loads, falsification floor (1, in a copy), prune-safety read and probe, `--basetemp` respect. No UI, no security/prod-write trigger, no full suite (full-suite trigger: conftest edit -> pre-push 6c run).

## What I re-ran
1. `uv run pytest tests/test_core.py tests/test_ids.py` -> 18 passed, 1 warning in 4.86s.
2. `uv run ruff check src tests scripts` -> All checks passed. `uv run autotester doctor` -> doctor: clean.
3. Conftest-loads sample: tests/test_doctor, test_env_loading, test_store, test_ledger_checks, test_mutation_sandbox, test_backup_restore, test_bug_store, test_explore_traversal -> 151 passed, 1 skipped in 203.5s (no tmp_path path-length or repo-relative failures).

## Diff scope (4c)
`git diff fcedc9f4..HEAD --stat`: tests/conftest.py (+30), tests/test_core.py (+16), qa/manifests/at672-tmp-root.md (+54). Matches the manifest's What-changed. Diff read in full; nothing deleted or renamed, no assertion weakened, no skip added to an existing test (the new test's skip applies only to an explicit `--basetemp`). conftest.py 263 lines <= 300.

## Falsification floor (copy outside the worktree: git archive HEAD into the scratchpad, worktree venv python)
Named test `tests/test_core.py::test_tmp_root_not_on_system_volume`.
- green (HEAD conftest): 1 passed.
- red (base conftest `git show fcedc9f4:tests/conftest.py`): `AssertionError: C:\Users\Lenovo\AppData\Local\Temp\pytest-of-Lenovo\pytest-36839\test_tmp_root_not_on_system_vo0 is not under ...\fals672c\.work\pytest-tmp` (the named assertion, not an import error).
- restored (HEAD conftest): 1 passed.

## Prune data-loss review (the brief's named risk) - none found
Read tests/conftest.py:42-52. The loop touches only direct children of `<repo>/.work/pytest-tmp` (`_TMP_ROOT.iterdir()`), only `is_dir()` entries older than 24 h, `shutil.rmtree(..., ignore_errors=True)`; `_TMP_ROOT` is a fixed path from `__file__`, not user/env input. Probed in the copy with a seeded tree: 48 h-old dir `old1/sub/f` pruned; fresh dir kept; 48 h-old plain file kept (files are not pruned); an aged Windows junction pointing OUTSIDE the root (`mklink /J`, target mtime aged to 48 h, `is_dir()` true) was NOT followed or deleted, and the outside directory's files (`keep.txt`, `deep/g`) were intact afterwards. Python 3.11 rmtree refuses reparse-point roots. Nothing outside `.work/pytest-tmp` can be deleted by this code.

## basetemp and xdist
- Explicit `--basetemp=<dir>`: conftest returns early (`config.option.basetemp is not None`), run used the caller's dir, new test skipped (1 skipped), nothing created under `.work/pytest-tmp` for it. Respected.
- xdist: the project venv does not have xdist installed (`import xdist` fails), so `-n 2` could not be run. Read only: `hasattr(config, "workerinput")` is the standard worker check, and xdist also forwards the controller's `basetemp` option to workers, so the first condition already returns early on a worker. Not executed; not a criterion item.

## Findings (non-blocking, ledger row AT-1014 appended)
- low: the new test asserts the tmp dir is under `<repo>/.work/pytest-tmp`, not that the volume differs from the OS temp volume; if a checkout lived on C: it would still pass. C1 is met for this host (repo on D:, test red on base). Wording of the criterion vs the instrument only.
- low: runs older than 24 h are pruned but a run's own dir is not removed at session end, so a full-suite loop can leave several GB under `.work/pytest-tmp` for a day (D: had 131 GB free). Acceptable; noted.
- Scratch left in the checker scratchpad (junction `fals672c/.work/pytest-tmp/oldjunc` -> `outside_victim`): the cleanup command was denied by the harness; harmless, outside the repo.

## EXPLANATION
Lane: normal (lane disabled; tier L). Full-suite trigger: conftest edit (session-wide) -> required at the maker's pre-push 6c run; this unit check ran no full suite per brief.

Metrics: start=2026-10-17T10:58:00Z end=2026-10-17T11:15:00Z wall_min=17 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=1 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-15.12 lane=normal check_s=1020 mutants=1 defects_unit=0 defects_6c=0
