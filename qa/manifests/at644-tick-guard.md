# at644-tick-guard

Status: ready-for-check
Fix cycle: 0
Issue: AT-644 (high) -- qa/.last-tick has no guard against a truncating write
Authority: D-087 item 2 (docs/DECISIONS.md), Approved-by: Umesh (chat, 2026-10-12)

## Built
- `src/autotester/tick_guard.py`: `append_tick` (temp file in same dir, fsync, `os.replace`; refuses a damaged log, a non-stamped line, or any shrink), `problems`/`text_problems` (empty, no trailing newline = partial write, first line not an ISO stamp).
- `autotester loop-status` prints `TICK LOG DAMAGED: ...` and `--strict` exits 1 on a damaged log (so the session-start hook flags it; hook file untouched).
- `autotester tick-append "<stamped line>"`: the safe write path.
- Format unchanged; the tracked qa/.last-tick validates clean.

## Tests (`tests/test_tick_guard.py`, run per file, `-p no:xdist -o addopts=`)
truncated/partial/empty detected; valid and multi-line tick passes; append keeps history; simulated `os.replace` failure leaves original and no temp file; loop-status --strict flags damage; tick-append CLI. Also test_loop_status, test_loop_status_integrity, test_mc_sessionstart_loop_status pass. ruff clean; `autotester doctor` clean (docs/MAP.md regenerated).
