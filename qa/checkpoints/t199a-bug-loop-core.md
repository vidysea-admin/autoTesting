# Checkpoint - t199a-bug-loop-core, checker coordinator, cycle 0
Verdict: qa/verdicts/t199a-bug-loop-core.md (PASS, built subset only). Head 325d9903f1af0f9752a272303d8f7282c429b5e5, code 1976502d, merge base 6504de03. Attribution: checker coordinator (claude-sonnet-subagent), evidence under qa/evidence/t199a-bug-loop-core/.

Environment: Windows 11, Python 3.11.15, pytest 9.1.1, uv env inside a `git archive 325d9903` copy on C: (scratchpad/ck199a); `autotester.__file__` = that copy's `src\autotester\__init__.py`; pytest rootdir = that copy. 20 GB free on D:. No checkout, worktree or venv on D:.

| Check | Command and scope | Code hashes (tree 325d9903) | Result |
|---|---|---|---|
| Affected tests | `uv --directory <copy> run pytest -p no:xdist -p no:cacheprovider -o addopts=` over test_bug_loop, test_bug_store, test_bug_store_concurrency | head tree | 123 passed, 51 s (pytest-affected.txt) |
| Lint, design | `ruff check src tests scripts`; `autotester doctor` | head tree | clean (lint-doctor.txt) |
| Fold attack | probes/probe_fold.py, probe_future.py, probe_gaps.py: 45-cell oracle, 5040 permutations, 800 shuffles, ties, duplicates, future, gaps | bug_loop.py, tracked_bug.py | BAD 0; future and gap findings P1, P2, P6, P8 (fold/*.out) |
| Storage attack | storage/s1..s7: 16 threads, 6-8 processes, same-id and different-at races, reader vs writer, hostile and corrupt files, path escape, missing dir, timing | bug_store.py, filestore.py | no loss, tear, exception or escape; P3, P4, P8 (storage/*.out) |
| Falsifications | falsify/transcript2.txt: 8 single-hunk mutants and the 3-hunk marker-equivalent in isolated copies (plus own m_TB6 run) | stages/bug_loop.py, store/bug_store.py, schema/tracked_bug.py, stages/issues.py | all red on the named assertion, none survived |

Reuse note: nothing reused from earlier checks. Full suite and suite lock not used (brief forbade). The falsification copies also held scripts/ and qa/contracts/ because tests/conftest.py imports scripts/regression_proof.py.
