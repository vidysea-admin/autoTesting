# Contract — run video (T-191, AT-587)

**Status:** ACTIVE (authored by /checker 2026-09-26 under D-048, written under D-050). Judges T-191's units.
**Feature:** a Playwright recording of one case's browser session, kept **only** when that
case's `Verdict.result` is `FAIL` or `INCONCLUSIVE` (never `PASS`), with secret inputs masked to
the same guarantee `EvidenceMixin.screenshot()` already gives screenshots, retained as the most
recent 20 such videos per project, deterministically pruned, surfaced in the report as a link.
**Covers:** goal task T-191 (`.goal/goal.json`, `done_check: uv run pytest tests/ -k video`).
**Deps:** `browser-and-secrets.md` B7 (screenshot masking, the guarantee this unit must match);
`core-invariants.md` C3 (single choke point), C5 (secrets never reach an artifact), C6 (evidence
stays a plain file, view over it), C7 (falsifiable checks + guard-sabotage); `report-export.md`
RE3, whose named video-link exception (D-050) this unit relies on. See "Blocking dependency"
below, now resolved.
**Grounding:** gate `qa/gates/meeting-run-video-scope.md`, answered **A**, retention 20, by Umesh
via AskUserQuestion, 2026-09-26; authorized by `docs/DECISIONS.md` D-048 ("meeting-run-video-scope
= A. Record video on FAIL or inconclusive only, keep the last 20, and mask secrets as in
screenshots."), which also names this contract as one the checker writes once T-191 exists.
Code seams: `browser/evidence.py:21-24` (`MASK_CSS`), `browser/evidence.py:29` (`EvidenceMixin.
screenshot`), `browser/launch.py:21` (`launch_options`, the dict Playwright's persistent-context
launch consumes), `browser/session.py:98-99` (the one call site that consumes `launch_options`
via `launch_persistent_context`), `browser/secrets.py:261` (`SecretStore.masked_field_keys`),
`core/redact.py:120` (`assert_no_raw_secrets`), `schema/run.py:15-24` (`Evidence`), `schema/run.py:
39-56` (`RawResult`, its `evidence` field at line 55), `schema/enums.py:129-135` (`Result`),
`schema/enums.py:138-145` (`EvidenceKind` — no `VIDEO` member exists yet; this unit adds one),
`stages/run_case_pipeline.py:101` (`run_and_grade_case`) and `:117` (`run_and_grade_case_
resilient`) — the two places a case's `RawResult` and its `Verdict` are both in scope together,
`core/paths.py:78` (`runs_dir`) and `:110` (`run_dir`), `stages/report_export.py:187-199`
(`_case_section`, where evidence becomes report markup; the `figures` loop at line 198 filters
strictly on `EvidenceKind.SCREENSHOT`, so a `VIDEO` item added to `RawResult.evidence` is invisible
there until new code reads it), `stages/parallel_run.py:38` (`DEFAULT_PER_CONTEXT_MB`) and `:45`
(`_RAM_FLOOR_MB`) — the existing RAM-budget precedent this unit's video cost joins, and
`stages/parallel_run.py:106-125` (`plan_parallel_run`), whose `per_context_mb` parameter is
already a caller-supplied number, not a hardcoded one — recording overhead can be added there
without a new mechanism, `media/frames.py:25` (`extract_frame(video, t_s, out_png) -> bool`, the
existing ffmpeg seam this unit's masking proof reuses).

## Blocking dependency (RESOLVED 2026-09-26 by D-050)

`report-export.md` RE3 says: *"`export_html` produces a single `.html` file with every screenshot
embedded as a base64 data URI — opening the file needs no other file on disk, no server, no
network."* That is a stated, tested invariant (`RE5`'s neighboring "self-contained" property),
and a linked (not embedded) video violates it as written — the exported HTML would then need the
video file to sit alongside it to be useful. This contract does not relitigate the "never embed a
15–20 minute video as base64" decision (that is the right call — RE3 was written before video
evidence existed and did not anticipate it) — but only the checker may amend `report-export.md`
(core-invariants.md, "Owner: /checker" on every contract), and that amendment needs to exist,
with its own amendment-log row, stating RE3's self-contained guarantee is scoped to screenshots
and inline text, with video as a named, dated exception (the same shape as core-invariants C5's
D-034 owner-only-editor exception). **Resolved 2026-09-26 (D-050):** RE3 now carries the named video-link exception, so V8 is gradeable.
Any further change to RE3 is checker-only; the maker's plan must not attempt one.

## What it is

Today a case's evidence is screenshots, DOM notes, URLs, and network/DB observations
(`schema/enums.py::EvidenceKind`, `schema/run.py::Evidence`) — nothing continuous. The 2026-09-25
counselor-tool meeting asked for a 15–20 minute walkthrough a human can watch; the gate answer
scoped it to **failure evidence, not a demo reel**: a video is recorded per case, and is kept only
when the run did not PASS. Because the verdict is not known until `grade()` runs — after the
video has already been captured — "kept only for FAIL/INCONCLUSIVE" is enforced as a **post-grade
prune**, at the one seam that already sees both a `RawResult` and its `Verdict` together:
`stages/run_case_pipeline.py::run_and_grade_case` (and its resilient sibling). This is the same
shape B7 already uses for screenshots — masking happens at capture, not after — but video is a
*continuous* capture, so the masking guarantee has to hold for the whole recording, not one point
in time, which is the hard new part this unit adds over screenshots.

## Plan-level decisions (the maker's `docs/plan.md` must record these; the checker does not
pre-decide them, and re-opens the gate answer above if it tries to)

The PLAN gate must name, before any code:

1. **Mechanism: `record_video_dir`/`record_video_size` on the persistent context, not
   `browser.tracing`.** Playwright `Tracing` captures DOM snapshots/network/console for
   debugging, not a watchable video; the gate asked for something "a human can review," and
   `launch_persistent_context` (`browser/session.py:98-99`, options built in `browser/launch.py::
   launch_options`) already supports `record_video_*` the same as `new_context`. Tracing is out of
   scope for this unit (see No-fire list).
2. **Codec/container and size.** Playwright's own encoder (`.webm`) unless the plan states and
   justifies an alternative; a concrete `record_video_size` (e.g. scaled below `DEFAULT_VIEWPORT`,
   `browser/launch.py:16`, not full 1366×850) and the disk-per-case reasoning at 15–20 min length.
3. **Recording lifetime and prune call site.** Recording starts with the case's context/page and
   stops when the case's steps finish, before grading; the file lives under `projects/<slug>/
   runs/<run_id>/` (`core/paths.py:110`) from the moment it is written, never a scratch location;
   the plan names the exact function inside `stages/run_case_pipeline.py` that performs the prune.
4. **Deterministic "most recent 20" ordering.** `Evidence` (`schema/run.py:15`) carries no
   timestamp of its own — the plan states what breaks the tie deterministically (e.g. `Run.
   started_at` then `run_id`, then case order within the run) and which store/index query supplies
   that ordering without scanning every run directory on every case.
5. **The persistent-mask mechanism.** `MASK_CSS` (`browser/evidence.py:21-24`) is injected via
   `page.add_style_tag` right before each screenshot — a point-in-time call. The plan states
   whether the video equivalent is (a) injecting the same style once, permanently, at page/context
   creation, so it is already active for every frame the recorder ever captures, or (b) some other
   mechanism — and why, given `[data-autotester-secret]` is attribute-driven, not per-screenshot.
6. **RAM/disk budget.** Named below (V6) as a hard requirement; the plan states the concrete
   numbers it will assert, consistent with `stages/parallel_run.py::plan_parallel_run`'s existing
   `per_context_mb` parameter (already caller-supplied, not hardcoded — recording overhead can be
   passed there without new mechanism) and `_RAM_FLOOR_MB` precedent, or forces serial recording
   the way `write_policy=ALLOW_WRITES` already forces serial execution (PR3, `parallel-run.md`).
7. **Report-export exception.** Already resolved by the checker (D-050, RE3 amendment); the plan
   only cites it.

The plan must **not** re-open: recording scope (FAIL/INCONCLUSIVE only — gate answer A, not B or
C), retention count (20 — the gate answer's own number), or whether masking must reach the same
guarantee as screenshots (CLAUDE.md's credentials boundary, restated verbatim in the gate answer).
Any of those three needs a new HUMAN_GATE, not a plan footnote.

## Criteria (V1–V8)

### V1 — A video is recorded per case, transiently, before the verdict exists
Every case run through `run_and_grade_case`/`run_and_grade_case_resilient`
(`stages/run_case_pipeline.py:101,117`) produces exactly one video file under `projects/<slug>/
runs/<run_id>/` (`core/paths.py:110`) for that `case_id`, written by the session's
`record_video_*` context option — no second recorder, no per-step manual capture.
**Verify:** a fixture case run once produces exactly one `*.webm` (or the plan's chosen
container) file matching the case, non-empty, before grading returns. Sabotage: delete the
`record_video_dir` option from `launch_options` — the test must flip from pass (file exists) to
fail (no file exists), the guard-sabotage proof C7 requires.

### V2 — A PASS keeps no video; FAIL/INCONCLUSIVE does; BLOCKED defaults to keep
After `grade()` returns a `Verdict`, the video is deleted (or never persisted past a scratch
path, per plan-decision 3) when and only when `verdict.result is Result.PASS` (`schema/enums.py:
132`). `Result.BLOCKED` (line 134) is not named by the gate answer as a keep condition; until an
amendment says otherwise, it is treated as "keep" — the conservative default. **Verify:** three
fixture cases graded PASS/FAIL/INCONCLUSIVE → PASS's video file is absent afterward; FAIL's and
INCONCLUSIVE's are present. Sabotage: invert the `is PASS` check to `is not PASS` — the
PASS-video-absent assertion must flip to failing.

### V3 — Masking is persistent for the whole recording, not point-in-time
The masking CSS (or the plan's chosen equivalent per plan-decision 5) is active for every frame
the video recorder captures of a field `SecretStore.masked_field_keys()` (`browser/secrets.py:
261`) names, from the moment that field exists on the page, not only at the instant a screenshot
is taken. **Verify:** drive a fixture page, type a **FAKE** secret value (never a real one — this
test never touches `.env`) into a field marked `mask_in_screenshot`, record video through the
interaction, then query the field's computed style via `page.evaluate` at three points (before,
mid-keystroke, after) — all three must show the masking CSS applied. Sabotage: apply the mask
only inside `screenshot()` (as today), never at page-load — the mid-keystroke check must flip
from passing to failing, since nothing screenshot-triggered runs between keystrokes.

### V4 — The stored video cannot be used to recover the fake secret (equivalent guarantee to B7)
This is the credential boundary CLAUDE.md and the gate answer both name directly. Pixel-perfect
frame OCR is impractical here (no OCR dependency exists in this repo) — this contract accepts a
narrower, still-real pair of checks:
- **(a) Byte-level (necessary, not sufficient):** the raw fake-secret string does not appear
  anywhere in the recorded video file's bytes. A compressed video encoding a masked field
  correctly would also never contain the raw string this way, so this check alone proves little
  — it is a cheap first gate.
- **(b) Frame-level, using the existing ffmpeg seam:** `media/frames.py::extract_frame` (line 25)
  is reused, not reimplemented (C3), to pull 3+ frames spanning the interval the fake secret was
  typed. Each extracted PNG is diffed against a frame of the same field rendered *unmasked* (a
  throwaway comparison render, never a real recording) — the masked frame's pixels in that
  field's bounding box must visually differ from the unmasked one there, beyond incidental
  background overlap.
**Verify:** the V3 fixture, video bytes grepped for the fake value → zero matches; 3 extracted
frames during the typed interval visually differ from the unmasked-comparison render in the
field's region. Sabotage: type the fake secret into a control field the mask CSS does **not**
target — check (a) must then find the raw value, or (per C7's zero-failure clause) the manifest
records that this host's encoder happened to compress even the unmasked glyphs away and reports
the sabotage INCONCLUSIVE rather than silently passing.

### V5 — Retention: the most recent 20 per project, pruned deterministically
After any prune runs, a project has at most 20 kept videos across all its runs, chosen by the
plan's stated deterministic ordering (plan-decision 4) — never by filesystem `mtime` alone (two
videos written in the same second are not distinguishable by mtime). **Verify:** a fixture
project seeded with 25 kept videos across several runs, in known creation order → after the
prune, exactly the 20 most-recent-by-the-stated-order remain and the 5 oldest are gone; a second
prune on the same state is a no-op. Sabotage: swap the ordering key for `mtime`, force two
videos to an identical mtime with a known-different logical order — the test must fail to select
the right 20, or (per C7's zero-failure clause) the manifest records the timestamp collision did
not occur on this filesystem and reports the mutation INCONCLUSIVE, not a false kill.

### V6 — RAM/disk budget is a stated, measured number, not a guess
Recording concurrently-running cases costs resident memory per browser context beyond
`DEFAULT_PER_CONTEXT_MB` (`stages/parallel_run.py:38`). The plan's stated numbers (plan-decision
6) must be exercised, not merely written down: either (a) `plan_parallel_run`'s `per_context_mb`
argument (`stages/parallel_run.py:106-125`) is called with a larger value when recording is on,
so parallel fan-out does not oversubscribe RAM, or (b) recording forces serial execution the way
PR3 already forces it for `write_policy=ALLOW_WRITES`, with a stated reason. **Verify:** a test
asserts `plan_parallel_run`'s output (fewer concurrent slots, or a forced serial fallback with the
stated reason) changes between recording-on and recording-off for the same measured-free-RAM
input. Disk: a test asserts a stated per-video ceiling (duration or file-size cap, consistent
with plan-decision 2) is enforced — a case running longer than the cap either stops recording at
the cap or the plan names the alternative, never records unbounded. Sabotage: hardcode
`per_context_mb` so the recording-on path never differs from recording-off — the "output changes"
assertion must flip to failing.

### V7 — Single choke point (C3): one recorder, one pruner
The only occurrence in `src/` of a `record_video_dir`/`record_video_size` option is inside
`launch_options` (`browser/launch.py`), consumed at its one call site (`browser/session.py:
98-99`) — no stage independently starts a second recording of the same session. The only
function in `src/` that deletes a video based on a verdict is the one named in plan-decision 3,
inside `stages/run_case_pipeline.py`. **Verify:** `grep -rn "record_video" src/` returns matches
only in `browser/launch.py`; `grep -rn` for that prune function's deletion call outside its own
definition returns nothing. Sabotage: add a second, ad-hoc `record_video_dir` call in a stage
file — the grep-count assertion must flip from one match-site to two.

### V8 — `EvidenceKind.VIDEO`, linked in the report, never embedded (RE3 exception, D-050)
`schema/enums.py::EvidenceKind` (currently lines 138-145, no `VIDEO` member) gains
`VIDEO = "video"`. A kept video is recorded as `Evidence(kind=EvidenceKind.VIDEO, path=<run-
relative path>, masked=True, ...)` on the case's `RawResult.evidence` (`schema/run.py:55`) — the
same envelope every other evidence kind uses, not a new field on `RawResult`.
`stages/report_export.py::_case_section` (line 187) renders a video row as a link (`<a
href="...">`) next to the case's screenshots (whose `figures` loop, line 198, filters strictly on
`EvidenceKind.SCREENSHOT` and so needs new code to surface video at all) — never base64-embedded
the way `figures` embeds PNGs, because a 15–20 minute recording bloating a portable HTML file the
way a screenshot does not is the "not embedded if large" case names. The RE3 exception this depends on landed under D-050. **Verify:** a fixture `RawResult` carrying one
`VIDEO` evidence row, exported via `export_html` → the output HTML contains an `<a>` tag whose
`href` is the video's path and contains **no** `data:` URI for that path; `export_excel`'s
existing row shape is unaffected. Sabotage: base64-embed the video path the way `figures` does
for screenshots — the "no `data:` URI for the video path" assertion must flip to failing.

## Out of scope / ignore

- Option B or C from the gate (always-record, a stitched end-to-end walkthrough, or "not now") —
  the gate answered **A**; raising either against this contract relitigates an answered HUMAN_GATE
  (D-048).
- Playwright `Tracing`/trace viewer integration — named explicitly in plan-decision 1 as the
  rejected mechanism for this unit's "watchable video" requirement.
- OCR-based frame verification — V4 states plainly why pixel-diff, not OCR, is this unit's
  accepted proof; adding OCR for stronger proof is a scope increase this contract does not ask for.
- Retention count other than 20, or scoping retention per-run instead of per-project — both fixed
  by the gate answer's own number and wording.
- CI/scheduled-trigger interaction with video (`Trigger.CI`/`SCHEDULE`) — out of scope the same
  way `execute.md`'s own no-fire list excludes trigger wiring.
- The video codec/size numbers themselves, once the plan states and justifies them under
  plan-decision 2 — second-guessing "should it be 480p or 720p" without a stated, measured reason
  is a style nit, not a criterion violation.

## No-fire list

- A sabotage for V4(b) that reports INCONCLUSIVE because this host's webm encoder happens to
  compress the control field's glyphs away too (C7's zero-failure clause explicitly allows this;
  it is not itself a finding against the unit).
- A sabotage's exact byte-for-byte frame diff threshold — the criterion requires a real, checkable
  visual difference, not a specific pixel-count tolerance the manifest must justify to the digit.
- A test file/function name that does not literally contain "video" — as long as `uv run pytest
  tests/ -k video` (T-191's `done_check`) collects and runs it, the exact name is not a finding.

## Amendment log (append-only; git history is the version)

- 2026-09-26 · init · contract authored by /checker (D-050), from D-048's fold-in of the
  `meeting-run-video-scope` gate answer (Answered A, retention 20, Umesh via AskUserQuestion,
  checker session, 2026-09-26) and goal task T-191 (AT-587). No prior draft existed for this
  feature; nothing amended. Grounded in `browser/evidence.py`, `browser/launch.py`,
  `browser/session.py`, `browser/secrets.py`, `core/redact.py`, `schema/run.py`, `schema/enums.py`,
  `stages/run_case_pipeline.py`, `core/paths.py`, `stages/report_export.py`,
  `stages/parallel_run.py`, and `media/frames.py` as they exist as of this date. V8's dependency on a
  `report-export.md` RE3 exception was resolved in the same change (D-050). The maker's `docs/plan.md`
  (PLAN gate, not yet written) must record the seven plan-level decisions named above before any
  code lands against V1–V7.
