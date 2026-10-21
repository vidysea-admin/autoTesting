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
