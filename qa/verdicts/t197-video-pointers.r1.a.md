# Verdict — t197-video-pointers, coordinator A (blind dual check), repair check
Cycle checked: 1
Verdict path: qa/verdicts/t197-video-pointers.r1.a.md
Policy-Version: proportional-verification/2026-10-10.9
Bound to: D:/autoTesting; tree under test D:/autoTesting/.worktrees/t197-video-pointers, head 0dcbbfa5 (product c726cfda, tests-only 802c72c9, manifest 0dcbbfa5). Repair base 3d0be650 verified as an ancestor of HEAD; whole-unit base 09828f2d (= merge-base with master).
Date: 2026-10-11. Evidence: qa/evidence/t197-video-pointers-r1-A/ (scripts in scripts/).

## Check plan
Tier L, dual check (manifest `dual-trigger: security cli_video_review.py:73`; lint exit 0; line 73 is inside `build_gate.gate`, the CLI half of the approval gate). Repair scope: the four cycle-0 failures, mapped by me to TV10 storage / TV7.3 (F1), TV7.4 bounded spend (P2), CLI contract "valid JSON document on stdout" (J1), TV1 pointer input bounds (P5). Re-run those plus every criterion the repair diff's files feed (TV7.3 redaction ordering via `media/redacted.py`, TV8 via `stages/video_review.py`). Angles: cleanup class attack, ignore-rule scope, cap values, JSON exits, pointer boundaries, redaction ordering, owner decisions 4-9, new-module rule D-082 item 1.
Command discipline: every pytest, ruff and doctor run was started from inside the tree (`cd <tree>` first, or `uv --directory <tree> run`). Proof: `autotester.__file__` = `D:\autoTesting\.worktrees\t197-video-pointers\src\autotester\__init__.py`; the collected counts (118 and 135) equal the manifest's, and master `D:/autoTesting/tests` holds none of the 8 `*video_review*` test files, so the collected files are the tree's. Ruff and doctor were redone with `uv --directory` after the correction arrived (same results). No run used `--project` from another directory.

## Result
VERDICT: FAIL
SCOREBOARD: the five repaired criteria are met on behaviour; 1 required adapter gate is red at head (ruff). Whole-unit TV1-TV10: the built subset is met; TV7.1, TV9 flows, TV10 routes, `ingest run --pointers` and live acceptance are not built (HELD, see rulings), so no goal task can close.
TIER: L (data egress to an external model, TV7 CRITICAL; cited `cli_video_review.py:73`; unchanged by me)

FAILURES:
- [adapter verify gate: `uv run ruff check src tests scripts`, expect exit 0] sev: low · `uv --directory <tree> run ruff check src tests scripts` exits 1 at head: `E501 Line too long (103 > 100) tests/test_video_pointers.py:199` (I read the line; `git blame` puts it in the tests-only commit 802c72c9). The manifest's pre-check line for 802c72c9 says "ruff All checks passed!", which I cannot reproduce. · fix direction: wrap that one line (comment onto its own line), re-run ruff. Evidence: evidence/ruff-directory.txt. issue: P1

Everything below was met; the FAIL is the lint gate only.

## Per-criterion
| Repaired criterion | Result | Evidence |
|---|---|---|
| TV10 / F1 storage: nothing derived from the recording outlives the review, nothing committable | MET | set1 118 passed (incl. 19 cleanup tests, real ffmpeg). My attack: success, ProviderError, RuntimeError, KeyboardInterrupt, SystemExit from the provider, no-window run: reviews dir holds only `<id>.json` after each (cleanup-attack-2). `git check-ignore -v` hits `.gitignore:81 projects/*/reviews/` for the work dir, frames and the stored review; `git ls-files 'projects/*/reviews/*'` = 0 on the branch and on master. Falsified: `review_scratch` finally -> no-op: 4 failed; `.gitignore` line removed: 8 failed. |
| TV7.4 cap: non-finite refused, stop fires before the call | MET | CLI: nan, NaN, inf, -inf, 1e999, -1 -> exit 1, usage_error document, zero calls; -0.0 accepted as cap 0 (stops before the first call). Stage: nan/inf/-inf -> `ReviewRefused` before the gate; loop uses `not cost < cap` so a NaN cap stops. Falsified 3 rows: CLI isfinite removed 3 failed; stage 3 failed; loop `>=` 1 failed. A single call can still overshoot the cap by its own cost (unchanged, the cap is checked after each call; the contract says "stops analysis when reached"). |
| CLI contract: one JSON document on every exit | MET for every exit the command itself takes; two gaps below as PROPOSED-ISSUE | set2 135 passed (14 exit-path cases, one document each, `exit_code` matches, no tmp path or planted secret). Falsified `_fail` not writing the document: 10 failed. |
| TV1 pointer limits | MET; numbers are an owner decision | Boundaries (pointer-limits.txt): 100 lines ok, 101 -> error on line 101 (CRLF too); note 500 ok / 501 error (ASCII and 3-byte chars; free pointer likewise); exactly 32768 bytes ok, 32769 error, BOM counts its 3 bytes, a 40 KB single line is one error, multi-byte file by bytes; count identity holds in all. Falsified lines 2 failed, note 1 failed, file 1 failed. No documented input is refused (the contract table lines, BOM, CRLF all parse). One consequence to know: 100 lines x 500 chars cannot coexist under the 32 KiB cap. |
| TV7.3 redaction before the call (touched by the repair) | MET | Provider receives only stills cut from the copy that passed `verify_blackout`; mutation `self.origin = video` after the check: 1 failed. Mutation removing the `verify_blackout` call from the constructor: 2 failed (my first selection ran only the redaction file and missed it; the rerun with the cleanup file caught it, falsify-tv7-noverify-rerun.txt). The "redaction after the call" mutation has no single-hunk form (lazy frame source), as the builder said; equivalent covered by the origin row. |
| TV8 scrubbed quote (touched) | MET | set1 includes `test_a_model_that_quotes_the_scrubbed_narration...`; builder's falsification not repeated (unchanged input). |

Affected tests: set1 `test_video_pointers, test_video_review, _gates, _redaction, _guards, _cleanup` 118 passed in 1021 s; set2 `test_cli_video_review, _exits, test_cli_advice_resolves, test_approve_cli, test_cli_surface` 135 passed in 253 s. The third manifest set (ingest/consent/signing, 103) is not reachable from the repair diff (none of its files changed) and was not re-run. `autotester doctor`: clean. Ruff: RED (above).

## Class attack findings (not FAIL; PROPOSED-ISSUE lines)
PROPOSED-ISSUE: {"severity":"medium","feature":"team-video-review","title":"--output json: a click parse error (--max-cost abc, empty value, 0x10, unknown option, missing argument) exits 2 with an empty stdout, and exit 2 means 'pointer errors' in this CLI","evidence":"json-attack-1.txt: exit=2 NO-DOC for 5 cases; the builder removed click's min=0.0 only to get exit 1 for negatives","regression_check":null} (P2)
PROPOSED-ISSUE: {"severity":"medium","feature":"team-video-review","title":"--output json: an unexpected exception from the provider (RuntimeError, OSError) escapes `_review`, prints a traceback, exit 1, no JSON document; Ctrl-C gives exit 130 with none","evidence":"json-attack-2-provider-exceptions.txt (4 of 5 cases NO-DOC); only CliFail, PointerErrors, ReviewRefused are caught in cli_video_review.py:_review","regression_check":null} (P3)
PROPOSED-ISSUE: {"severity":"low","feature":"team-video-review","title":"Cleanup is silent when it cannot remove a file: rmtree(ignore_errors=True) leaves frames of the copy if a handle is open (Windows lock); a hard kill leaves the copy until the same review id runs again","evidence":"cleanup-attack-1.txt 'locked': 14 entries remain under reviews/<id>/ with status ok and no log line. Gitignored, so not committable","regression_check":null} (P4)
PROPOSED-ISSUE: {"severity":"low","feature":"team-video-review","title":"If reviews/<id> is a pre-planted junction/symlink, the run writes redacted.mp4 and frames into the target and rmtree refuses to remove them; cleanup did NOT delete the target's other files (precious.txt survived)","evidence":"cleanup-attack-1.txt 'junction'. Needs write access to the project dir, so not a boundary; refuse a reparse-point work dir for hardening","regression_check":null} (P5)
PROPOSED-ISSUE: {"severity":"low","feature":"team-video-review","title":"Two runs of the same review id share one work dir: the second run's start-of-run rmtree deletes the first run's in-flight files and the first run's end deletes the second's","evidence":"read of review_scratch (media/redacted.py) and run_review; not run. No leak: both copies are redacted by the same windows, and every file is removed at the end; the worst case is a failed or partial review","regression_check":null} (P6)
PROPOSED-ISSUE: {"severity":"low","feature":"team-video-review","title":"Wording/hygiene: the manifest's ruff claim is false at head; the video_pointers docstring now holds literal CR/LF characters (`\\r\\n` became `\r\n`); `transcript_hash` was refactored in the repair (same behaviour) though no finding asked for it; JSON documents for a failed or unreadable review carry no exit_code while the error documents do","evidence":"git diff 3d0be650..HEAD","regression_check":null} (P7)
PROPOSED-ISSUE: {"severity":"low","feature":"process","title":"This L check ran 143 min wall against a 45 min deadline: the first affected set took 17 min on a machine shared with other checkers; all mandatory checks completed, so no CONTINUE-NEEDED","evidence":"Metrics","regression_check":null} (P8)

## .gitignore scope
`projects/*/reviews/` ignores the stored review JSON and any export as well as the media. TV10 says the review is stored "under the project through core.paths (never beside the source video, never in the repo)", so ignoring the whole tree follows the contract literally; the stored review quotes the recording in a public repo. Nothing tracked is affected (0 tracked files under it, on the branch and on master). Supported by the contract; I rule it MET and not an owner decision, with one remark: an owner who later wants reviews committed as fixtures would need to reverse it.

## Rulings on owner decisions 4-9
- 4 (approval is a per-run ceiling, never consumed): TV7.2 reads "a recorded per-use approval exists for (project, provider); another project or provider does not count; never an inferred approval". The tests prove all three refusals (wrong project, wrong provider, too-narrow `max_actions`). As written the criterion is MET. What the text does not say is whether one approval buys one review or many until expiry; that is a spend-policy choice only the owner can make. Confirmation needed, not a FAIL.
- 5 (`langchain-fallback` fans out): criterion MET as written (an explicit approval for that provider id exists). It is still a CRITICAL-area gap: its docstring chains Anthropic, Gemini, Ollama, ChatGPT, so one approval releases frames to whichever vendor answers. Only reachable by `--provider langchain-fallback` (default is `gemini`). HUMAN_GATE-REQUEST: refuse `langchain-fallback` for `ingest review`, or require the approval to name the vendor.
- 6 (TV9 / TV7.1 contradiction, HELD parts): the contradictions are real (I read `stages/review.py:43` `require_reviewed` refusing non-APPROVED, and `docs/spec.md:169`: a pointer review needs `project.edit` plus `video.view`, TV7.1 says `video.upload`). TV7.1 (`authorize()`), TV9 flows, TV10 view/export routes, `ingest run --pointers` and the live acceptance are NOT built, so those cited criteria are unmet as written. Only the owner can settle which unit relaxes the expand gate and which permission key applies. HUMAN_GATE-REQUEST: (a) TV9 flows vs D-073 `require_reviewed`; (b) TV7.1 permission key `video.upload` vs spec.md:169; (c) the contract's out-of-scope list should name the T-204/T-205 parts. A PASS for this unit means the declared built subset only and cannot close T-197.
- 7 (`ApprovalKind.VIDEO_REVIEW`, reuse of the signed `RunApproval`): met and consistent with the existing machinery (signed, expiring, bound to project, kind and target); a separate record type is the alternative the builder offered. Confirmation only.
- 8 (pointer limits 100 lines / 500 chars / 32768 bytes): the contract names none; I found no legitimate documented input refused. Recorded as an owner decision, not a FAIL.
- 9 (helper modules): see the table.

## New-module table (D-082 item 1: named by contract or brief, one-job docstring, doctor clean, listed here)
Doctor is clean (`doctor: clean`). Names checked in the contract and in `qa/briefs/t197-video-pointers.md` (master checkout; the brief is untracked there).
| New file (vs 09828f2d) | Named by | One-job docstring | Lines |
|---|---|---|---|
| src/autotester/cli_video_review.py | brief, contract | yes ("autotester ingest review") | 250 |
| src/autotester/media/redacted.py | brief, contract | yes (redacted derivative and its frames) | 155 |
| src/autotester/schema/video_pointer.py | brief, contract | yes | 46 |
| src/autotester/schema/video_review.py | brief, contract | yes | 157 |
| src/autotester/stages/video_pointers.py | brief, contract | yes (parse a pointer file) | 130 |
| src/autotester/stages/video_review.py | brief, contract | yes (the run) | 297 |
| src/autotester/stages/video_review_items.py | brief only | yes (reply -> validated items) | 150 |
| src/autotester/stages/video_review_plan.py | brief only | yes (which seconds are looked at) | 129 |
| src/autotester/stages/video_review_prompt.py | brief only | yes (prompt for one batch) | 111 |
| src/autotester/stages/video_review_render.py | brief only | yes (Markdown/HTML render) | 70 |
| src/autotester/prompts/video_review_v1.md | brief, contract (a prompt file, not a module) | n/a | 43 |
All qualify under D-082 item 1; the one caveat is that `video_review.py` at 297 lines is within 25 lines of the cap. `ApprovalKind.VIDEO_REVIEW` is an enum value, not a module.

## Falsifications (throwaway copies outside the tree, green before / red after, deleted)
11 rows (evidence/falsify-rows.txt, falsify-tv7-noverify-rerun.txt): F1 finally 4 failed; F1 gitignore 8 failed; CLI cap 3 failed; stage cap 3 failed; loop compare 1 failed; JSON `_fail` 10 failed; pointer lines 2, note 1, file 1 failed; TV7 origin-after-check 1 failed; TV7 verify removed 2 failed (after correcting my own test selection). Mutants: 11, above the L guidance of 10; mutant-cap-raise: the floor needs 4 and I added the redaction-ordering and per-limit rows because the brief calls redaction critical.

## Full suite
NOT RUN. Owed only when every criterion is met; the lint gate is red, so the one checker suite stays owed for the next check. Lock state: not requested.

## Diff scope (step 4c)
Repair diff read in full (12 files, all declared in the manifest's fix-cycle list). Whole-unit diff 30 files vs 09828f2d, all in the manifest's lists or the carried g2 set. Nothing deleted or renamed except the one test assertion inverted on purpose (`redacted.mp4` is_file -> `not work.exists()`, stricter). No file outside scope.

EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent; builder executor differs)
EXPLANATION: Every behaviour repaired in cycle 1 holds under my own attacks and falsifications, and the required ruff gate is red at head from a one-line test-file E501 that the manifest says passed, so this is a FAIL that a one-line wrap fixes. The unit also leaves TV7.1, TV9 flows, TV10 routes, `run --pointers` and live acceptance unbuilt (HELD for the owner), and I found two json-mode gaps (click parse errors, unhandled provider exceptions) that I filed as PROPOSED-ISSUE rather than FAIL because the contract lists exit codes only for the command's own outcomes.
Metrics: start=2026-10-11T04:37Z end=2026-10-11T07:05Z wall_min=148 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=11 cycle=1 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=8880 mutants=11 defects_unit=1 defects_6c=0
slow: affected tests 17 min + falsification copies 40 min, both inflated by other checkers' ffmpeg load
