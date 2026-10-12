# Build brief: t197-video-pointers (goal task T-197, plan unit G2 `t197-pointers-review`)

Written 2026-10-11 by the readiness pass (read-only; nothing was built). Self-contained.
Contract: `qa/contracts/team-video-review.md` (TV1-TV10 + cross-cutting + live acceptance, ACTIVE 2026-10-07). Spec: R32-R38, R63, R65. Intent: O8 primary (`docs/features/team-loop/intent.md`, `docs/intent.md`).
Dispatchable: YES, as a CONTINUATION of the existing branch `wave/g2-review-core`. The pure core is built and has a cycle-0 checker verdict; what is missing is wiring that needs T-205 (route registration, path headroom) and T-204 (`authorize()`).

## 1. Policy and tier

- `Policy-Version: proportional-verification/2026-10-10.9`
- **Tier L.** Triggers: (a) data egress to an external model (TV7 is CRITICAL in the contract: redaction before egress, per-use approval, bounded spend); (b) permission gate on `video.upload` through `authorize()` (auth); (c) writes a stored artifact under the project (TV10).
- `Dual check: required`, trigger `security src/autotester/stages/video_review.py:210` on branch `wave/g2-review-core` (`gate()` is the first statement of `run_review`; the redaction-before-egress path is `src/autotester/media/redacted.py:51` `redact_video` and `:90` `verify_blackout`). The earlier slice manifest said "not required" because that slice had no permission code; this brief covers the wiring, which does.
- Persona walk: required (section 9).

## 2. Root and base

- Root: `D:/autoTesting`. Current `master` = `3a16616cf2c99a63c8d763150a1ca6410dfc0acc`.
- **Continue on the existing branch `wave/g2-review-core`** (worktree `D:/autoTesting/.worktrees/g2-review-core`, clean, tip `faa02786`). Reasons: it holds the whole pure core (14 source files, 5 test files, a manifest at `Fix cycle: 1`, a cycle-0 verdict `qa/verdicts/g2-review-core.md` = CONTINUE-NEEDED with findings F1-F8, fix cycle 1 already committed in `faa02786`). Rebuilding it would repeat about 2400 lines and lose the verdict binding.
- State against master (measured): 3 commits ahead, 57 behind. `git merge-tree` against master shows one textual conflict, in `docs/MAP.md` (generated: take master's and rerun `uv run autotester map`). `core/paths.py` merges textually but ends at **306 lines (limit 300)**, so doctor fails until T-205 frees headroom.
- How to bring it current: MERGE master into the branch (do not rebase: the cycle-0 verdict binds HEAD `f3587d5d`; rewriting commits orphans it). Do this only after `wave/t205-g10-headroom` has merged to master. Until then the builder can start on the parts that touch none of the shared files (CLI body, TV9, tests, flows) in the same worktree.
- Branch status for the record: manifest `qa/manifests/g2-review-core.md` and verdict `qa/verdicts/g2-review-core.md` exist ONLY on the branch (master has neither). No cycle-1 verdict yet. Not landed. Under D-080 item 1 it reaches master only by the exact commit a checker PASS reviewed.

## 3. Acceptance criteria (verbatim from `qa/contracts/team-video-review.md`)

## Purpose

A human reviewer hands AutoTester a recording plus approximate timestamps and two or three free-text pointers. AutoTester returns a flow
summary and a short confirm-list (`time | screen | seen | suggestion | severity`), each item citing the exact second. Pointers raise
attention and never hide the rest of the recording; the review names every span nobody looked at; narration is quoted, never invented;
and nothing that was redacted reaches a model.

## Vocabulary (fixed here so criteria are falsifiable)

- **Pointer line** = one line of a pointer file or one form row. Time forms: `12:30`, `1:02:03`, `~12:30` (approximate, same second,
  flagged `approx`), `12:30-14:00` (a window), each optionally followed by `| free text`. A line with only free text and no time is a
  **free pointer** (kept, applies to the whole recording). The unit may accept at most three free pointers per review; a fourth is
  refused with a reason, not dropped.
- **Base depth / pointer depth** = frames per minute of recording analysed outside / inside a pointer window. Pointer depth is strictly
  greater than base depth; both are named constants in `stages/video_pointers.py`.
- **`not_reviewed`** = the list of `[start_s, end_s]` spans of the recording with no analysed frame.
- **Redaction window** = `[start_s, end_s]` on one source, set by a human on the review request (and persisted with the review).
  Blackout for frames, mute for audio. The model sees only the **redacted derivative**, never the original path.
- **Item origin** = one of `pointer`, `narration`, `visual`, `suspected`. The system never writes the word "confirmed" for an item; a
  human confirms (intent O8 calls the list a *confirm-list*).
- **Permission for this unit (R63, no new key):** *running* a review spends model money and moves frames off the machine, so it is gated
  by `video.upload` on the video's project (scope `own`, `assigned` or `all`, resolved by `authorize()`). *Viewing or exporting* a stored
  review needs `video.view` (any scope the engine grants). Group 10 adds no key; if either needs another key it is a contract gap to
  raise, not a reason to invent one.

## Criteria

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

## Live acceptance (evidence for TV2-TV5, reported as numbers, not a pass threshold)

On the three **redacted** Navnit videos, with a per-use approval already recorded for the cheap model (Gemini, recorded 2026-10-07),
the unit reports: recall against the 13 high-severity rows of `.work/pathlynks-dev-videos-oracle-2026-10-07.md`; items with no human
counterpart, labelled unconfirmed and never counted as false positives or true positives; time-to-review; and the `not_reviewed` spans.
The claim wording is "fixture-proven" or "measured on 3 videos", never "matches a human". No numeric pass threshold exists until Umesh
answers intent Q3; a missed oracle row is reported, not hidden. A live run is the checker's Mode D evidence under
`qa/evidence/browser-t197-*-checker/`; it is refused if TV7's approval is missing. Persona walk (when the UI exists): **admin** opens a
video, types pointers, runs the review and reads the rows in <= 4 steps, and understands which spans were not reviewed without being
told; a **tester** with the video shared sees the stored review but no Run control.

## Out of scope / ignore

- Upload, zip and Drive intake and their size limits (`hosting.md` HO30-HO33, G3); share links, access requests, timestamped comments
  and comment-to-pointer promotion (G9); the permission engine and groups (`auth.md`); the run queue and concurrency (T-203).
- Reconciling video flows against the crawled KG and the "another possibility" alternatives (`reconcile.md`, D-073).
- The sheet/tracker and the bug loop adapter for video issues (T-199, G6/G8).
- Model quality beyond the structural guarantees here: no criterion says the model found the right bugs. That is measured, not asserted
  (Live acceptance), and the oracle threshold is gated on intent Q3.
- Wording, colours and layout beyond the TV10 export and the persona-walk steps.

## No-fire list (must NOT happen)

- No frame or audio from a redaction window, and no original (unredacted) path, ever reaches a Provider.
- No Provider call without `video.upload`, a per-use approval for (project, provider), and a within-cap plan.
- No pointer line silently dropped or clamped; no unreviewed span unnamed; no item without a real second and a registered source.
- No quote that is not a verbatim transcript substring; no "confirmed" written by the system; no "nothing was said" for silence.
- No secret in the review, an export, a log or a prompt.
- No new permission key, no new dependency, no `*_v2` / `*_new`; files <= 300 lines, functions <= 50, one-job docstring per module
  (D-072 item 2 authorizes the new modules `schema/video_pointer.py`, `schema/video_review.py`, `stages/video_pointers.py`,
  `stages/video_review.py`, `cli_video_review.py`, `ui/routes_video_review.py`; the checker judges them against the doctor rules).

## 4. What exists and what is missing

Exists on branch `wave/g2-review-core` (NOT on master). Line counts are from the branch tip:

| Module | Lines | Job / key symbols |
|---|---|---|
| `src/autotester/stages/video_pointers.py` | 103 | pointer grammar parser (TV1), count identity, whole error list |
| `src/autotester/stages/video_review.py` | 279 | `run_review` :200 (keyword-only required `gate` and `secrets`; `gate()` is the first statement :210), `preview_review` :101, `review_id` :89, `load_review` :97, `_merge_human_status` :112, `provider_cost` :77, `ReviewRefused` :65, `PointerErrors` :69 |
| `src/autotester/stages/video_review_plan.py` | 131 | frame plan, spans, preview; base grid 4 frames/min, pointer grid 12/min (named constants, TV2) |
| `src/autotester/stages/video_review_items.py` | 150 | model reply to validated items (TV3-TV6) |
| `src/autotester/stages/video_review_prompt.py` | 111 | prompt build; `visible_transcript` drops speech touching a redaction window (F1 fix) |
| `src/autotester/stages/video_review_render.py` | 67 | Markdown and HTML with identical item ids (TV10) |
| `src/autotester/media/redacted.py` | 130 | `redact_video` :51, `verify_blackout` :90 (start/mid/end samples), `has_audio` :40 |
| `src/autotester/schema/video_pointer.py`, `schema/video_review.py` | 46, 157 | typed, `extra="forbid"` |
| `src/autotester/prompts/video_review_v1.md` | - | placeholders SOURCE_ID DURATION FRAME_TIMES POINTERS NARRATION MAX_ITEMS |
| `src/autotester/core/pricing.py` (28 lines on master) | edit | `estimate_cost_conservative` (unpriced label charged the dearest known rate; F2 fix) |
| `src/autotester/core/paths.py` | edit | `ProjectPaths.review_path`, `review_work_dir` |
| tests | - | `tests/test_video_pointers.py`, `test_video_review.py`, `test_video_review_gates.py`, `test_video_review_redaction.py` (real ffmpeg; skipped without it), `tests/video_review_fakes.py`; 84 passed at cycle 1 per the manifest |

Verdict cycle 0 (CONTINUE-NEEDED), findings and their state in the cycle-1 commit: F1 transcript text from a redaction window reached the Provider (fixed), F2 spend cap inert for default-labelled providers (fixed), F3 narration slack 1.0 s vs "overlaps" (fixed, now 0.0), F4 Markdown had no item ids (fixed), F5 blackout verification midpoint-only (fixed), F7 `secrets` optional (fixed), **F6 open**: `overlapping()` / `_quote_verbatim` do not consult `narration_state`, so a `Transcript` with `engine="none"` or `"unreadable"` that still carries segments yields `origin=narration` (unreachable from the sidecar loader today; guard it anyway), **F8 open**: TV2 vocabulary puts the depth constants in `stages/video_pointers.py` but they live in `video_review_plan.py` (move them or ask the checker to amend), and a record naming `media/redacted.py` plus the four helper modules is owed (a D-entry, written by the coordinator, not the builder).

Exists on master and must be reused (not rebuilt):
- `src/autotester/cli_video.py` (291 lines): typer app `ingest` (registered `cli.py:31`); commands `register` :35, `list` :60, `prep` :81, `frames` :118, `run` :182 (`run_cmd`), `analyze` :227, `map` :275; helpers `_require_source` :152, `_merge_into_reviewed` :161.
- `src/autotester/stages/ingest.py` (300 lines, at the cap): `register_source` :101, `persist_ingest` :236, `ingest_video` :251, `load_sidecar` :186, `RECORDING_SUFFIXES` :74, `FlowSpecApproved` :41.
- `stages/analyze_video.load_transcript`, `stages/merge_flowspec.py::merge_flowspec` :108 (225 lines), `stages/expand.py::expand` :133, `stages/review.py::require_reviewed` :43 (D-073: do not weaken), `schema/media.py::Transcript` :41.
- `ui/routes_video.py` (75 lines) serves run videos only; there is no per-source video page and no review route.

Missing (the gap to each criterion):
- TV1 CLI/route halves: `ingest run --pointers <file>` and `ingest review` with exit 2 on pointer errors (Provider never called), 3 approval or permission missing, 4 source unreadable, `--output json` valid on stdout with logs on stderr, `--dry-run` printing the plan. HTTP 422 on the route.
- TV3 exit-4 mapping for `unreadable`.
- TV7 permission (`video.upload` via `authorize()`; needs T-204, which is NOT on master) and the per-use approval for (project, provider). No store or type for a per-use provider approval exists on master (`ApprovalKind` in `schema/enums.py:166` has only read, crawl, adversarial, live_case). Where the 2026-10-07 per-use Gemini approval is recorded: unknown (the contract says "recorded 2026-10-07"; no gate file under `qa/gates/` names it; `docs/DECISIONS.md` D-070/D-071 do not carry it). The gate callable is the seam: the builder wires it to whatever `authorize()` and the approval record are, and until T-204 exists TV7.1 stays HELD and the unit cannot close.
- TV8 beyond the branch: nothing new, but re-run for the new CLI/route output.
- TV9: write review-derived flows to the FlowSpec as `DRAFT` with `source_id`, narrated intent and provenance, keep every flow, `expand` over a DRAFT-only spec still generates cases, "no baseline to compare" phrase when no product KG exists, never edit an approved flow. Not started.
- TV10: viewing and export routes with `video.view` (404 for an invisible project, 403 for a visible one lacking the action); the stored-review view on a video page.
- Live acceptance on the 3 redacted Navnit videos against the 13-row oracle (`.work/pathlynks-dev-videos-oracle-2026-10-07.md` exists). This is the checker's Mode D evidence and is refused without TV7's approval; the builder does not run it.
- Linux/Ubuntu run record of these tests (R65), reusing T-204's/T-203's Ubuntu run if it covers them.
- The independent `senior-software-engineer` review and the dual check.

## 5. Files the builder will touch

Product files:

| Path | New / existing | Lines now |
|---|---|---|
| all 14 files in the table above | new on master (exist on the branch) | see table |
| `src/autotester/core/paths.py` | existing | 300 on master (branch edit adds 6; ends over the cap unless T-205 freed room) |
| `src/autotester/core/pricing.py` | existing | 28 |
| `src/autotester/cli_video.py` | existing | 291 (room for about 8 lines: hook only) |
| `src/autotester/cli_video_review.py` | new | - (D-072 item 2 names it) |
| `src/autotester/stages/ingest.py` | existing | 300 (hook only, net zero lines, or the delegation lives in `cli_video.py`) |
| `src/autotester/ui/routes_video_review.py` | new | - |
| `src/autotester/ui/routers.py` | existing after T-205 | - (the `video_review` stub is filled by appending the real router; no edit to `ui/app.py`) |
| flow-writing for TV9 | the maker's choice among `stages/merge_flowspec.py` (225) or the review stage | unknown; edit in place, do not duplicate `merge_flowspec` |
| `docs/MAP.md` | existing, generated | regenerate with `uv run autotester map` only |

Test files:

| Path | New / existing |
|---|---|
| `tests/test_video_pointers.py`, `tests/test_video_review.py`, `tests/test_video_review_gates.py`, `tests/test_video_review_redaction.py`, `tests/video_review_fakes.py` | new on master (exist on the branch) |
| CLI tests (exit codes 2/3/4, `--output json`, `--dry-run`) | new, name unknown, for example `tests/test_cli_video_review.py` |
| route tests (permission matrix, 422, 403 vs 404, export parity) | new, for example `tests/test_ui_video_review.py` |
| TV9 flow tests (`expand` over a DRAFT-only spec, no-baseline phrase, approved flow untouched) | new, for example `tests/test_video_review_flows.py` |

## 6. Test scope

```
uv run pytest tests/test_video_pointers.py tests/test_video_review.py tests/test_video_review_gates.py tests/test_video_review_redaction.py
uv run pytest <the new CLI, route and TV9 test files named above>
uv run pytest tests/test_ingest.py tests/test_ingest_real_cli.py tests/test_ingest_persist.py tests/test_ingest_transcripts.py tests/test_merge_flowspec_cli.py tests/test_cli_surface.py
uv run ruff check src tests scripts
uv run autotester doctor
```

Symbols removed or renamed: none planned (additions only). `ingest run` gains an option; existing callers of `["ingest", "run", ...]` that must keep passing unchanged: `tests/test_ingest_real_cli.py:68,87,98,115,129,228,246,261`, `tests/test_ingest_transcripts.py:111,156`, `tests/test_merge_flowspec_cli.py:86,105`. `git grep -ln cli_video -- tests`: `tests/test_cli_advice_resolves.py`, `tests/test_ensemble_honesty.py`, `tests/test_merge_flowspec_cli.py`. The redaction test file needs ffmpeg; if absent it skips, which is not evidence for TV7.3 (record whether ffmpeg ran).

## 7. Reachable test cases (happy path first)

- TV1: a reviewer pastes a pointer file with `12:30`, `~12:30`, `12:30 | note`, `12:30-14:00`, `1:02:03` and two free pointers into `ingest run --pointers` / the form: all parsed, run proceeds. Then the bad inputs: `14:00-12:30`, `99:99`, a time past the recording's duration, a negative time, an unparsable line, a fourth free pointer, a BOM, Windows `\r\n`: each comes back with its 1-based line number, the CLI exits 2 / the route answers 422, the Provider call count is 0, and `len(parsed)+len(errors)` equals the non-blank line count. Mutation: `continue` on a bad line.
- TV2: fake Provider records frame times; with zero, one and three pointers the with-pointers set is a superset of the no-pointer set; pointer-depth frames outnumber base-depth; analysed spans plus `not_reviewed` partition `[0, duration]`; the summary names the unreviewed spans in words.
- TV3/TV4: fake Provider replies with 2 valid items (review says fewer than 4 found), 5, 9 (5 shown, 4 in `overflow`), one malformed item (to `rejected`), non-JSON (status `failed`), a hallucinated second (99999, -3) and an unknown `source_id` (to `rejected`, absent from HTML and Markdown), and a zero-length, corrupt and audio-only file (status `unreadable`, CLI exit 4).
- TV5/TV6: real quote kept as `narration`; fake quote, case-changed quote and a quote from a far segment downgraded to `suspected`; `engine=none` says "no narration on record", `unreadable` says "narration unreadable", speech elsewhere says "no narration at this moment"; none says "nothing was said"; the system never writes "confirmed"; transcript file hash identical before and after. F6 case: a `Transcript(engine="none")` that carries segments must produce no `narration` item.
- TV7: one run per refusal with `provider.calls == 0`: no `video.upload` (403, or 404 for an invisible project), no per-use approval for this (project, provider) (an approval for another project or provider does not count), redaction no-op (blackout that is a copy), cap reached (`partial`, leftover spans listed), `--dry-run` (plan only, zero calls). The fake Provider asserts no handed path is under `D:/pathlynks_videos/_original_unredacted/` and none is the original. Planted secret in a transcript segment and in pointer free text stays out of the Provider prompt.
- TV8: a canary in the transcript and in a pointer is absent from every file written, both exports and `caplog`.
- TV9: run the review on a source, then `expand` over the resulting DRAFT-only spec with no human approval: cases exist and every flow is present; with no KG the review says "no baseline to compare"; approve a flow by hand, re-run the review, the approved flow is byte-identical.
- TV10: run twice, one artifact and one id; mark an item `confirmed`, re-run, the mark survives; change one pointer, a new id; export Markdown and HTML and compare item-id sets; request as an Admin, as a Tester with the video shared (view yes, run control absent) and not shared (404).

## 8. Gate answers

- `qa/gates/plan-approved-g10.md`, final section, verbatim: `Approved -- Umesh, 2026-10-07 (chat), recorded as D-074.` It also records the assumption: "Review needs a per-project, per-provider approval before a video goes to a model."
- New modules: `docs/DECISIONS.md` D-072 item 2, verbatim: "New modules: yes to all. This covers ... the Group 10 split modules ... Every file stays at or under 300 lines with a one-job docstring, and the checker judges it." The checker's cycle-0 ruling 1 on the four helper modules and `media/redacted.py`: covered on the same reading, a record naming them is owed (F8).
- Per-use Gemini approval for the three Navnit videos: the contract says "recorded 2026-10-07"; the file that records it: unknown (not a `qa/gates/` file; `qa/feedback-inbox.md:5803` mentions Umesh's Gemini-flash ingest of the 3 videos). Do not treat it as an `Answered:` line. The live run is the checker's and is refused without TV7's approval.
- Intent Q3 (numeric recall threshold): unanswered per the contract; no pass threshold exists, recall is reported as numbers.
- Other gates (`drive-identity`, `email-sender-credentials`, `t199-first-live-write`, `t203-host-and-dns`): none applies.

## 9. UI surface and persona walk

- UI surface: yes (`ui/routes_video_review.py`: pointer form, Run, stored review view, Markdown and HTML export; the unreviewed-span summary; a Run control hidden from users without `video.upload`).
- `Persona walk: required (admin: opens a video, types pointers, runs the review and reads the rows in <= 4 steps, understands which spans were not reviewed without being told; tester: with the video shared sees the stored review but no Run control)`. Audience is `internal-tool`, 1-2 user types. Evidence under `qa/evidence/browser-t197-*-checker/`. Browser lane max 1; the builder runs no browser.

## 10. Dependencies and conflicts

Must land first:
- `t205-g10-headroom` for `core/paths.py` headroom and `ui/routers.py` (this unit needs +6 lines in `paths.py`; master's file is at 300) and the CLI conventions. Builder may start the non-shared parts earlier; the merge waits.
- T-204 (`authorize()`) for TV7.1 and the `video.view` / `video.upload` checks. Until it lands: the gate seam is built and tested with a fake, TV7.1 is reported HELD, and the unit cannot close the task. This is outside the three units in this readiness pass.

Shared files (one owner each):

| File | Also wanted by | Proposed owner |
|---|---|---|
| `core/paths.py` | T-205 (headroom), T-203, T-200 | T-205 frees room; T-197 adds its 6 lines after |
| `core/pricing.py` | T-202 (provider work on `codex/t202-completion` may touch it) | T-197 (small, additive); unknown conflict risk |
| `cli_video.py` (291) | T-198 (`fetch-drive` / zip command) | T-197 first (the `--pointers` option plus a registration hook of <= 4 lines), then T-198 adds its own <= 4 lines after rebasing; both put real code in their own new modules |
| `stages/ingest.py` (300) | none of the three need more than a hook | T-197 (net zero lines) |
| `ui/routers.py`, `ui/app.py` | T-205, T-204, every route unit | T-205 |
| `schema/project.py` | T-205, T-198 | not touched by this unit |
| `docs/MAP.md` | every unit | integrator regenerates at merge |
| `docs/ARCHITECTURE.md` | every unit | orchestrator, under one D-entry that names the section |
| `qa/manifests/g2-review-core.md`, `qa/verdicts/g2-review-core.md` | none | this unit (they live on the branch) |

Pending units that do NOT share files with this one: T-199 (`stages/issues.py`, tracker modules), T-200 (`schema/schedule.py`, scheduler), T-201 (delivery, `ui/project_view.py`), T-202 (providers; possible `pricing.py` touch), T-203 (runs/queue/settings), T-204 (auth).

## 11. Budget and process rules

- Check budget for tier L: 45 min wall clock per checker. Builder budget: unknown (no figure in the repo); the earlier slice took one session.
- The builder runs no full suite (the checker's one combined G-core run, then the orchestrator's pre-push full suite).
- Falsification only in a throwaway copy outside the bound tree; the 15 mutations of the cycle-0 verdict and the cycle-1 ones are the floor to re-run on changed criteria.
- Kill only PIDs you started. No real model call in any test; the only live model use is the checker's Mode D run with TV7's approval.
- Edit in place; no `*_v2.py` / `*_new.py`; files <= 300 lines, functions <= 50, one-job docstring, `extra="forbid"`; prompts are files (`prompts/video_review_v1.md`), all model calls through `providers.base.Provider`.
- Do not edit `qa/contracts/`, `docs/DECISIONS.md`, `.goal/goal.json`, `qa/issues.jsonl`. Update `qa/manifests/g2-review-core.md` (bump `Fix cycle`) rather than creating a second manifest.
- Use `git -C <worktree> ...`, never `cd X && ...`.
