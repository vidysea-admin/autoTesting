# t167-release-regression r2 A checkpoint (coordinator A)
Agent: claude-sonnet-subagent; verdict: qa/verdicts/t167-release-regression.r2.a.md; head 1b6f07e7 (product 7e09124a); repair base 102a4b91.
Lock hash: uv.lock tracked, unchanged in repair diff. Environment: Windows 11, CPython 3.11.15, copy via git archive, PYTHONPATH pinned to copy src.

| check | command / scope | code hashes | result |
|---|---|---|---|
| repair diff | git diff --stat 102a4b91 1b6f07e7 (src+docs empty) | src tree = 102a4b91 | test-only: PASS |
| touched tests | pytest tests/test_cli_advice_resolves.py tests/test_release_gate.py (34 collected) | test_cli_advice_resolves.py, test_release_gate.py @1b6f07e7 | 34 passed |
| CLI resolves | autotester release --help; release-log --help | cli_release.py @1b6f07e7 | exit 0, args/options match advice |
| falsify registry | mut1 remove release-log site; mut2 add unregistered site | cli_release.py | red on gone/new, green before |
| falsify wall clock | mut3 drop max() in orchestrate_gate.py:46-49 | orchestrate_gate.py blob 1021b5d9 | DID NOT RAISE, green before |
| lint/doctor | ruff check src tests scripts; autotester doctor | tree 1b6f07e7 | clean |
Reuse: RR criteria results from qa/checkpoints/t167-release-regression.r1.a.md remain valid (no src change). full-suite trigger: none new.
