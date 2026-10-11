# Checkpoint - t198a-zip-drive-intake r1, seat B (cycle 1)

Policy: proportional-verification/2026-10-10.9. Head 3918a8aa, product 0d17d67d, Repair base 894549ee. Environment: Windows 11, CPython 3.11.15, worktree venv (python-multipart 0.0.32 per uv.lock hash 4882ef560a), root venv for R3.
Code blob hashes at 3918a8aa: zip_intake.py 46ad724dff, upload_stream.py de7297dc4f, test_ui_intake.py 349236ce2b, test_zip_intake_atomic.py 7870dfa12a, test_zip_intake_register.py b48dbeb452.
Checker: claude-sonnet-subagent (seat B). Evidence: qa/evidence/t198a-zip-drive-intake-r1-B/.

| check | command and scope | result |
|---|---|---|
| archive battery | `scripts/zip_attack.py <src> <work> <out>` 331 cases, old and new tree | new: 1 raise (UnicodeDecodeError), no staging left; 39 cases changed, all old raises |
| fuzz | `scripts/fuzz.py <src> 2500` seed 1198 | 0 exceptions |
| field caps | `scripts/http_attack.py <src> <work> <out>` 29 cases | all refusals 400/413, 0 file bytes, 0 rows |
| R1a R1b | pytest copy r1a/r1b `-k "damaged_compressed_member or zip_version_python"` | green 10 and 1, red 3 and 1 |
| R2a R2b | pytest copy `test_ui_intake.py -k f2` | green 3 each, red 1 each |
| R3a R3b | `scripts/runpt.py` root venv, `test_zip_intake_atomic.py -k killed_between_copy_and_row` | new green, old test red, heal mutant red |
| affected tests | 8 files, copy at 3918a8aa | 167 passed |
| ruff | 5 changed files | clean |
Result: FAIL (P1 UnicodeDecodeError). Reusable on an unchanged tree: R2, R3, affected tests, archive battery for every case but cd-utf8-flag-bad-name.
