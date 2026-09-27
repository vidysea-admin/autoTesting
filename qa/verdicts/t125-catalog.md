# Verdict — t125-catalog

**Date:** 2026-09-27
**Cycle checked:** 1
**Mode:** A (unit check), with Mode D (live browser) — the unit renders `GET /projects/{slug}/catalog`.
**Checker:** fresh Claude Sonnet subagent, read-only toward the artifact, bound to
`D:/autoTesting/.worktrees/t125-catalog`.
**Scope:** the whole T-125 catalog, both commits — `cfc13b0b` (the original catalog, never
previously checked — no manifest existed for it) and `2e397500` (AT-588 standard-pack
extension), with `b1befe89` a clean master merge in between. Base for diff-scope:
`git merge-base master wave/t125-catalog` = `c473ceb8`.

## VERDICT: FAIL

## SCOREBOARD: 5/8 criteria met, 0/0 invariants (contract declares no separate `[I*]` list)

| Criterion | Result | Notes |
|---|---|---|
| CT1 pure/deterministic | PASS | `catalog()` reads only `project`/`spec`/`.env` presence; no `Provider`/network/write. `test_catalog_is_pure_same_inputs_same_output` re-run green. |
| CT2 every CaseClass once | PASS | `TIER_BY_CLASS` key set == `set(CaseClass)`; `packs` correctly NOT governed by CT2 (contract now says so explicitly, see amendment below). |
| CT3 closed BlockedReason | PASS | Exactly 6 values, `extra="forbid"`, present iff blocked — confirmed by code + tests. |
| CT4 no-FlowSpec blocks everything | PASS | Every `CaseClass` and every pack blocked `no_flowspec`; page renders it (`test_no_flowspec_page_renders_the_reason_on_every_row...` green). |
| CT5 missing-credential names the KEY | **FAIL** | See ISS-t125-2 below — the action text names every missing key project-wide, not just the one this entry needs. |
| CT6 tier ordering real in `routes_runs.py` | **FAIL** | See ISS-t125-1 below — `tiers_to_run()` is correct and tested in isolation but is never called from `routes_runs.py::trigger_run`; the dispatch behaviour CT6 requires does not exist in the running system. |
| CT7 one Catalog/BlockedReason | PASS | `grep -rn "^class Catalog\b" src/` and `^class BlockedReason\b` each return exactly one hit (`schema/catalog.py`). `StandardPack`/`PackEntry` live in the same file, reuse `BlockedReason`, no `stages/ai_catalog.py` exists yet (T-152, correctly out of scope). |
| CT8 blocked row states reason + the one action | **FAIL** | Same root cause as CT5 — a row's action names a union of keys, one of which may be irrelevant to that row, so it is not "the one action that clears" it. |

## Re-derivation of the manifest's central claim (item 1 of the dispatch)

The manifest states it "read `qa/contracts/catalog.md` end to end against `stages/catalog.py`/
`schema/catalog.py`" for the pre-existing `cfc13b0b` code and found "CT4/CT5/CT6/CT8: covered by
the existing... tests. No gaps found — the unit's only real defect was the missing manifest, not
the code." Re-deriving this line by line:

- **CT6 does not hold.** `stages/catalog.py::tiers_to_run()`'s own docstring says plainly: *"Not
  yet wired into `ui/routes_runs.py::trigger_run`... Reconciling RU3 with tiered stopping is a
  contract-level call outside D-039's Changes-authorized scope... left as a named gap, not
  silently resolved either direction."* `cfc13b0b`'s own commit message says the same thing. This
  is an honest disclosure, not a hidden defect — but it directly contradicts "no gaps found": CT6
  as literally worded ("`routes_runs.py`'s tiered dispatch runs static before behavioural before
  adversarial, and STOPS...") describes behaviour the shipped system does not have.
  `grep -rn "stages.catalog\|tiers_to_run\|Tier\b" src/autotester/ui/routes_runs.py` returns
  nothing. All three CT6 tests in `tests/test_catalog.py` call `tiers_to_run(cat)` directly and
  never touch `routes_runs.py`, so nothing in the suite could have caught this — filed as
  **ISS-t125-1**, severity high. This is a genuine conflict between two ACTIVE contracts
  (`catalog.md` CT6 vs `ui-run.md` RU3) that needs a human decision, not a unilateral resolution
  by maker or checker — see the issue's `expected` field.
- **CT5/CT8 do not hold under more than one flow.** Every existing fixture (in both
  `test_catalog.py` and the new `test_catalog_packs.py`) declares exactly one credential-consuming
  flow at a time, so `_missing_keys(project, _auth_secret_keys(spec))`'s global (whole-FlowSpec,
  not per-flow) computation never gets a chance to leak an irrelevant key into a row that doesn't
  need it. Live Mode D walk below reproduces this with two flows and two secrets — filed as
  **ISS-t125-2**, severity high.
- CT1, CT2, CT3, CT4, CT7 genuinely do hold, both for the pre-existing code and after the AT-588
  extension — re-verified independently above, not taken on the manifest's word.

## CAPABILITY-COVERAGE: 5/5 rows reproduced

All five rows re-derived independently, **never in the bound tree**. Built a scratch copy from
`git ls-files` (tracked content only; working tree was clean, `git status --short` empty both
before and after) at
`C:\Users\Lenovo\AppData\Local\Temp\claude\...\scratchpad\t125-catalog-check`, ran `uv sync` there
(its own venv, its own editable install). **Proved the copy was real, not shadowed**, two ways:
(1) `.venv/Scripts/python -c "import autotester.stages.catalog as m; print(m.__file__)"` resolved
to the **scratch copy's** path, not the bound tree's; (2) inserted an unconditional
`raise RuntimeError("CANARY-MUTATION-CHECKER")` at the top of `catalog()`, ran
`tests/test_catalog_packs.py`, got 8 failed/1 passed with the canary's own traceback visible, then
reverted and got `9 passed` again — the same class of falsification-that-proves-nothing trap the
manifest's own disclosure names (PYTHONPATH shadowing) does not apply here.

For each row: reverted to a clean baseline, ran the **named** test file, applied the **exact**
single-hunk edit quoted in the manifest's table (anchor matched exactly once each time, confirmed
by `assert s.count(old) == 1` before writing), re-ran the same test file, then reverted again
(confirmed byte-identical to the original via `diff` at the end) before starting the next row.

| Capability | Before (checker, in scratch copy) | After (checker) | Matches manifest? |
|---|---|---|---|
| OAuth pack detected from Google CLICK/NAVIGATE | `9 passed` | `3 failed` — `test_unapproved_flowspec_blocks_every_pack_not_approved`, `test_oauth_signup_pack_detected_and_runnable`, `test_oauth_signup_pack_blocked_missing_credential_names_the_key`, `AssertionError: assert False is True` on `.applicable` | Yes, exactly |
| Date-picker pack detected from field type | `9 passed` | `1 failed` — `test_date_picker_pack_detected_from_field_type`, `assert False is True` on `.applicable` | Yes, exactly |
| Excel pack detected from UPLOAD step | `9 passed` | `1 failed` — `test_excel_column_mapping_pack_detected_from_upload_step`, `assert False is True` on `.applicable` | Yes, exactly |
| OAuth pack blocks on missing_credential | `9 passed` | `1 failed` — `test_oauth_signup_pack_blocked_missing_credential_names_the_key`, `assert True is False` on `.runnable` | Yes, exactly |
| No-FlowSpec blocks every pack | `9 passed` | `1 failed` — `test_no_flowspec_blocks_every_pack_no_flowspec`, `assert False` on `all(p.applicable is False and p.runnable is False ...)` | Yes, exactly |

Every row's assertion fired for the named reason (not a parse/import-level blanket failure) —
confirmed by reading each traceback, not just the pass/fail count. Bound tree confirmed untouched
throughout (`git status --short` empty before and after the whole exercise).

## LIVE-BROWSER: `qa/evidence/browser-t125-catalog-2026-09-27-checker/report.json`

Drove a real browser (Playwright) against the bound tree's own code — `uv run uvicorn
autotester.ui.app:app` launched from `D:/autoTesting/.worktrees/t125-catalog`, `AUTOTESTER_ROOT`
pointed at an isolated scratch data directory (never the bound tree's own `projects/`), seeded via
a script that calls the bound tree's real `ProjectStore`/schema (read-only toward the tree; writes
only to the scratch data dir). Server killed afterward (`taskkill /F /PID`), confirmed down
(`curl` → connection refused).

Fixture: a project with **two** flows, each needing a different unset secret (login needs
`DEMO_PASSWORD`, a Google sign-up flow needs `GOOGLE_SIGNUP_TOKEN`) — chosen specifically because
every existing unit test uses only one flow/one secret at a time, which is exactly the gap that
hides ISS-t125-2.

- `GET /projects/demo/catalog` → 200, 0 console errors/warnings. Case-class table showed a real
  mix of states (`happy` etc. green "runnable"; `double_submit` warning "needs a wider write
  policy..."; `auth_wrong_creds`/`auth_expired_session` warning "missing credential..."). Packs
  table showed `Month/year picker` and `Excel column-mapping upload` as "not applicable" (neutral,
  Applicable=no) side by side with `OAuth sign-up carry-over` as "missing credential"
  (Applicable=yes) — **the three-way distinction (runnable / blocked-with-reason /
  not-applicable) does survive into the UI and is not collapsed to two states** (item 4 of the
  dispatch, confirmed rather than assumed from the test's name alone).
  **But**: `auth_wrong_creds`, `auth_expired_session`, and the OAuth pack row all rendered the
  identical text *"missing credential — set DEMO_PASSWORD, GOOGLE_SIGNUP_TOKEN in the repo-root
  .env"* — i.e. every missing-credential row on the page names **both** keys, regardless of which
  one that row's own flow actually reads. Filed as **ISS-t125-2**.
- `GET /projects/nope/catalog` → 404 (expected, matches `test_catalog_page_404s_for_an_unknown_project`).
  The one console error logged is the browser's own "Failed to load resource: 404" for the main
  document — not a defect.
- Screenshot: `qa/evidence/browser-t125-catalog-2026-09-27-checker/catalog-page.png`.

## Diff scope (step 4c)

`git diff c473ceb8..HEAD --stat`: 9 files, **all additions, zero deletions/renames**
(`src/autotester/schema/catalog.py`, `src/autotester/stages/catalog.py`,
`src/autotester/ui/routes_catalog.py`, `src/autotester/ui/app.py` [+2 lines, router
registration], `tests/test_catalog.py`, `tests/test_catalog_packs.py`, `tests/test_ui_catalog.py`,
`docs/MAP.md`, `qa/manifests/t125-catalog.md`). No existing function/class/export/test/config key
was removed or renamed anywhere in the unit's history. `ui/app.py`'s 2-line router registration is
not separately named in the manifest's "What changed" list, but it is trivial, necessary plumbing
for `routes_catalog.py` (itself disclosed in "Starting state") and not a scope-creep concern.

## Test-split check (item 5 of the dispatch)

`git diff cfc13b0b 2e397500 -- tests/test_catalog.py` is **empty** — `test_catalog.py` was not
touched by the AT-588 commit at all. The manifest's phrase "split from `test_catalog.py`" is
imprecise: nothing was moved out of it; `test_catalog_packs.py` is wholly new tests for wholly new
capability. Net effect: **no coverage was lost or weakened** (confirmed: zero deletions in the
whole diff, `test_ui_catalog.py`'s diff is a pure append of 3 new tests, nothing existing changed).
This is a manifest-wording accuracy note, not a defect — not filed as an issue.

## CT7 (item 3 of the dispatch)

`grep -rn "^class Catalog\b" src/` → exactly one hit (`schema/catalog.py:120`).
`grep -rn "^class BlockedReason\b" src/` → exactly one hit (`schema/catalog.py:21`).
`StandardPack`/`PackEntry` live in the same three files as `CatalogEntry`/`Catalog`
(`schema/catalog.py`, `stages/catalog.py`, `ui/routes_catalog.py`) — no parallel catalog module,
`stages/ai_catalog.py` does not exist yet (T-152, correctly out of scope per the no-fire list).
CT7 holds.

## Verify commands re-run myself

```
$ uv run pytest tests/test_catalog.py tests/test_catalog_packs.py tests/test_ui_catalog.py
37 passed, 1 warning in 4.15s

$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester doctor
doctor: clean
```
All three match the manifest's pasted output. Did not re-run the full suite (21+ minutes; the
targeted suite plus the independent capability-coverage re-derivation is the checker's evidence
here) — the manifest's disclosed pre-existing flake
(`test_flake_probe_real_process.py::test_run_once_kills_a_real_hung_process_and_its_real_grandchild`,
AT-627) is accepted as not chargeable to this unit per the dispatch's own note; no second failure
found.

## Contract maintenance performed this check

`qa/contracts/catalog.md` was DRAFT with no mention of `StandardPack`/`PackEntry`. Added a routine
(non-weakening) section documenting them — they reuse `BlockedReason` (CT7 applies), are additive
and not governed by CT2, and CT5/CT8's naming requirements apply to `PackEntry.unblock_action`
too — plus updated the verify command to include `tests/test_catalog_packs.py`. Logged in the
contract's amendment log as `routine`. **Status remains DRAFT** — DRAFT→ACTIVE requires a PASS,
and this cycle is a FAIL.

## Issues addressed (manifest's claim)

AT-588 ("no standard test packs") — the three packs are built, detected, and rendered, and 4/5 of
the pack-specific capability rows are clean. However the same code path (the OAuth pack's
missing-credential handling) is implicated in ISS-t125-2, and the unit's overall verdict is FAIL,
so **AT-588 stays `open`**, not flipped to `fixed` — matching this checker's ledger discipline
("each one must actually be fixed by this unit or it stays open") and the fact that a live defect
was found in the exact code AT-588 shipped.

## FAILURES

- [CT6] sev: high · `routes_runs.py`'s tiered dispatch (the dispatch behaviour CT6 requires)
  does not exist — `tiers_to_run()` is unused pure code · needs a HUMAN_GATE reconciling CT6
  against the ACTIVE `ui-run.md` RU3 before either contract or code changes · issue: ISS-t125-1
- [CT5, CT8] sev: high · a missing-credential row's `unblock_action` names every declared secret
  key missing anywhere in the whole FlowSpec, not just the one that row's flow needs, reproduced
  live with two flows/two secrets · scope `_auth_secret_keys`/`_missing_keys` per the relevant
  flow(s), add a two-flow/two-secret test · issue: ISS-t125-2

## CAPABILITY-COVERAGE: 5/5 rows reproduced

## LIVE-BROWSER: qa/evidence/browser-t125-catalog-2026-09-27-checker/report.json

## ISSUES-WRITTEN: ISS-t125-1, ISS-t125-2

## EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent — independent fresh session, no `ANTHROPIC_BASE_URL` override)

## EXPLANATION

CT1/CT2/CT3/CT4/CT7 hold, independently re-derived, and the AT-588 pack extension is well-built
on its own terms — the pack detectors are correct (all 5 capability-coverage rows reproduced
cleanly), packs correctly avoid a second `Catalog`/`BlockedReason`, and the three-way
runnable/blocked/not-applicable distinction genuinely survives into the live UI. But this is
T-125's first-ever checker pass (contract was DRAFT with no prior verdict, `cfc13b0b` shipped
seven days ago with zero checking), and the dispatch's core instruction — re-derive the "already
satisfied" claim rather than accept it — surfaced two real, high-severity gaps that the manifest's
line-by-line re-read missed: CT6's dispatch integration was disclosed as absent in the code's own
docstring but not registered as a CT6 gap, and CT5/CT8's "one action" promise breaks the moment a
FlowSpec has more than one credential-consuming flow, which no existing test constructs. Neither
is a regression introduced by AT-588 in the sense of new breakage — CT6's gap predates it entirely,
and CT5/CT8's gap is a latent design issue AT-588's second flow happened to make visible — but
both are real, both are evidenced, and per this contract's own DRAFT→ACTIVE gate, a first check
that finds unresolved CT gaps must not soften them into passes to unblock the ledger.
