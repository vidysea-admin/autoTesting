# Contract — persona-ux-advisory (advisory UX/comprehension track, D-048)

**Status:** ACTIVE (authored by /checker 2026-09-26 under D-048, written under D-050). Judges T-190's units.
**Feature:** a `UserPersona` (role, tech comfort, locale, device) attachable to a project and/or a
case, plus a separate, severity-scored UX/comprehension findings pass per screen/case that is
**advisory only** — it never touches `Verdict.result` or any functional PASS/FAIL/BLOCKED/
INCONCLUSIVE line. Findings surface in the HTML/Excel exports as their own section, distinct from
failures.
**Covers:** goal task T-190 (AT-583 — no user-persona model; AT-584 — no UX/comprehension judging
on live runs). **Deps:** none (`deps: []` in `.goal/goal.json`).
**Grounding:** `qa/gates/meeting-user-persona-ux-judging.md` (Answered 2026-09-26, option A) ·
D-048 (`docs/DECISIONS.md` 2026-09-26, "meeting-user-persona-ux-judging = A. An advisory UX track
that never changes PASS/FAIL.") · `schema/verdict.py:15-22` (`Criterion`: "if it can be argued
about, it is not a criterion" — the line this unit must never cross) ·
`schema/verdict.py:79-113` (`Verdict` — the functional result this unit must leave byte-identical,
verified: the file is 113 lines and the class runs to its end) · `schema/run.py:15-25` (`Evidence`
— what a UX pass may read, never invent) · `schema/case.py:13-30` (`Case`'s identity/config fields,
including `rubric_ref` at line 30 — where a persona ref attaches per-case, by reference not
embedding) · `schema/portal_persona.py` (existing durable `PortalPersona`/PP1-PP6 pattern this
unit's persistence should match, not duplicate — see `qa/contracts/portal-persona.md`) ·
`providers/base.py:33-101` (`Provider` — the class, and its `see_video`/`act`/`judge` role methods
specifically — the only seam a UX-judging model call may go through; `record()` at line 106 and
`available()` at 103 are outside this range on purpose, they are not call seams) ·
`providers/base.py:165-189` (`load_skill_prompt` — the only way a prompt reaches a call) ·
`core/redact.py:43-144` (`Redactor` / `assert_no_raw_secrets` — the gate before any model call;
`assert_no_raw_secrets` itself is lines 120-144) · `browser/secrets.py:256-259`
(`SecretStore.guard_prompt` — the existing call-site pattern a UX prompt-builder must reuse, not
reinvent) · `browser/launch.py:16-18,21-47` (`DEFAULT_VIEWPORT`, `launch_options` — what "device" a
persona can honestly claim) · `stages/execute.py` E6 / `qa/contracts/execute.md` E6 (AT-581 — an
unenacted execution condition must not be claimed) · `stages/run_case_pipeline.py:101-148`
(`run_and_grade_case`/`run_and_grade_case_resilient` — the seam a UX pass attaches beside, never
inside) · `stages/report_export.py:187-281` (`_case_section` through `export_html`, i.e. also
covering `_failure_detail_html` at 219 — where a findings section must render, kept out of
`_failure_detail_html`'s own output), `export_excel:114-161` · core-invariants C1/C2/C3/C5/C7
(`qa/contracts/core-invariants.md`).

## What it is

Today AutoTester's judge is deliberately functional-only: `Rubric.criteria` are "checkable bar"s
(`schema/verdict.py:16`), and `Verdict.result` is the one line every later stage (report export,
regression gating, the goal ledger) trusts as ground truth. D-048/gate-A adds a second, parallel
judgment that never writes to that line: a `UserPersona` describes *who* is testing (role, tech
comfort, locale, device), and a UX pass — reading the same `RawResult.evidence` the functional
judge reads, run through `Provider.judge` (or a dedicated role) with its own skill prompt — emits
a list of severity-scored `UXFinding`s per case/screen (confusing copy, a hidden or unreachable
control, ambiguous navigation). The UX pass is a second reader of the same evidence, not a second
executor and not a second grader of the same question: `Verdict` stays exactly what `grade.py`
already produces, unexamined and unadjusted by anything this unit adds.

## Criteria (PU1-PUn) — each judged on re-runnable evidence

- **PU1 — `UserPersona` is a `schema/` Pydantic model, `extra="forbid"`, attachable at both
  levels.** A new module (e.g. `schema/user_persona.py`, following `schema/portal_persona.py`'s
  file-per-artifact pattern rather than growing an existing file past its 300-line cap) defines
  `UserPersona` with at minimum `role: str`, `tech_comfort` (a closed `Severity`-style enum in
  `schema/enums.py`, not a free string a `no_fire` list would have to keep re-explaining),
  `locale: str`, `device: str`. `Project` (or `Case`) carries an optional reference to a persona —
  attachment is by id/ref, mirroring `Case.rubric_ref`'s pattern (`schema/case.py:30`), not by
  embedding the whole model twice. (Falsifiable: instantiate `UserPersona(**{...}, extra_field=1)`
  → `ValidationError`, same as every other model in `schema/`; a `Project`/`Case` round-trips
  through `read_json`/`write_json` with a persona ref attached and reloads identically.)
- **PU2 — UX findings are a separate artifact, never a field on `Verdict` or `Judgment`.** A new
  model (e.g. `UXFinding`: `case_id`, `screen` or `step_order`, `severity` (S1-S3, reusing
  `schema.enums.Severity` — C3, not a second severity vocabulary), `finding`, `persona_id`) and a
  container (e.g. `UXReport`) are persisted at their own path under
  `projects/<slug>/runs/<run_id>/` (a sibling of `<case_id>.json`, not inside it) — `schema/
  verdict.py`'s `Verdict`/`Judgment` classes gain zero new fields. (Falsifiable: `git diff` on this
  unit's branch touches `schema/verdict.py` in no way that adds a field, method, or import related
  to UX/persona; `UXFinding`/`UXReport` live in their own module.)
- **PU3 — The functional verdict is byte-identical with or without the UX pass (the load-bearing
  property).** A test drives one fixture case through `run_and_grade_case` (or
  `run_and_grade_case_resilient`) twice against the same `RawResult` — once with the UX pass
  invoked immediately after, once without it ever being called — and asserts
  `verdict_a.model_dump_json() == verdict_b.model_dump_json()` (every field, including
  `criteria_met`/`criteria_total`/`failures`/`scoreboard`, not a spot check on `result` alone).
  (Falsifiable: a single-hunk sabotage that makes the UX pass mutate the passed-in `Verdict` object
  in place, or that threads a UX finding into `grade()`'s prompt/rubric, must turn this test red;
  reverting the sabotage turns it green again — C7's failing-first sabotage proof, recorded in the
  unit's manifest.)
- **PU4 — A persona is never a route to a softer or stricter functional criterion.** `Rubric`
  construction (`stages/run_case_pipeline.py::default_rubric`/`_rubric_for_claim`) and `grade.py`'s
  prompt-building (`build_grade_prompt`) take no `UserPersona` argument and reference no persona
  field — a search for `UserPersona`/`persona` inside `stages/grade.py` and
  `stages/run_case_pipeline.py`'s rubric-building functions returns nothing (confirmed empty on the
  current codebase: `grep -n "[Pp]ersona" src/autotester/stages/grade.py
  src/autotester/stages/run_case_pipeline.py` returns no matches today). (Falsifiable: the same grep
  must return no matches on this unit's branch; a sabotage that imports `UserPersona` into
  `_rubric_for_claim` and interpolates its `tech_comfort` into criterion text must be caught by a
  doctor rule or a test asserting the no-import invariant, not left to review alone.)
- **PU5 — The UX pass goes through `Provider`, with a prompt file, like every other model call
  (C8).** The UX pass calls an existing `Provider` role (`judge`, reusing `providers/base.py:90-101`,
  or a new role added the same way `ProviderRole` already enumerates vision/agent/judge in
  `schema/enums.py:172-175`) — it never constructs its own HTTP call to a model vendor. Its prompt
  text is loaded via `load_skill_prompt` (`providers/base.py:165-189`) from a new
  `skills/ux_judge/SKILL.md` (or equivalent existing-directory placement under `skills/`) — never an
  inline f-string. (Falsifiable: `grep -rn` for a raw `requests`/`httpx`/vendor-SDK call inside the
  UX-pass module returns nothing outside a `Provider` subclass; deleting the new `SKILL.md` file
  makes the UX pass raise `FileNotFoundError` at the `load_skill_prompt` call site, not silently
  fall back to an inline string.)
- **PU6 — The UX prompt passes the redaction gate before any model call (C5).** The UX-pass
  prompt-builder calls `SecretStore.guard_prompt` (`browser/secrets.py:256-259`) — or, where no
  `SecretStore` is in scope, `assert_no_raw_secrets` directly (`core/redact.py:120-144`) — on the
  fully-assembled prompt string, before the `Provider.judge`/role call, exactly where `grade.py`
  today builds its own prompt and hands it to `judge` unguarded-but-placeholder-only evidence.
  (Falsifiable: a fixture project with a fake secret bound to a `SecretRef`, a case whose evidence
  or persona `device`/`locale` string is contrived to carry the raw value, driven through the UX
  pass → `guard_prompt`/`assert_no_raw_secrets` raises before any `Provider` call is made; a
  sabotage that removes the guard call must make this test red.)
- **PU7 — Findings render in the exports as their own section, never merged with failures.**
  `stages/report_export.py::export_html`'s `_case_section` gains a UX-findings block that is
  visually and structurally distinct from `_failure_detail_html`'s output (a separate `<div
  class='ux-findings'>` or `<section>`, not appended into `.detail`), and `export_excel` gains
  either a distinct sheet or distinct columns clearly labeled `UX finding` — never concatenated into
  the existing `Failures`/`Repro steps` columns. Exports for a case with zero UX findings render no
  empty section (matching the existing `no_shots`/empty-`failures_html` convention). (Falsifiable: a
  fixture run with UX findings and a FAIL verdict on the same case → the HTML output contains both
  `<h3>Failures</h3>` and the UX-findings heading as siblings, never one inside the other's
  containing element; the Excel workbook's failures cell contains no UX-finding text and vice
  versa.)
- **PU8 — A persona's `locale`/`device` claim matches what the run actually executed under
  (execute.md E6 / AT-581).** Before a `UXReport` is persisted, its persona's `locale`/`device`
  fields are checked against the `RawResult`/`Case.case_class` the findings were derived from: a
  `LOCALE_I18N`/`VIEWPORT_MOBILE` claim on a case whose `Outcome` is `NOT_RUN`
  (`schema/enums.py:125-126`, `RawResult.not_run_reason`) — or whose `case_class` names no such
  condition at all — is refused, not silently recorded as a finding under that persona. (Falsifiable:
  a fixture `RawResult` with `outcome=Outcome.NOT_RUN`, `not_run_reason` set, run through the UX
  pass with a mobile-device persona attached → the pass either records zero findings for that case
  or raises, never a `UXFinding` claiming a mobile-viewport observation; a sabotage that skips this
  check must turn the test red.)
- **PU9 — File/function caps hold (C2).** No file touched by this unit crosses 300 lines or
  introduces a function over 50 lines; `schema/portal_persona.py` and `schema/verdict.py` in
  particular are checked for headroom before any field is added to them, and a new module is used
  instead of forcing headroom that isn't there. (Falsifiable: `uv run autotester doctor` exits 0
  after the unit's changes.)

## Out of scope / ignore

- Persona-driven **case generation** (option B in the gate) — T-166 territory, not this unit. A
  `UserPersona` existing is a precondition for that later work, not an implementation of it.
- Any UI/UX judging of the AutoTester product's own screens — this is about the product **under
  test**, never AutoTester's own interface.
- A weighting or aggregate "UX score" that rolls findings up into anything resembling a pass/fail
  number. Findings stay a list; nothing here computes a scalar that could be mistaken for a verdict.
- Editing `schema/verdict.py`'s `Rubric`/`Criterion`/`Judgment`/`Verdict` classes at all, beyond
  what PU2 already forbids — any edit there is out of scope for this unit and belongs to a future,
  separately-authorized contract change.
- Choosing which model/provider config serves the UX role, its per-run token/cost cap, and exactly
  where `UXReport` files live under `runs/<run_id>/` — these are plan-level decisions (see "Plan
  gate" below), not criteria this contract fixes in advance.

## No-fire list

- "The UX pass doesn't catch every real usability problem a human tester would" — this is an
  advisory heuristic pass, not a certified UX audit; recall is not what PU1-PU9 judge.
- "No persona-driven case generation yet" — explicitly out of scope (see above), tracked separately
  as T-166.
- "The severity scale for UX findings doesn't match `Severity` exactly" — reusing
  `schema.enums.Severity` (S1-S3) is the requirement (C3); a UX-specific label text on top of that
  enum is not a violation.
- "No dedicated `ProviderRole.UX` was added" — reusing the `judge` role is acceptable; PU5 requires
  going through `Provider`, not a specific role name.

## Plan-gate — what `docs/plan.md` must decide before any code (maker PLAN gate)

The maker's PLAN gate (`docs/intent.md` → `docs/spec.md` → `docs/plan.md` →
`qa/gates/plan-approved.md`) must name, before code:

1. **Which model serves the UX-judging call** — the same provider as the functional judge, or a
   cheaper/faster one, and why (this is a cost/quality tradeoff, not a correctness one — PU5 only
   requires it go through `Provider`).
2. **A cost cap per run** for the UX pass (token/call budget), and what happens when it is hit —
   skip remaining cases with a recorded reason, or fail the run. It must never silently degrade into
   softening the functional verdict (PU3/PU4).
3. **Where `UXReport`/`UXFinding` files are stored** under `projects/<slug>/runs/<run_id>/` — exact
   filename pattern, one file per run vs. one per case, and how `report_export.py` locates them
   (PU7 depends on this being resolvable without guessing).
4. **Where `UserPersona` is stored and attached** — a new top-level store file (mirroring
   `portal_persona.json`) vs. an inline field on `Project`/`Case`, and whether a persona is
   project-scoped, case-scoped, or both, per the gate answer's "attachable to a project and/or a
   case."
5. **Whether the UX pass runs by default on every regression run, or opt-in** (a project/run flag)
   — this changes cost and is explicitly the plan's call, not this contract's.

The plan must NOT decide, because this contract already fixes them: that findings never touch
`Verdict`/`Judgment` (PU2/PU3), that a persona never softens a criterion (PU4), that the call goes
through `Provider` with a prompt file (PU5), that the prompt is redaction-gated first (PU6), or
that findings render as a separate export section (PU7).

## Verify (adapter slot 1)

`uv run pytest tests/ -k persona` (T-190's `done_check` in `.goal/goal.json`) + `uv run pytest`
(full suite, to catch PU3's byte-identical-verdict regression against existing callers) +
`uv run ruff check src tests scripts` + `uv run autotester doctor`, all exit 0; PU1-PU9 each carry
a capability-coverage row with a single-hunk falsifying edit reproduced
green→red-for-the-named-reason→revert→green, per C7's guard-sabotage clause (D-048, at218=2) — this
applies to every guard this unit introduces (the byte-identical-verdict assertion in PU3, the
no-import check in PU4, the redaction-gate call in PU6, the E6-alignment refusal in PU8), not only
to new tests.

## Amendment log (append-only; git history is the version)

- 2026-09-26 · init · contract authored by /checker (D-050), from D-048 (Approved-by Umesh —
  AskUserQuestion answers, checker session, 2026-09-26; gate
  `qa/gates/meeting-user-persona-ux-judging.md` answered A) and goal task T-190. No prior draft
  existed; nothing amended.
