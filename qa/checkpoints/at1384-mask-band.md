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
