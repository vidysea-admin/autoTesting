# Checkpoint - t179a-lead-tester-core (coordinator A, cycle 2)

Head 86d240a9 (code cc7f29ed), base 16aaa402, repair base c489e201. Policy proportional-verification/2026-10-10.9. Tier L.
Environment: git-archive copy on C: (chk_t179a_r2a_*), worktree venv python, PYTHONPATH = copy src;scripts;tests (autotester.__file__ printed from the copy).

| Check | Command + scope | Code hashes (blob7) | Result |
|---|---|---|---|
| C1 + AL6 + AL2 + AL3 affected | pytest tests/test_agent_{destination_seam,read_only,credential_gate,tools}.py -o addopts= | guards.py:3d59e067 tools.py:d16464c7 | 392 passed |
| affected, wider | + tests/test_explore_safety.py test_execute.py test_schema.py test_doctor.py | same | 532 passed |
| lint | ruff check src tests scripts (copy); autotester doctor (worktree) | same | clean; "doctor: clean" |
| C1 differential probe | 44 hostile NAVIGATE targets x TEST_ACCOUNT/ALLOW_WRITES, real BrowserSession.goto as oracle | guards.py:3d59e067 | guard refuses iff seam refuses; 3 malformed-bracket targets raise ValueError out of the guard (seam errors too) |
| AL6 variant probe | 19 separator forms x 4 places (error, evidence.label, stage error, summary) | tools.py:d16464c7 | real separators, \uXXXX, %09, &#9; withheld; literal backslash-t/n/x09/u{9} NOT withheld (P1) |
| size-cap probe | 238 real stored case_*.json RawResults of projects/*/runs | tools.py:d16464c7 | 4 of 238 withheld by the 256-node / 16 KiB cap (P2) |
| falsify C1 | m1: _seam_refuses drops placeholder exemption; m3: above READ_ONLY use _destination | guards.py | m1 12 failed 2 passed; m3 28 failed 155 passed (unmutated copy 183 passed) |
| falsify AL6 | m2: _carries_credential gates json.dumps(data) | tools.py | 20 failed 20 passed (unmutated 40 passed) |
| full suite (L security, 1 per coordinator) | shard_suite --shards 4 --ref 86d240a9 | n/a | NOT RUN: suite lock held by pid 2844 (t204-team-login) for 48+ min; two 901 s waits, exit 3 |

Remaining: the one full suite (shard_suite, ref 86d240a9) once the lock is free. Everything above is complete and keeps its identity while guards.py, tools.py and the four test files are unchanged.
