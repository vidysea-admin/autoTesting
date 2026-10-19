# Verdict - integration-6c-int1019-redact (maker step 6c pre-push, cycle 0)
Verdict: FAIL
Cycle checked: 0
Head tested: 15d9ca7b (int/1019; detached worktree .worktrees/int-6c-15d9ca7b). Base: ec151a35 (= origin/master). Policy: proportional-verification/2026-10-19.17.
Full suite (.13-2 a: crawl-redact-timestamp is tier L security). TMP/TEMP=D:/autoTesting/.work/tmp.

## Evidence
- `uv run ruff check src tests scripts`: All checks passed. `uv run autotester doctor`: clean (D-087 advisories only).
- Full suite, no -x/--maxfail: 534 test files, 5 in parallel, `pytest-timeout --timeout=240` (as r5). First pass passed=8770 failed=24 skipped=10 errors=0.
  Red files rerun serially once (docker/__pycache__ cleared): test_hosting_deploy green; judgement and mutation_check reds drop to the 10 baseline nodes.
  After rerun: failed=19 = 14 baseline + 4 test_explore_replay (new) + 1 test_role_port_mail (pre-existing on base).
- Logs: .work/6c-int1019-redact/files/ (first pass), .work/6c-int1019-redact/serial/ (rerun), .work/6c-int1019-redact/base-replay-mail.log (base).

## NEW red, owned by crawl-redact-timestamp (FAIL)
`tests/test_explore_replay.py`, 4 nodes (red in the parallel pass and serially, green on ec151a35: 11 passed on base):
- test_a_replay_that_lands_off_domain_is_refused_and_recorded[click], [fill]
- test_the_off_domain_replay_refusal_is_recorded_as_an_edge_a_surface_can_show
- test_a_refill_that_leaves_the_domain_is_caught_before_the_submit_is_clicked
Cause: `AttributeError: '_Redactor' object has no attribute 'scrub'` at src/autotester/stages/explore_summary.py:69
(`redactor.scrub(value)` in `_scrub_text`, new in the merged unit), reached via explore_node.py:72 `persisted.scrubbed(rt, issue)`
from explore_replay.py:131. The test double `_Redactor` (tests/test_explore_replay.py:84) only offers what the old code called,
so every replay path that records a crawl issue now crashes. The unit's own tests (tests/test_crawl_redact_timestamp.py) did not touch
this importer. Fix is in the unit's lane (give the double `scrub`, or run explore_replay in the unit's affected set); no repair made here.

## Reds that are not new
- Baseline (qa/checkpoints/baseline-reds.md): test_cli_advice_resolves x1, test_goal_contract_registration x1, test_infra_trio x2,
  test_mutation_check x9, test_mutation_check_judgement x1 (14).
- `tests/test_role_port_mail.py::test_w2_a_mail_that_arrived_is_observed_through_the_read_only_reader`: not in the baseline record, but red on a real
  detached worktree of ec151a35 (1 failed, 15 passed there), so pre-existing; to be recorded in baseline-reds.md by the maker.

No green stamp written; push NOT performed.

Metrics: start=2026-10-19T20:03 end=2026-10-20T00:00 wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=2 repeat_runs=1 mutations=0 cycle=0 resumes=1 tokens=unavailable policy=proportional-verification/2026-10-19.17 check_s=unavailable mutants=0 defects_unit=1 defects_6c=0 prepush_wall_min=unavailable tests=8794 mode=full shards=5
