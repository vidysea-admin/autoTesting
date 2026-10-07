# Contract — reconcile (video knowledge graph → product knowledge graph, no human gate)

**Status:** DRAFT (goes ACTIVE on the first checker PASS of this unit).
**Tier:** M (additive, default-valued schema fields that old files still load without a rewrite and a
new stage; no consent, credential, approval or deletion boundary changes. It becomes L only if the maker
adds a migration that rewrites stored FlowSpec files, or touches `review.py` — both are out of scope here).
**Policy-Version:** proportional-verification/2026-10-07.7
**Feature:** a reconcile stage that re-maps what each video taught (its screens, actions and the flow the
narrator says they are doing) onto the product knowledge graph (the crawl's screens and the FlowSpec's
screens), keeps every flow, and records where a video diverges from the ideal path as an "another
possibility" alternative.
**Covers:** goal task T-166 (the reconcile half; the eval compiler half is `eval-compiler.md`) and
**D-070 part 2** ("Video flows are reconciled by the system, not approved by a human").
**Grounding:** `docs/DECISIONS.md` D-070 (what, why, result); `qa/feedback-inbox.md` entry
"2026-10-07 · maker · D-070 part 2 reconcile design" (root cause + proposed RC1–RC10, folded in and
tightened below); `docs/intent.md` O1, O3, O4, O5, O7; `docs/spec.md` R2, R4, R6, R7, R16.
**Related (not restated here):** `ingest.md` I1–I7 (video → FlowSpec), `core-invariants.md` C1/C2/C3/C5/C7/C8,
`review-gate.md` (status only after D-070), `ui-flow-diagram.md` (consumes the flow kinds).
**Design home:** new module `stages/reconcile.py` — **needs Umesh's approval before it is created**
(inbox "Open for Umesh"). If he does not approve a new module, the maker proposes an existing file under
C3 instead; no criterion below names the file, only the behaviour.

## Why this exists (root cause, verified on the 38-screen / 4-flow DRAFT from the 3 Navnit videos)

1. Nothing binds a step to a screen: `ObservedStep` and `Step` have no screen field, so "step names do not
   resolve to screens" cannot be fixed downstream.
2. `ingest._to_flow` drops `narration`, `on_screen_text` and `exit_screen`, which is exactly the evidence of
   what the narrator says the flow is for (D-070: speech is evidence of intent).
3. Screen ids are model-authored (`Screen.id` is a content hash of `(name, signals)`), so one route got 3+
   ids and `merge_flowspec` treats each as a new screen.
4. `Flow.id` is a hash of the flow `name` only, so two same-named flows from two videos collide and
   `_new_flows` silently drops the second.
5. The only Pathlynks crawl is the school portal; counsellor/admin videos have no route overlap with it, so
   most video screens will legitimately be "new". That must be a reported outcome, not a failure.

## Criteria (RC1–RC14) — each judged on re-runnable evidence

Every criterion states `serves:` (intent outcome / spec requirement) and a falsifiable check. "Frozen
sample" = a redacted fixture checked in under `tests/fixtures/reconcile/` that is derived from the three
real Gemini ingests (38 screens, 4 flows); the maker freezes it, and the checker verifies it is non-trivial
(≥3 sources, ≥30 screens, ≥4 flows, at least one route that two videos share, at least two same-named flows).

### Schema and ingest

- **RC1 — a step carries an optional screen linkage.** *serves: O1, R2.* `schema/` gains an optional
  `Step.screen_id: str | None = None` (and the matching `ObservedStep.screen: str | None = None` that the
  vision prompt asks for); every new field has a default and `extra="forbid"` stays (C1), so a FlowSpec file
  written before this unit still loads unchanged. `_to_flow` resolves `ObservedStep.screen` through the same
  name→minted-id map it already uses for `entry_screen`. A step whose screen name cannot be resolved keeps
  `screen_id=None` and is **listed in the reconcile report** (step order, flow, source second); it is never
  dropped. *Check:* on the frozen sample, ≥95% of steps have a `screen_id` that `FlowSpec.screen()`
  resolves; the remainder appear in the report's `unresolved_steps`; a pre-unit FlowSpec fixture still
  loads and round-trips byte-identically.
- **RC2 — `_to_flow` stops dropping evidence.** *serves: O1, O3.* A produced `Step` preserves
  `ObservedStep.narration` and `on_screen_text` (new optional fields on `Step`), and a produced `Flow`
  carries `exit_screen` resolved through the same map as RC1. *Check:* an observation with narration,
  on-screen text and an exit screen on every step/flow round-trips through `ingest_video` with all three
  present and equal; an observation without them yields `None`, not `""` and not an invented string.
- **RC3 — narration is a quote, not a paraphrase.** *serves: O3, O7.* A narration kept on a step, or cited
  by the report, must be a substring of the transcript it came from (whitespace-normalised, case-folded)
  **or** is rejected and recorded as `narration_unverified` with the step left intact. Values pass
  `Redactor.scrub` before they are stored. *Check:* a step whose narration is not in the transcript is
  not stored as narration; a narration containing a seeded secret value is stored scrubbed (the raw value
  appears nowhere in the saved FlowSpec or report).

### Identity and matching

- **RC4 — one route, one screen id.** *serves: O1, R6.* Reconcile canonicalizes screen identity: screens
  whose templated `url_pattern` is equal (the same `core.urls.url_template` the crawler uses, ingest I7)
  fold to one canonical screen, and every step, `entry_screen` and `exit_screen` that pointed at a folded
  id is rewritten to the canonical id. No flow is left pointing at an id that no longer exists. Screens
  with no `url_pattern` are never folded on route alone. *Check:* a fixture where a model authored 3 ids for
  one route reduces to 1 screen and every reference follows; a dangling-reference scan over the whole
  FlowSpec finds none; two same-route screens with `url_pattern=None` stay two.
- **RC5 — matching signals and the fixed bands.** *serves: O1, O4, R6.* A video screen is compared with
  each crawl `ScreenNode` and each existing FlowSpec screen on three signals: route (templated URL), title,
  and element signature (the `(role, normalised-name)` set the crawl's `structural_signature` uses, here
  compared as a similarity of the video's `ui_elements`/`fields`/`signals`). The combined score is a pure
  function of those three, fixed in code, and bands are fixed: **≥0.8 `matched`, 0.5–0.8 `ambiguous`,
  <0.5 `new`** (0.8 is matched, 0.5 is ambiguous). Every match row records the three signal scores, the
  total, the band and who decided (`rules` | `judge`). *Check:* boundary fixtures at 0.80, 0.79, 0.50 and
  0.49 land in the stated bands; the thresholds exist in exactly one place (grep: no second literal).
- **RC6 — the judge handles ambiguity only, and cannot promote.** *serves: O3, O7.* The Provider `judge`
  is called **only** for screens in the ambiguous band, never when rules decide (`matched` or `new`). A
  judge confidence **<0.8 never yields `matched`**; it leaves the screen `ambiguous` (kept and flagged).
  A same-route decoy whose labels and elements are disjoint is never `matched` without the judge saying so
  at ≥0.8. A judge error or `Unsupported` leaves the screen `ambiguous` and reports it; it never raises
  out of reconcile and never silently becomes `new` or `matched`. *Check:* a counting mock provider shows
  0 judge calls on the frozen sample's rule-decided rows and exactly one per ambiguous row; the decoy,
  the low-confidence and the provider-error cases each end `ambiguous`.
- **RC7 — an unmatched video screen survives.** *serves: O4, O5.* A video screen scored `new` is kept in
  the reconciled FlowSpec marked `video_only` (a new optional `Screen` field, default `False`), still
  referenced by its flows, and counted in the report. Counsellor/admin screens that no crawl has reached
  are therefore reported, not lost, and never treated as covered by a crawl that did not see them.
  *Check:* every video screen is in exactly one of `matched | ambiguous | new(video_only)`; their counts
  sum to the number of canonical video screens.

### Flows: keep all, no gate

- **RC8 — no flow is dropped, even a same-named one.** *serves: O1, R7.* `len(flows_out) == len(flows_in)`
  for the union of video flows and existing FlowSpec flows. Flow identity includes the source, so two
  videos that both name a flow "Login" produce two flows with different ids (the `content_id` payload gains
  the source id; existing flow ids already in a saved FlowSpec are never rewritten). *Check:* the frozen
  sample's same-named flows both survive; merging the same flow set twice still adds nothing the second time
  (idempotent, see RC11); an existing flow's id is byte-identical before and after.
- **RC9 — every flow has exactly one kind and a stated basis.** *serves: O3, R7.* Each flow carries exactly
  one `kind` in `ideal | narrated | variant` and one `ideal_basis` in `crawl | modal | only` (new optional
  schema fields, with a default that keeps old files loading). `ideal_basis=crawl` means the ideal is the
  crawl path (the flow whose screens are the crawl's); otherwise `modal` means the most common video path
  (ties broken by earliest source id, then flow id, never by dict order); `only` means one path exists.
  *Check:* a crawl-overlapping fixture picks the crawl path as ideal even when a video path is more common;
  a no-crawl fixture picks the modal path; a tie resolves identically in 5 runs; no flow has two kinds or
  no kind.
- **RC10 — divergence is an "another possibility", not an error and not a gate.** *serves: O3, O4.* A
  video flow that diverges from the ideal path is kept as `kind=variant` with a recorded reference to the
  ideal flow, the first divergent step, and the video second (`source_ref`) plus a narration quote when one
  exists (RC3). Nothing in reconcile sets, requires or waits on a human approval; the produced FlowSpec's
  `review.status` is whatever it was and reconcile never reads it to decide anything (D-070: the review gate
  is a status only). *Check:* the report's "Another possibility" section lists each variant with its ideal
  flow, divergence step, video id + second and quote; its counts balance (`ideal + narrated + variant ==
  flows_out`); a spec with `review.status=DRAFT` reconciles exactly as one with `APPROVED`; grep of the
  reconcile module for `require_reviewed` / `ReviewStatus.APPROVED` finds none.

### Determinism, safety and shape

- **RC11 — deterministic and idempotent.** *serves: O2, O3.* Reconciling the same inputs (the video
  observations/FlowSpecs, the crawl nodes, the same mock provider script) twice gives byte-identical saved
  output (same ids, same order, same report); reconciling an already-reconciled FlowSpec with the same
  inputs changes nothing (no version bump, nothing re-ordered). Output order never depends on dict/set
  iteration or wall-clock time; timestamps are not part of the compared payload. *Check:* two runs produce
  equal bytes; a second run over its own output produces equal bytes; the judge is called 0 times on the
  second run over a fully decided fixture.
- **RC12 — model calls go through the seam; no secret and no original reaches a model.** *serves: O7,
  R16.* Every model call goes through `providers.base.Provider` (no direct SDK import in the new code);
  the judge prompt is a file (`skills/…/SKILL.md` via `load_skill_prompt`, never an inline string);
  `core.redact.assert_no_raw_secrets` runs over the full prompt text before every call; only redacted
  text and no unredacted original (transcript sidecar, screenshot, step value) is passed. *Check:* a
  seeded secret in a step value, a field and a narration is replaced in the captured prompt (or the call is
  refused) and the recording mock never sees the raw value; the reconcile module has no `import anthropic`,
  `google.genai` or `requests`/`httpx`; its judge prompt file exists on disk.
- **RC13 — tests are offline and unpaid.** *serves: O7, D-070 part 1 test guards.* Every reconcile test
  uses `MockProvider` and the frozen fixture; there is no network call, no browser launch, no real
  credential read and no paid model call. *Check:* the test files run green with sockets blocked and with
  `GEMINI_API_KEY`/`ANTHROPIC_API_KEY` unset; a test that imports a real provider class fails the check.
- **RC14 — design rules and scope hold.** *serves: C1, C2, C3.* New schema models and fields live in
  `schema/` with `extra="forbid"`; every touched or new file stays ≤300 lines and every function ≤50 lines
  (if `schema/flowspec.py` would pass 300 lines the maker splits a model family out, as D-014 did, rather
  than raising the cap); the module has a docstring naming its one job; no second definition of any class
  or public function name; no `*_v2.py`/`*_new.py`. **Out of scope and untouched:** `stages/review.py`
  `require_reviewed` and review-gate R1 — downgrading it to status-only is a separate L unit (protected
  test change) and a diff of this unit that touches either fails this criterion. `docs/ARCHITECTURE.md` and
  `docs/MAP.md` are updated only through their own authorized paths. *Check:* `uv run autotester doctor`
  exits 0; `git diff --stat` shows no change to `stages/review.py` or `tests/test_review*.py`.

## Verify (the checker re-runs these itself)

```
uv run pytest tests/test_reconcile.py tests/test_reconcile_schema.py tests/test_ingest.py tests/test_merge_flowspec.py tests/test_schema.py
uv run ruff check src tests scripts
uv run autotester doctor
```

No CLI `-q` on pytest (AT-503). The maker may add test files for this unit, but the two named above must
exist and must contain the RC checks; a PASS also needs a manifest that lists, per RC, the test node id
that proves it and for RC6/RC11/RC12 a sabotage line (break the behaviour, show the test goes red, per C7).

## Falsifiable sabotage the checker will try

- Make the judge return confidence 0.79 and assert the screen is not `matched` (RC6).
- Swap two videos' flow order and assert the output is unchanged (RC11).
- Rename a screen id in the input and assert the dangling-reference scan still passes (RC4).
- Give a step a narration that is not in the transcript and assert it is not stored as a quote (RC3).
- Delete one flow from the output and assert the balance check goes red (RC8/RC10).

## No-fire list (do not raise these as findings)

- That no crawl of the counsellor/admin roles exists: needs an Umesh-provided account, tracked as a gate;
  reconcile reports `new/video_only` for those screens by design (RC7).
- That the three Gemini ingests are re-run with a prompt that asks for a step `screen`: a paid re-run that
  waits on Umesh; fixtures stand in for it (RC13).
- That `review.py` still raises on an unreviewed spec: it is a separate unit (RC14).
- Eval generation from variants/the ideal flow: `eval-compiler.md`, not this unit.
- Rendering of the variants in the flow diagram UI: `ui-flow-diagram.md`.

## Amendment log (append-only; git history is the version)

- 2026-10-07 — created by the checker from D-070 part 2 and the maker's RC1–RC10 proposal. Changes from
  the proposal: determinism and quote-checking are separate criteria (RC11, RC3); added RC8 same-named flow id collision
  (found in `ingest._to_flow`, `Flow.id` is a hash of `name` only); added RC10's explicit "reconcile never
  reads the review status" check; the 0.8/0.5 bands are made boundary-testable and single-sourced (RC5).
