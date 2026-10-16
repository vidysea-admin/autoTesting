# Manifest - ledger-tick-integrity

**Status:** ready-for-check
**Fix cycle:** 0
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
