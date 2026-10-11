# Checkpoint - t197-video-pointers - coordinator B, cycle 2 (repair)

Verdict: qa/verdicts/t197-video-pointers.r2.b.md (PASS). Attribution: claude-sonnet-subagent, repair checker B.
Environment: Windows 11, Python 3.11 (uv), ffmpeg on PATH; copy of `git archive b59dda0d` on C: (scratchpad `r2b-copy`), venv from `uv sync --frozen`; uv.lock hash de23568d86e1; no D: checkout.

Code hashes (sha256 prefix of `git show b59dda0d:<file>`): cli_video_review.py b3724644935d; cli_video.py b71c66f9d035; stages/video_pointers.py 7387ae0602c8; tests/test_cli_video_review_exits.py aaf9b8c6e6a5; tests/test_video_pointers.py 84c9da00f13a.

| check | command / scope | result |
|---|---|---|
| lint | `uv run ruff check src tests scripts` | All checks passed |
| doctor | `uv run autotester doctor`; `wc -l cli_video_review.py` | clean; 300 lines |
| exit-path table | harness/table.py, subprocess `drv.py ingest review ...`, wrapped mock provider (modes ok/runtime/oserror/hang/unavailable), 67 runs | exit-path-table.md/.json: 0 exit_code mismatches |
| real Ctrl-C / CTRL_BREAK | harness/sendctrl.py AttachConsole + GenerateConsoleCtrlEvent on the base python process | Ctrl-C: exit 130 + `interrupted` doc, reviews/ empty (x3); CTRL_BREAK: exit 3221225786, no doc, scratch kept |
| redaction | extra.py + ffmpeg signalstats | no still in 60-70 s; live redacted frame YAVG 16, outside ~122 |
| old store | repair-base code (0dcbbfa5 src) writes a review; head re-serves it | exit 0, same id, no provider call, stored file has no exit_code |
| falsification | harness/falsify.py, one copy per row | 7 rows green -> red (falsification.json) |
| affected tests | pytest exits, pointers, cli_video_review, advice_resolves, cli_surface, cleanup | 180 passed + 8 archive-without-.git artefacts; cleanup 19 passed after `git init` |

Not run: full suite (policy .7, not an L security/prod-write unit for this coordinator's brief). Reuse: none from earlier cycles.
