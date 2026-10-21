# Checkpoint - at1384-mask-band (coordinator A) - cycle 0
Head 6b2a679c (code 714720db). Environment: Windows, .venv python 3.11, pytest 9.1.1, Tesseract local.

| Check | Scope | Result |
|---|---|---|
| pytest (own run, bound tree) | 15 files: manifest's 11 + test_acceptance_baseline, acceptance/test_ta09_tracker_export, test_run_case_pipeline, test_agent_tools | 304 passed |
| ruff check src tests scripts | whole repo | All checks passed |
| autotester doctor | whole repo | 2 violations, both docs/SNAPSHOT.md |
| green-before in copy | 6 files in .work/tmp/chkA1384/base (PYTHONPATH on the copy, path printed) | 165 passed |
| C1 falsification (default 0.85) | copy c1 | 5 red |
| C2 falsification (Pathlynks 0.9) | copy c2 | 2 red |
| C3 falsifications (invalid-limit check off; text_remains raise off; zero-width mask) | copies c3a/c3b/c3c | 5 / 2 / 34 red |
| C4 falsification (unseen-gap guard off) | copy c4 | 5 red |
| wiring mutants, one site per copy | s1..s5 (run_case_pipeline x2, orchestrate_downstream, run_artifacts, agents/tools) | 101 passed each: SURVIVED (C1 FAIL) |
| measurement probe (counts only, nothing saved) | 38 PNGs, sibling worktree live-t136-r5 runs dir | max kept 0.8224, six at 1.0; limit None 18 kept, 0.85 26 kept |

Remaining: none. A repair checker needs only C1 (the wiring tests) plus one falsification per repaired site.

# Cycle 1 (repair check, head 1515721a, product code unchanged since 714720db)
| Check | Scope | Result |
|---|---|---|
| pytest (own run, bound tree) | manifest's 11 files + tests/test_at1384_mask_limit_wiring.py | 256 passed |
| pytest (own run, bound tree) | wiring + engine/grade_visual/schema/golden/privacy/reocr/orchestrate/run_failure/run_case_pipeline/agent_tools | 212 passed |
| ruff check src tests scripts | whole repo | All checks passed |
| autotester doctor | whole repo | 2 violations, both docs/SNAPSHOT.md |
| control in copy .work/tmp/chk1384A2 | wiring file, PYTHONPATH on copy | 5 passed |
| wiring mutants s1..s5, one site per copy (chk1384A2_s1..s5) | wiring file | 1 failed / 4 passed each: all 5 KILLED (C1 PASS) |
| limit validation probe (copy) | schema + _check_mask_area on 0,-1,0.95,NaN,inf | all rejected / invalid_mask_limit |
Caller grep: only grade_errored_result (unreachable ERRORED path) and no-project callers use the default. Remaining: none.

# Cycle 2 (repair check, coordinator A, head a6afa018, repair base d31003bf, product code unchanged since 714720db)
| Check | Scope | Result |
|---|---|---|
| pytest (own run, bound tree) | test_ui_runs_serial_resilience + test_ui_runs_serial_entry_order + test_at1384_mask_limit_wiring | 34 passed |
| pytest (own run, bound tree) | wide set: all test_ui_runs*.py, agent_tools, ai_capture, grade_evidence, orchestrate_downstream, run_case_pipeline, video_evidence, agent_fallback, agent_loop, run_failure_artifacts, video_frames, vision_probe, image_privacy*, grade_visual, project_schema_team, multi_role_schema | 481 passed |
| ruff check | the 2 touched test files | All checks passed |
| C1 floor falsification | copy .work/tmp/chk-c2A (git archive HEAD, PYTHONPATH on copy): control 35 passed; resilience:100 old signature -> 1 failed; restored -> 8 passed | red-after / restored |
| sibling probe | copy: assert verdicts in test_ui_runs_serial_entry_screenshot_namespace -> INCONCLUSIVE TypeError mask_limit; double widened -> PASS | stale double found (C1 FAIL) |
| candidate grep | shard_suite --candidates c437d3a5..a6afa018 -> integration-required (exit 2, range spans other units); hand git-grep over tests/ scripts/ src/ | 1 uncovered double |
| C2-C4 identity | at1384 src files + their test files unchanged since 714720db; reused | reused |
Remaining: none for this cycle (FAIL on C1 sibling gap).

# Cycle 3 (repair check, coordinator A, head 01f111de, code 5051ba30, repair base 2655c047)
| Check | Scope | Result |
|---|---|---|
| pytest (own run, bound tree) | brief set: test_ui_runs*.py, wiring, run_pathlynks_first_cases, regression_proof, bench*, acceptance_comparison, crawl_findings, run_record, ui_bench_inputs, run_case_pipeline, video_evidence, vision_probe + agent_tools, ai_capture, grade_evidence, orchestrate_downstream | 378 passed, 1 skipped |
| pytest (own run, bound tree) | manifest verify list, 11 files | 251 passed |
| ruff check src tests scripts / autotester doctor | whole repo | All checks passed / 2 violations, both docs/SNAPSHOT.md |
| caller + double enumeration | git grep over src, scripts, tests; each site read | complete; defaults only where no Project in scope |
| green-before in copy .work/tmp/chk3A/base | namespace, run_pathlynks_first_cases, wiring, regression_proof, bench, bench_marks | 74 passed |
| falsifications, one copy each (f1, f2a, f2b, s1) | F1 double signature; F2 grade call; F2 main() call; run_case_pipeline.py:299 | all red (1 failed each) |
| surviving non-floor mutants s2, s3 | bench_trial.py:104, regression_proof.py:147 | survive; low PROPOSED-ISSUE |
| golden falsification (copy g2) | line removed from pre_g11_project.json | red at byte 956 (green-before 63 passed) |
| C2-C4 identity | image_privacy, schema, project.json, grade_images, golden: empty diff since 714720db | reused, re-run green |
Remaining: none.
