# Baseline reds (.8-5)

Recorded 2026-10-19 by the 6c r3 checker. Baseline sha: `fcedc9f4` (= origin/master). Each row was shown red on a real
detached worktree of the baseline (`.worktrees/base-6c-r3`), not on a `git archive`. Hash = first 12 hex of sha256 over the
first three `E` lines of the failure section, with temp-dir ids, hex addresses, durations and absolute paths removed.
A record is reusable only while baseline sha, node id and message hash all match and the test file is unchanged.
Environment of the run: Windows, `TMP`/`TEMP=D:/autoTesting/.work/tmp` (inside the repo tree), no usable WSL bash,
`pytest-timeout` added with `uv run --with pytest-timeout`, `--timeout=240`, `-p no:cacheprovider`.

| Baseline | Node id | Msg hash | Cause (one line) | Ticket |
|---|---|---|---|---|
| fcedc9f4 | tests/test_cli_advice_resolves.py::test_the_collector_reports_what_it_could_not_resolve | 64117fe5c1cf | collector reports unresolved route at routes_crawl_approval.py:184 | AT-1024 |
| fcedc9f4 | tests/test_goal_contract_registration.py::test_revised_goal_contract_is_registered | 3016cce7b43d | `assert 92 == 106` | AT-743 |
| fcedc9f4 | tests/test_infra_trio.py::test_verify_gates_keeps_exit_code[0] | 7da89c6efab4 | WSL has no /bin/bash, exit 1 | env |
| fcedc9f4 | tests/test_infra_trio.py::test_verify_gates_keeps_exit_code[3] | 898a8dd1f0cc | WSL has no /bin/bash, exit 1 | env |
| fcedc9f4 | tests/test_mutation_check.py::test_a_real_mutation_is_killed_and_attributed | c9949b2c7ed4 | node ids come back prefixed `.work/tmp/mutation-check-*/repo/` when TMP is inside the repo | env (TMP) |
| fcedc9f4 | tests/test_mutation_check.py::test_it_refuses_when_the_named_test_survives_but_another_fails | 479320731850 | same TMP-prefix cause | env (TMP) |
| fcedc9f4 | tests/test_mutation_check.py::test_a_suite_split_across_files_is_still_one_suite | 7a861f4c48a1 | same TMP-prefix cause | env (TMP) |
| fcedc9f4 | tests/test_mutation_check.py::test_a_kills_entry_may_be_the_full_nodeid_the_guard_asks_for | 9fd4ab372872 | `MutationError ... names test(s) that are not collected` | env (TMP) |
| fcedc9f4 | tests/test_mutation_check.py::test_a_passing_sibling_is_never_credited_with_another_tests_failure | 4d89d797e5fd | same | env (TMP) |
| fcedc9f4 | tests/test_mutation_check.py::test_a_failing_test_that_prints_a_summary_line_cannot_fake_a_kill | e9b139a84ac1 | same | env (TMP) |
| fcedc9f4 | tests/test_mutation_check.py::test_a_named_test_that_did_not_run_under_the_mutation_is_never_killed | f75de8e4c02d | same | env (TMP) |
| fcedc9f4 | tests/test_mutation_check.py::test_a_named_test_that_errors_in_setup_is_not_a_kill | b6b5e7f314b7 | same | env (TMP) |
| fcedc9f4 | tests/test_mutation_check.py::test_a_mutation_is_attributed_to_a_parametrized_test_with_spaces_in_its_id | 441725533781 | `MutationError ... names test(s) that are not collected: [tests/test_spaced.py::test_small[one small value]]` (same TMP cause; shown red on `.worktrees/base-6c-fcedc9f4` by the r5 checker) | env (TMP) |
| fcedc9f4 | tests/test_mutation_check_judgement.py::test_an_interrupted_run_with_real_failures_is_not_a_kill | 194d6ac656d7 | `an interrupted run still reports the tests that really failed` (TMP-prefix cause) | env (TMP) |

## Not recorded as baseline (load-dependent, one-offs)

- `tests/test_mutation_check_judgement.py::test_a_hung_baseline_is_refused_even_when_a_child_holds_the_output_open`
  (hash 490062c349d2) was red on base once and green on the head in the same serial pass: a timing flake, not a record.
- `tests/test_crawl_inventory_live.py`, `test_video_parallel_sweep.py`, `test_viewport_locale_enact.py`,
  `test_video_review_redaction.py` failed or timed out only under 5-way parallel load and pass serially on head and base.
- `tests/test_hosting_deploy.py::test_no_secret_value_anywhere_under_docker_or_in_the_dockerfile` reads
  `docker/__pycache__/supervise.cpython-311.pyc` when an earlier test has imported `docker/supervise.py`; it passes on a clean tree.
  Order-dependent artifact, not a defect of a merged unit (candidate issue: make the test skip `__pycache__`).

## NOT baseline (new on int/1017, see qa/verdicts/integration-6c-int1017-r3.md)

- `tests/test_hosting_deploy.py::test_env_example_documents_every_key_the_code_reads` (hash a9a7ccacc7a4): green on fcedc9f4,
  red on d9a70882. `AUTOTESTER_TESSERACT` is read at `src/autotester/core/image_privacy.py:36` (commit d6ab9e30,
  image-privacy-mask) and is missing from `.env.example`.
