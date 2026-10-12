# Contract — FlowSpec review gate (T-065)

**Covers:** goal task T-065. **Owner:** /checker. **Criticality:** HIGH — the north star's own
words ("derives a **reviewed** FlowSpec") name this gate as the primary false-positive control.
*Amended 2026-10-11 per D-070 item 2 (Umesh, 2026-10-07): the DRAFT review gate is a status only and
never blocks case generation from reconciled flows; see R5. Until the code catches up (R5 build
note), `stages/expand.py` and `stages/eval_compiler.py` still call `require_reviewed` unconditionally.*
**Depends on:** `core-invariants.md` (all), `ingest.md` (I1-I5, dependency — produces the
`FlowSpec` this gate reviews).

## Purpose

A `FlowSpec` fresh from `ingest_video` is a machine's first guess, not ground truth. This stage
is the mechanism a human uses to say "yes, this is right" (or "no, fix this") before anything
downstream treats it as fact. `FlowSpec.review.status` starts `draft`; only a human-driven
`approve` call moves it to `approved`. *(D-070 item 2, 2026-10-11: that approval is available, never a
dependency. The status says whether a human has looked; it does not stop case generation from
reconciled flows. R5 states exactly what still blocks and what no longer does.)*

## Criteria

### R1 — A fresh FlowSpec is unreviewed, and the guard still reports it
`stages/ingest.py::ingest_video` never sets `review.status` to anything but its default
(`ReviewStatus.DRAFT`) — unchanged by this unit, verified as still true. `require_reviewed(spec)`
raises `FlowSpecNotReviewed` for `DRAFT` and for `NEEDS_EDIT`, naming the project and the exact
CLI command to unblock it. *(2026-10-11, D-070 item 2: this is the guard function's behaviour in
isolation, and it is unchanged. Which stage calls it, and for which specs, is governed by R5.)*

### R2 — Approval is human-attributed and does not mutate the original
`approve(spec, by, note=None)` returns a **new** `FlowSpec` with `review.status=APPROVED`,
`review.by` set to the given name, `review.at` set to a real timestamp, `review.note` carrying
the optional note — the input `spec` object is never mutated in place (Pydantic's `model_copy`
semantics). `approve` refuses an empty `by` — there is no such thing as anonymous approval.

### R3 — request_edit sends it back with a mandatory reason
`request_edit(spec, by, note)` returns a new `FlowSpec` with `review.status=NEEDS_EDIT` and the
given note — refuses an empty `by` or `note` (a review rejection with no stated reason is not
useful to whoever fixes it next). A `NEEDS_EDIT` spec still fails `require_reviewed`.

### R4 — The CLI is a thin wrapper, not a second source of truth
`autotester flowspec status/approve/request-edit <project>` load and save through
`ProjectStore.load_flowspec`/`save_flowspec` — the same file (`projects/<slug>/flowspec.json`)
and format every other stage reads, no parallel state.

### R5 — The review status never blocks case generation from reconciled flows (D-070 item 2)
`FlowSpec.review.status` is a status, not a precondition, for generating cases. Definition used below:
a spec is **reconciled** when every `Flow` in it has `kind` set (`schema/flowspec.py:127`, "set by
reconcile (D-070)"; `reconcile.md` RC9).
- **(a) DRAFT does not block.** `stages/expand.py::expand` and `stages/eval_compiler.py::compile_evals`
  (and the CLI and UI paths that call them) generate cases from a reconciled spec whose status is
  `DRAFT` exactly as from the same spec at `APPROVED`: the same flows, the same case ids and classes, no
  `FlowSpecNotReviewed`, no wait. Generation never reads the status to choose, drop or order a flow and
  never changes it.
- **(b) What still blocks, until Umesh answers (D-070 does not speak to either).** A spec with any flow
  whose `kind` is unset (not reconciled) and a spec at `NEEDS_EDIT` (a human explicitly sent it back,
  R3) still make generation raise `FlowSpecNotReviewed`, as in R1. Open questions for Umesh:
  (i) should `NEEDS_EDIT` also stop blocking, or is an explicit human "fix this" a stop? (ii) should
  an unreconciled `DRAFT` spec generate too (status-only for every spec)?
- **(c) Human review stays possible and protected.** `approve`, `request_edit` and
  `autotester flowspec status/approve/request-edit` are unchanged (R2-R4). No stage approves on a
  human's behalf and no stage waits for approval. A human-`APPROVED` spec is still never overwritten by
  a re-ingest without `--replace` (`ingest.md` I6): D-070 removes the dependency on a human, not the
  protection of one's judgement.
- **Verify (by construction, C12):** with `MockProvider`, a reconciled `DRAFT` spec through `expand`
  and through `compile_evals` returns case lists equal (ids, classes, count) to the same spec with
  `status=APPROVED`, raises nothing, and `spec.review.status` is still `DRAFT` afterwards; a spec with
  one `kind=None` flow at `DRAFT` and a reconciled spec at `NEEDS_EDIT` each still raise
  `FlowSpecNotReviewed` before any provider call (the unpopulated case, which a populated-only test
  cannot reach); `approve` on the DRAFT spec still returns an `APPROVED` copy and leaves the original
  untouched (R2). Falsification (checker, throwaway copy, copy green first): restore an unconditional
  `require_reviewed(spec)` at the top of `expand`, and the reconciled-`DRAFT` test must go red on its
  own named assertion; remove the `kind` condition and the unreconciled-`DRAFT` refusal test must go
  red.
- **Build note (not a criterion).** The code change (`stages/expand.py:137`,
  `stages/eval_compiler.py:96`, and the guard condition in or beside `stages/review.py`) is a
  separate **L** unit: D-073 says changing `require_reviewed` "is NOT authorized here; it is a
  separate L unit", and rewriting the existing tests that assert `DRAFT` raises is a protected test
  change (weakening an assertion; checker justification required). D-070 and D-073 name no source
  file as authorized for this, so the maker appends a D-entry whose `Changes-authorized` names these
  files before building it. `ui/routes_learn.py::generate_cases` must show the button under the same
  condition (`expand.md` X6).

## No-fire list

- Whether and when `stages/expand.py` / `stages/eval_compiler.py` call `require_reviewed` — that is
  R5 (the rule) and `expand.md` X1 (the stage's criterion). R1-R4 require only that the guard
  function exists and works correctly in isolation.
- A UI review screen — the CLI is the interface for now (T-100).
- Merge/diff logic when a FlowSpec is re-ingested after edits — a future concern, not required to
  approve or reject a spec as a whole.

## Amendment log (append-only; git history is the version)

- 2026-09-03 · init · contract created for T-065 — no contract existed before this cycle.

- 2026-10-11 · owner-authorized (D-070 item 2; Umesh, chat 2026-10-07, "Don't make any human dependency")
  · **R5 added; Purpose, header, R1 title and the first no-fire bullet reworded.** Before: R1/R2
  required a human `approve` before *any* generating stage ran. After: approval stays available (R2-R4
  unchanged) but is no longer a precondition for generating cases from reconciled flows. Classification:
  this narrows a gate the north star calls the primary false-positive control, so it is not a routine
  fold; it is recorded as a **human-authorized change** (D-070 item 2 is the authority, "The FlowSpec
  DRAFT review gate remains as a status only, and it never blocks case generation from reconciled
  flows"; "Contract changes come through the checker's inbox fold-in"). It goes only as far as D-070
  says: a spec with an unreconciled flow, and `NEEDS_EDIT`, keep their current behaviour until Umesh
  answers the two questions in R5. The same pass amends `expand.md` X1 and `ingest.md` (I16) and
  reconciles `consent.md` CN11 "Remaining gates". `reconcile.md` RC10/RC14 and `team-video-review.md`
  TV9 already assumed this and are unchanged. **Changes-authorized:** D-070 item 2 (contract text only;
  no `src/` change is authorized by it, see R5 build note). **Links:** D-070; D-073; T-065; T-166;
  `qa/feedback-inbox.md` 2026-10-07 "answers to the five asks".
