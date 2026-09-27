# Manifest — t125-catalog

**Contract:** `qa/contracts/catalog.md` (CT1-CT8, D-039), extended with the AT-588 standard packs.
**Goal task:** T-125 — the test catalog: what applies, what is runnable, what is blocked and why
(+ cheap->expensive ordering).
**Date:** 2026-09-27
**Fix cycle:** 1 of max 3
**Dual check:** no
**Persona walk:** skip (backend catalog, no UI surface beyond a read-only table already covered
by CT8-style tests)
**Issues addressed:** AT-588 (checker-sweep, 2026-09-26 meeting-review goal-coverage finding —
"No standard test packs" for Google OAuth sign-up carry-over, month/year pickers, and Excel
upload with column mapping).
**Executor:** claude-sonnet-subagent — dispatched as a `/maker` build subagent scoped to the
`wave/t125-catalog` worktree; no human interactively drove tool calls this cycle.

## Starting state

T-125's code (`schema/catalog.py`, `stages/catalog.py`, `ui/routes_catalog.py`,
`tests/test_catalog.py`, `tests/test_ui_catalog.py`) was already committed on this branch
(`cfc13b0b`) but carried no evidence manifest, so the maker/checker handshake had never seen it.
The branch was also behind master (32 files: T-175 prompt-skill migration, `redact_wrap`,
`trace`, `parallel_run`, several new test files). `git merge master` (fast, no conflicts) brought
the branch current before any new work.

## What I verified about the pre-existing T-125 code (all CT1-CT8 held already)

Read `qa/contracts/catalog.md` end to end against `stages/catalog.py`/`schema/catalog.py`:
- CT1 (pure/deterministic): `catalog()` reads only `project`, `spec`, and `.env` key *presence*
  via `SecretStore` — no `Provider` import, no network call, no write. `test_catalog_is_pure_...`
  already asserted this.
- CT2 (every `CaseClass` once): `TIER_BY_CLASS`'s key set already pinned equal to `set(CaseClass)`.
- CT3 (closed `BlockedReason`, present iff blocked): held via Pydantic `extra="forbid"` + the
  existing tests.
- CT4/CT5/CT6/CT8: covered by the existing `no_flowspec`, `missing_credential`,
  `tiers_to_run` and page-rendering tests. No gaps found — the unit's only real defect was the
  missing manifest, not the code.
- CT7 (one `Catalog`/`BlockedReason`): `test_exactly_one_catalog_model_and_blocked_reason_enum_in_src`
  already existed and passes.

No fixes were needed to the pre-existing behaviour; all new work is the AT-588 extension.

## What I built (AT-588 extension, same catalog module — no second catalog)

`stages/ai_catalog.py` (T-152, not yet built) is required by `plan.md` §5B to reuse this same
`Catalog`/`BlockedReason` (CT7) — so the AT-588 packs had to live inside `schema/catalog.py` /
`stages/catalog.py`, not a parallel module.

1. **`src/autotester/schema/catalog.py`** — added `StandardPack` (closed enum: 3 values —
   `oauth_signup_carryover`, `date_picker_month_year`, `excel_column_mapping`) and `PackEntry`
   (`pack`, `applicable`, `runnable`, `blocked_reason: BlockedReason | None`, `unblock_action`).
   `PackEntry` **reuses `BlockedReason`** rather than inventing a pack-specific vocabulary — CT7
   stays satisfied (one `BlockedReason` definition in `src/`). `Catalog` gained
   `packs: list[PackEntry]` and a `.pack(StandardPack) -> PackEntry | None` accessor, mirroring
   `.entry()`.
2. **`src/autotester/stages/catalog.py`** — three deterministic, structural signal detectors (no
   model call, same C8/discovery discipline as the rest of the stage):
   - `_has_oauth_signup_carryover(spec)` — a CLICK/NAVIGATE step whose target/value/note mentions
     "google", "oauth", or "accounts.google.com".
   - `_has_date_picker_month_year(spec)` — a `Screen.fields[].type` of `date`/`month`/`year`, or a
     step mentioning "date picker" or both "month" and "year".
   - `_has_excel_column_mapping(spec)` — an `Action.UPLOAD` step whose target/value names
     `.xlsx`/`.xls`/`.csv`/"excel".
   `_pack_entries(project, spec, missing_auth_keys)` computes one `PackEntry` per `StandardPack`,
   reusing the same blocking states as the `CaseClass` table (`no_flowspec` when there is no
   spec, `flowspec_not_approved` when the spec is unreviewed) and additionally blocking the OAuth
   pack on `missing_credential` when its flow references an unset `{{SECRET:KEY}}` (it signs in
   against a real Google account, same `missing_auth_keys` computation the AUTH case classes
   already use). **A pack whose structural signal is absent from an approved spec is
   `applicable=False, blocked_reason=None`** — distinct from *blocked*, because the product
   simply does not have that flow; this is a deliberate design choice, not a contract gap (CT2's
   "every `CaseClass` gets exactly one entry" governs `entries`, not `packs` — packs are
   additive, not a second closed-CaseClass-shaped table).
   `catalog()` now threads `packs=_pack_entries(...)` through all three branches
   (no-flowspec / not-approved / approved).
3. **`src/autotester/ui/routes_catalog.py`** — a second table, "Standard packs", on the same
   `GET /projects/{slug}/catalog` page (`_pack_table`/`_pack_row`/`_pack_status_cell`), reusing the
   existing `_status_cell` shape (now parameterised, shared between `CatalogEntry` and `PackEntry`
   rows) so a not-applicable pack renders "not applicable" (a `neutral` pill) distinct from a
   `runnable`/`blocked` row — same CT8 honesty discipline extended to packs.
4. Tests: `tests/test_catalog_packs.py` (new file — the AT-588 capability, split from
   `test_catalog.py` per `autotester doctor`'s own C2 file-size guidance once `test_catalog.py`
   crossed 300 lines) and three added tests in `tests/test_ui_catalog.py` for the page's packs
   table.

## Design questions resolved

- **Why not add three more `CaseClass` values instead?** CT2 requires `Catalog.entries` to cover
  `CaseClass` "once each — never fewer... and never a duplicate", and the existing
  `test_every_case_class_gets_exactly_one_entry_*` tests pin `len(cat.entries) == len(CaseClass)`
  exactly. A pack is conditional on the product actually having that flow (most login/browse
  flows have none of the three); a `CaseClass` is presumed to apply to every product. Folding
  packs into `CaseClass` would either force `len(CaseClass)` to grow for every project regardless
  of relevance, or require `entries` to become conditional-length, breaking CT2's own wording.
  `packs` is a parallel, additive list for exactly this reason.
- **Why does the OAuth pack alone get a `missing_credential` check?** It is the only one of the
  three that authenticates against a real external account (Google) to prove the data actually
  carried over; the date-picker and Excel packs are pure UI/upload interactions with no secret
  involved under `plan.md`'s existing secret model.

## How to verify

```
uv run pytest tests/test_catalog.py tests/test_catalog_packs.py tests/test_ui_catalog.py
uv run ruff check src tests scripts
uv run autotester doctor
uv run pytest        # full suite
```

## Actual outputs (real, pasted)

**Targeted suite:**
```
$ uv run pytest tests/test_catalog.py tests/test_ui_catalog.py tests/test_catalog_packs.py
.....................................                                    [100%]
37 passed, 1 warning in 4.20s
```

**ruff:**
```
$ uv run ruff check src tests scripts
All checks passed!
```

**doctor:**
```
$ uv run autotester doctor
doctor: clean
```
(`docs/MAP.md` was regenerated via `uv run autotester map` after adding `StandardPack`/`PackEntry`
to `schema/catalog.py` — doctor flagged `stale-generated` until that ran; committed alongside.)

**Full suite (`uv run pytest`, bare, no CLI `-q` — AT-503):**
```
........................................................................ [ 34%]
.........................................F.............................. [ 38%]
... (2043 more dots/markers) ...
================================== FAILURES ===================================
_______ test_run_once_kills_a_real_hung_process_and_its_real_grandchild _______
...
FileNotFoundError: [Errno 2] No such file or directory: '...\\child.pid'
=========================== short test summary info ===========================
FAILED tests/test_flake_probe_real_process.py::test_run_once_kills_a_real_hung_process_and_its_real_grandchild
1 failed, 2045 passed, 6 skipped, 32 xfailed, 15 warnings in 1298.45s (0:21:38)
```
**Residual, pre-existing, unrelated to this unit:** `test_flake_probe_real_process.py`'s one test
spawns a real OS grandchild process, times it out at a real 10s bound, and asserts the grandchild
is dead — sensitive to process-kill semantics of the host it runs on (same class of issue as the
documented `AT-196` flake in `qa/contracts/core-invariants.md`). Confirmed unrelated: that file
was last touched 2026-09-18 (`git log -1`, well before this unit), is absent from `git status`
and from this unit's diff, and re-running it alone (`uv run pytest
tests/test_flake_probe_real_process.py`) reproduces the same failure deterministically on this
host — so it is an environment-sensitivity issue in a pre-existing test, not a regression this
unit introduced, and not something T-125/AT-588 code touches.

## Capability coverage

Every falsifying edit below was applied to a **standalone scratch copy** built from
`git ls-files` (tracked content) + the new untracked test file, with its own `uv`-managed `.venv`
(so its own editable install resolves against the scratch copy, not the bound tree), under
`C:\Users\Lenovo\AppData\Local\Temp\claude\...\scratchpad\t125-full` — never in
`D:/autoTesting/.worktrees/t125-catalog`. Each anchor was confirmed to match **exactly once**
before the edit; the bound tree was untouched throughout (confirmed by `git status --short`
before and after).

| Capability | Covering check | Falsifying edit | Before (green) | After (red) |
|---|---|---|---|---|
| OAuth sign-up pack detected from a Google CLICK/NAVIGATE step | `test_oauth_signup_pack_detected_and_runnable`, `test_unapproved_flowspec_blocks_every_pack_not_approved` (`stages/catalog.py::_has_oauth_signup_carryover`) | `if "google" in text or "oauth" in text or "accounts.google.com" in text:` → `if False:  # MUTATION` | `9 passed` | `3 failed` (`test_unapproved_flowspec_blocks_every_pack_not_approved`, `test_oauth_signup_pack_detected_and_runnable`, `test_oauth_signup_pack_blocked_missing_credential_names_the_key`) — `AssertionError: assert False is True` on `oauth.applicable` |
| Month/year date-picker pack detected from an `InputField.type` | `test_date_picker_pack_detected_from_field_type` (`stages/catalog.py::_has_date_picker_month_year`) | `if field.type.lower() in {"date", "month", "year"}:` → `if field.type.lower() in {"nope_never_matches"}:` | `9 passed` | `1 failed` — `AssertionError: assert False is True` on `entry.applicable` |
| Excel column-mapping pack detected from an UPLOAD step naming a spreadsheet | `test_excel_column_mapping_pack_detected_from_upload_step` (`stages/catalog.py::_has_excel_column_mapping`) | `for ext in (".xlsx", ".xls", ".csv", "excel")` → `for ext in ("nope_never_matches",)` | `9 passed` | `1 failed` — `AssertionError: assert False is True` on `entry.applicable` |
| OAuth pack blocks on `missing_credential` (never runs against an unset Google-flow secret) | `test_oauth_signup_pack_blocked_missing_credential_names_the_key` (`stages/catalog.py::_pack_entries`) | `if pack is StandardPack.OAUTH_SIGNUP_CARRYOVER and missing_auth_keys:` → `if False:  # MUTATION` | `9 passed` | `1 failed` — `AssertionError: assert True is False` on `entry.runnable` (pack wrongly reports runnable with no credential) |
| No FlowSpec blocks every pack (not just every `CaseClass`) | `test_no_flowspec_blocks_every_pack_no_flowspec` (`stages/catalog.py::_pack_entries`, no-flowspec branch) | `_blocked_pack(p, applicable=False, ...)` → `_blocked_pack(p, applicable=True, ...)` in the no-flowspec list comprehension | `9 passed` | `1 failed` — `AssertionError` on `p.applicable is False` |

Each row's mutation was reverted and the scratch suite re-confirmed `9 passed` before moving to
the next row (shown live in the session's tool transcript; not re-pasted five times here to keep
this manifest readable — the pattern is identical each time: green → one anchor-matched-once edit
→ red for the named assertion → revert → green).

## Live browser evidence

Not UI-touching in the sense of a rendered browser walkthrough — this unit's UI surface is a
read-only server-rendered HTML table (`GET /projects/{slug}/catalog`), already covered by
`TestClient`-based `tests/test_ui_catalog.py` assertions on the rendered HTML (CT8-style: pack
labels, "not applicable" pill, reason+action text). No Playwright/browser walk was run.
Changed paths: `src/autotester/schema/catalog.py`, `src/autotester/stages/catalog.py`,
`src/autotester/ui/routes_catalog.py`, `tests/test_ui_catalog.py`, `tests/test_catalog_packs.py`,
`docs/MAP.md` (regenerated).

## What changed

- `src/autotester/schema/catalog.py` — `StandardPack`, `PackEntry`, `Catalog.packs` + `.pack()`.
- `src/autotester/stages/catalog.py` — pack detectors, `_pack_entries`, wired into `catalog()`.
- `src/autotester/ui/routes_catalog.py` — packs table on the catalog page.
- `tests/test_catalog_packs.py` (new) — 9 tests for the AT-588 packs.
- `tests/test_ui_catalog.py` — 3 tests for the packs table rendering.
- `docs/MAP.md` — regenerated (`autotester map`) to pick up `StandardPack`/`PackEntry`.

## Open items

- `qa/issues.jsonl`'s AT-588 row is left `"status": "open"` — that ledger is checker-owned per
  this repo's CLAUDE.md ("Open issues: qa/issues.jsonl (canonical)... Only `/checker` can PASS a
  unit"); flipping it to `fixed` is the checker's action on PASS, not the maker's.
  `qa/contracts/catalog.md` is DRAFT and checker-owned; I did not amend it, but note here that its
  CT1-CT8 text (all about `CatalogEntry`) does not yet mention `PackEntry`/`StandardPack` — a
  checker amendment naming the pack extension explicitly would remove the one remaining ambiguity
  (that packs are additive, not CT2-governed) for a future reader.
- `test_flake_probe_real_process.py`'s one real-process test fails deterministically on this host
  (see "Actual outputs" above) — pre-existing, unrelated to T-125/AT-588, not fixed here.

**Status: ready-for-check**
