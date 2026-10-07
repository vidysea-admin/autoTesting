# Contract — catalog (the test catalog: applicable, runnable, blocked-and-why)

**Status:** DRAFT (goes DRAFT->ACTIVE on T-125's first checker PASS).
**Feature:** `stages/catalog.py::catalog(project, spec, store) -> Catalog` — a pure, derived view
over existing artifacts that says, per `CaseClass`, whether it is `applicable`, `runnable`, and
when not runnable, the one `BlockedReason` (closed vocabulary) plus the action that clears it.
Adds a cheap→expensive `tier` per `CaseClass` (`static → behavioural → adversarial`) so a run
pays for the expensive tier only after the cheap one has runnable entries. Read-only page
`GET /projects/{slug}/catalog`.
**Covers:** goal task T-125. **Deps:** T-124 (consent gates; done). **Grounding:** `plan.md` §5A
"T-125 — the test catalog" (lines 505-524); D-039 (authorization; names the exact schema, the
closed `BlockedReason` vocabulary, and the tier ordering — this contract does not invent beyond it).
**Reused by (not built here):** T-152's `stages/ai_catalog.py::match(target) -> Catalog` is
required by `plan.md` §5B (line 588) to reuse this same `Catalog`/`BlockedReason` rather than
define a second one; T-166 (eval compiler) also depends on T-125. This contract's CT7 is what a
later T-152 checker judges against.

## What it is

`schema/catalog.py`: `CatalogEntry` (case class, `applicable: bool`, `runnable: bool`,
`blocked_reason: BlockedReason | None`, `tier`), `Catalog` (project + `list[CatalogEntry]`), and
the closed enum `BlockedReason` = `no_flowspec | flowspec_not_approved | missing_credential |
no_ground_truth | needs_write_policy | no_live_endpoint` — exactly D-039's list, no more, no fewer.
`stages/catalog.py::catalog()` reads only artifacts already on disk (the reviewed `FlowSpec`,
declared `SecretRef`s, the project's `write_policy`, whether a live endpoint is configured) and
computes the table — no model call, no network call, no mutation of anything it reads.

## Criteria (CT1-CTn) — each judged on re-runnable evidence

- **CT1 — Pure, deterministic, no side effects.** `catalog(project, spec, store)` reads artifacts
  and returns a `Catalog`; it writes nothing and calls no `Provider` (core-invariants C8). Same
  inputs on disk → byte-identical `Catalog` output, run twice. (Falsifiable: call `catalog()` twice
  against the same fixture project with no change between calls; assert the two results are equal.)
- **CT2 — Every `CaseClass` gets exactly one entry.** `Catalog.entries` covers every member of the
  closed `CaseClass` enum, once each — never fewer (a class silently dropped) and never a duplicate
  (two entries for one class). (Falsifiable: `len(catalog(...).entries) == len(CaseClass)` and no
  repeated `case_class` value.)
- **CT3 — `BlockedReason` is exactly D-039's six values, closed.** A `runnable=False` entry always
  carries a non-null `blocked_reason` from that exact vocabulary (core-invariants C1: `extra="forbid"`
  keeps it closed — no seventh reason invented ad hoc); a `runnable=True` entry's `blocked_reason` is
  null. (Falsifiable: no entry is `runnable=False` with `blocked_reason=None`, and no entry is
  `runnable=True` with a non-null `blocked_reason`.)
- **CT4 — No FlowSpec → every entry blocked `no_flowspec`, and the page says so.** A project with no
  persisted `FlowSpec` yields a `Catalog` where every entry's `blocked_reason` is `no_flowspec`, and
  `GET /projects/{slug}/catalog` renders that reason on every row, not a generic empty state.
  (Falsifiable: fixture project with no FlowSpec on disk → all entries `no_flowspec`; the rendered
  page contains the string for each row.)
- **CT5 — A missing credential names the KEY, never a value (core-invariants C5).** An approved
  FlowSpec whose case class needs a declared `SecretRef` that has no value set in the root `.env`
  yields `blocked_reason=missing_credential` and the entry's unblocking-action text names the
  `SecretRef` key (e.g. `PATHLYNKS_PASSWORD`) — the raw value is never read, held, or rendered by
  this stage. (Falsifiable: an unset declared secret produces an entry whose text contains the key
  name; `assert_no_raw_secrets`/`Redactor.scrub` over the rendered page and the `Catalog` JSON finds
  nothing resembling the actual `.env` value.)
- **CT6 — Cheap→expensive tier ordering is real, ordering and reporting only, and never skips a case.**
  (Narrowed 2026-09-29 by **D-057**, `Approved-by: Umesh`; the earlier wording — "STOPS before paying
  for a tier that has zero runnable entries" — filtered which cases execute and contradicted
  `ui-run.md` RU3 and F-058. Amended again 2026-10-07 per gate t125-ct6 answer A (**D-071**): the
  cost-avoidance "stop before an expensive tier" half is removed outright, and prominent reporting of
  cheap-tier failures is added.) `CaseClass.tier` places every class into
  `static < behavioural < adversarial`; the ordering is total (every class has exactly one tier).
  The run trigger (`ui/routes_runs.py::trigger_run`) dispatches **every** case on file, ordered
  cheapest tier first (`static` before `behavioural` before `adversarial`), and **never skips a
  tier**. The run report **surfaces cheap-tier failures first and prominently** (a failed `static`
  case is listed above any `behavioural` or `adversarial` result, not buried in case-id order) and
  **reports each tier's runnable count** (including a count of zero). It **never omits a case that
  RU3 says runs**: the set of cases executed is identical with and without the ordering, and a
  pinned case (F-058) runs every time whatever tier it is in. `stages/catalog.py::tiers_to_run()` is
  an ordering input, not a filter. (Falsifiable, four parts, each driven through the run endpoint
  (`POST` of the run trigger, then the run record and the rendered report), not only by calling
  `tiers_to_run()` directly. (1) Ordering, observed via dispatch call order and not only final
  state: a project with runnable `static`, `behavioural` and `adversarial` cases records dispatch
  `static → behavioural → adversarial`. (2) Never skip: a project with a fully blocked or empty
  `static` tier and a runnable `adversarial` case still RUNS the `adversarial` case, and the
  executed set equals `store.list_cases()` (RU3). Sabotage: gate dispatch on the tier's runnable
  count, the old rule — this fixture goes red on the executed-set assertion. (3) Reporting, counts:
  the run record carries a runnable count per tier, and the empty tier's count is `0`, not absent.
  (4) Reporting, prominence: with a failing `static` case and a failing `adversarial` case, the
  rendered run report lists the `static` failure before the `adversarial` one, in a failures section
  ahead of passing results; sabotage by sorting the report by case id turns this red. A pinned
  `adversarial` case in a run whose `static` tier is empty still runs.)
- **CT7 — One `Catalog`, reused, not duplicated (C3).** `schema/catalog.py::Catalog` and
  `BlockedReason` are the only such model/enum in the repo — this criterion is judged over every
  unit that touches `stages/ai_catalog.py` or any later Track-C catalog code: a second `Catalog`-
  shaped model, or a second `BlockedReason`-shaped enum, anywhere in `src/` is a CT7 failure, not a
  new feature. (Verify at T-125's own check: `grep -rn "class Catalog" src/autotester/schema/`
  returns exactly one definition; `grep -rn "class BlockedReason" src/` returns exactly one.
  Re-verified at any later unit that imports or extends catalog matching.)
- **CT8 — The catalog page is honest, not just present.** `GET /projects/{slug}/catalog` renders one
  row per case class with a green runnable count, and every blocked row states both the reason and
  the one action that clears it (not merely the enum value) — matching `plan.md`'s own acceptance
  line ("every blocked row saying *why* and the one action that unblocks it"). (Falsifiable: for
  each `BlockedReason` value, a fixture producing that reason renders row text distinct from the
  bare enum name, e.g. `missing_credential` renders "set PATHLYNKS_PASSWORD in .env", not the literal
  string `missing_credential`.)

- **CT9 — Which credential gates which row: only keys the row's own flows read, and never fewer
  (added 2026-09-29 under **D-051**, `Approved-by: Umesh`, which authorizes the checker to define
  flow relevance).** A `CatalogEntry`'s `missing_credential` gate, and the key its `unblock_action`
  names, are computed from the `SecretRef` keys referenced (`{{SECRET:KEY}}`) by **the flows that
  feed that row's case class** (`Case` is keyed by `flow_id`, `schema/case.py:22`; the class-to-flow
  mapping is `stages/expand.py`'s). Three rules, in priority order:
  (a) **No under-block.** A row is never `runnable=True` while any key read by a flow feeding it is
  unset. A false green is the unsafe direction (`qa/debug/t125-catalog-cycle3.md`: it propagates into
  T-152/T-166 through CT7). (b) **No cross-flow leak.** A key read only by flows that feed a
  *different* class neither blocks this row nor appears in its `unblock_action` (this is ISS-t125-5).
  (c) **Declared, never inferred.** Relevance comes only from the SecretRef declarations and the
  `{{SECRET:KEY}}` references in flow steps. A keyword match on flow text, or the shape of an input
  field, does not decide it (`stages/explore_merge.py:50-51`: "`secret_key` is deliberately never
  inferred"). **Stated limit, not a gap:** with one row per class (CT2), two flows of the same class
  needing different keys make the row's wording a union of both. That is allowed; naming a key of a
  flow that does not feed the class is not. An unrelated flow that reads a key for a class it also
  feeds (an admin import that fills `SFTP_KEY`) is not distinguished by this contract; over-blocking
  there is the accepted direction. (Falsifiable: (a) two flows of one class, one key set and one unset
  — the row is blocked and names the unset key; (b) a fixture with an unset key referenced only by an
  `oauth_signup` flow and a set key for the login flow — the auth row is `runnable=True` and its text
  contains neither the key nor its name; (c) a flow whose text says "sign in with Google" but
  references no `{{SECRET:*}}` contributes no key. Each is observed on a real `catalog()` return, and
  the two named sabotages — union the keys spec-wide, and add a keyword rule — each turn the named
  fixture red.)

## Standard packs (AT-588, additive — recorded 2026-09-27)

`schema/catalog.py` also defines `StandardPack` (a closed 3-value enum: `oauth_signup_carryover`,
`date_picker_month_year`, `excel_column_mapping`) and `PackEntry` (`pack`, `applicable`,
`runnable`, `blocked_reason: BlockedReason | None`, `unblock_action`), plus `Catalog.packs:
list[PackEntry]`. `PackEntry` reuses `BlockedReason` rather than defining a second closed
vocabulary — CT7 governs `PackEntry` exactly as it governs `CatalogEntry`: a second
`BlockedReason`-shaped enum anywhere in `src/` is a CT7 failure. `packs` is additive and NOT
governed by CT2 — a pack whose structural signal is absent from the FlowSpec is
`applicable=False, blocked_reason=None` ("not applicable"), which is deliberately distinct from a
blocked pack (`blocked_reason` set). CT5 and CT8's naming-the-action requirements apply to
`PackEntry.unblock_action` exactly as they apply to `CatalogEntry.unblock_action`.

## Explicit no-fire list (do not raise these as findings)

- T-152's `stages/ai_catalog.py::match()` is NOT built by this unit — CT7 governs it for when it
  lands; raising "Track C catalog missing" against T-125 itself is out of scope.
- T-166 (eval compiler) consuming the catalog is a later dependency, not this unit's job.
- Anything about the *content* of an individual `CaseClass`'s applicability rule beyond what
  `plan.md` names (FlowSpec presence/approval, credential presence, ground truth, write policy,
  live endpoint) — new blocking conditions are a contract amendment, not a T-125 defect.
- UI styling/polish beyond CT8's honesty requirement.
- Concurrent/racing catalog reads — the stage is read-only and pure; no locking is claimed or needed.

## How a unit is verified (adapter slot 1)

`uv run pytest tests/test_catalog.py tests/test_catalog_packs.py tests/test_ui_catalog.py` (bare, no CLI `-q`, AT-503) +
`uv run ruff check src tests scripts` + `uv run autotester doctor`, all exit 0; each CT criterion
carries a capability-coverage row with a single-hunk falsifying edit reproduced
green→red-for-the-named-reason→revert→green. File/function caps (core-invariants C2: ≤300 lines /
≤50 lines) apply to every new module this unit adds.

## Amendment log (append-only; git history is the version)

- 2026-09-24 · init · contract authored by /checker as DRAFT, from `plan.md` §5A and D-039
  (Approved-by Umesh — "allow krr doo , goal pura hona chaiyee", `qa/gates/t125-d039-entry-draft.md`).
  No prior draft existed; nothing amended.
- 2026-09-29 · amend (Changes-authorized: D-057, D-051) · **CT6 narrowed** from "stop before an empty
  tier" to "dispatch in cheap-to-expensive order and report each tier's runnable count; never skip a
  case". Umesh's answer at `qa/gates/t125-ct6-tiered-dispatch-vs-ru3.md`, option A "order only, never
  skip", recorded as D-057 (`ade87168`). This IS a weakening of the old CT6 stop-rule and is on the
  record as human-approved, not routine; RU3 and F-058 are unchanged and CT6 now cites them.
  **CT9 added** (a tightening): D-051 authorized the checker to define flow relevance and nothing was
  ever written, so all three T-125 cycles and the cycle-4 candidate were judged against an
  unwritten rule (AT-732). Grounding: `qa/debug/t125-catalog-cycle3.md`. CT2/CT5/CT8 are untouched.
  **Links:** D-057; D-051; T-125; ISS-t125-1; ISS-t125-5; F-058; ui-run.md RU3.
  **Merge note:** the `wave/t125-catalog` branch carries its own 2026-09-27 amendment (the "Standard
  packs" section and a verify-command change, commit 3da63550) that is not on master; the two log
  tails will conflict on merge and both entries are to be kept.
- 2026-10-07 · amend (Changes-authorized: D-071; gate `qa/gates/t125-ct6-tiered-dispatch-vs-ru3.md`
  answer A, Umesh, chat) · **CT6 amended** — "Amended 2026-10-07 per gate t125-ct6 answer A (D-071)".
  The run trigger dispatches every case, cheapest tier first, never skips a tier; the cost-avoidance
  "stop before an expensive tier" half is removed; cheap-tier failures must be surfaced first and
  prominently in the run report. Verify rewritten to be checkable through the run endpoint (ordering
  plus reporting), not only via `tiers_to_run()`. RU3 (`ui-run.md`) and F-058 unchanged. This
  re-states D-057's order-only rule and adds the reporting requirement (part 4); it tightens, not
  weakens. **Links:** D-071; D-057; T-125; ISS-t125-1; F-058; ui-run.md RU3.
