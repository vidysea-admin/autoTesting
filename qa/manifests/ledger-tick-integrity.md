# Manifest - ledger-tick-integrity

**Status:** ready-for-check
**Fix cycle:** 1
**Cycle 0 base-of-fix SHA:** ce4e124a5ffefef83f881d07aa538860b5b515b8 (verdict commit 1e1cbef6 FAIL)

## Fix cycle 1 changes
- `cli.py` back to 300 lines: loop commands attach via `cli_loop.attach_loop_commands(app)`.
- `docs/MAP.md` regenerated with `autotester map` (run with PYTHONPATH pinned to this worktree's src; the venv editable install points at another worktree).
- `core/atomic_tick.py`: `file_lock` sidecar (`.last-tick.lock`), unique temp name (pid + thread id + uuid), `os.replace` retried with backoff on PermissionError and raised if all retries fail.
- `.gitignore`: `qa/*.lock`.
- Tests added: threaded 8-writer all-lines-land, retry-then-succeed, raise-after-exhausted retries.
- Doctor: base exit 0 (checker-measured), candidate exit 0 (doctor: clean). Tests 30 passed.
**Issues addressed:** AT-644, AT-645, AT-676
**Base SHA:** c4d48ad109f1ef77f73ee9172866cc5feeca7063
**Candidate SHA:** this commit (HEAD of branch worktree-agent-a1fe02b3d106c13e7)

## Changed paths
- `src/autotester/core/atomic_tick.py` (new): `append_tick` reads old content, writes old+new to a temp file, fsyncs, `os.replace`s; refuses empty lines and any result with fewer lines.
- `src/autotester/cli_loop.py`, `src/autotester/cli.py`: `autotester loop-tick [note]` stamps `qa/.last-tick` through `append_tick`.
- `src/autotester/ledger/issue_ids.py`: `duplicate_lines` + doctor violation now names the id and line numbers; `append_issue` now runs under `file_lock`; new `append_new_issue` allocates the next free id and appends in one locked step; appends never glue onto an unterminated last row.
- `tests/test_ledger_tick_integrity.py` (new).

## Findings at base
- The id guard (doctor rule `issue-id-duplicate`, grandfather list, renumber script) already existed at base. `qa/issues.jsonl` at base has 0 duplicate ids (1025 lines), so the 10 historical duplicates were already renumbered. `qa/issues-dupes-grandfathered.json` still lists 10 now-stale pairs; left untouched (no history rewrite). The list can only shrink; deleting it is a follow-up the checker may verify.
- Nothing in shipped code wrote `.last-tick`; the writer is the maker shell/hooks. `qa/hooks/*` and `.claude/hooks/*` are enforcement paths and were NOT edited. Those writers must call `autotester loop-tick` (or `append_tick`) instead of `>`; that change needs an Approved-by: Umesh decision.
- `merge=union` kept deliberately (AT-676).

## Consumers
`autotester doctor` (check_issue_id_unique), `loop_status.read_ticks`, project_store/routes_issues do not use `issue_ids` writers.

## Required checks
- `pytest tests/test_ledger_tick_integrity.py tests/test_issue_ids.py tests/test_loop_status.py` : 27 passed
- `ruff check` on changed paths : clean
- `autotester doctor` : 0 file-size/issue-id violations; 3301 pre-existing decision-citation-* violations unrelated to this unit.
