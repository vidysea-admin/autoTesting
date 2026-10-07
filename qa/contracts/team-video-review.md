# Contract — team video review with human pointers (T-197, Group 10 unit G2 `t197-pointers-review`)

**Covers:** goal task T-197, plan unit G2. **Owner:** /checker. **Status:** ACTIVE (2026-10-07).
**Criticality:** HIGH. **TV7 is CRITICAL** (it gates outward-facing model spend and what leaves the machine).
**Serves:** intent O8 (primary), O3, O4, O7, O9, O15; spec R32-R38, plus the cross-cutting R63 and R65; D-070 part 2, D-072.
**Depends on:** `ingest.md` (I8 narration is ground truth, I9), `video-learning.md` (VL1, VL1c, AT-134), `consent.md`,
`core-invariants.md` (C5, C7, C11), `auth.md` (permission keys), `hosting.md` (HO30-HO33 own upload and Drive intake).
**Unit split:** this contract is the pointer file, the review itself and its persistence. Video upload and Drive intake are G3 (T-198,
`hosting.md` HO30-HO33). Share links, access requests and comments are G9. Reconciling video flows against the crawled product KG is
T-166 / `reconcile.md` (D-073). The permission engine is T-204; this unit calls `authorize()` and adds no key.
**Source of the rows:** the maker's proposal `.work/plan-g10/contract-proposal-T-197.md` (TV1-TV15), folded and tightened here.
Rows TV11-TV15 of that proposal are folded into the rows below as marked, not dropped (see the amendment log).

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

## Amendment log (append-only; git history is the version)

- 2026-10-07 · init · contract created for T-197 / G2 from the maker's proposal (`.work/plan-g10/contract-proposal-T-197.md`), spec
  R32-R38, intent O8-O15, plan unit G2 and D-072. Row mapping to the spec: R32 TV1, R34 TV2, R33 TV3+TV4, R35 TV5+TV6, R36 TV7+TV8,
  R37 TV9, R38 TV10. Permission ruling: running a review is gated by `video.upload`, viewing by `video.view`, no new key (R63).
  Folded rather than dropped: proposal TV11 (CLI exit codes) into TV1/TV3/TV7 and the cross-cutting list; TV12 (unreadable media) into
  TV3; TV13 (bounded spend, `partial`) into TV7; TV14 (oracle measurement) into "Live acceptance"; TV15 (Windows and Ubuntu, R65) into
  the cross-cutting list. Tightened: TV3 allows 0-5 items (no padding) and `failed` status; TV5 requires temporal overlap for a quote;
  TV7 adds the permission check, a no-op-blackout check and approval scoping; TV10 id includes the redaction windows and the id keeps
  human-set item status.
