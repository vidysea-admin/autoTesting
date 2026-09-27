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
- **CT6 — Cheap→expensive tier ordering is real, not decorative.** `CaseClass.tier` places every
  class into `static < behavioural < adversarial`; the tier ordering is total (every class has
  exactly one tier) and `routes_runs.py`'s tiered dispatch runs `static` before `behavioural` before
  `adversarial`, and STOPS before paying for a tier that has zero runnable entries at the point it
  would start (a cheap structural failure is visible before an expensive graded run is triggered).
  (Falsifiable: a fixture with a blocked `static` tier and a runnable `adversarial` tier still stops
  before `adversarial` runs; a fixture with `static` entries runnable and nothing blocking
  `behavioural` runs both tiers in `static → behavioural` order, observed via call order not just
  final state.)
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

`uv run pytest tests/test_catalog.py tests/test_catalog_packs.py tests/test_ui_catalog.py` (bare,
no CLI `-q`, AT-503) +
`uv run ruff check src tests scripts` + `uv run autotester doctor`, all exit 0; each CT criterion
carries a capability-coverage row with a single-hunk falsifying edit reproduced
green→red-for-the-named-reason→revert→green. File/function caps (core-invariants C2: ≤300 lines /
≤50 lines) apply to every new module this unit adds.

## Amendment log (append-only; git history is the version)

- 2026-09-24 · init · contract authored by /checker as DRAFT, from `plan.md` §5A and D-039
  (Approved-by Umesh — "allow krr doo , goal pura hona chaiyee", `qa/gates/t125-d039-entry-draft.md`).
  No prior draft existed; nothing amended.
- 2026-09-27 · routine · added the "Standard packs (AT-588, additive)" section documenting
  `StandardPack`/`PackEntry` (present in code since commit 2e397500 but never named in this
  contract) and added `tests/test_catalog_packs.py` to the verify command — pure documentation of
  what already ships plus a verify-command update; no criterion tightened, weakened, or reworded.
  Filed at t125-catalog cycle-1 Mode A check (verdict: FAIL on CT5/CT6 — see
  `qa/verdicts/t125-catalog.md`; this amendment is independent of that verdict and does not
  soften either failing criterion). Status remains DRAFT — DRAFT→ACTIVE still requires a PASS.
