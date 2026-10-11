# Manifest — t197-video-pointers

**Contract:** qa/contracts/team-video-review.md (TV1-TV10 + cross-cutting + live acceptance, ACTIVE 2026-10-07)
**Goal task:** T-197 (plan unit G2 `t197-pointers-review`); brief `qa/briefs/t197-video-pointers.md`
**Date:** 2026-10-11
**Executor:** claude-sonnet-subagent (builder only; no checker dispatched)

## Status: checked-PASS
Merged: d867024f
Fix cycle: 2
Repair base: b59dda0d
Policy-Version: proportional-verification/2026-10-10.9
Tier: L (data egress to an external model: TV7 is CRITICAL; per-use approval gate for model spend; redaction before egress)
Dual check: required
dual-trigger: security src/autotester/cli_video_review.py:75 (`require_approval` for `ApprovalKind.VIDEO_REVIEW`, target = provider id, actions = planned calls; this is the CLI half of the gate that precedes every Provider call; the stage side is `src/autotester/stages/video_review.py:228` `gate()`, and redaction is `src/autotester/media/redacted.py` `redact_video`/`verify_blackout`/`review_scratch`)
Persona walk: not owed by this cut (no UI surface changed: no route, template or browser step is in scope; the pointer form, stored view and exports are HELD with TV10, see below)
Product commit: 89371ca4362b7bad9a8aa7b5fc285dc602d684c8 (master-merge reconcile on b59dda0d, no new fix cycle; fix cycle 2 product was 28035c82637972a32332dab1fa48694d3720e032; cycle 1 product was c726cfdafb198f0229117d9145a5cc2d1daa3220, head 0dcbbfa5; cycle 0 product 5032cfa15d01974a208ce5be7647f1eaf5ba0626, head 3d0be650)

## Base, and the earlier work carried forward
- Branch `wave/t197-video-pointers` cut from master `09828f2d`. The earlier slice `wave/g2-review-core` (pure core, 14 files, 5 test files, cycle-1 fixes F1-F5 and F7; its manifest and verdict live only on that branch and were NOT carried, so this is the one manifest for the unit) was MERGED in (commit `3298586a`; `docs/MAP.md` taken from master and regenerated). The old branch and its worktree are untouched. Nothing was rebuilt.
- `core/paths.py` after the merge is exactly 300 lines (limit 300): fits without T-205.

## What changed (on top of the carried core)
- src/autotester/cli_video_review.py:1-220 (NEW, named by D-072 item 2) — `ingest review`: `review_cmd`, `build_gate`, `parse_windows`; exit 0/1/2/3/4, `--dry-run`, `--output json` (document on stdout, notes on stderr), `--redact`, `--max-cost`, `--refresh`.
- src/autotester/cli_video.py (+2) — imports and registers `review_cmd` on the `ingest` app (hook only).
- src/autotester/schema/enums.py (net 0 lines) — `ApprovalKind.VIDEO_REVIEW = "video_review"` (docstring shortened to stay at 300). OWNER DECISION, see below.
- src/autotester/cli_crawl.py (net 0) — `approve --kind` help lists `video_review`; the "target does not match base_url" note is skipped for a non-URL target (a provider id).
- src/autotester/browser/secrets.py (+5) — `SecretStore.scrub_values()` (the mapping a secret gate needs; no value is ever printed).
- src/autotester/stages/video_review.py — `unreadable_reason()` (one check shared by the stage and the CLI exit 4); the stage now calls it.
- src/autotester/stages/video_pointers.py — `BASE_FRAMES_PER_MIN`, `POINTER_FRAMES_PER_MIN` now live here (F8; the contract vocabulary puts them here); `video_review_plan.py` imports them, and its preview cost now uses `estimate_cost_conservative` (a dry-run for `gemini` no longer prints $0).
- src/autotester/stages/video_review_prompt.py + video_review_items.py — F6: `engine=none` carrying segments is "none", and `overlapping()` returns nothing unless the state is `speech`.
- src/autotester/stages/video_review_render.py — a `Baseline` line, "No baseline to compare ...", in both exports (TV9 phrase).
- tests/video_review_fakes.py (NEW, 111 lines; carried from the g2 slice, listed here at last after B's cycle-1 note) - the recording fake `RecordingProvider`, `FakeFrames` and the reply builders every video-review test shares.
- tests/test_cli_video_review.py (NEW, 20 tests, real ffmpeg), tests/test_video_review_guards.py (NEW, 8 tests), tests/test_cli_advice_resolves.py (+1 site `cli_video_review.py` / `ingest list`, count 21 -> 22).
- docs/MAP.md regenerated with `autotester map`.
- Also changed by the carried work and not listed in cycle 0 (A's P10): src/autotester/core/pricing.py (+15, `estimate_cost_conservative`: an unpriced label is charged the dearest known rate, never zero), src/autotester/core/paths.py (+6, `review_path`/`review_work_dir`; the file is exactly 300 lines), src/autotester/prompts/video_review_v1.md (NEW, 43 lines, the review prompt file with its placeholders).

### Fix cycle 1 (repair base 3d0be650, product c726cfda)
- src/autotester/media/redacted.py:1-155 (+25) — `review_scratch(work_dir)` context manager (emptied before use, removed whole in `finally`, Ctrl-C included); `RedactedFrames.__init__` deletes its derivative on ANY failure of the copy or the blackout check (`except BaseException`); `verify_blackout` unlinks each still in a `finally`.
- src/autotester/stages/video_review.py:228-262 — `run_review` runs the frame/prompt/call section inside `with review_scratch(paths.review_work_dir(rid))`; a non-finite `max_cost_usd` is refused before the gate; the cap comparison is `not cost < cap` (NaN-safe). File 297 lines, `run_review` 49.
- src/autotester/cli_video_review.py:1-250 — `CliFail` (reason + exit code) is raised by every usage/refusal site and turned into the stderr note plus, in json mode, ONE document `{"status": "usage_error"|"refused", "reason", "exit_code"}` in one place (`_fail`); `pointer_errors` and `unreadable` documents now carry `exit_code` too; `--max-cost` no longer uses click's `min=0.0` (which let NaN/inf through and gave click's own exit 2) and is checked by hand (finite, >= 0); a pointer file over the size limit is refused unread (exit 2). `review_cmd` split into `review_cmd` + `_review` to stay under 50 lines per function.
- src/autotester/stages/video_pointers.py:1-130 — `MAX_POINTER_LINES = 100`, `MAX_POINTER_NOTE_CHARS = 500`, `MAX_POINTER_FILE_BYTES = 32768` and `oversize_parse()`; `parse_pointers` turns each violation into a `PointerError` (count identity kept).
- .gitignore — `projects/*/reviews/` (see "Decisions").
- tests/test_video_review_cleanup.py (NEW, 19 tests, real ffmpeg, directory-listing assertions), tests/test_cli_video_review_exits.py (NEW, 26 tests: json document per exit code, non-finite cap, dry-run writes nothing, pointer size limits), additions to tests/test_video_pointers.py (+1), tests/test_video_review.py (+1, TV8 scrubbed quote), tests/test_video_review_gates.py (+5: plain re-run keeps human status, non-finite cap at the stage and in the loop), tests/test_video_review_redaction.py (one assertion: the work dir is gone after the run).

### Fix cycle 2 (repair base 0dcbbfa5, product 28035c82)
Both cycle-1 verdicts (A: ruff gate; B: ruff + JSON on every exit) are the brief. Four product files edited in place; no new module.
- src/autotester/cli_video_review.py:1-300 (was 250; limit 300, every function <= 50) - (2a) `ReviewCommand(TyperCommand)` overrides `parse_args`: a usage error raised before our code runs (`--max-cost abc`, `""`, `0x10`, a missing argument, an unknown option) is shown on stderr and exits **1**, not click's 2 (2 is pointer errors here); when `--output json` or `--output=json` is in argv (`_wants_json`) it also writes the one document `{"status": "usage_error", "reason", "exit_code": 1}`. (2b) `review_cmd` catches any other `Exception` from the run and writes `{"status": "internal_error", "reason", "exit_code": 1}`; `_failure_reason` builds the reason as the class name plus the message passed through `Redactor.scrub` (the project's declared secrets) with the recording's path, posix path and file name replaced by `<recording>`, whitespace collapsed, 300 characters, and never raises. (2c) `KeyboardInterrupt` writes `{"status": "interrupted", "reason", "exit_code": 130}` and exits 130; the stage's `review_scratch` `finally` (cycle 1) has already removed the scratch on the way up. (2d) `_finish` and `_print_plan` add `exit_code` (the code the process really exits with) to the review and plan documents. `CliFail` gained a `status` so the one `_fail` writes every non-review document.
- src/autotester/cli_video.py (293 lines, unchanged count) - the `review` registration passes `cls=ReviewCommand`.
- src/autotester/stages/video_pointers.py (130 lines, unchanged count) - the `parse_pointers` docstring is back to the escaped \\r\\n, \\r, \\n text (cycle 1 had made them literal CR and LF characters inside the docstring).
- tests/test_video_pointers.py (+17) - (3) `test_the_pointer_file_limit_is_exactly_32768_bytes`: a 100-line valid file of exactly 32768 UTF-8 bytes is accepted, one of 32769 is one error naming "32769"; the E501 line wrapped.
- tests/test_cli_video_review_exits.py (+113, 284 lines) - 5 usage-error cases, a missing argument, the `--output=json` form, the text-mode and bare-`--output` case, RuntimeError and OSError from the provider, Ctrl-C, `exit_code` on ok / dry-run / partial / failed documents, and the stored-review-still-loads test.
- `exit_code` is an ENVELOPE key of the CLI document, not a field of `VideoReview`: the stored review file is written by the stage before the CLI adds it, so `schema/video_review.py` did not change and every review stored before this change loads as before (`test_exit_code_is_an_envelope_key_not_a_stored_field_and_old_reviews_still_load` loads the stored file, asserts it has no `exit_code` key, and validates the CLI document minus that key as a `VideoReview`).
- No existing assertion weakened; no skip or xfail. Redaction, storage, cap and pointer-limit behaviour untouched.

## New modules (owner confirms before merge)
- src/autotester/cli_video_review.py — the `ingest review` command (named by D-072 item 2).
- Carried unchanged in job from the g2 slice: schema/video_pointer.py, schema/video_review.py, stages/video_pointers.py, stages/video_review.py (D-072 item 2) and stages/video_review_plan.py, stages/video_review_items.py, stages/video_review_prompt.py, stages/video_review_render.py, media/redacted.py (the g2 cycle-0 ruling 1 covers them on the same reading; a D-entry naming them is still owed by the coordinator, F8).

## Acceptance criteria (verbatim from qa/contracts/team-video-review.md)

- **TV1 — Pointer grammar, and nothing is dropped (R32).** The parser accepts every form in the vocabulary. A negative time, a reversed
  range (`14:00-12:30`), an unparsable line, a time at or past the recording's duration, and a fourth free pointer each come back in
  `errors[]` with the 1-based line number and a reason; none is clamped, reordered or skipped. The count identity holds for every input:
  `len(parsed) + len(errors) == number of non-blank lines`. On any error the CLI/route stops with **exit code 2 / HTTP 422**, the Provider
  is never called, and the error list is shown to the user whole (not first-error-only). `serves:` R32, O8.
  *Verify:* table-driven pytest over 20+ lines including `1:02:03`, `~12:30`, `12:30 | note`, `99:99`, an empty-after-pipe note, Windows
  `\r\n` endings and a BOM. *Mutation:* make the parser `continue` on a bad line -> the count identity fails.
- **TV2 — Pointers prioritise, they never exclude (R34).** For the same recording, the set of frame times analysed **with** a pointer
  file is a superset of the set analysed **without** one; frames inside a pointer window are at pointer depth, frames outside at base
  depth (pointer depth strictly greater). `not_reviewed` is exactly the complement: analysed spans plus `not_reviewed` cover
  `[0, duration_s]` with no gap and no overlap, and a recording nobody pointed at is still analysed end to end. The spans the review
  names as not reviewed are rendered in the summary in plain language, not only stored. `serves:` R34, O8, O4.
  *Verify:* fake Provider records the requested frame times; run with zero, one and three pointers (one a window, one `~` approximate);
  assert superset, depth ordering, and the exact partition. *Mutation:* restrict analysis to pointer windows only -> the superset
  assertion fails; drop `not_reviewed` rendering -> the summary assertion fails.
- **TV3 — Output shape, no padding (R33).** `VideoReview` (a Pydantic model in `schema/video_review.py`, `extra="forbid"`) has a
  non-empty flow summary and 0-5 `ConfirmItem`s, each with non-empty `time_s`, `screen`, `seen`, `suggestion`, `severity` and a
  `source_id`. A model reply with 2 valid items yields 2 and the review says fewer than 4 were found (it does not pad to reach the
  4-5 the oracle shows); a reply with 9 yields the 5 highest-severity, the other 4 kept in `overflow` (never discarded); an item with an
  empty or missing field goes to `rejected` with a reason and is never rendered blank. A reply that is not valid against the schema
  yields a review with status `failed` and the raw reason, not an empty-but-clean review. *Unreadable or empty media (proposal TV12):*
  a corrupt, zero-length or audio-only file yields status `unreadable` with the reason, never a review that looks verified.
  `serves:` R33, O8, O3. *Verify:* fake Provider returning 2, 5, 9, one malformed item, non-JSON, and a
  zero-length fixture file. *Mutation:* truncate silently to 5 without `overflow` -> fails.
- **TV4 — Every item cites a real second (R33).** For every rendered item `0 <= time_s <= duration_s` and `source_id` resolves to a
  registered source in the project. A hallucinated second (for example 99999, or negative) or an unknown `source_id` moves the item to
  `rejected` with reason `time_outside_recording` / `unknown_source`; it reaches neither the rendered list nor either export.
  `serves:` R33, O3. *Verify:* fake Provider returns out-of-range and wrong-source items; assert absence from the HTML, the Markdown and
  the stored `items`; assert presence in `rejected`.
- **TV5 — Provenance is labelled, and narration is verbatim (R35).** Every item has `origin` in the four values. `narration` requires a
  `quote` that is an exact substring of a transcript segment whose time span overlaps the item's second (comparison on the stored
  transcript text, not a paraphrase, not a normalised variant that changes words); otherwise the item is downgraded to `suspected`
  and the downgrade is recorded. A `pointer` item must cite the pointer line it came from. The system never labels any item
  "confirmed" (grep of the rendered output and the model for the word as a status finds none). The transcript on disk is read as-is
  and never regenerated by the review (VL1 / `ingest.md` I8). `serves:` R35, O3, O8.
  *Verify:* fake quote not in the transcript -> `suspected`; a real quote -> kept as `narration`; a quote from a segment far from the
  item's second -> `suspected`; transcript file hash identical before and after. *Mutation:* skip the substring check -> the fake-quote
  test fails.
- **TV6 — Silence is not verification (R35, AT-134 carried).** With `Transcript.engine == none` the summary says "no narration on
  record"; with `unreadable` it says "narration unreadable"; no item has origin `narration` in either state; and neither is ever
  rendered as "nothing was said" or equivalent. A transcript with speech but none overlapping an item's second is stated as "no
  narration at this moment", not as agreement. `serves:` R35, O3, O4.
  *Verify:* one fixture per engine value plus one with speech elsewhere; assert both phrasings in the rendered HTML and Markdown and
  the absence of "nothing was said", "no issues" and "narrator agrees". *Mutation:* map `unreadable` to `none` -> fails.
- **TV7 — Redaction, approval and permission before any call; bounded spend (CRITICAL; R36, R63).** Four conditions, all checked
  **before the first Provider call**, each with its own refusal naming the missing thing and **zero Provider calls** on refusal:
  1. *Permission:* the caller holds `video.upload` on the video's project through `authorize()` (not an email or group-name compare);
     otherwise 403, or 404 where the caller cannot see the project at all (the auth.md AU13 rule).
  2. *Approval:* a recorded per-use approval exists for (project, provider); an approval recorded for another project or another
     provider does not count; model money is never spent on an inferred approval.
  3. *Redaction:* with redaction windows set on a source, no frame whose timestamp falls inside a window and no audio from inside a
     window is passed to the Provider, and the unredacted original path is never passed (the Provider is handed only the derivative).
     Redaction is applied to the derivative **before** the call, and the derivative is checked to differ from the original inside the
     window (a blackout that is a no-op is a failure).
  4. *Bounded spend:* a per-review cost cap (a named config value, default cheap) stops analysis when reached; the review is marked
     `partial` and `not_reviewed` lists what was left (proposal TV13). `--dry-run` / the preview prints the plan (windows, frame count,
     estimated cost) with zero Provider calls.
  `serves:` R36, R63, O7, C5. *Verify:* fake Provider records every frame timestamp and every file path it is handed; assertions over
  both; one run per refusal asserting `provider.calls == 0`; a priced fake with the cap at 2 calls asserting the `partial` label and
  leftover spans. *Mutations (each must fail a test):* apply redaction after the call; pass the original path; compare permission by
  group name; ignore the cap. The live fixture is the **redacted** Navnit sources; the originals under
  `D:/pathlynks_videos/_original_unredacted/` are never passed to any provider in any test (a path-prefix assertion in the fake).
- **TV8 — Nothing secret in the artifact (R36, R16).** The summary, items, quotes, pointers' free text, `rejected`, `overflow`, logs and
  both exports pass `Redactor.scrub`; a planted secret value (a password, a token, a `{{SECRET:KEY}}` resolved value) present in a
  transcript segment or in a pointer's free text does not appear in the persisted review, its Markdown or HTML export, or `caplog`.
  `serves:` R36, O7, C5. *Verify:* plant a canary in the transcript and in a pointer; grep every file written and the log. *Mutation:*
  skip the scrub on quotes -> fails.
- **TV9 — Video flows never gate case generation (R37, D-070 part 2).** Flows learned through the review path are written to the
  FlowSpec as `DRAFT` carrying `source_id`, the narrated intent and provenance; **every** flow is retained (ideal, narrated, variant),
  none is dropped as a duplicate here. `expand` runs over a spec made only of these flows **without** a human approval of them and
  generates cases. Where no product knowledge graph exists, the review says "no baseline to compare", never "matches the product".
  Reconciliation against the crawled KG belongs to `reconcile.md`; this unit must not weaken `require_reviewed` (D-073). The pointer
  review never edits a flow that a human has already approved. `serves:` R37, O8, O9, D-070 part 2.
  *Verify:* run `expand` over a DRAFT-only spec produced by this unit and assert cases exist and all flows are present; run with no KG
  and assert the "no baseline" phrase; approve a flow by hand, re-run the review, assert the approved flow is untouched.
- **TV10 — Deterministic id, idempotent re-run, viewable and exportable (R38).** `VideoReview.id` is derived from content: source
  sha256 + the canonical form of the parsed pointer file + the transcript hash + the redaction windows. The same inputs give the same id;
  a second run creates no second artifact (it returns the stored one, or refreshes it in place) and **does not reset any human-set item
  status** (a human may mark an item `confirmed`, `dismissed` or `fixed`; that is stored on the item, separately from the model's
  output). Changing a pointer, the transcript or a window gives a new id. The review is stored under the project through `core.paths`
  (never beside the source video, never in the repo), is viewable on the video page and exportable as Markdown and HTML with identical
  item sets; viewing and export need `video.view` on that video (scope via `authorize()`; a project the viewer cannot see is a 404, a
  visible one lacking the action a 403). `serves:` R38, O8, O15.
  *Verify:* run twice, assert one artifact and same id; mark an item confirmed, re-run, assert the mark survives; change one pointer,
  assert a new id; export both formats and compare item ids; request as a Tester with and without the video shared. *Mutation:* derive
  the id from a timestamp -> the same-id test fails.

## Cross-cutting (judged inside the rows above; each is a no-fire on its own)

- **Windows and Ubuntu (R65).** Frame extraction, temp files, the redacted derivative and the review store use `pathlib` and
  `core.paths`; no POSIX-only module at import time. The pointer parser and redaction tests include paths with both separators and a
  drive letter. The same table-driven tests run on Windows (the checker's host) and in the T-203 / Ubuntu check; the Linux run is
  recorded under `qa/evidence/` (the unit may reuse the T-204 Linux run if it covers these tests).
- **One path to a model.** Every model call goes through `providers.base.Provider`; the prompt is a file
  (`prompts/video_review_v1.md`) carrying its placeholders (the I8 lesson: a template that loses `{{NARRATION}}` ships a blind prompt,
  so a test defends the template as well as the code). No inline prompt string.
- **CLI contract (proposal TV11, T-174 conventions).** `ingest run --pointers <file>` and `ingest review`: exit 0 ok, 2 pointer errors
  (TV1), 3 approval or permission missing (TV7), 4 source unreadable (TV3); `--output json` is a valid document on stdout with logs on
  stderr. Judged inside TV1, TV3 and TV7.

## Master merge (reconcile at b59dda0d, not a fix cycle)
Dual PASS head b59dda0d; its merge into master was aborted on conflicts. `git merge --no-ff --no-autostash master` run in `.worktrees/t197-video-pointers`.
- **Master SHA merged:** d42e94456d04409389cb854ae40693a7996dba50. **Merge commit:** 89371ca4362b7bad9a8aa7b5fc285dc602d684c8 (parents b59dda0d, d42e9445). Merge base 09828f2d. `autotester.__file__` resolves inside the worktree.
- **Conflict 1, `src/autotester/cli_video.py` import block:** kept both `from autotester.cli_intake import register_intake_commands` (master, T-198a) and `from autotester.cli_video_review import ReviewCommand, review_cmd` (branch), in isort order. Call sites checked: line 38 `app.command("review", cls=ReviewCommand)(review_cmd)` (branch) and the final line `register_intake_commands(app)` (master) are both intact and unchanged. 297 lines (cap 300).
- **Conflict 2, `tests/test_cli_advice_resolves.py` `EXPECTED_SITE_COUNT`:** base 21, master 24, branch 22. The test, run with the constant left at 24, reported 25 found sites. Arithmetic: master's 24 + the branch's one added site (`cli_video_review.py`, "ingest list", the review command's not-found hint, line 161; the only line the branch added to `EXPECTED_SITES`) = **25**, so the constant is 25 and the docstring now carries the count history. The site set auto-merged with both sides' entries (`git diff master` on the file shows exactly that one added line), so no difference to explain.
- **Conflict 3, `docs/MAP.md` (generated):** taken from master and regenerated with `autotester map`. `docs/SNAPSHOT.md` (generated, merged with changes on both sides) regenerated with `autotester snapshot` because doctor reported it stale.
- **Two merge-induced doctor violations (no textual conflict; the sides collided semantically), both fixed minimally:**
  - `file-too-long` `src/autotester/core/paths.py` 305 > 300: master added `case_proposals` (+5), this branch added `review_path` / `review_work_dir` (+6), master was 299 and the branch 300. Fixed by joining the `ensure()` directory tuple (9 lines) onto two lines, no behaviour change: now 298 lines. The earlier manifest note that paths.py is "exactly 300 lines ... fits without T-205" is superseded: master's `case_proposals` leaves no headroom, so the next path addition needs the T-205 split.
  - `duplicate-concept` `render_html` defined in both `stages/video_review_render.py` (this unit) and `stages/unified_report_render.py` (master, T-168). Renamed this unit's function to `render_review_html` in `video_review_render.py` and its three test files (`test_video_review.py`, `test_video_review_gates.py`, `test_video_review_guards.py`); no `src` caller used it. Ruff then reordered the three test import lines (isort only).
- **Auto-merged with changes on both sides** (comm of `git diff --name-only` merge-base..b59dda0d vs merge-base..master): `docs/MAP.md`, `src/autotester/cli_video.py`, `src/autotester/core/paths.py`, `tests/test_cli_advice_resolves.py`. Only `paths.py` merged silently: all three methods are present (`case_proposals` from master, `review_path` and `review_work_dir` from the branch). `src/autotester/cli.py` changed on master only and no `tests/golden/*` file changed on either side, so no golden file was regenerated.
- **Tests at the merge head (file-scoped, `-p no:xdist -o addopts= --rootdir <worktree>`):** unit affected group 1 (exits, pointers, cli_video_review, cli_surface, cli_advice_resolves) 175 passed; group 2 (video_review x5, approve_cli) 101 passed; group 3 (ingest, consent, signing) 103 passed; master's intake CLI group (test_cli_intake, test_ensemble_honesty, test_intake_schema, test_cli_orchestrate, test_cli_issues, test_cli_release) 86 passed. `ruff check src tests scripts` -> All checks passed!; `autotester doctor` -> doctor: clean. Group 1 was 169 at 28035c82; the six extra tests come from the merge (master's changes to the shared test files, not broken down here). No full suite run.
- Nothing was changed beyond what the merge needed; `qa/contracts/`, `qa/issues.jsonl` and `qa/verdicts/` are untouched. Not pushed, not merged into master.

## Verification scope
Affected tests (one pytest process at a time, `-p no:xdist -o addopts= --rootdir <worktree>`; ffmpeg is present so the real-ffmpeg files RAN). Run as `uv --directory D:/autoTesting/.worktrees/t197-video-pointers run ...`; `autotester.__file__` is inside that worktree. Final product SHA 28035c82637972a32332dab1fa48694d3720e032. A first affected run (270 passed across 11 files) ran one lint-only edit earlier (an import moved to `itertools.pairwise`, a dead `noqa` removed, one `next(...)` rewritten); every number below was re-run at the final SHA.
- `uv run pytest tests/test_cli_video_review_exits.py tests/test_video_pointers.py tests/test_cli_video_review.py tests/test_cli_surface.py tests/test_cli_advice_resolves.py` -> 175 passed (re-run at the merge head 89371ca4, see Master merge)
- `uv run pytest tests/test_video_review.py tests/test_video_review_gates.py tests/test_video_review_redaction.py tests/test_video_review_guards.py tests/test_video_review_cleanup.py tests/test_approve_cli.py` -> 101 passed
- `uv run pytest tests/test_ingest.py tests/test_ingest_real_cli.py tests/test_ingest_persist.py tests/test_ingest_transcripts.py tests/test_merge_flowspec_cli.py tests/test_consent.py tests/test_approval_signing.py` -> 103 passed, 2 warnings (the `ingest` group registers `review` through `cli_video.py`, which changed)
- `uv run ruff check src tests scripts` -> All checks passed! (exit 0). The cycle-1 manifest claim "ruff: All checks passed" was FALSE at 0dcbbfa5: E501 at tests/test_video_pointers.py:199 (103 > 100), found by both checkers; it is wrapped now. Four findings of this cycle's own first draft (RUF007, RUF100, RUF005, E501) were fixed before the commit.
- `uv run autotester doctor` -> doctor: clean (exit 0)
No full suite was run (the checker's combined run stays owed).

Pre-check: 89371ca4362b7bad9a8aa7b5fc285dc602d684c8 uv run pytest tests/test_cli_video_review_exits.py tests/test_video_pointers.py tests/test_cli_video_review.py tests/test_cli_surface.py tests/test_cli_advice_resolves.py -> 175 passed (TV1, TV3, TV7 CLI half, TV8, TV10, the json-on-every-exit rows and the pointer limits including exactly 32768 and 32769 bytes)
Pre-check: 89371ca4362b7bad9a8aa7b5fc285dc602d684c8 uv run pytest tests/test_video_review.py tests/test_video_review_gates.py tests/test_video_review_redaction.py tests/test_video_review_guards.py tests/test_video_review_cleanup.py tests/test_approve_cli.py -> 101 passed (TV2 to TV7 at the stage, TV9 baseline phrase, the work-dir cleanup, the spend cap)
Pre-check: 89371ca4362b7bad9a8aa7b5fc285dc602d684c8 uv run pytest tests/test_ingest.py tests/test_ingest_real_cli.py tests/test_ingest_persist.py tests/test_ingest_transcripts.py tests/test_merge_flowspec_cli.py tests/test_consent.py tests/test_approval_signing.py -> 103 passed
Pre-check: 89371ca4362b7bad9a8aa7b5fc285dc602d684c8 uv run ruff check src tests scripts -> All checks passed!
Pre-check: 89371ca4362b7bad9a8aa7b5fc285dc602d684c8 uv run autotester doctor -> doctor: clean
Metrics: start=2026-10-11T09:00Z end=unavailable wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=36 cycle=2 resumes=2 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=unavailable
mutant-cap-raise: one falsification per criterion TV1-TV10 and the CLI exit code (cycle 0, 17 rows), plus fix cycle 1: 14 more rows covering the work-dir leak (4), the non-finite cap (3), JSON on every exit (1), pointer limits (4) and the two test gaps A named (2); the carried g2 mutations are not re-run; fix cycle 2: 5 more rows (2a, 2b, 2c, 2d, 3)

## Falsification
Throwaway copy of `src/ tests/ scripts/ pyproject.toml` under the scratchpad, `PYTHONPATH` at the copy, anchor asserted unique, copy deleted; green before, red after (the copy for the `.gitignore` row also gets `.gitignore` and `git init`).

### Cycle 0 (at 5032cfa1)

| Criterion | edit | before -> after |
|---|---|---|
| TV1 | parser `continue`s instead of recording the error | 27 passed -> 11 failed |
| TV2 | no base grid when pointers exist (pointer windows only) | 20 passed -> 1 failed |
| TV3 | truncate to 5 with `overflow = []` | 28 passed -> 1 failed |
| TV4 | time-range check removed | 28 passed -> 1 failed |
| TV5 | `_quote_verbatim` returns True | 28 passed -> 6 failed |
| TV6 | `unreadable` state never returned | 28 passed -> 1 failed |
| TV7 stage | `gate()` removed from `run_review` | 20 passed -> 1 failed |
| TV7.2 approval | CLI asks for `actions=0` (a too-narrow approval no longer refused) | 20 passed -> 1 failed |
| TV7.2 approval | CLI matches the target against any approved target, not the provider | 20 passed -> 1 failed |
| TV7.4 cap | cap check removed | 20 passed -> 3 failed |
| TV8 | the quote scrub alone removed | 28 passed -> 28 passed (SURVIVED at cycle 0; closed below by the new direct test) |
| TV8 | quote scrub AND the final whole-review scrub removed | 28 passed -> 1 failed |
| TV9 | Baseline line removed from the header | 8 passed -> 1 failed |
| TV10 | review id mixes in `time.time()` | 20 passed -> 3 failed |
| CLI exit | pointer-error exit code 2 -> 1 | 20 passed -> 3 failed |
| F6 | `engine != none` guard removed from `narration_state` | 8 passed -> 1 failed |

### Fix cycle 1 (rows ran at c726cfda; the two P5 file rows were re-run at the tests-only commit 802c72c9 after their tests were strengthened)

| Repaired criterion | edit (file) | tests run | before -> after |
|---|---|---|---|
| F1 work dir removed on every path | `review_scratch` `finally` does nothing (media/redacted.py) | cleanup: success, provider, cap, Ctrl-C, refresh, blackout, midway | 8 passed -> 8 failed |
| F1 nothing committable | `projects/*/reviews/` line removed from `.gitignore` | `git check-ignore` tests | 8 passed -> 8 failed |
| F1 failed blackout leaves no copy | `RedactedFrames.__init__` no longer unlinks its derivative on failure | constructor test | 1 passed -> 1 failed |
| F1/P4 provider only gets stills of the copy | `self.origin = video` after the blackout check (frames cut from the original) | provider-received-black-stills test | 1 passed -> 1 failed |
| P2 CLI cap | `isfinite` check removed from `_review` | cap tests | 9 passed -> 8 failed, 1 passed |
| P2 stage cap | `isfinite` check removed from `run_review` | non-finite stage tests | 3 passed -> 3 failed |
| P2 loop comparison | `not cost < cap` back to `cost >= cap` | batch-loop NaN test | 1 passed -> 1 failed |
| JSON on every exit | `_fail` stops writing the document | every-exit-path tests | 14 passed -> 10 failed, 4 passed |
| P5 note limit | note-length branch disabled | size-limit test | 1 passed -> 1 failed |
| P5 line limit | line-count branch disabled | size-limit test | 1 passed -> 1 failed |
| P5 file limit (parser) | size branch disabled | size-limit test (a 40 KB file of valid lines) | 1 passed -> 1 failed |
| P5 file limit (CLI) | stat-size branch disabled (file would be read) | oversized-file test | 1 passed -> 1 failed |
| P3 plain re-run keeps human status | stored review returned with every status reset to `open` | plain-rerun test | 1 passed -> 1 failed |
| P5/TV8 scrubbed quote | `or quote in scrub(s.text)` removed | scrubbed-narration test | 1 passed -> 1 failed |

### Fix cycle 2 (rows ran at 28035c82; copies of src, tests, scripts and pyproject.toml on C: under the session scratchpad, `PYTHONPATH` at the copy, `autotester.__file__` printed from inside the copy, anchor asserted unique, copies deleted)

| Repaired item | edit (file) | tests run | before -> after |
|---|---|---|---|
| 2a click usage errors | `app.command("review", cls=ReviewCommand)` -> plain `app.command("review")` (cli_video.py) | usage, missing-argument, `--output=json` and text-mode tests | 14 passed -> 8 failed, 6 passed |
| 2b unexpected exception | `except Exception as exc:` -> `except ZeroDivisionError as exc:` (cli_video_review.py) | the RuntimeError and OSError tests | 2 passed -> 2 failed |
| 2c Ctrl-C | `except KeyboardInterrupt:` -> `except ZeroDivisionError:` (cli_video_review.py) | the Ctrl-C test | 1 passed -> 1 failed |
| 2d exit_code on review documents | `_finish` writes the review without `"exit_code": code` (cli_video_review.py) | ok / dry-run / partial / failed + envelope tests | 5 passed -> 4 failed, 1 passed |
| 3 file-size boundary (B's D2) | `size > MAX_POINTER_FILE_BYTES` -> `size > MAX_POINTER_FILE_BYTES + 1` (stages/video_pointers.py) | the exact 32768 / 32769 test | 1 passed -> 1 failed |

Two survivors were found on the first pass and fixed by strengthening the tests, then re-run red: the parser file-size branch (a single 32 KB line was also caught by the note limit) and the CLI stat branch (the parser caught the same file after it was read).

Not falsified (no code on this cut to mutate): TV7.1 `authorize()` (compare permission by group name), TV9 flows, TV10 route permissions. The TV7.3 mutation "redaction after the call" has no clean single hunk (the frame source is lazy); the nearest equivalents are the F1/P4 row above and the cycle-0 rows on branch `wave/g2-review-core`.

## Owner decisions
1. **New `ApprovalKind.VIDEO_REVIEW`.** The per-use provider approval store did not exist on master, and no gate file records the 2026-10-07 Gemini approval. It reuses the signed `RunApproval` machinery: `autotester approve <project> --kind video_review --target <provider id> --scope ... --max-actions <calls> --expires <date>`; `target` is the provider id (for example `gemini`), `max_actions` bounds model calls. A separate approval record type is the alternative; say if you want that instead.
2. **Exit code 1** is used for usage errors (unknown project or source, bad `--redact`, unreadable pointer file, provider unavailable, a non-finite or negative `--max-cost`) and for a `failed` review; the contract names only 0, 2, 3 and 4. In json mode each of these writes `{"status": "usage_error" or "refused", "reason", "exit_code"}`.
3. The CLI permission seam is `local_operator_permission()` (the CLI runs as the machine's operator, who holds the `.env` and the approval key). It is the single place to wire `video.upload` through `authorize()` when T-204 lands.
4. **P3 - the approval is a per-run ceiling, never consumed.** The contract (TV7.2) says "a recorded per-use approval". What is built: one signed approval for (project, provider) with `max_actions = N` is checked against each run's planned call count and is NOT decremented or marked used, so it stays valid until it expires and authorises any number of reviews, each within N calls. Total spend is therefore bounded only by the per-review cap and the expiry date. No code was changed. Owner to rule: keep the per-run ceiling, or consume the approval on use (needs a used-actions counter on the approval record).
5. **P4 - `langchain-fallback` fans out to several vendors.** The approval `target` is the provider id, so approving `langchain-fallback` approves every vendor behind it, and the frames go to whichever answers. `gemini` and the other single-vendor ids are unaffected. No code was changed. Owner to rule: refuse `langchain-fallback` for `ingest review`, or require the approval to name the vendor.
6. **P9 - the contract contradicts itself and does not carve out the HELD parts.** TV9 (contract line 108 vs 111) says flows are written to the FlowSpec and expand runs without approval, while `require_reviewed` refuses non-APPROVED and D-073 forbids changing it; TV7.1 gates on `video.upload` while `docs/spec.md:169` says `project.edit + video.view`; the contract's out-of-scope list omits the T-204/T-205 parts. This manifest covers the BUILT SUBSET ONLY (TV1-TV8 and the stored-review half of TV10 on the CLI). T-197 cannot close on this cut: TV7.1, TV9 flows, the TV10 routes, `ingest run --pointers` and the live acceptance remain open (see HELD).
7. **What is gitignored and why (F1).** `projects/*/reviews/` - the whole tree: the work dir `reviews/<rid>/` (redacted copy, frames, verify stills), the stored review `reviews/<rid>.json` and any Markdown/HTML export beside it. Contract TV10: "The review is stored under the project through `core.paths` (never beside the source video, never in the repo)". Only the work dir is ever media; the stored review is scrubbed text, but it quotes the recording and the repo is public, so the contract line is read literally and nothing the review writes is committable. Nothing is lost: the work dir is deleted after every run anyway. Frames are NOT kept after the calls (the stored review holds no media and TV10 does not ask for frames); a frame that was sent was cut from the copy that passed the window check.
8. **P5 - pointer limits are a builder choice (the contract names none): the checker is asked to rule.** `MAX_POINTER_LINES = 100` non-blank lines, `MAX_POINTER_NOTE_CHARS = 500` characters per note or free pointer, `MAX_POINTER_FILE_BYTES = 32768` (32 KiB) per file, named constants in `src/autotester/stages/video_pointers.py`. A violation is a pointer error (exit 2, zero provider calls, the whole list shown; an oversized file is refused unread as one error). Checker evidence was a 3,000,000-character pointer sent as a 3 MB prompt and 60k timed lines taking 46 s.
9. **HUMAN_GATE-REQUEST carried from checker A:** approve the helper modules (`media/redacted.py`, `stages/video_review_plan.py`, `video_review_items.py`, `video_review_prompt.py`, `video_review_render.py`), `prompts/video_review_v1.md` and `ApprovalKind.VIDEO_REVIEW` with a D-entry, or direct the folds A suggested (`media/redacted.py` into `media/frames.py`, `video_review_plan.py` into `video_pointers.py`; both fit under 300 but are different jobs).

10. **Fix cycle 2 - click usage errors exit 1.** The contract names exit 2 for pointer errors, so a malformed flag may not share it. `ingest review` now exits 1 for every usage error, in text mode too (stderr shows click's usage line and message; stdout stays empty). The one case that stays text in the json family: **a bare `--output` with no value anywhere in argv names no format**, so no document is written (stderr note, exit 1, empty stdout); the same holds for an `--output` value that is neither `text` nor `json` (the cycle-0 behaviour). That is a decision, not an oversight: guessing json for a caller who did not ask for it would put a document on the stdout of a human terminal. Typer 0.27 vendors its own click (`typer._click`), so the hook catches `typer.exceptions.TyperException`, the public base of those errors; `import click` would not have matched. No other `cli*.py` command turns usage errors into JSON today (searched `src/autotester/cli*.py` on this branch and master), so there was no pattern to reuse; `ReviewCommand` is the one mechanism, on this command only.
11. **Fix cycle 2 - statuses and the `exit_code` key.** New json statuses: `internal_error` (exit 1; an exception the command did not expect) and `interrupted` (exit 130). Every document, review and plan included, carries `exit_code` equal to the process's real code; for a review it is an envelope key added by `_finish` (0 ok and partial, 1 failed, 4 unreadable), not a `VideoReview` field. A hard kill (taskkill /F, CTRL_BREAK) still runs no Python `finally` and leaves the work dir until the next run of the same review id (B's low PROPOSED-ISSUE: a cleanup-on-kill hardening, outside the repair list, not touched).

## HELD (nothing guessed)
- **TV7.1 permission through `authorize()`** and **TV10 view/export routes** (`video.view`, 404 vs 403, the pointer form and stored-review page, a Run control hidden from users without `video.upload`): need T-204 (`authorize()`, not on master) and T-205 (`ui/routers.py`, not on master). `ui/routes_video_review.py` was NOT created. HTTP 422 for pointer errors waits with it.
- **TV9 flows**: "expand runs over a DRAFT-only video spec without human approval" contradicts `stages/review.py::require_reviewed` (which `expand` calls and which refuses anything not APPROVED), and D-073 says changing `require_reviewed` is NOT authorized here ("a separate L unit"). The review path also produces no flows today (`ReviewReply` carries a summary and items only). Left unbuilt; needs an owner decision on which unit relaxes the expand gate and how flows reach the FlowSpec. Only the "no baseline to compare" phrase is built.
- **`ingest run --pointers <file>`**: not built. Wiring pointers into the vision ingest prompt needs `stages/ingest.py` (at 300 lines) and the TV9 flow semantics; an option that accepts the file and ignores it would be a lie. `ingest review --pointers` is the working path.
- **Live acceptance** (3 redacted Navnit videos against the 13-row oracle) is the checker's Mode D evidence and is refused without a recorded approval; the builder ran no live model call and no browser.
- **R65 Linux/Ubuntu run** of these tests: not run (Windows host); reuse the T-204 / T-203 Ubuntu run if it covers them.
- The record naming the g2 helper modules (F8): a D-entry written by the coordinator (see Owner decisions 9).

## Open items for the checker
- `tests/test_cli_video_review.py`, `tests/test_cli_video_review_exits.py`, `tests/test_video_review_cleanup.py` and `tests/test_video_review_redaction.py` need ffmpeg (they skip whole without it); they ran here, 0 skipped.
- The fix-cycle-1 P5 limits are a builder choice for the checker to rule on (Owner decisions 8); P6-P8 of checker A are left alone, as instructed.
- The system never writes "confirmed" as a status: only the human status echo ("... (set by a human)") exists, unchanged from the carried render.
- No `qa/issues.jsonl` row appended.

## Live browser evidence
Not UI-touching on this cut — no route, template or browser step changed. Changed paths: .gitignore, src/autotester/media/redacted.py, stages/video_pointers.py, src/autotester/cli_video_review.py, cli_video.py, cli_crawl.py, schema/enums.py, browser/secrets.py, stages/video_*.py, tests/test_cli_video_review.py, tests/test_video_review_guards.py, tests/test_cli_advice_resolves.py, docs/MAP.md (plus the carried g2 files).
