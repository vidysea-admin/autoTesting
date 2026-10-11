# Seat A r1 evidence (3918a8aa), measured in git-archive copies under the scratchpad (deleted after)

Interpreter for everything: D:/autoTesting/.venv/Scripts/python.exe (root venv, Python 3.11.15). cwd = the copy (never the scratchpad root, which holds a stray copy.py that shadows stdlib `copy`).

## F3
- `python -m pytest -p no:xdist -o addopts= -p no:cacheprovider tests/test_zip_intake_atomic.py -v` in the copy -> 5 passed in 2.86s (ti6 kill test PASSED).
- Child import resolution: with PYTHONPATH=<copy>/src -> autotester.__file__ = <copy>/src/autotester/__init__.py, zip_intake.__file__ = <copy>/src/autotester/sources/zip_intake.py.
  Without PYTHONPATH -> autotester.__file__ = D:\autoTesting\src\autotester\__init__.py and `import autotester.sources.zip_intake` -> ModuleNotFoundError (the cycle-0 failure).
- Falsification (copy r1a-fals-f3): drop `env=env` from the kill test's subprocess.run -> green before (1 passed), red after (1 failed, returncode 1 != 9, ModuleNotFoundError autotester.sources.zip_intake).

## F1
- Stdlib: zipfile.py:1442 `if x.extract_version > MAX_EXTRACT_VERSION (=63): raise NotImplementedError` sits inside ZipFile._RealGetContents, in the loop over every central-directory record.
- scripts/ver_f1.py: version byte on member 0, 1 or 2 of 3, versions 6.3 / 6.4 / 9.9 / 25.5. 6.3 -> status ok, 3 rows. >=6.4 (all 9 combos) -> stdlib raises in ZipFile(); intake returns status failed, exit 2, one '(archive)' failed row "unsupported zip version ...", 0 rows, no crash.
- scripts/fuzz_f1.py: 3-member zip (STORED, LZMA, BZIP2, DEFLATE), flip 0xFF at 40 data positions + all 30+n local-header bytes + all central-record bytes of the middle member: 507 runs, 0 crashes. Data region: every one 'partial' (a.mp4 registered in all), 0 leftover staging. fuzz_f1.json has each record.
  Central-record flips: 24 ok, 20 partial, 7 failed per method; the 7 failed are archive-level (extract_version byte at cs+6, extra-length bytes at cs+30/31 etc.: central directory unreadable).
- scripts/fuzz_f1_edges.py: first 48 and last 48 data bytes of the middle member, every method: 384 runs, 0 crashes, all data flips 'partial' (LZMA 8 'ok': flip landed in bytes that do not change the output).
- Affected tests, one process: tests/test_zip_intake_names.py test_zip_intake_limits.py test_zip_intake_register.py test_zip_intake_atomic.py test_cli_intake.py test_ui_intake.py test_ui_intake_drive.py test_drive_intake.py -> 167 passed in 10.37s.
- Falsification (copy r1a-fals-f1): remove `lzma.LZMAError` from the member handler and the `NotImplementedError` catch around `zipfile.ZipFile(...)`; `-k ti5` on test_zip_intake_register.py: 13 passed before, 4 failed / 9 passed after (3 LZMA positions + the version case).

## F2 (scripts/f2_measure.py, scripts/f2_headers.py; real app, ASGI level; tracemalloc peak)
case | status | body bytes pulled KiB | peak KiB | sources | leftover staging files
A 1,000 tiny named fields before file | 400 | 70 | 913 | 0 | 0
A 10,000 | 400 | 141 | 1109 | 0 | 0
A 100,000 | 400 | 141 | 567 | 0 | 0
B 2 x 15 KiB before file | 303 | 34 | 881 | 1 | 0
B 5 x 15 KiB | 400 | 75 | 241 | 0 | 0
B 3 x 16 KiB | 400 | 48 | 199 | 0 | 0
B 1 x 16 KiB+1 | 400 | 16 | 166 | 0 | 0
C 2x7 KiB before + 2x7 KiB after the file part (28 KiB) | 303 | 32 | 122 | 1 | 0
C 4x7 KiB before + 4x7 KiB after (>32 KiB) | 400 | 60 | 179 | 0 | 0
C 1 before + 3,000 tiny after the file | 400 | 216 | 634 | 0 | 0
C 0 before + 20 fields after | 400 | 5 | 117 | 0 | 0
D 1,000 nameless fields | 303 | 61 | 257 | 1 | 0
D 100,000 nameless fields | 303 | 5765 | 601 | 1 | 0
D one nameless 20 KiB field | 400 | 19 | 172 | 0 | 0
D 100,000 empty-name fields | 303 | 6644 | 671 | 1 | 0
F 100,000 same-name 'label' fields | 400 | 427 | 710 | 0 | 0
E 10k / 100k / 400k distinct headers in one part | 400 | 52 | 1224 / 501 / 500 | 0 | 0
E 400k identical-name headers | 400 | 39 | 472 | 0 | 0
G legit label + 1 MiB file | 303 | 1024 | 103 | 1 | 0
G legit label + 300 MiB file (limit 512 MiB) | 303 | 307200 | 103 | 1 | 0
- Zero file bytes before the file part: in every A/B/D/E refusal the recording folder and staging are empty (rec_files 0, leftover 0); the C cases that refuse after the file part also leave nothing registered and no staging.
- Falsification (copy r1a-fals-f2): MAX_FIELDS -> 10**9 and FIELDS_TOTAL_CAP -> 10**12; `-k f2` in tests/test_ui_intake.py: 3 passed before, 3 failed after. Same copy, case A 100,000 tiny fields: status 303, peak 11469 KiB (1487 KiB at 10,000) vs 567 KiB with the caps.
