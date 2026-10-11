# Checkpoint - t198a-zip-drive-intake, seat A, cycle 1 (repair)

Attribution: checker seat A, claude-sonnet-subagent; verdict qa/verdicts/t198a-zip-drive-intake.r1.a.md; evidence qa/evidence/t198a-zip-drive-intake-r1-A/.
Environment: Windows 11, root venv D:/autoTesting/.venv, Python 3.11.15 (pytest 9.1.1, python-multipart as locked). Code identity: branch head 3918a8aa, product 0d17d67d (git diff 0d17d67d 3918a8aa -- src tests is empty). uv.lock identical to master. No build/deploy id, no data snapshot (local checks).

| check | command and scope | code hashes | result |
|---|---|---|---|
| F3 / TI6 | root python -m pytest -p no:xdist -o addopts= tests/test_zip_intake_atomic.py in a git-archive copy of 3918a8aa (5 collected); child import path probe | tests/test_zip_intake_atomic.py, src/ at 3918a8aa | 5 passed; child imports the copy |
| F3 falsify | drop env=env in the kill test (copy) | same | 1 passed -> 1 failed (ModuleNotFoundError) |
| F1 / TI5 | 507 + 384 byte flips on a 3-member zip x 4 methods; 12 version-byte archives (version 6.3, 6.4, 9.9, 25.5 on the first, middle and last member); affected set of 8 test files | src/autotester/sources/zip_intake.py at 3918a8aa | 0 crashes; 167 passed |
| F1 falsify | remove lzma.LZMAError and NotImplementedError catch (copy); -k ti5 (13 collected, 24 in file) | same | 13 passed -> 4 failed |
| F2 / HO30 | ASGI-level measurements, 20 cases; tracemalloc peak | src/autotester/ui/upload_stream.py at 3918a8aa | caps hold; legit form 1 MiB and 300 MiB ok |
| F2 falsify | MAX_FIELDS and FIELDS_TOTAL_CAP neutered (copy); -k f2 (3 collected) | same | 3 passed -> 3 failed; peak 567 -> 11469 KiB at 100k fields |

Reuse note for the next check: criteria TI1-TI4, TI7-TI9, TI11, HO32, HO33 were not re-run in cycle 1 (input files untouched by the repair); builder pre-check lines were not reused.
