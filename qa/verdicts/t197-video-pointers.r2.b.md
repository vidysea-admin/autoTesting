# Verdict - t197-video-pointers - coordinator B (repair, blind dual check)

Cycle checked: 2
Date: 2026-10-11
Bound to: D:/autoTesting. Branch `wave/t197-video-pointers`, head b59dda0d (product 28035c82), `Repair base: 0dcbbfa5` (verified ancestor with git).
Policy-Version: proportional-verification/2026-10-10.9
Checkpoint: qa/checkpoints/t197-video-pointers.r2.b.md
Evidence: qa/evidence/t197-video-pointers-r2-B/ (exit-path-table.md/.json, falsification.json, extra.json, extra-partial.json, harness/)
Resume: 1 (interrupted once by the coordinator, resumed on the same C: copy; nothing re-run that was complete)

## Plan (check planner)
Tier L (dual-trigger security `src/autotester/cli_video_review.py:75`, the per-use approval gate). Repair scope: failed list F1, F2a-d, F3, plus the repair diff 0dcbbfa5..b59dda0d read in full, whole-unit scope scan, one falsification per repaired item. My emphasis: behaviour of the REAL CLI as a subprocess. No suite run, no suite lock. Copy: `git archive b59dda0d` on C: (session scratchpad `r2b-copy`, own venv); `autotester.__file__` printed from inside the copy; pytest rootdir = the copy. Nothing created on D: except evidence files.

## Verdict
VERDICT: PASS
SCOREBOARD: 3/3 repaired criteria met (F1, F2 a-d, F3); 0 invariants touched
TIER: L (security/approval gate `src/autotester/cli_video_review.py:75`; dual-trigger cited in the manifest and confirmed by me at that line)
FAILURES: none
CAPABILITY-COVERAGE: 7/7 falsification rows reproduced green -> red (F2a, F2b, F2c, F2d x2, F3 x2)
LIVE-BROWSER: not-applicable (no UI surface in the changed paths)
ISSUES-WRITTEN: none (dual coordinator: PROPOSED-ISSUE lines only)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)

## Per failed item
- F1 ruff: `ruff check src tests scripts` -> All checks passed (in my copy); `autotester doctor` -> clean; `cli_video_review.py` = 300 lines exactly, doctor (function <= 50) clean. MET.
- F2a click usage errors: every form exits **1**, never 2, with exactly ONE document `{"status":"usage_error","reason","exit_code":1}` in json mode: `--max-cost abc`, `""`, `0x10`, `--bogus`, `--output` without a value, missing source argument, no arguments, extra positional, `--max-cost --output json` (option eats the flag), each as `--output json` and `--output=json`, option before and after the positional. Text mode: exit 1, stdout empty, message on stderr. MET.
- F2b unexpected exception: provider RuntimeError and OSError -> exit 1, one `internal_error` document, no traceback, nothing under `reviews/` but the empty directory. The reason is `unexpected RuntimeError during the review: [REDACTED]:DEMO_PASSWORD at <recording> and <recording> in <project root>`: no canary secret, no recording path, no file name in stdout or stderr. MET.
- F2c Ctrl-C: a REAL CTRL_C_EVENT sent with AttachConsole/GenerateConsoleCtrlEvent to the live process (mid-judge, `--redact` window active, scratch dir present with redacted.mp4 and 8 stills) -> exit 130, one document `{"status":"interrupted","exit_code":130}`, `reviews/` empty afterwards (repeated twice in json mode, once in text mode: exit 130). MET.
- F2d exit_code on every document: ok 0, dry-run 0, partial (multi-batch, cap 1e-9, 1 of 2 calls) 0, failed (cap 0) 1, pointer_errors 2, refused 3, unreadable 4, usage_error 1, internal_error 1, interrupted 130: in all 40+ json rows the document's `exit_code` equals the real process exit code (0 mismatches). MET.
- F3 32768/32769: the new test pins both sides and goes red under both off-by-one mutants. MET. At the real CLI a 33008-byte file is refused unread: exit 2, one `pointer_errors` document, provider calls 0.

## Behaviour checks beyond the list
- Stored review files carry no `exit_code`; a review stored by the repair-base code (0dcbbfa5, archived and run) is re-served by head with exit 0, same id, `exit_code: 0` added in the envelope only, zero provider calls (`extra.json`).
- Redaction: with `--redact 1:00-1:10` the provider got 8 stills from `reviews/<id>/frames/` (cut from the redacted copy), at 0, 15, 30, 45, 75, 90, 105, 120 s: none in 60-70 s; the live redacted copy sampled at t=65 s has YAVG 16 (black) while the stills outside are ~122 (bright).
- Non-finite cap: `--max-cost nan`, `inf`, `-1` -> exit 1, one usage_error document, provider calls 0.
- Refusal without approval: exit 3, calls 0. Unreadable source: exit 4, calls 0. Unknown source / project, provider unavailable, missing pointer file, bad `--redact`: exit 1 + one document.

## Rulings on the builder's declared exception
- A bare `--output`, or an `--output` value other than text/json (`xml`, `JSON`): stays text, exit 1, stdout empty, message on stderr. ACCEPTED: the caller did not name json, a document on a human terminal would be a guess, and the exit code is no longer the pointer-errors 2. (When `--output json` appears anywhere in argv, a later bare `--output` still produces the document.)
- Usage errors exiting 1 in text mode too: ACCEPTED. The contract's own table gives 2 to pointer errors (TV1) and names 1 for usage; sharing 2 with click was the defect. It does differ from other commands (see P3).

## Scope, diff and falsification
- Repair diff read in full (6 files): matches the manifest. Whole-unit diff vs master base 09828f2d: 30 files, every one named in the manifest; deletions are 5 lines, all declared (cli_crawl help/branch, enums docstring, advice-site count 21 -> 22). No function, class or test removed.
- Falsifications (copies on C:, anchor unique, green then red, `autotester.__file__` inside each copy): F2a 13 passed -> 8 failed; F2b 2 -> 2 failed; F2c 1 -> 1 failed; F2d review doc 5 -> 4 failed; F2d plan doc 4 -> 1 failed; F3 `>=` 1 -> 1 failed; F3 `+1` 1 -> 1 failed (`falsification.json`).
- Affected tests in the copy (exits, pointers, cli_video_review, advice_resolves, cli_surface, cleanup): 188 collected, 180 passed, 8 failed; the 8 are the `git check-ignore` tests failing only because `git archive` has no `.git`; re-run in the copy after `git init`: 19 passed. Not a defect.

## PROPOSED-ISSUE (all low, none blocks)
PROPOSED-ISSUE: {"severity":"low","feature":"team-video-review","title":"CTRL_BREAK / hard kill: exit 3221225786, no JSON, work dir kept","evidence":"real CTRL_BREAK to the process: exit 0xC000013A, stdout empty, reviews/rv_*/ keeps redacted.mp4 and 8 stills (redacted derivative only); next run of the same id cleans it. Disclosed by the builder (manifest item 11)."}
PROPOSED-ISSUE: {"severity":"low","feature":"team-video-review","title":"internal_error reason masks the recording and secrets but not other absolute paths","evidence":"cli_video_review.py _failure_reason: a provider message containing the project root path prints it unmasked in stdout and stderr (observed in x-ie-runtime). Not a secret; recording path and file name are masked."}
PROPOSED-ISSUE: {"severity":"low","feature":"team-video-review","title":"usage errors now exit 1 here while every other ingest/crawl command keeps click's exit 2","evidence":"ReviewCommand.parse_args; chosen deliberately because 2 = pointer errors. Consider documenting in the CLI contract."}
PROPOSED-ISSUE: {"severity":"low","feature":"team-video-review","title":"CLI-side stat boundary (cli_video_review.py:171) is not pinned at 32768/32769","evidence":"mutating `size > MAX_POINTER_FILE_BYTES` there to `+1` is behaviour-equivalent (parse_pointers repeats the check after the read), so only the parser boundary has a test. Informational."}
PROPOSED-ISSUE: {"severity":"low","feature":"team-video-review","title":"`--help` with `--output json` prints help text on stdout, exit 0","evidence":"u-help-json row; help is not a failure exit, listed for completeness."}

## EXPLANATION
Every way `ingest review` can end, driven through the real CLI as a subprocess with a wrapped mock provider, produced exactly one document in json mode (except the declared text-by-design cases and an OS-level CTRL_BREAK kill), with `exit_code` equal to the real exit code in every json run that produced a document (67 runs recorded, 0 mismatches). The repair is in place, not stacked: one command class, one `_fail` writer. L budget note: wall time passed the 45 min L target because of the coordinator interruption and the 3-5 min per-process cost of the cleanup tests; no mandatory check was left unrun.

Metrics: start=2026-10-11T18:43Z end=2026-10-11T20:20Z wall_min=97 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=2 mutations=7 cycle=2 resumes=1 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=5820 mutants=7 defects_unit=0 defects_6c=0
slow: affected tests + cleanup tests 8 min, behaviour table shards 25 min (one interruption of unknown length is inside wall_min)
