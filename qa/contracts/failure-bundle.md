# Contract — failure-bundle (one atomic unit per failure, priority, and pruning before spend)

**Current interpretation (D-099, 2026-10-15):** original code/status/landing notes
below are historical observations, not current absence claims. Judge existing
bundle machinery and new integration by FB1-FB6 and committed evidence; this
amendment alone does not certify a prior task PASS.

**Status:** **DRAFT** (authored by /checker 2026-09-29 under **D-041**, `Approved-by: Umesh` —
Result names this file). Goes **ACTIVE** on T-178's first checker PASS.
**Feature:** T-178 — an atomic, self-contained failure bundle with one id; case priority `p0`..`p3`;
and human pruning of proposed cases before any provider spend on them.
**Serves:** intent O3 (every finding carries evidence) · spec R24.
**Code:** does not exist yet (T-178 `pending`, depends on T-125). Today evidence is human-browsable
folders (`qa/evidence/<unit>/`, run dirs), not one consumable unit; `Case` has no priority;
`schema/case.py::Case.pinned` (AT-585) is expected to be subsumed by `p0`.
**Tests:** none yet.
**Grounding:** D-041 §6 row T-178 · `docs/research/testsprite-2026-09.md` §4 D, G, H (the integrity
rule matters, not the file layout: one id, self-contained, neighbours of the failing step,
`.partial` when a write dies, refusal to mix runs) · `review-gate.md` (nothing expands an
unreviewed spec) · `expand.md` (one provider call per case class) · `report-export.md` RE5 ·
core-invariants C5, C7, C12 · AT-585.

## Why it exists

A finding that arrives as five folders and a paragraph is a finding a human reassembles by hand and
an agent cannot consume at all. The failure this contract refuses is a bundle that looks complete and
is not — half-written after a crash, or stitched from two runs — because a false bundle is worse than
none: it gets believed. The second failure is spending provider calls on cases a human would have
deleted.

## Criteria

### FB1 — A bundle is atomic: complete, or visibly not

One bundle per failing case run, with one bundle id. It is **self-contained**: the case, the verdict,
the failing step **and its neighbouring steps**, the screenshot(s), the error, and the redacted
trace slice — a consumer needs nothing outside it. It is written under a `.partial` name and renamed
only when every part is present; a write that dies leaves the `.partial` marker.

**Verify:** a fixture whose writer raises mid-bundle — afterwards no complete bundle exists, the
`.partial` marker does, and the loader **refuses** it. A complete bundle contains the failing step
and at least one neighbour on each side where they exist. Sabotage: remove the rename-on-complete —
the crash test goes red on "a complete-looking bundle exists".

### FB2 — A bundle never mixes runs

Every artifact carries its run id, and assembling a bundle from artifacts of more than one run is a
hard refusal, not a warning.

**Verify:** plant one artifact belonging to another run in the source set — assembly raises and no
bundle is written. Sabotage: drop the run-id comparison — the planted-artifact test goes red.

### FB3 — No secret reaches a bundle

A bundle passes the same scrub as every other report artifact (C5, `report-export.md` RE5):
`Redactor.scrub` on text, masked secret inputs in screenshots.

**Verify:** run a fixture case that types a planted secret into a masked field and fails — the value
appears nowhere in the bundle (`scripts/check_no_secrets.py` clean on the bundle directory).

### FB4 — Case priority is real, selectable, and does not weaken `pinned`

`Case.priority ∈ {p0, p1, p2, p3}` in `schema/` (`extra="forbid"`), with a stated default. A regression
run can select by priority. Pinned cases (AT-585) are `p0`, and `ProjectStore.delete_case` still
**refuses** to delete them — the AT-585 guarantee is preserved through the migration, not dropped with
the flag. A case saved before this unit still loads.

**Verify:** four fixture cases, one per priority — selecting `p0` runs exactly the `p0` case(s) and
the count is asserted. Pin a case, then attempt `delete_case` — refused, as before. Load a case file
written without a priority — it loads with the stated default. Sabotage: make selection ignore the
priority — the count assertion goes red.

### FB5 — Human pruning happens before provider spend

Proposed cases are staged as **proposals** (class, title, rationale — no steps yet) for a human to
approve or prune, and **only approved proposals reach the provider calls that generate steps**. The
review gate is not bypassable (the `review-gate.md` shape).

**Verify:** a fixture with 5 proposals, 3 pruned — a counting fake provider records **exactly 2**
step-generation calls; prune all 5 and the count is **0**. With no approval recorded, nothing is
generated. Sabotage: generate before the approval check — the pruned-proposals count goes red.

## Landing note

### FB6 — Production integration preserves functional results
Failed/inconclusive runs expose their sanitized failure bundles through existing
reports. Bundle assembly failure retains the original RawResult/Verdict and
records the unavailable bundle reason; it never turns a failure into success.
FB1/FB2 atomicity and isolation still bind. Screenshot withholding under B11 is
represented as explicitly missing visual evidence, not a fabricated complete
image; such a bundle makes no full-visual-completeness claim.
FB5 applies to the reviewed proposal path. D-097's reconciled source-derived
DRAFT generation exception retains source provenance and requires no human
proposal approval; NEEDS_EDIT/unreconciled material remains blocked.
Verify through the production run/report caller, including failure injection,
privacy sanitation/withholding and run isolation. Direct bundle writer tests alone
cannot establish the integration.

## Historical landing note (preserved)

None of this exists, and `Case.pinned`'s own description says T-178 "is expected to subsume `pinned`
with `priority == p0`" — so a check that only asserts "pinned cases survive" passes today. FB4's
**Verify** requires a `priority` field to select on, which the current tree cannot supply.

## No-fire list

- Building T-178 itself.
- A UI for pruning (the requirement is that pruning happens before spend, not its screen) — if the
  build adds one, `docs/plan.md` row 13 already marks a persona walk `required`.
- A PDF or scheduled export (`report-export.md`'s own declined scope).
- Retiring `Case.pinned` as a field — allowed by the source comment, not required here.

## Amendment log (append-only; git history is the version)

- 2026-09-29 · init · authored by /checker under D-041 (Result names `failure-bundle.md`). Cause:
  T-178 had a plan row (unit 13) and a goal task but zero checkable criteria; the authorization has
  stood since 2026-09-24 and the file was never written. DRAFT until T-178's first PASS.
  **Changes-authorized:** this file (named by D-041). No enforcement-path file touched.
  **Links:** D-041; T-178; R24; AT-585.
