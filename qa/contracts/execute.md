# Contract — EXECUTE stage (T-040, T-045)

**Covers:** goal tasks T-040, T-045. **Owner:** /checker. **Criticality:** MEDIUM — the stage
every later regression run depends on, but not itself user-facing yet.
**Depends on:** `core-invariants.md` (all), `browser-and-secrets.md` (B1-B9, all already built).

## Purpose

Run one `Case`'s steps against a real, already-started `BrowserSession` and produce a
`RawResult` — what happened, evidence-first, with **no PASS/FAIL judgement**. Judgement is
`grade.py`'s job (T-041), given only the rubric and this stage's evidence. This is the "executor
only observes" line in the T-040 goal task note, made literal.

## Criteria

### E1 — The executor observes and records; it never grades
`stages/execute.py::run_case` never assigns PASS/FAIL/INCONCLUSIVE. Its outputs are the four
`Outcome` observations: `COMPLETED` (every step ran without raising), `ERRORED` (an exception
mid-step), `BLOCKED_HITL` (a step needed a secret the project does not have — see E3), and
`ASSERTION_FAILED` (D-032/AT-540: a step's declared expectation — or an `Action.ASSERT` step's
declared expectation — deterministically did not hold at settle time; an observation, never a
grade). `Action.ASSERT` evaluates the step's declared expectation (`url`/`visible_text`/
`absent_text`/`dom_asserts`) through `browser/assertions.py` and records one
`assert <field>: met|unmet (<detail>)` DOM evidence item per evaluated field; after any step
whose `expected` declares checkable fields the expectation is evaluated post-settle the same
way. A bare ASSERT (nothing declared) stays harmless. `network` stays observer-derived and
`visual_signal` stays the judge's (no-fire). The executor never grades: a declared expectation
either held or did not — recorded as evidence — and `grade.py` still owns every verdict (C7:
an `ASSERTION_FAILED` run reaches the judge, which weighs the recorded facts and may disagree
with a wrongly-authored expectation).

### E2 — Every step composes existing session primitives
`run_case` dispatches each `Step.action` to a `BrowserSession` method
(`goto`/`click`/`fill`/`select_option`/`upload`/`wait_for`) — it never touches
`session.page` directly for a mutating action. New `BrowserSession` methods added for this unit
follow the existing pattern: one action, evidence recorded via `_record`, secret-safe (any value
that looks like `{{SECRET:KEY}}` goes through `SecretStore.resolve`, never logged raw). A
screenshot is captured after every step, labeled with the step's order and action, so a human or
`grade.py` can review the run frame by frame.

### E3 — A missing secret blocks for a human, it does not fail the run
If resolving a step's `{{SECRET:KEY}}` value raises `MissingSecret` (the project declared the key
but `.env` has no value — the OTP/2FA case B8 anticipates), `run_case` returns
`Outcome.BLOCKED_HITL` with `hitl_prompt` naming what is needed, not `ERRORED`. Any other
exception (selector not found, navigation refused, timeout, …) is `ERRORED` with `error` naming
the exception type and message — never an unhandled traceback out of `run_case`.

### E4 — RawResult is complete and persisted
The returned `RawResult` carries `case_id`, `outcome`, `duration_s`, and every `Evidence`
recorded during this case — never evidence from an earlier case that reused the same session
(D-044, AT-577) — already redacted/masked per B4/B7 (`run_case` does not re-implement masking).
`ProjectStore.save_result(run_id, result)` writes it to
`projects/<slug>/runs/<run_id>/<case_id>.json`; `ProjectStore.save_run(run)` writes the `Run`
envelope to `.../runs/<run_id>/run.json`. Both round-trip through `read_json`/`write_json` (C6 —
no new file format).

### E5 — write_policy is respected
`run_case` performs exactly the actions in `case.steps` — it never invents an extra click,
submit, or navigation. A `write_policy=READ_ONLY` project is protected by never running a case
whose steps were authored to mutate data, which is an EXPAND-stage (T-070) and human-review
(T-065) concern, not this stage's; `run_case` itself has no branch on `write_policy` because it
has no way to add or remove actions from what the case already specifies.

### E6 — A case's execution condition is enacted, or the case did not run (D-045)
A case whose `case_class` names an execution condition (`VIEWPORT_MOBILE`, `LOCALE_I18N`) runs under that
condition: a mobile-sized viewport, or the non-default locale. If the executor cannot enact it, the case is
recorded as not run, with the reason. It never yields a PASS from a run at the default desktop viewport or
locale. (Current gap tracked by AT-581: `browser/launch.py:30` hard-codes 1366x850.)

## No-fire list

- Vision/LLM-based judgement of `visual_signal` (belongs to `grade.py`, T-041).
- The agent fallback path (write→run→read→edit a generated script) — that is T-080; this unit is
  the script-first / direct-steps path only.
- `EvidenceKind.DB` / read-only Mongo assertions — that is T-045's own follow-on once
  `PATHLYNKS_MONGO_URI` is declared as a `SecretRef`; T-040 does not need it to close.
- Retrying a step automatically on transient failure (no retry logic required yet).
- CI/scheduled triggers (`Trigger.CI`/`SCHEDULE`) — `Run.trigger` exists in the schema already;
  wiring a trigger source is a later phase.

## Amendment log (append-only; git history is the version)

- 2026-09-03 · init · contract created for T-040 (execute stage), the follow-on named in
  `browser-and-secrets.md`'s amendment log ("belongs to a future `execute` contract, not B1-B9").
- 2026-09-04 · routine · recorded the `at044-entry-case-profile-isolation` fix (AT-045, ledger
  F-030): `run_case` now calls the new `BrowserSession.settle()` (networkidle + 500ms grace,
  both independently exception-suppressed) after a CLICK step, before its screenshot, so
  evidence capture sees the post-transition state rather than mid-transition. E2 ("composes
  existing session primitives") and E5 ("never invents an extra click/submit/navigation") both
  hold unchanged — `settle()` is a passive wait called through `session.settle()`, not a new
  step. Checker-PASSed cycle 1 (`qa/verdicts/at044-entry-case-profile-isolation.md`). Residual
  evidence-timing flakiness for pathlynks live reruns is tracked separately as AT-046 (open,
  medium) — not fixed by this amendment. Found by sweep: shipped with zero contract-side trace
  until now (AT-048).
- 2026-09-06 · routine · recorded the `at053-navigate-settle` fix (AT-053, ledger row AT-053):
  `run_case` now calls `session.settle()` after a NAVIGATE step too, not only after CLICK
  (AT-045's fix covered CLICK only) — a real live-site run against a brand-new production URL
  came back a false FAIL because the navigate screenshot was captured before the page rendered
  (blank white frame; the click step afterward was fine). E2/E5 hold unchanged for the same
  reason as the AT-045 amendment above — `settle()` remains a passive, exception-suppressed wait,
  not a new step. Checker-PASSed cycle 1 (`qa/verdicts/at053-navigate-settle.md`), re-verified
  live against `https://www.vidysea.com/erp` (3 consecutive real PASSes, real Gemini multimodal
  grading). Found unrecorded by this sweep — same contract-side-trace gap class as AT-048; this
  entry closes it for AT-053.
- 2026-09-22 · routine (fold-in of D-032, authorized there) · **E1 superseded** per
  docs/DECISIONS.md D-032 (AT-540, Umesh's 2026-09-22 assertions-first approval): the executor
  now evaluates each step's declared deterministic expectation (`Action.ASSERT` is real,
  `absent_text`/`dom_asserts` are evaluated, `Outcome.ASSERTION_FAILED` is added as a fourth
  observation — never a grade) and records per-field `assert <field>: met|unmet` DOM evidence
  via `browser/assertions.py`. C7 unchanged: grade.py still owns every verdict, and an
  `ASSERTION_FAILED` run reaches the judge with its recorded facts (D-032 point 4 is this
  entry; the one-sentence docs/ARCHITECTURE.md Execution-model addition lands with it).
  Note: AT-540's cycle-1 check (`qa/verdicts/at540-assertion-layer.md`) is FAIL on
  capability-coverage rows (dom_asserts / ERRORED-precedence / C7-for-assertions unisolated)
  plus three deleted E3 tests — the behaviour is in and verified; the checks lag the claims.
- 2026-09-25 · amendment (authorized by D-044) · **E4 scoped to the case**: "every `Evidence` the
  session recorded" → "every `Evidence` recorded during this case". The serial route reuses one
  session across cases; `run_case` returns only the evidence recorded from its own start index,
  and `browser/assertions.py::_network_met` reads the same scope (AT-577, AT-578). Proven live in a
  real browser by `qa/verdicts/at576-577-serial-runs.md` cycle 2 PASS (merged 8e50efc). Reported
  stale by the builder via qa/feedback-inbox.md (at576-577 cycle 1 entry).
- 2026-09-26 · amendment (authorized by D-045) · **E6 added** — execution-condition classes
  (VIEWPORT_MOBILE, LOCALE_I18N) must be enacted or reported not-run, never PASS on a default-condition run. Tightening
  only. The current code violates it (AT-581, high): the viewport is hard-coded and no locale is set. Source: the
  checker's goal-coverage review of the 2026-09-25 counselor-tool meeting.
