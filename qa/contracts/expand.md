# Contract — EXPAND stage (T-070)

**Covers:** goal task T-070. **Owner:** /checker. **Criticality:** HIGH — the product's
differentiator; the whole taxonomy exists so a suite covers more than the happy path anyone
would write by hand.
**Depends on:** `core-invariants.md` (all), `review-gate.md` (R1-R4 — the gate this stage must
respect), `ingest.md` (I1-I5 — produces the `FlowSpec` this stage consumes).

## Purpose

Turn one reviewed `Flow` into a set of `Case`s — one per taxonomy class that genuinely applies,
never fewer than the flow's own happy path. This is the plan's differentiator: "a systematic
matrix derived from observed UI," not a hand-written happy-path test. T-070's own goal-task note:
"the differentiator: >=12 cases for the login flow, >=1 per applicable taxonomy class."

## Criteria

### X1 — Refuses a FlowSpec the review gate still blocks, and only that one
`stages/expand.py::expand` applies the review gate first (`review-gate.md` R5, which is the rule). A
spec the gate still blocks raises `FlowSpecNotReviewed` before any provider call is made, never
silently expanding a guess: a spec at `NEEDS_EDIT`, and a spec with an unreconciled flow (any
`Flow.kind` unset). A **reconciled** spec at `DRAFT` is not blocked: it expands exactly as at
`APPROVED` (D-070 item 2; amended 2026-10-11). *Verify:* the R5 tests in `review-gate.md`, run through
`expand`. *Until the R5 code unit lands, `expand` still calls `require_reviewed` unconditionally, so
the original behaviour (any `DRAFT` raises) is what the code does today.*

### X2 — Every flow gets its own happy-path case, unmodified
`expand_flow` always produces exactly one `CaseClass.HAPPY`/`CaseKind.BEST` case whose steps are
the flow's own observed steps, verbatim — no model call needed or made for this one case.

### X3 — Class applicability is deterministic where confident, model-judged where not
`applicable_classes(flow)` decides input/auth classes (`INPUT_EMPTY`, `INPUT_BOUNDARY`,
`INPUT_UNICODE_OVERSIZE`, `AUTH_WRONG_CREDS`, `AUTH_EXPIRED_SESSION`) purely from the flow's own
step shape (does it have a `FILL` step; does a `FILL` step reference a `{{SECRET:KEY}}`) — no
model call decides whether these apply. Every flow is additionally asked about the 8 universal
classes (`DOUBLE_SUBMIT`, `BACK_REFRESH_MIDFLOW`, `NETWORK_OFFLINE_SLOW`, `SERVER_ERROR`,
`VIEWPORT_MOBILE`, `LOCALE_I18N`, `CONCURRENT_TAB`, `DEEPLINK_UNAUTH`) via the model, which may
decline with an empty `ExpandedSteps.steps` (D-004: the rule decides only where it can be
certain; everywhere else, a judgment call is spent, not guessed).

### X4 — A model's decline produces no case, never an empty/broken one
When `ExpandedSteps.steps` is empty, `expand_flow` produces no `Case` for that class — it never
constructs a `Case` with zero steps or synthesizes placeholder steps to force one.

### X5 — Never a real secret literal invented for a "wrong" value
The prompt (`src/autotester/skills/expand-case/SKILL.md`, loaded by `stages/expand.py:17`
`SKILL_NAME = "expand-case"` via `load_skill_prompt` - T-175, D-043; the old
`prompts/expand_case_v1.md` no longer exists) instructs the model to invent an obviously-fake value
for a "wrong credential" scenario, never something resembling a real secret, and to leave a
genuinely-needed real credential's `{{SECRET:KEY}}` placeholder untouched — this is a prompt-level
instruction (verified by reading the prompt file), not independently enforced in code this cycle
(no case produced by this stage is ever run against a real product without going through
`execute.py`'s existing credential boundary regardless).

### X6 — The stage has a door, and every refusal behind it writes nothing
A stage nobody can reach is an absent feature, not a slow one. `expand` is called from **two real
entry points a person uses**, not only from tests:

- `cli.py::expand_cases` (`autotester expand <project>`) — loads and persists through
  `ProjectStore`, and `expand()` itself still does not persist (this contract's no-fire list keeps
  that the caller's job).
- `ui/routes_learn.py::generate_cases` (`POST /projects/{slug}/cases/generate`) — the button, shown
  **only** when `expand` would accept the spec (today: `review.status is APPROVED`; after the
  `review-gate.md` R5 unit: also a reconciled `DRAFT`), so X1 is enforced by the interface as well as
  by the code behind it.

The button's four refusal paths — **no FlowSpec**, **an unapproved FlowSpec** (X1 reaching the
UI), **no provider with credentials**, and **a `ProviderError` raised mid-generation by an
otherwise-available provider** (AT-264: the one step that runs *after* every gate check passes) —
each return a themed page carrying a next action, never a raw `{"detail": …}` blob, and each
writes **zero** cases. A refusal that half-persists is worse than one that refuses, because the
operator cannot tell which of the two happened. The fourth path holds because `expand()` returns a
fully-materialized `list[Case]` (`stages/expand.py::expand`/`expand_flow`) — an exception raised
mid-loop propagates before the function returns anything, so `generate_cases`'s
`for case in cases: store.add_case(case)` never runs on a partial result.

**Evidenced, not asserted:** this criterion is only met while a real run of it exists. Against a
real approved `FlowSpec` and a live provider, the button produced **16 cases across 11 classes,
spanning all three `CaseKind`s (best / worst / edge)**, and `autotester expand` produced 10 across
10 classes — the first cases this stage has ever generated outside a `MockProvider`.


## No-fire list

- Actually persisting the produced `Case`s via `ProjectStore.add_case` — that's the caller's job
  (a future CLI command or pipeline orchestrator), not `expand()`'s.
- `Case.rubric_ref`/`script_ref` — left `None`; grading rubrics per expanded case are a future
  concern.
- Real live model calls in the default test suite — `tests/test_expand.py` uses `MockProvider`
  exclusively.
- Merging/deduplicating cases across multiple `expand()` runs on an updated `FlowSpec` — `Case`'s
  own content-addressed id (unchanged by this unit) already makes `ProjectStore.add_case`
  idempotent; this stage does not add its own merge logic on top.

## Amendment log (append-only; git history is the version)

- 2026-09-03 · init · contract created for T-070 — no contract existed before this cycle.

- 2026-09-09 · /checker (at241-cold-start unit, cycle 1) · **new criterion X6 added** — X1–X5 all
  described what `expand` does when called, and for the whole life of this contract **nothing called
  it**: `expand_flow` had no caller in `src/` or `scripts/`, and 50 of 52 cases across four real
  projects were `happy`. A contract that never asks whether a feature is reachable will pass a
  feature that is not. Routine, non-weakening (adds a criterion, softens none). Re-derived by this
  checker rather than read from the manifest, which had claimed the opposite was still true ("no case
  has yet been generated by the expander on a real product"): driving the **button in a real browser**
  against a live provider produced 16 cases across 11 classes with `best`/`worst`/`edge` all present
  (`qa/evidence/browser-at241-cold-start-2026-09-09-checker/report.json`), and `autotester expand`
  produced 10. All three refusal branches were exercised live and each wrote zero cases — including
  the provider branch, reached honestly by running a server whose root had no credentials. X1 was
  confirmed through the button, not merely in `expand()`: a `needs_edit` spec refused with a themed
  page and no cases. One residual filed rather than folded in: **AT-260** — `autotester expand
  --provider gemini` lets a `ProviderError` escape uncaught, dumping a full traceback and persisting
  nothing; the default `langchain-fallback` path is unaffected. AT-250's 50-of-52 measurement over
  the four REAL projects is untouched — this evidence comes from a synthetic project, and the
  taxonomy firing once does not retroactively populate suites that were never expanded.

- 2026-09-09 · /checker (at264-generate-error-boundary unit, cycle 1) · **X6 amended to name a
  fourth refusal path** — the criterion above listed only the three gate refusals; AT-264 added a
  fourth (a `ProviderError` raised by the model itself, after every gate check passes), and
  `qa/issues.jsonl`'s own checker-sweep filing of AT-264 already described this as a hole X6 did not
  cover. Routine, non-weakening: it adds detail to an existing criterion and softens nothing.
  Re-derived independently rather than read from the manifest: reverted the fix in a `git archive
  dc8acef` extract (never the live tree) back to the bare pre-fix loop and confirmed
  `tests/test_ui_learn.py::test_generate_when_the_model_fails_midway_is_refused_as_a_page_not_a_500`
  fails with the exact same `ProviderError` class `providers/gemini.py` raises in production, then
  confirmed it passes with the fix restored; read `stages/expand.py` to confirm `expand`/
  `expand_flow` return a fully-materialized list (not a generator), so no partial write is possible
  by construction, not merely by the test's luck. Went further than the manifest's disclosed gap
  ("needs monkeypatching a provider instance inside a running server process, which a black-box
  browser client cannot do"): setting `OLLAMA_BASE_URL` before starting a real `uvicorn` process adds
  an ollama tier to `LangChainFallbackProvider`'s chain with no code change, and driving the
  Generate button against it — first via a plain HTTP client, then via this checker's own
  Playwright-driven Chromium (the shared MCP browser's profile was locked by a concurrent session;
  launched an independent `playwright.chromium` instance instead of forcing it) — reproduced the
  *exact* AT-264 failure shape live end-to-end: a themed 400 HTML page, zero `cases.jsonl` writes,
  one explained console error (the page's own intentional 400 navigation, not a JS defect), and the
  three sibling routes (approve/request-edit forms, the requests page) unregressed
  (`qa/evidence/browser-at264-generate-error-boundary-2026-09-09-checker/report.json`). Also checked
  and confirmed safe: the interpolated `f"Generating cases failed partway through: {exc}"` message
  carries only `ProviderError`'s own text (a finish-reason label, a schema-mismatch summary, or —
  live — `ModuleNotFoundError: No module named 'langchain_ollama'`), never a raw API key or prompt
  content, across every `raise ProviderError(...)` site in `providers/gemini.py` and
  `providers/langchain_fallback.py`. See `qa/verdicts/at264-generate-error-boundary.md`.
- 2026-09-28 - routine (correct) - the criterion's prompt path updated from `prompts/*_v1.md` to the
  `skills/<name>/SKILL.md` the code actually loads. Cause: the T-175 skills migration (D-043) moved
  the three stage prompts and amended core-invariants C8, but the three sibling per-stage contracts
  were never updated - so a criterion that says "verify by reading the prompt file" named a file that
  does not exist, making it UNCHECKABLE rather than merely out of date. Verified: src/autotester/
  prompts/ now holds only agent_fix_v1.md and relitigation_v1.md, and each stage's SKILL_NAME comment
  records the old filename it replaced. No behaviour claim changed. **Changes-authorized:** this
  contract's prompt-location line + Amendment log (this entry). **Links:** AT-670; T-175; D-043;
  core-invariants C8.
- 2026-09-28 - CORRECTION (id only) - the entry above cites `AT-670`; the correct id is **AT-690**.
  AT-670 was already spent by the t191 remap the same day, so the sweep row collided with it and was
  renumbered into the checker's new block (AT-690..AT-709). No criterion, claim or verification line
  changes. Appended rather than edited because this log is append-only. **Links:** AT-690; AT-664.

- 2026-10-11 · owner-authorized (D-070 item 2) · **X1 reworded; X6's button condition follows it.**
  X1 required every `DRAFT` to raise; D-070 item 2 makes the DRAFT gate status-only for reconciled
  flows, so X1 now refuses only what `review-gate.md` R5 still blocks (`NEEDS_EDIT`, unreconciled
  specs). X2-X5 unchanged. The code (`expand.py:137`) still raises on every `DRAFT` until the separate
  R5 unit lands (D-073). **Links:** D-070; D-073; `review-gate.md` R5.
