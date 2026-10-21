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
