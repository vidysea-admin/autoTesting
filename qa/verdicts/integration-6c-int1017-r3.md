# 6c integration check r3 - int/1017 @ d9a70882

Verdict: FAIL
Cycle checked: 0
Head tested: d9a70882ade754fc5b5d851c5102ca85976b05d1 (int/1017 has since moved to f63ba310 by docs-only commits 984b93ae, f63ba310)
Base: fcedc9f4. Policy: proportional-verification/2026-10-17.13 (full suite: tests/conftest.py edit, tier-L units).

## Commands run (real detached worktree .worktrees/int-6c-d9a70882)
- `uv run ruff check src tests scripts`: All checks passed.
- `uv run autotester doctor`: clean (advisory D-087 findings only).
- Full suite, no -x/--maxfail. The single-process run hung at ~15% (a first attempt) and died silently at ~29% (second
  attempt, `--timeout=240`, exit 1, no summary), so the suite was run file by file (486 test files, 5 in parallel,
  `--timeout=240`) and the 10 red files were rerun serially on head and on base `fcedc9f4`.
- Counts (after the serial rerun): passed=8040 failed=16 skipped=10 errors=0. Of the 16, 1 is a pyc artifact (below), so 15 are real reds.
- `tick.mjs --push-gate` takes `--root`/cwd, no path argument; run in int-1017 it printed `no green stamp` (expected). No stamp written.

## Reds
- NEW (1): `tests/test_hosting_deploy.py::test_env_example_documents_every_key_the_code_reads`: undocumented env key
  `AUTOTESTER_TESSERACT` (`src/autotester/core/image_privacy.py:36`, commit d6ab9e30). Green on base. Owner unit: image-privacy-mask.
  Fix: add the key to `.env.example`.
- Order artifact (1): `test_no_secret_value_anywhere_under_docker_or_in_the_dockerfile` read a stale `docker/__pycache__/*.pyc`; green after removing it.
- Baseline (13, all red on fcedc9f4 with the same message hash): test_cli_advice_resolves (AT-1024), test_goal_contract_registration (AT-743),
  test_infra_trio x2 (WSL bash), test_mutation_check x9 and test_mutation_check_judgement x1 (TMP inside the repo). See `qa/checkpoints/baseline-reds.md`.
- Load-only (not reds): test_crawl_inventory_live, test_video_parallel_sweep, test_viewport_locale_enact, test_video_review_redaction pass serially.

Not done: no merge, no push (index.lock present in the main checkout; head will move when T-208/T-209 merge, so 6c reruns on the final head).

Metrics: start=2026-10-18T23:19 end=2026-10-19T01:10 wall_min=111 agent_min=unavailable blocked_min=0 suite_runs=4 repeat_runs=1 mutations=0 cycle=0 resumes=2 tokens=unavailable policy=proportional-verification/2026-10-17.13 lane=normal check_s=6660 mutants=0 defects_unit=0 defects_6c=1
