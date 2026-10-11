# Checkpoint - t167-release-regression - repair coordinator B (cycle 1)
Attribution: coordinator B, verdict qa/verdicts/t167-release-regression.r1.b.md · sha 102a4b91 · env win32, uv-synced copy
Code hashes (blob at 102a4b91): orchestrate_gate.py 1021b5d9748e · release.py 932dcb614e4e · orchestrate.py 8040c7423661 · tests/test_release_gate.py 82d90ac15a68
Config/lock: uv.lock 4882ef560a75 · tests/conftest.py e5ff4b8402fd (session fixture sets the signing key)
- RR2 reproduction + attack matrix A0-A9: `pytest tests/test_zz_attack_b.py -p no:xdist -o addopts=` (38 tests, throwaway copy only, file not in the repo) -> 38 passed after fixing 2 of my own warns-assertion errors · PASS
- Affected tests: 9 files named in the verdict, 102 collected -> 102 passed · PASS
- `ruff check src` -> clean · PASS
- Falsification F1 (mine): orchestrate_gate.py:50 wall re-cost removed -> A6 forged-wall test red by assertion, restored · PASS
- Falsification F2 (builder row): orchestrate_gate.py:45 `actions = scope.max_actions` -> test_rr2_an_under_declared... DID NOT RAISE · PASS
- RR3/RR4/RR5: no repair-diff file feeds them; recorded results kept. No full suite run (the other coordinator owns it).
