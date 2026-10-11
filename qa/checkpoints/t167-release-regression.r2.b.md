# Checkpoint - t167-release-regression - repair coordinator B (cycle 2)
Attribution: coordinator B, verdict qa/verdicts/t167-release-regression.r2.b.md · sha 1b6f07e7 (product 7e09124a) · env win32, `git archive` copy + `uv sync --frozen`
Code hashes (blob at 1b6f07e7): tests/test_cli_advice_resolves.py f38eaf4492cc · tests/test_release_gate.py eb7880b7221f · cli_release.py unchanged since 102a4b91 · orchestrate_gate.py unchanged since 102a4b91
Config/lock: uv.lock unchanged (diff 102a4b91..1b6f07e7 touches only 2 test files + manifest)
- `pytest tests/test_cli_advice_resolves.py tests/test_release_gate.py` (34 collected) -> 34 passed · PASS
- click make_context parse of `release --run-id --approve-by|--decline-by` and `release-log` (script outside repo) -> parsed · PASS
- F1 registry entry removed -> test_no_advice_site_can_vanish_unnoticed red by assertion · PASS
- F2 orchestrate_gate wall-clock max removed -> test_rr2_an_under_declared_wall_clock_alone_is_refused DID NOT RAISE · PASS
- Attack A (`releaze`) red x2; Attack B (`--approve`) guard green = latent gap, PROPOSED-ISSUE low
- ruff check src tests scripts clean; autotester doctor clean
- Earlier r1 evidence (RR1, RR3-RR6, RR2 matrix) valid: src unchanged. No full suite run.
