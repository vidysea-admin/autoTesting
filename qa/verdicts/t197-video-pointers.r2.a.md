# Verdict - t197-video-pointers, repair check A (blind dual, coordinator A)

Cycle checked: 2
Verdict path: qa/verdicts/t197-video-pointers.r2.a.md · Checkpoint: qa/checkpoints/t197-video-pointers.r2.a.md
Date: 2026-10-12 · Bound to D:/autoTesting · Policy-Version: proportional-verification/2026-10-10.9
Git verified: branch wave/t197-video-pointers, head b59dda0d (product 28035c82), `Repair base` 0dcbbfa5 is an ancestor of head; repair diff 6 files (3 src, 2 tests, manifest).
Copy: `git archive b59dda0d` on C: (scratchpad), own venv, `autotester.__file__` inside the copy, nothing created on D: except these qa files. Resumed once after an interruption; copy and venv were reused (valid).

## Check plan
Repair scope: F1 (ruff), F2 a-d (JSON on every exit), F3 (32769 boundary), criteria whose input files the repair diff touches (cli_video_review.py, cli_video.py, video_pointers.py docstring: TV1 pointer exit, TV3 unreadable doc, TV7 CLI half, TV8 scrub, TV10 stored review), the affected tests, repair diff read in full, whole-unit stat scan, one falsification per repaired item, TV7.3/TV7.4 re-check, one full suite (L, security trigger). Untouched criteria keep their recorded result and were not repeated.

VERDICT: PASS
SCOREBOARD: repair scope 3/3 failed items met (F1, F2 a-d, F3); touched criteria TV1 TV3 TV7(CLI half) TV8 TV10(stored half) still hold; 1/1 invariants touched (file/function limits) hold. Built subset only, as the manifest declares: TV7.1, TV9 flows, TV10 routes, `ingest run --pointers` and the live acceptance are HELD by the owner's own record, so this PASS does not close T-197.
TIER: L (security: `require_approval` for `ApprovalKind.VIDEO_REVIEW`, cli_video_review.py:75-77 [the manifest cites :75, the call starts at :76; wording only]; dual check, A of two).
FAILURES: none.

## Per item
- F1: `ruff check src tests scripts` -> All checks passed (exit 0); `autotester doctor` -> clean; cli_video_review.py = 300 lines, every function <= 50. Met.
- F2a: all 6 listed click usage errors, missing argument, unknown option, `--output` with no value (after json) -> exit 1 (never 2), one document `{status:"usage_error", reason, exit_code:1}` when json is in argv, provider calls 0. Met. Evidence: probes in `qa/evidence/t197-video-pointers-r2-A/`.
- F2b: RuntimeError and OSError from the provider -> exit 1, one `internal_error` document, no traceback, no canary secret, scratch (`rv_*`) gone. Met (path-masking limits: see P1).
- F2c: KeyboardInterrupt -> exit 130, one `interrupted` document, scratch gone; also in the `--dry-run` preview. Met.
- F2d: ok, dry-run, partial, failed, unreadable, pointer_errors, refused, usage documents all carry `exit_code` equal to the process code. Met.
- F3: `test_the_pointer_file_limit_is_exactly_32768_bytes` (32768 accepted, 32769 one error naming "32769"). Met.

## Rulings asked for
1. `ReviewCommand.parse_args` and exit 1. Consistent with the contract: team-video-review.md "CLI contract" names only 0/2/3/4 and says pointer errors are 2; usage errors are not named, so 1 (already used by this command for usage) cannot collide with 2. cli-mcp.md CM1 wants usage/validation distinct from the others; no shared exit-code enum exists yet (T-174 unbuilt). No other command is changed (`cls=` is used by this command only). No repo test asserts click's exit 2 for `ingest review`; test_cli_surface and the 373-test affected set pass. `--help` still exits 0 (not a TyperException).
2. JSON detection from argv: sound for every real case I tried (`--output json`, `--output=json`, repeated options, option after the positional, a flag value that swallows `--output`, extra positional). No `-o` option exists (`-o json` is an unknown option: text, exit 1). Two over-emits where click's last-wins or `--` would make the format text: `--output json --output text --bogus` and `-- --output json` print a document anyway (harmless, low, P2). The bare `--output` / `--output xml` / `--output JSON` cases stay text with exit 1: ACCEPTED. The contract promises a document for `--output json`, and a caller who named no valid format has not asked for one; guessing json would put a document on a human terminal.
3. `internal_error`: no secret (Redactor path; removing it turns 2 tests red), no traceback on either stream, scratch cleaned, class name only plus a 300-char scrubbed message, never raises (secret loading failure drops the message). Redaction on the stored path not weakened (stage untouched). Limits found: P1.
4. `exit_code` is an envelope key: stored review has none (asserted from disk), `schema/video_review.py` unchanged in the whole-unit diff beyond the carried slice and untouched this cycle, a stored review re-serves with the key added, and the document minus `exit_code` validates as `VideoReview`.
5. TV7.3/TV7.4 after the `cli_video_review.py` edit: `_review`, `build_gate`, the stage and `redacted.py` are not in the repair diff. The redaction, gates, cleanup and guards test files all pass in the affected run (provider receives only stills cut from the verified redacted copy; NaN/inf/negative caps refused with 0 provider calls, also checked by my own CLI probes). Mock provider only, a synthetic ffmpeg clip, no live call.

## Falsification floor (one per repaired item, copies on C:, green before, red after, restored by deletion)
F2a 13 passed -> 8 failed (`2 == 1`) · F2b 2 -> 2 failed (no document) · F2c 1 -> 1 failed · F2d 5 -> 4 failed (`KeyError exit_code`) · F3 1 -> 1 failed (`0 == 1`, 32769 accepted) · extra row, scrub removed: 2 -> 2 failed (canary leaks). All reds are on the named assertion, not import errors. Table: evidence/falsification-and-probes.md. mutants=1 (beyond floor), mutations=6.

## Diff scope (4c)
Repair diff read in full: nothing removed but docstring text, the `_finish` one-liner and a moved import; no def/class/test/assertion deleted or weakened, no skip/xfail. Whole-unit stat (30 files vs 09828f2d): every file is listed in the manifest "What changed" or its carried-work note; none outside scope.

## Tests
Affected set (18 files): 373 passed; 8 first failed only because an archive copy has no `.git` (`check-ignore` tests), 19/19 pass after `git init` in the copy.
Full suite (ONE, sharded 4, lock free, blocked_min 0): collect proof ok 3631; 3605 passed, 19 skipped, 7 failed, all classified:
- AT-858 `test_mc_sessionstart_loop_status` x2 (passed alone), AT-750 `test_crawl_inventory_live` (passed alone), AT-725 `test_redact_wrap_perf` (timing, load), AT-920 `test_env_example_documents_every_key_the_code_reads`, AT-921 `test_healthz_source_root_is_the_package...`: known master reds/load-sensitive.
- `test_reconcile_schema::test_rc2_ingest_video_keeps_narration_on_screen_text_and_exit_screen`: NOT in the known list. Fails identically at the unit's merge base 09828f2d, passes on master ccf3683b; the unit changes none of its files (`git diff` on the test, stages/ingest.py, stages/reconcile.py is empty). Pre-existing at the base, not owned by this unit; it clears on merge with master.

## PROPOSED-ISSUE
PROPOSED-ISSUE: {"severity":"low","feature":"t197-video-pointers","type":"info-disclosure","title":"internal_error reason can still carry the recording's directory: a genuine FileNotFoundError reports the path as repr (doubled backslashes), so only the file name is masked to <recording>; an upper-cased path or name is not masked either (case-sensitive replace)","evidence":"cli_video_review.py:_failure_reason masks path, posix path and name by str.replace; probe qa/evidence/t197-video-pointers-r2-A/probe_r2a.py::test_real_oserror_repr_path_leaks_directory prints `[Errno 2] ... 'C:\\\\Users\\\\Lenovo\\\\...\\\\cliv0\\\\rec.nope'`","fix":"mask the repr form and compare case-insensitively on Windows, or print the class name only"}
PROPOSED-ISSUE: {"severity":"low","feature":"t197-video-pointers","type":"cli-edge","title":"_wants_json ignores click's last-wins and the `--` separator, and SystemExit from a provider is not turned into a document","evidence":"probe_r2a.py::test_argv_shapes[last-wins-text-after-json], [double-dash-json], test_systemexit_from_provider (exit 7, empty stdout, scratch still removed)","fix":"optional; none needed for the contract"}
Why neither blocks: the contract forbids secrets in output (TV8, C5), not paths; the document goes to the invoking operator's own stdout; no criterion names path masking, and the secret path is intact and falsified.

## Capability, browser
CAPABILITY-COVERAGE: 6/6 rows reproduced (floor met). LIVE-BROWSER: not-applicable (no UI path changed: cli*.py, stages/video_pointers.py, tests). Persona walk: not owed. full-suite trigger: run (L, security).
Over-scope test: none. Wording: manifest line 14 cites `:75`.

## New-module table (D-082 item 1, whole unit; D-085 reads a Group 10 module named by its job in the brief as named)
| Module | Named by | One-job docstring | Lines |
|---|---|---|---|
| cli_video_review.py | brief s3 (D-072 item 2) | yes | 300 |
| schema/video_pointer.py, schema/video_review.py | brief s3 + s4 table | yes | 46, 157 |
| stages/video_pointers.py, stages/video_review.py | brief s3 + s4 table | yes | 130, 297 |
| stages/video_review_plan.py, _items.py, _prompt.py, _render.py | brief s4 table, by job | yes | 129, 150, 111, 70 |
| media/redacted.py | brief s4 table, by job | yes | 155 |
| tests/video_review_fakes.py | brief s4 table | yes | 111 |
`autotester doctor` clean at b59dda0d; all listed here. Not new modules: prompts/video_review_v1.md (prompt file), core/pricing.py and paths.py edits.

ISSUES-WRITTEN: none (dual coordinator; PROPOSED-ISSUE lines only).
EXECUTOR: claude-sonnet-subagent (builder, per manifest); checker: claude-sonnet-subagent. Self != executor.
EXPLANATION: The repair closes F1, F2 a-d and F3 with evidence I produced: lint and doctor clean, usage errors now exit 1 with one document, unexpected errors and Ctrl-C each produce one document and clean the scratch, `exit_code` is an envelope key only, and the 32769-byte boundary is pinned. Six falsifications went red on the named assertions. The one full suite shows only known reds plus one pre-existing failure that also fails at the merge base. Two low issues are proposed; I judge them non-blocking.
Metrics: start=2026-10-11T18:55Z end=2026-10-11T19:52Z wall_min=57 agent_min=unavailable blocked_min=0 suite_runs=1 repeat_runs=0 mutations=6 cycle=2 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=3420 mutants=1 defects_unit=0 defects_6c=0
slow: full suite 28 min (collect 1, shards 21, solo re-run 6); wall includes an interruption and resume, 12 min over the L 45-min deadline with all mandatory evidence complete.
