# Checkpoint -- t198a-zip-drive-intake, coordinator B, cycle 0

Head 894549ee (product 642575ce; tree c11a04ee). Checker: claude-sonnet-subagent (seat B, blind). Policy .9. Verdict: PASS (qa/verdicts/t198a-zip-drive-intake.b.md). Retry 1 (network error, no work lost).

| Check | Command / scope | Code hash | Result |
|---|---|---|---|
| Criterion tests | worktree .venv python `-m pytest -p no:xdist -p no:cacheprovider`, 13 files: test_ui_intake, test_ui_intake_drive, test_drive_intake, test_cli_intake, test_gws_drive, test_gws_runner, test_drive_link, test_drive_verify, test_intake_schema, test_zip_intake_names/limits/register/atomic | commit 894549ee, tree c11a04ee | 297 passed, 1 warning |
| Falsification | 14 edits (TI1-TI9, TI10 seam, TI11, HO30, HO32, HO33), one copy of src/tests each, PYTHONPATH into copy proven | same | 14/14 green -> red (qa/evidence/t198a-zip-drive-intake-B/results/falsify.out) |
| Zip attack | scripts/zip_attack.py, ~45 hostile archives via `expand_zip` | same | all refused/skipped cleanly, no write outside root |
| HTTP attack | scripts/http_attack.py + drive_attack.py, ASGI TestClient with fake gate | same | all refused; boundary >256 gives 500 |
| Drive/gws attack | scripts/drive_attack.py, FakeDrive/FakeRunner, local recorder for real SubprocessGwsRunner | same | no injection; typed errors only |
| Concurrency/fault | scripts/misc_attack.py | same | consistent state; job-file transient errors; 300k-entry memory slope |
| Full suite / browser | not run (seat A owns) | n/a | n/a |

Environment: Windows 11, Python 3.11 worktree .venv, no network call, no real Drive call. Dependency lock not changed by this check.
Evidence dir: qa/evidence/t198a-zip-drive-intake-B/ (scripts, results). Scratch inputs deleted after the check.
