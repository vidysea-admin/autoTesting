# Checkpoint - at1384-mask-band (coordinator B)
Head 6b2a679c · base c437d3a5 · cycle 0 · result PASS (verdict qa/verdicts/at1384-mask-band.b.md)

| check | command / scope | code identity | result |
|---|---|---|---|
| manifest set | `uv run pytest` on the 11 files named in the manifest | 6b2a679c | 251 passed |
| lint | `uv run ruff check src tests scripts` | 6b2a679c | All checks passed |
| doctor | `uv run autotester doctor` | 6b2a679c | 2 violations, docs/SNAPSHOT.md only |
| reference-hit set | `shard_suite.py --affected c437d3a5..6b2a679c --candidates` -> 71 test files (reference hits on grade, judge_images, sanitized_images, project.json path, golden) | 6b2a679c | 1435 passed, 335 s |
| measurement | probe over 38 PNGs in .worktrees/live-t136-r5 (read in place, counts only), real tesseract, recorder on `_check_mask_area` | 6b2a679c, image set of 38 files | max kept 0.8224, six at 1.0; 18 kept at 0.75, 26 kept at 0.85 |
| falsification | M0 control 102 passed; M1-M7 each red; wiring probe M8/M8b green (untested) | git archive 6b2a679c copies | see verdict |

Environment: Windows 11, uv .venv of the bound worktree, TMP=D:/autoTesting/.work/tmp. Outputs: D:/autoTesting/.work/tmp/chkB/ (mut_out.txt, pytest_hits.txt, cand.json). No real screenshot copied or committed.

## Cycle 1 (repair 6b2a679c..1515721a) - result PASS (verdict qa/verdicts/at1384-mask-band.b.md; cycle-0 verdict archived as at1384-mask-band.r0.b.md)

| check | command / scope | code identity | result |
|---|---|---|---|
| repair diff | git diff 6b2a679c..1515721a over src, projects, tests/golden (empty) and the 1 new test file (blob 245cde0) | 1515721a | read in full |
| product identity | git diff 714720db..1515721a over src, projects, tests/golden is empty; cycle-0 rows above keep identity | 1515721a | unchanged |
| manifest set | uv run pytest, 12 files (11 manifest files + wiring) | 1515721a | 256 passed |
| lint / doctor | ruff check src tests scripts; autotester doctor | 1515721a | clean; 2 violations docs/SNAPSHOT.md only |
| falsification | 5 sites, full-tree copy per mutant (D:/autoTesting/.work/tmp/chkB1/mut_M1..M5), control 5 passed | 1515721a copies | each 1 failed (its own test), 4 passed |
| invalid-limit probe | _check_mask_area and Project(image_mask_limit) over nan/0/-1/0.91/inf/True | 1515721a (read only) | all rejected; None/0.9/0.85/0.75 accepted |
| call-site grep | git grep sanitized_images, judge_images, grade( over src and scripts | 1515721a | every project-scoped site wired |

## Cycle 2 (repair d31003bf..a6afa018, tests only) - result FAIL (verdict qa/verdicts/at1384-mask-band.b.md; cycle-1 verdict archived as at1384-mask-band.r1.b.md)

| check | command / scope | code identity | result |
|---|---|---|---|
| failed criteria | uv run pytest tests/test_ui_runs_serial_resilience.py tests/test_ui_runs_serial_entry_order.py tests/test_at1384_mask_limit_wiring.py | a6afa018 (blobs 01c5ff4, a9df793, 245cde0) | 34 passed |
| sibling doubles | tests/test_ui_runs_serial_entry_screenshot_namespace.py tests/test_run_case_pipeline.py tests/test_video_evidence.py tests/test_ui_runs_target_closed.py tests/test_vision_probe.py | a6afa018 | 36 passed |
| reference-hit set | uv run pytest over 64 test files from git grep (grade, judge_images, sanitized_images, run_and_grade*, _assemble_case, make_grade_stage, grade_case, image_mask_limit, pre_g11_project, run_case_pipeline, orchestrate_downstream) | a6afa018 | 957 passed, 215 s |
| lint / doctor | ruff check src tests scripts; autotester doctor | a6afa018 | clean; 2 violations docs/SNAPSHOT.md only |
| falsification C1 | copy D:/autoTesting/.work/tmp/chkB2/copy; resilience :100 old signature | a6afa018 copy | green-before 30 passed, red-after 1 failed |
| product identity | git diff 714720db..a6afa018 over the at1384 src/project/golden/privacy-test files | a6afa018 | empty (C2-C4 identities kept) |
| call-site grep (supersedes the cycle-1 row) | git grep sanitized_images, judge_images, grade( over src and scripts, then reading each hit's scope | a6afa018 | scripts/run_pathlynks_first_cases.py:139 unwired with project in scope (FAIL); the cycle-1 grep row missed it |

## Cycle 3 (repair 2655c047..01f111de) - result PASS (verdict qa/verdicts/at1384-mask-band.b.md; cycle-2 verdict archived as at1384-mask-band.r2.b.md)

| check | command / scope | code identity | result |
|---|---|---|---|
| repair diff | git diff 2655c047..01f111de over src, scripts, tests, projects (11 files, manifest excluded) | 01f111de | read in full; no assertion removed |
| failed criterion + set | uv run pytest -o addopts= tests/test_ui_runs*.py tests/test_at1384_mask_limit_wiring.py tests/test_run_pathlynks_first_cases.py + regression_proof, bench*, acceptance_comparison, crawl_findings, run_record, ui_bench_inputs, run_case_pipeline, video_evidence, vision_probe (blobs: screenshot_namespace d1bb11d8, first_cases fcf9a635, wiring 58eeecf8) | 01f111de | 240 passed, 1 skipped (RAM-gated live test, untouched) |
| privacy + siblings | 14 files: test_image_privacy*, grade_visual, project_schema_team, multi_role_schema, orchestrate_downstream, run_failure_artifacts, video_frames, agent_loop, agent_fallback, agent_tools, ai_capture, grade_evidence | 01f111de | 377 passed |
| product identity | git diff 714720db HEAD over the unit-owned file set of c437d3a5..714720db | 01f111de | only run_case_pipeline.py:299; core/image_privacy.py, schema, project.py, pathlynks project.json unchanged, so C2-C4 and the 38-PNG measurement identity stand |
| caller enumeration | git grep over src, scripts, tests (grade(, judge_images(, sanitized_images(, store_masked_screenshot(, doubles) plus reading each scope | 01f111de | matches manifest; default-callers have no Project in scope |
| invalid-limit probe | _check_mask_area + Project over nan/0/-1/0.91/inf/True/None/0.9/0.85/0.75 | 01f111de | six rejected, four accepted |
| lint / doctor | ruff check src tests scripts; autotester doctor | 01f111de | clean; 2 violations docs/SNAPSHOT.md only |
| falsification | git archive copies D:/autoTesting/.work/tmp/chkB3/M*, PYTHONPATH on the copy (import verified), control 58 passed | 01f111de copies | M1, M2, M3, M6 red; M4, M5 survive (behaviour-neutral, PROPOSED-ISSUE P1) |
