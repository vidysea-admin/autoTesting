# f2 purge_project attack (sub-checker, read-only toward the worktree)

Subject: `.worktrees/t200b-scheduled-test/src/autotester/stages/schedule_store.py` (purge_project, project_records_path, append_record, read_records, claim, list_claims).
Method: throwaway copies `scratchpad/f2-copy` (attacks 1-6) and `f2-copy2` (attack 7); `PYTHONPATH=<copy>/src`, python = worktree .venv, Windows 11, Python 3.11.15.
`autotester.__file__` printed before every run: `...\scratchpad\f2-copy\src\autotester\__init__.py` (and `f2-copy2\src\...` for attack 7).
Scripts (re-runnable): `f2-scripts/` (atk2 concurrency, atk3 shared layout, atk4(+child) crash points, atk5/5b/holder Windows handles, atk6 prefix).
Reproduce: `PYTHONPATH=<copy>/src <venv>/python f2-scripts/atkN.py <tmp dir>` (copy needs `scripts/` for tests/conftest).

| # | Attack | Result |
|---|---|---|
| 1 | tests/test_schedule_marker.py in copy | PASS, 10 passed |
| 2 | 3 spawn neighbours x300 (claim+append) vs 200 victim purges, shared claim_dir; 3 variants (records in sibling dir; records dir == stage parent; second run) | PASS: purges 200/200/239, purge errors 0, neighbour exceptions 0, acked 900/900 present in each variant, lost_records 0, lost_claims 0, duplicate lines 0, `.purge-*` left 0, victim fully gone |
| 3 | records file with 2 projects (old layout) | PASS for valid foreign rows: foreign row in middle + live neighbour appending: 28300 purge attempts all ValueError, file kept the old bytes as prefix, neighbour 150/150 acked present, claims unchanged, no stage. Foreign row LAST: ValueError, tree byte-identical. |
| 3b | foreign row that is torn / invalid | FINDING (low): torn JSON fragment of a foreign row (last line or middle) and a foreign row with an unknown field (newer schema, extra=forbid) are skipped by `read_records`, so the guard does not fire; purge returns normally and deletes the file with that foreign data (3c, 3d, 3e all "NO RAISE, file deleted"). Reachable only if purge is pointed at an old shared-layout file. |
| 4 | crash points (3 moves: 2 markers + records) | see below |
| 5i | foreign process holds default `open('rb')` / `os.open` RDONLY / O_APPEND handle on victim records | PASS: PermissionError WinError 32 (is an OSError); both already-moved markers rolled back, tree identical to before, no stage dir; retry after release succeeds |
| 5ii | reader process loops read_records(victim) while 80 purges | PASS for purge: 60 ok, 20 PermissionError, 0 inconsistent states, 0 stage leaks. Side note: the reader itself got PermissionError x178 and FileNotFoundError x17 (read_records is not race-safe against a purge: is_file then read_text) - a reader of a project being purged must tolerate that |
| 5iii | handle on 1st / 2nd claim marker | PASS: PermissionError, state restored (2nd case rolled back marker 1), no stage, retry ok |
| 5iv | rollback itself fails (monkeypatched os.replace) | PASS as designed, but see crash table: stage kept holding the files; the exception that escapes is a PermissionError (OSError); rollback loop stops at the FIRST failing restore, so later moved files stay in the stage too |
| 5v | names 'a b','a:b','Ab' vs 'ab' | 'Ab' and 'ab' map to different names ('Ab.jsonl','ab.jsonl') that are the SAME file on NTFS (writing 'Ab' made `ab` exist). Cannot occur in practice: `Project.slug` pattern `^[a-z][a-z0-9-]*$` (schema/project.py:133) and ui/helpers `_SLUG_RE`; quote() makes 'a b'/'a:b' safe file names anyway. No guard inside purge_project/project_records_path itself. |
| 5vi | handle WITH FILE_SHARE_DELETE (ctypes) on records / a marker | PASS: move succeeds, purge returns, no stage leak |
| 6 | prefix: 'a' vs 'ab','a-b','a1' | PASS: only a's markers removed. 'a:x' would be purged by purge('a') (startswith "a:"), but ':' is rejected by the slug pattern, so cannot occur; purge_project does not itself validate the name |
| 7 | falsification in f2-copy2 | PASS (tests bite): `if False and any(...)` -> shared-file test FAILED (1 failed, 1 passed); rollback `os.replace(held, src)` -> `pass` -> fail-part-way test FAILED; baseline 2 passed; copy restored identical |

## Attack 4 detail (each in a child process; "re-run" = purge_project again)

| Crash point | State left | Re-run converges? | Stage leak |
|---|---|---|---|
| os._exit before 1st move | nothing moved, all 3 files in place | yes, fully purged | empty `.purge-*` dir |
| os._exit before 2nd move | marker0 in stage, marker1 + records in place = HALF PURGED | yes (purges rest) | stage with marker0 stays |
| os._exit before LAST move | both markers in stage, records in place = HALF PURGED | yes | stage with 2 files stays |
| os._exit just before rmtree | everything in stage (fully purged from the live view) | n/a (nothing to do) | stage with all 3 files (deleted project data persists) |
| KeyboardInterrupt / SystemExit at 2nd move (not a hard crash) | NOT rolled back (`except OSError` only): marker0 in stage, rest in place = HALF PURGED | yes | stage leaks |
| 3rd move fails, crash at 1st rollback move | 2 markers in stage, records in place = HALF PURGED | yes (finishes purge, not a rollback) | stage with 2 files |
| 3rd move fails, crash at 2nd rollback move | 1 marker in stage, rest restored = HALF PURGED | yes | stage with 1 file |
| 3rd move fails, rollback complete, crash before rmtree | all 3 restored (clean) | yes | empty stage dir |
| rollback move raises OSError (1st or 2nd) | files stay in stage, others not attempted = HALF PURGED; escaping PermissionError | yes | stage kept (as designed) |

Plain statement: "together or not at all" holds for an exception that is an OSError during a move (rolled back). It does NOT cover: any hard crash/kill between moves (before 2nd, before last), KeyboardInterrupt/SystemExit/other non-OSError at a move, and a failing rollback. In every such case the half-purged state is forward-recoverable: re-running purge_project converges to fully purged (no marker or record of the project remains). Never converges: the `.purge-<uuid>` stage directory (nothing in src references or sweeps `.purge-`), so the deleted project's moved files persist there. purge_project is also not yet called from anywhere in src (tests only).
