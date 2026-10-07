# Contract — GRADE stage (T-041)

**Covers:** goal task T-041. **Owner:** /checker. **Criticality:** HIGH — the stage that turns
observation into the verdict everything downstream (T-050, T-090, T-110, T-120, the north star's
bugs-found/false-positive scoring) depends on.
**Depends on:** `core-invariants.md` (all, esp. C7 "the executor never grades itself"),
`execute.md` (E1-E5, produces the `RawResult` this stage consumes).

## Purpose

Grade one case's `RawResult` against its `Rubric` in a fresh, stateless context — never re-run,
never given the case's own steps/script/reasoning, only the rubric and the evidence `execute.py`
recorded. Produces a `Verdict`. This is the plan's "the runner never grades itself" line, made
literal: `stages/grade.py` cannot see anything `stages/execute.py` did except what it wrote down.

## Criteria

### G1 — Stateless, evidence-only judge
`stages/grade.py::grade` receives only a `Rubric` and a `RawResult` (plus a `run_id` and a
`Provider`) — it never imports `Case`, never reads `case.steps`, never reads a `Script`. The
prompt built by `build_prompt` contains only the rubric's criteria/no-fire list and the
`RawResult`'s evidence list — no case metadata, no script source, no prior verdict.

### G2 — Deterministic outcomes never reach the judge
`Outcome.BLOCKED_HITL` → `Result.BLOCKED` and `Outcome.ERRORED` → `Result.INCONCLUSIVE`, both
without calling `judge.judge(...)` — there is nothing coherent to grade when the execution itself
didn't complete. Only `Outcome.COMPLETED` results are sent to the judge. *(amended D-074,
2026-10-07)* `Outcome.ASSERTION_FAILED` results (D-032) are also sent to the judge, under the
restriction in G6; they are never graded by the executor.

### G3 — PASS requires cited evidence; an unevidenced or inconsistent judgment is rejected
Before a judge's `Judgment` becomes the stage's `Verdict`, `_inconsistency` checks it against the
rubric it was actually given: every `Failure.criterion_id` must name a real criterion; a
criterion with `evidence_required=True` must have a non-empty `evidence_refs` when cited as a
failure; `criteria_total` must equal the rubric's criterion count; `PASS` requires an empty
`failures` list; `FAIL` requires a non-empty one. Any violation downgrades the result to
`Result.INCONCLUSIVE` with a `note` naming which check failed — the stage never lets a
self-contradictory or unevidenced judgment ship as PASS or FAIL. This is the mechanism behind the
plan's "seeded fake-pass rejected" eval row.

### G4 — Verdict is complete and persisted
Every path through `grade()` returns a `Verdict` with `run_id`, `case_id`, `result`,
`grader_provider` (the real provider id for a judged call, `"rule"` for a deterministic one),
and `rubric_hash` (`Rubric.fingerprint`) always set. `ProjectStore.save_verdict(run_id, verdict)`
writes it to `projects/<slug>/runs/<run_id>/<case_id>.verdict.json`, distinct from the
`RawResult` file at `<case_id>.json` so `load_results`/`load_verdicts` never cross-read each
other's files (C6 — no new file format, one glob pattern per artifact kind).

### G5 — Prompt is a file, not an inline string
The grading prompt lives at `src/autotester/skills/grade/SKILL.md`, loaded by
`stages/grade.py:23` `SKILL_NAME = "grade"` via `load_skill_prompt` (T-175, D-043; the old
`prompts/grade_v1.md` no longer exists). Versioned per the project's
"prompts are files" rule; `build_prompt` only fills placeholders, it never constructs prompt
text inline in `grade.py`.

### G6 — A failed deterministic assertion is never graded PASS (D-074 rule A)
*(added D-074, 2026-10-07; amends the part of D-032 that let the judge overrule a failed assertion)*
For a `RawResult` whose `outcome` is `Outcome.ASSERTION_FAILED`, or that carries any `assert <field>:
unmet` evidence item, `grade()` returns only `Result.FAIL` or `Result.INCONCLUSIVE`. A judge
`Judgment` of PASS for such a run is rejected and downgraded to `Result.INCONCLUSIVE` with a `note`
naming the failed assertion (same path as the G3 `_inconsistency` downgrade), and the judge's PASS
is never persisted as the stage's `Verdict`. The rule holds whatever the judge's confidence, rubric
or provider, and whether the judge is real, mock or fallback. A run with no failed assertion is
unaffected. `serves:` D-074(b), D-032, AT-773 (6 of 6 T-122 false PASSes were failed-assertion runs
the judge passed). (Falsifiable: a case with a step expecting visible text that is absent,
graded with a mock judge that returns PASS -> `Verdict.result` is `FAIL` or `INCONCLUSIVE`, never
`PASS`; the same case with the assertion met and a PASS judge -> `PASS`. Mutation: remove the
downgrade -> the first test fails.)

## No-fire list

- Choosing which provider judges (that's the project's `providers{judge: ...}` config, not this
  stage's job — `grade()` takes an already-constructed `Provider`).
- Multi-case aggregate scoring / a run-level report (T-100's job).
- Retrying a judge call on a malformed response (the mock provider in tests never fails this
  way; a real provider's structured-output failure handling is a provider-layer concern).
- `EvidenceKind.DB` assertions (T-045) — grade.py grades whatever evidence exists; it does not
  require a particular evidence kind to be present.

## Amendment log (append-only; git history is the version)

- 2026-09-03 · init · contract created for T-041 (grade stage), following the pattern set by
  `execute.md` for T-040 — no contract existed before this cycle.
- 2026-09-04 · routine · G1 clarified: the judge call must attach the real bytes of any
  `SCREENSHOT`-kind evidence it has been given a `run_dir` for, not just describe that evidence
  as a filename/label in the text prompt. Prompted by AT-049 (critical, `qa/issues.jsonl`) — every
  prior `Verdict` was graded from evidence filenames only, `Provider.judge()`/`grade()` never
  attached image bytes, which explained run-to-run flakiness far better than a timing theory
  (a text-only judge guessing plausibility from a label is inherently non-deterministic). Fixed
  in `providers/base.py`, `providers/langchain_fallback.py`, `providers/gemini.py`,
  `providers/anthropic.py`, `stages/grade.py::_screenshot_paths`,
  `stages/run_case_pipeline.py::run_and_grade_case`; checker-verified 2026-09-04
  (`qa/verdicts/at049-multimodal-grading.md`). This does not weaken G1's "no case metadata, no
  script source" boundary — an image is evidence the same as a screenshot's filename always was,
  just now genuinely seen rather than merely named.
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
- 2026-10-07 - routine (authorized by D-074 rule A, Umesh 2026-10-07; tightening only) - **G6 added**
  (new id): a failed deterministic assertion can never be graded PASS; the judge may return only FAIL
  or INCONCLUSIVE for that run. **G2** gained a pointer so it no longer reads as "only COMPLETED
  reaches the judge" next to execute.md E1 (an `ASSERTION_FAILED` run does reach it, restricted).
  Amends D-032 partially: the "judge may weigh and overrule a failed assertion" part is removed, the
  rest of D-032 stands. Build authorized in `stages/grade.py` and `stages/run_case_pipeline.py`
  (D-074 Changes-authorized). **Links:** D-074; D-032; AT-773; execute.md E1.
