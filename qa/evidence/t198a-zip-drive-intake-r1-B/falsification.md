# t198a-zip-drive-intake r1, seat B: falsification rows (all in throwaway copies of `git archive 3918a8aa src tests scripts pyproject.toml`, outside the worktree)

Runner: worktree venv python, `PYTHONPATH=<copy>/src;<copy>/scripts`, `pytest -p no:xdist -p no:cacheprovider -o addopts=`, one process at a time. Copies deleted afterwards.
Each row: named tests green in the unedited copy first, then the edit, then red.

| Row | criterion | edit (one hunk, one file) | before | after (red on) |
|---|---|---|---|---|
| R1a | F1 / TI5 | `zip_intake.py:179` drop `lzma.LZMAError` from the member `except` | `-k "damaged_compressed_member or zip_version_python"` 10 passed | 3 failed: `test_ti5_a_damaged_compressed_member_is_failed_whatever_the_decompressor_raises[0.2/0.5/0.8-14]`, raised `_lzma.LZMAError: Corrupt input data` out of `expand_zip` |
| R1b | F1 / TI5 (extra) | `zip_intake.py:237` `except NotImplementedError` -> `except ZeroDivisionError` | `-k zip_version_python` 1 passed | 1 failed: `test_ti5_a_zip_version_python_cannot_read_is_a_failed_report_not_a_crash`, `NotImplementedError: zip file version 9.9` from `zipfile.py:1443` (central-directory parse, so the stdlib cannot list such an archive at all) |
| R2a | F2 | `upload_stream.py:162` `len(self.fields) >= MAX_FIELDS` -> `>= 10**9` | `-k f2` 3 passed | 1 failed: `test_f2_the_reader_holds_a_bounded_amount_however_many_fields_arrive` (the HTTP many-fields test still passes under this mutant because the total cap fires first) |
| R2b | F2 (extra) | `upload_stream.py:165` `self._kept > FIELDS_TOTAL_CAP` -> `> 10**12` | `-k f2` 3 passed | 1 failed: `test_f2_a_few_large_fields_are_refused_by_the_total_cap` |
| R3a | F3 / TI6 | revert `tests/test_zip_intake_atomic.py` to its 894549ee version; runner = root venv `D:/autoTesting/.venv` python, parent `sys.path` = copy/src, no PYTHONPATH env | NEW test: 1 passed | OLD test: `assert 1 == 9`, child `ModuleNotFoundError: No module named 'autotester.sources.zip_intake'` (child imported master) - reproduces the cycle-0 failure |
| R3b | F3 / TI6 heal (extra) | `intake_commit.py:99` `for stray in [...]:` -> `for stray in []:` (sweep never removes the orphan file) | NEW test 1 passed | 1 failed: `assert IntakeStatus.PARTIAL is IntakeStatus.OK` (second intake hits `FileExistsError` on the orphan): the test still kills between copy and row and still needs the heal |

Mutants beyond the floor: 3 (R1b, R2b, R3b), within the S/M/L cap of .9-4.
Affected tests (fix diff plus the merge diff; the merge brought in no src/tests change, only qa files): `test_zip_intake_{names,limits,register,atomic}.py test_ui_intake.py test_ui_intake_drive.py test_cli_intake.py test_drive_intake.py` -> 167 passed (10 s). `ruff check` on the 5 changed files: All checks passed.
