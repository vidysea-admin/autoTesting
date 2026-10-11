# Verdict A - t178-failure-bundle-fb4-fb5, fix cycle 1 (repair check, seat A of a blind dual check)

Date: 2026-10-11 · bound to D:/autoTesting · Cycle checked: 1 · Head 297207ff (product c142f8f1; master 8791b76b merged at 2587a7b1) · Repair base a7d3fa6c (git: ancestor of HEAD) · Policy-Version: proportional-verification/2026-10-10.9
Evidence: qa/evidence/t178-failure-bundle-fb4-fb5-r1-A/ · Checkpoint: qa/checkpoints/t178-failure-bundle-fb4-fb5.r1.a.md

## Check plan
Tier L (dual-trigger security, src/autotester/stages/failure_bundle.py:211-212). Repair-scoped: failed list = full suite red `test_no_advice_site_can_vanish_unnoticed`. Repair diff a7d3fa6c..HEAD split into (a) master merge, (b) fix agent's: `stages/expand.py::stage_and_review` (moved out of `cli.py::expand_cases`, expand.py:127-138, cli.py:220) and `tests/test_cli_advice_resolves.py` (+4/-1). FB5 inputs touched, so FB5 re-run; FB4 input files (schema/case.py, store/project_store.py, ui/routes_runs.py, ui/run_queue.py, schema/run_queue.py) are byte-identical to a7d3fa6c (`git diff --stat` empty), so FB4 kept its recorded result but was re-run anyway. No template or route response changed: no browser. One full suite on the new head.

VERDICT: PASS
SCOREBOARD: 2/2 criteria met (FB4, FB5) + containment + advice-guard repair; invariants C2 (doctor clean) and C5 hold
TIER: L (dual-trigger src/autotester/stages/failure_bundle.py:211-212, unchanged by the repair)
FAILURES: none

## Per-criterion
- FB4: met. 60 passed (test_schema, test_store, test_pinned_regression, test_ui_runs). Files unchanged by the repair; the recorded falsification stands.
- FB5: met. 61 passed (test_expand, test_expand_cli, test_ui_learn, test_eval_compiler). Falsified the moved code, each in its own copy of 297207ff, pristine copy 11 passed first:
  - m1 `for proposal_id in approve + prune:` -> `in []` (expand.py:134): red at `assert (0 == 1)` in test_cli_proposal_review_is_signed_and_pending_generation_spends_nothing (an unsigned `--approve` no longer refuses).
  - m3 delete `store_.preflight_case_proposals(spec)` (cli.py): red `Failed: pending proposals reached provider` in the same test (generation without approval).
- Containment: kept. failure_bundle.py / schema/failure_bundle.py are not in the repair diff (`git diff --stat a7d3fa6c 297207ff` empty); 23 passed again.
- Advice repair: 32 passed. Falsified in copy: delete `("ui/routes_learn.py", "expand")` from EXPECTED_SITES -> red `new: [('ui/routes_learn.py', 'expand')]`.

## The four rulings
1. EXPECTED_SITES +2 entries (`cli.py expand`, `ui/routes_learn.py expand`), count -> 23 (the 3 other additions, `release`, `release-log` and the 21 base, are master's). Correct, and NOT a protected change: it adds expectations and raises the count, weakens no assertion, and the test's own docstring says a new site "should be added here". Both sites exist and `autotester expand --help` lists `--proposals/--approve/--prune/--by`.
2. Moved product code: behaviour unchanged. Read: the block is moved verbatim (propose, stage, approve/prune conflict ValueError, review loop, id filter), same ValueError -> exit 1 path; `ids` is now built unconditionally, no effect. Differential: the same `autotester expand` sequence (pending generate, --proposals, approve+prune same id, unsigned prune, bogus id, prune 2, approve rest, generate) run on a7d3fa6c and on 297207ff gives identical exit codes, messages and statuses modulo proposal ids (probe-*.json): pending generate 1 with "human approval of HAPPY proposal required...", both 1, unsigned 1, bogus 1, then 13 proposals, 2 pruned, generate writes 11 cases and no pruned class. cli.py is 300 lines, doctor clean, ruff clean.
3. Docstring merge conflicts (cli.py `_bootstrap`, paths.py `prompts_dir`): nothing else dropped. `git diff 8791b76b 297207ff -- cli.py core/paths.py` shows only the unit's `expand_cases` hunk and `case_proposals`; the `release` and `release-log` registrations, `cli_release` import and master's wording are intact. Whole-unit diff vs master: 24 files, all named in the manifest; removed defs are only the signature-widened `expand_flow`/`expand`/`list_cases`/`_prepare_run`/`trigger_run`, `_compile`, and rewritten tests whose names still exist.
4. Path containment hunk untouched by the repair: confirmed; cycle-0 result kept.

## Full suite (policy .7, tier L security trigger: one run)
`shard_suite --repo D:/autoTesting --ref 297207ff --shards 4 -- -o addopts=`: 3457 passed, 4 failed, 19 skipped; collect proof ok (3480 = 3480). The advice guard is green. Reds, all already on the master list: test_rc2_ingest_video_keeps_narration_on_screen_text_and_exit_screen (AT-792, red alone), test_env_example_documents_every_key_the_code_reads (AT-920, red alone), test_healthz_source_root_is_the_package_even_when_the_data_root_is_elsewhere (AT-921, red alone), test_hook_prints_the_report_and_exits_zero_on_a_healthy_log (AT-858 load flake, passed alone). No new red. AT-725/750/924 did not fire.

CAPABILITY-COVERAGE: 4/4 repair rows reproduced (FB5 x2, ADVICE x1 here; FB4 and CONTAIN keep recorded results, files unchanged)
LIVE-BROWSER: not-applicable (repair diff changes no template or route response; persona walk owed by cycle 0 already done)
ISSUES-WRITTEN: none (dual coordinator)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)

PROPOSED-ISSUE: {"severity":"low","feature":"failure-bundle","title":"CLI `expand --prune` has no test: mutating stage_and_review `approved=proposal_id in approve` to `approved=True` survives test_expand_cli.py + test_expand.py (25 passed)","evidence":"src/autotester/stages/expand.py:135; scratchpad mutant m2; store-level prune is covered by test_five_nonhappy_proposals_prune_before_spend, only the CLI door is not","regression_check":null}

EXPLANATION: The cycle-0 red was real and is fixed by registering the two new advice sites; the code move into stage_and_review is a verbatim extraction that a differential run shows behaves identically to the pre-move CLI, and the gate falsifications still go red on the assertions they are named for. Master's merge dropped nothing, FB4 and the containment hunk are untouched by the repair, and the single full suite shows only reds already recorded on master. The surviving `--prune` CLI mutant is a coverage gap in existing behaviour, not a repair defect, so it is a low proposed row.

Metrics: start=2026-10-11T06:37:00+05:30 end=2026-10-11T06:59:00+05:30 wall_min=20 agent_min=unavailable blocked_min=9 suite_runs=1 repeat_runs=0 mutations=4 cycle=1 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=1320 mutants=3 defects_unit=0 defects_6c=0
