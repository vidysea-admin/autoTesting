# Checkpoint — t155-ai-report (single coordinator, cycle 0)

Checked 2026-10-11 · head a4308b35 · product b1ac3e40 · base 9c9a91f3 · agent: claude-sonnet-5-5 checker · verdict `qa/verdicts/t155-ai-report.md`

| Check | Command / scope | Code identity | Result |
|---|---|---|---|
| affected tests | `uv run pytest -p no:xdist tests/test_ai_report.py tests/test_crawl_report.py` (29 collected) | stages/ai_report.py, core/excel.py, stages/crawl_report.py at b1ac3e40; no conftest/fixture/lock change | 29 passed |
| lint | `uv run ruff check src tests scripts` | same | All checks passed |
| design rules | `uv run autotester doctor` | same | doctor: clean |
| diff scope (4c) | `git diff 9c9a91f3 wave/t155-ai-report` (6 files) | same | nothing removed beyond the helper move; no unlisted file |
| falsification x7 | `qa/evidence/t155-ai-report/falsification.md`, one copy each | same | 7/7 green before, red after on an assertion |
| secret/formula probe | scratchpad `t155chk/probe.py`, 24 builds | same | no secret in any cell; `=` cells become formulas (AT-925) |

Environment: Windows 11, Python from d:/autoTesting/.venv, openpyxl as locked. No browser, no data snapshot, no network. Full suite: not run (tier M); `full-suite trigger: none`.
