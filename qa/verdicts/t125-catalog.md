# Verdict — t125-catalog

**Date:** 2026-09-27
**Cycle checked:** 2
**Mode:** A (unit check), with Mode D (live browser, own fixture)
**Checker:** fresh Claude Sonnet subagent, read-only toward the artifact, bound to
`D:/autoTesting/.worktrees/t125-catalog` (branch `wave/t125-catalog`, commit `72f71aa1`).
**Answers:** `qa/verdicts/t125-catalog.md` cycle-1 body below (FAIL, 5/8, CT5/CT6/CT8), verdict
commit `3da63550`; and `qa/manifests/t125-catalog.md`'s "# Cycle 2" section.

## VERDICT: FAIL

## SCOREBOARD: 5/8 criteria met (CT1-4, CT7 pass; CT5, CT6, CT8 do not)

| Criterion | Cycle 1 | Cycle 2 | Notes |
|---|---|---|---|
| CT1 pure/deterministic | PASS | PASS | Unchanged this cycle; re-confirmed via `test_catalog_is_pure_...`. |
| CT2 every CaseClass once | PASS | PASS | Unchanged. |
| CT3 closed BlockedReason | PASS | PASS | Unchanged. |
| CT4 no-FlowSpec blocks everything | PASS | PASS | Unchanged. |
| CT5 missing-credential names the KEY | FAIL | **FAIL (new cause)** | ISS-t125-2's exact 2-flow repro is fixed. But the fix's OAuth/other split has its own scoping failure — see ISS-t125-3 below. |
| CT6 tier ordering real in `routes_runs.py` | FAIL | **GATED** (see ruling below) | Conflict verified real; correctly disclosed and not resolved unilaterally. Still not evidenced, so still blocks 8/8, but not chargeable to the maker as an unaddressed defect. |
| CT7 one Catalog/BlockedReason | PASS | PASS | Unchanged; `test_packs_never_add_a_second_catalog_or_blocked_reason_definition` re-confirmed. |
| CT8 blocked row states reason + the one action | FAIL | **FAIL (new cause)** | Same root cause as CT5 this cycle. |

## ISS-t125-2 (CT5/CT8) — the maker's claimed fix, re-derived

**The claim:** `catalog()` now computes two scopes instead of one union — the OAuth pack's missing
keys come from `_oauth_signup_flow_ids(spec)`-tagged flows, and the generic auth classes' missing
keys come from every other flow — so a row no longer advertises an irrelevant key.

**Re-run of the maker's own capability-coverage rows (in a throwaway `git archive HEAD` copy,
`…/scratchpad/t125c2-falsify`, own venv, proven to resolve its own source before any edit —
`.venv/Scripts/python -c "import autotester.stages.catalog as m; print(m.__file__)"` printed the
scratch path):**

| Capability | Before (copy, green) | After (copy, red) | Matches manifest? |
|---|---|---|---|
| Auth row does not advertise a sign-up-only key | `12 passed` | `2 failed` — both `test_an_auth_row_does_not_advertise_a_signup_only_key` and `test_the_oauth_pack_does_not_advertise_a_login_only_key`, on the single-hunk union-collapse edit the manifest names | Yes, exactly |
| OAuth pack does not advertise a login-only key | (same edit, same run) | (same edit, same run) | Yes, exactly |
| OAuth-only spec still names its keys (fallback branch) | `12 passed` | **1 failed** (isolated — see below) | **Better than claimed** |

The manifest disclosed the third row as "not independently falsified... that edit also changes
the other two rows' behaviour." I found a narrower single-hunk edit that isolates it cleanly:
changing `only=other_ids or None` to `only=other_ids` in `catalog()` (removing just the empty-set
fallback) makes `test_an_oauth_only_spec_still_names_its_keys_rather_than_nothing` fail
(`unblock_action` becomes `None`) while `test_an_auth_row_does_not_advertise_a_signup_only_key`
and `test_the_oauth_pack_does_not_advertise_a_login_only_key` both stay green
(`1 failed, 2 passed, 9 deselected`). **Capability coverage for cycle 2's three claimed rows is
therefore 3/3, not 2/3 — the manifest was honest but overly pessimistic about its own gap.**
Reverted; copy confirmed green again (`12 passed`) before moving on.

**Attacking the scoping rule (the dispatch's core ask) — built my own two-project fixture,
independent of the maker's, and drove my own browser against it (see LIVE-BROWSER below):**

1. **Two non-OAuth login flows needing different keys** (`demo-twologin`: consumer login needs
   `CONSUMER_PASSWORD`, admin login needs `ADMIN_TOKEN`, neither set). **Result: the auth row still
   names a union** — `"set CONSUMER_PASSWORD, ADMIN_TOKEN in the repo-root .env"` on both
   `auth_wrong_creds` and `auth_expired_session`. Narrower than cycle 1's whole-project union (no
   OAuth-only key leaks in), but a union nonetheless. **I am not filing this as a new blocking
   issue.** The manifest explicitly named this exact scenario as a design question for me to rule
   on, not a hidden defect: `_entry_for()` has no per-flow granularity for the generic auth
   classes, only OAuth-vs-other, and CT2 pins one row per `CaseClass` project-wide. Fully scoping
   this would need either a flow-aware `CaseClass` (a CT2 rewrite) or per-flow sub-rows (a CT8
   rewrite) — genuinely out of ISS-t125-2's blast radius. Recorded here so it isn't rediscovered as
   a surprise; not filed as an issue.
2. **A flow whose OAuth signal is incidental** — one flow that both CLICKs "Sign up with Google"
   AND FILLs the product's own password (`demo-hybrid`, `HYBRID_PASSWORD` unset). **Result: the
   credential requirement vanishes entirely.** `auth_wrong_creds` and `auth_expired_session` both
   render the green "runnable" pill — not a warning, not any mention of `HYBRID_PASSWORD` — even
   though it is the only secret the project declares and the only credential the product's own
   login path uses. Root cause: `_oauth_signup_flow_ids()` classifies the whole flow as OAuth
   (it has a Google CLICK step), excluding it from `other_ids`; the one other flow in the fixture
   has no FILL step at all, so `_auth_secret_keys(spec, only=other_ids)` returns `[]`, and
   `_entry_for()`'s `if case_class in _AUTH_CLASSES and missing_auth_keys` guard is simply False.
   **This is worse than the defect it replaces:** cycle 1 told the operator an irrelevant action
   (misleading but visible); this tells the operator nothing is wrong at all, and the case will
   fail for real the moment it runs, because `{{SECRET:HYBRID_PASSWORD}}` has no value to
   substitute. **Filed as ISS-t125-3, severity high.** CT5/CT8 stay FAIL on this new ground.
3. **Verified the OAuth-only fallback branch, which the maker flagged as tested but not
   independently falsified** — done above (item 3 of the capability table); it is real and
   correctly designed for the single-flow case it targets. It does not, however, protect the
   hybrid case above, because in that fixture `other_ids` is non-empty (`{'flow_other'}`), so the
   `or None` fallback never triggers — the bug is not in the fallback, it is in the primary split.

**My ruling on the scoping rule, since the manifest explicitly asked for it:** "the auth classes
are about every flow that is NOT an OAuth-signal flow" is the wrong rule. A flow can legitimately
be both a Pack-1 signal source (for `PackEntry` applicability) and a source of generic auth
secrets (for `CatalogEntry` blocking) at the same time — these are not mutually exclusive, and the
current code treats OAuth-classification as if it exhaustively removes a flow from the "product's
own credential form" category. The fix is the rule, exactly as the manifest itself anticipated:
scope by which flows actually reference a FILL-step secret relevant to each concern, not by a
single OAuth/non-OAuth partition of flow ids.

## ISS-t125-1 / CT6 — ruling: GATED, not a maker failure this cycle

**Verified the conflict is real, independently:**
- `grep -rn "stages.catalog|tiers_to_run|Tier" src/autotester/ui/routes_runs.py` — no matches,
  confirmed myself.
- Read `routes_runs.py::trigger_run` in full: `cases = store.list_cases()` then every case runs
  through `_execute_with_trace` unconditionally — no tier filtering, no early stop.
- Read `qa/contracts/ui-run.md` RU3 in full: "Every case in `store.list_cases()` gets a real
  result + verdict saved... a `Run` record is saved" — no tier exception exists in the ACTIVE text.
- Read `plan.md` §5A (lines 505-524) directly: it explicitly authorizes the STOP behaviour
  ("`routes_runs.py` runs tiers in order and stops a tier that has no runnable entries, so a cheap
  structural failure is reported before an expensive graded run is paid for") — so CT6 is not an
  invented overreach, it is D-039's own authorized text. The conflict with RU3 is real on both
  sides, not manufactured by either the maker or the cycle-1 checker.
- Read `docs/FEATURES.jsonl` F-058 directly: "Every regression run already runs every case on
  file" — confirming RU3's guarantee is a shipped, user-facing promise this contract already made,
  not a hypothetical.

**Judging the gate file's four options:** honestly costed. A (ordering/reporting only, no
skipping) keeps RU3/F-058 intact at the price of losing CT6's actual cost-saving; B (amend RU3 with
a pinned-case exemption) keeps the saving at the price of a real regression-hiding surface; C
(opt-in flag) keeps both true by default at the price of a second dispatch path; D (retire CT6) is
honest but throws away a plan.md-authorized feature. I don't find a materially different fifth
option — a "separate async endpoint that stops tiers" is C in different clothing (still two
dispatch paths to keep honest), and doesn't change the cost/benefit table.

**Ruling: CT6 is GATED, awaiting Umesh's decision at
`qa/gates/t125-ct6-tiered-dispatch-vs-ru3.md`.** This is not the same as a FAIL the maker could
have avoided — `tiers_to_run()` is correct, tested, and deliberately left unwired because wiring it
either direction would mean the maker (or this checker) amending one of two ACTIVE contracts
unilaterally, which neither is authorized to do. The unit still cannot reach 8/8 this cycle
(a gate is not evidence), but the cycle-cap clock should not run out on the maker for a criterion
that requires a human decision it correctly refused to make itself. ISS-t125-1 stays `open`.

## Diff scope (step 4c) — cycle 2 only

`git diff 3da63550..HEAD --stat`: 4 files, all additions except one in-place edit —
`qa/gates/t125-ct6-tiered-dispatch-vs-ru3.md` (new), `qa/manifests/t125-catalog.md` (append),
`src/autotester/stages/catalog.py` (+54/-14, the scoping fix, reviewed hunk-by-hunk above — no
existing function/test/export removed, only `_auth_secret_keys` gained a keyword arg and
`_oauth_signup_flow_ids` was added), `tests/test_catalog_packs.py` (+88, new tests only). No file
outside the manifest's "What changed" was touched. No regression against the whole-branch diff
scope either (`git diff master...HEAD --stat` re-run: same 16 files as cycle 1, all
additions/one in-place edit, nothing removed).

## LIVE-BROWSER: `qa/evidence/t125-catalog-2026-09-27-checker-cycle2/report.json`

Own fixture, independent of the maker's (which was never re-run). `uv run uvicorn
autotester.ui.app:app` from the bound worktree, `AUTOTESTER_ROOT` pointed at an isolated scratch
data dir (never the bound tree's own `projects/`), seeded via a script calling the bound tree's
real `Project`/`FlowSpec`/`ProjectStore` (read-only toward the tree; writes only to the scratch
data dir). Server killed afterward, confirmed down.

- `GET /projects/demo-hybrid/catalog` → 200, 0 console errors/warnings. `auth_wrong_creds` /
  `auth_expired_session` render "runnable" (should be blocked — see ISS-t125-3); OAuth pack
  correctly renders "missing credential — set HYBRID_PASSWORD in the repo-root .env". Screenshot:
  `qa/evidence/t125-catalog-2026-09-27-checker-cycle2/hybrid-catalog.png`.
- `GET /projects/demo-twologin/catalog` → 200, 0 console errors/warnings. Both auth rows render
  "missing credential — set CONSUMER_PASSWORD, ADMIN_TOKEN in the repo-root .env" (narrower union,
  documented above, not filed). Screenshot:
  `qa/evidence/t125-catalog-2026-09-27-checker-cycle2/twologin-catalog.png`.

**Note on evidence placement:** my first pass wrote these two screenshots to the repo root
(`d:/autoTesting/*.png`), which core-invariants C4 forbids. Moved into
`qa/evidence/t125-catalog-2026-09-27-checker-cycle2/` before this commit; repo root confirmed
clean (`git status --short` at root shows nothing untracked there now).

## Verify commands re-run myself

```
$ uv run pytest tests/test_catalog.py tests/test_catalog_packs.py tests/test_ui_catalog.py
40 passed, 1 warning in 0.97s

$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester doctor
doctor: clean

$ wc -l src/autotester/stages/catalog.py tests/test_catalog_packs.py
296 src/autotester/stages/catalog.py   (at the 300-line C2 cap — any further growth needs a split,
                                        confirmed, matches manifest)
267 tests/test_catalog_packs.py
```

All match the manifest's pasted output exactly.

**Full suite (`uv run pytest`, bare, no CLI `-q`, AT-503):** run in full by me this cycle, in the
background while the rest of this check proceeded (two peer checkers running concurrently per the
coordinator's live note):

```
2050 passed, 5 skipped, 32 xfailed, 15 warnings in 730.34s (0:12:10)
DONE_0
```

**Clean exit, zero failures** — none of the four known-flaky/load-sensitive tests
(`test_flake_probe_real_process.py` AT-627, `test_mutation_check_judgement`,
`test_redact_wrap_perf`, `test_crawl_inventory_live`) tripped on this run. Nothing beyond this
unit's own two new issues (ISS-t125-3, ISS-t125-4) was found anywhere in the suite.

## Audience / persona-walk check (step 5bb)

Manifest: `Persona walk: skip (backend catalog, no UI surface beyond a read-only table...)`. This
reasoning is imprecise — the unit's diff includes `src/autotester/ui/routes_catalog.py`, a real UI
route (`GET /projects/{slug}/catalog`); there IS a UI surface. The skip's *substance* is
defensible (this is an internal-tool operator diagnostic page, not a Vidysea end-user screen; no
`audience`/`personas` field is declared in `qa/adapter.json`, so the internal-tool default — 1-2
types, no literacy lens — applies by convention), and my own Mode D walk this cycle exercised the
page as an operator would (readable pills, case-specific action text, no dead ends). Filed as
**ISS-t125-4, severity low** — a manifest-wording hygiene note, not a functional defect; does not
affect the scoreboard.

## Contract maintenance performed this check

None this cycle. `qa/contracts/catalog.md`'s "Standard packs" section (added cycle 1) already
covers `PackEntry` correctly; no further amendment is needed by cycle 2's findings — ISS-t125-2/
ISS-t125-3 are code defects against the existing CT5/CT8 wording, not contract gaps. Status remains
DRAFT.

## Issues addressed (manifest's claim)

AT-588 stays `open` — left there by the maker's own choice ("the same code path is implicated in
ISS-t125-2... the checker owns that flip"), correctly so: ISS-t125-3 implicates the exact same
code path (`catalog()`'s scoping logic) this cycle too.

## FAILURES

- [CT5, CT8] sev: high · a hybrid flow (CLICK "Sign up with Google" + FILL its own password in the
  SAME flow) makes `_oauth_signup_flow_ids()` classify it as OAuth-only, excluding it from
  `other_ids`; if no other flow references a secret, the generic auth classes' missing-key list is
  empty and the row wrongly reports `runnable=True` — the credential requirement disappears
  entirely rather than being named · scope by secret-reference relevance, not by an exhaustive
  OAuth/non-OAuth partition of flow ids; add a hybrid-flow test fixture · issue: ISS-t125-3
- [CT6] sev: high, ruling: GATED not FAIL-on-maker · `routes_runs.py::trigger_run` has no tier
  filtering (confirmed via grep + full read); conflicts with ACTIVE `ui-run.md` RU3 and F-058's
  shipped guarantee ("every regression run already runs every case on file"); genuinely
  irresolvable without a human decision between the four costed options in
  `qa/gates/t125-ct6-tiered-dispatch-vs-ru3.md` · needs Umesh's answer, not a code change · issue:
  ISS-t125-1

## CAPABILITY-COVERAGE: 3/3 cycle-2 rows reproduced (better than the manifest's own 2/3 + 1
UNVERIFIED claim — I isolated the fallback-branch row too; see ISS-t125-2 section above). Cycle-1's
5/5 rows were not re-verified this cycle (unchanged code paths; diff-scope check confirms no
existing test or function was touched).

## LIVE-BROWSER: qa/evidence/t125-catalog-2026-09-27-checker-cycle2/report.json (own fixture, two
projects, screenshots included)

## ISSUES-WRITTEN: ISS-t125-3, ISS-t125-4 (ISS-t125-1 and ISS-t125-2 carried over from cycle 1;
ISS-t125-2 is NOT closed — its exact repro is fixed but the underlying scoping defect recurs under
a different fixture, so it stays `open` pending a fix that survives both fixtures, not just the
one the manifest tested against)

## EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent — independent fresh session,
no `ANTHROPIC_BASE_URL` override)

## EXPLANATION

This cycle's fix genuinely closes the exact gap the cycle-1 checker demonstrated (two flows, two
secrets, no OAuth involved) — re-verified independently, including a fallback-branch isolation the
manifest itself didn't think was possible. But "attack the scoping rule" was the dispatch's central
ask for a reason: the OAuth/non-OAuth partition the fix introduces is not the same thing as
"the flow this row is actually about," and a flow that is incidentally both (a "Sign up with
Google" button on the same screen as a password field — an entirely ordinary real-world pattern)
makes the fix silently drop a credential requirement it used to at least mention. That is a
regression in kind, not degree: cycle 1's bug was a too-broad, visible hint; this cycle's is a
too-narrow, invisible one, and invisible is worse for a catalog whose entire job is honesty about
what's blocked. CT6 is a different story — genuinely gated on a human decision between two
correctly-identified ACTIVE contracts, not a maker shortfall, and I'd ask Umesh not to let this
cycle's CT5/CT8 finding read as "the maker is stalling" on CT6 too. This unit has one cycle left
before the 3-cycle cap; cycle 3 needs to fix ISS-t125-3 with a test fixture that covers the hybrid
case specifically (not just re-running the two fixtures already in `test_catalog_packs.py`), and
CT6 needs Umesh's answer to `qa/gates/t125-ct6-tiered-dispatch-vs-ru3.md` before it can ever reach
PASS, on any cycle.

---

# Cycle 1 verdict (superseded by the above; preserved verbatim per the checker's supersede-not-delete rule)

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

## LIVE-BROWSER (cycle 1): `qa/evidence/browser-t125-catalog-2026-09-27-checker/report.json`

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

## Diff scope (step 4c, cycle 1)

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

## CT7 (item 3 of the dispatch, cycle 1)

`grep -rn "^class Catalog\b" src/` → exactly one hit (`schema/catalog.py:120`).
`grep -rn "^class BlockedReason\b" src/` → exactly one hit (`schema/catalog.py:21`).
`StandardPack`/`PackEntry` live in the same three files as `CatalogEntry`/`Catalog`
(`schema/catalog.py`, `stages/catalog.py`, `ui/routes_catalog.py`) — no parallel catalog module,
`stages/ai_catalog.py` does not exist yet (T-152, correctly out of scope per the no-fire list).
CT7 holds.

## Verify commands re-run myself (cycle 1)

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

## Contract maintenance performed this check (cycle 1)

`qa/contracts/catalog.md` was DRAFT with no mention of `StandardPack`/`PackEntry`. Added a routine
(non-weakening) section documenting them — they reuse `BlockedReason` (CT7 applies), are additive
and not governed by CT2, and CT5/CT8's naming requirements apply to `PackEntry.unblock_action`
too — plus updated the verify command to include `tests/test_catalog_packs.py`. Logged in the
contract's amendment log as `routine`. **Status remains DRAFT** — DRAFT→ACTIVE requires a PASS,
and this cycle is a FAIL.

## Issues addressed (manifest's claim, cycle 1)

AT-588 ("no standard test packs") — the three packs are built, detected, and rendered, and 4/5 of
the pack-specific capability rows are clean. However the same code path (the OAuth pack's
missing-credential handling) is implicated in ISS-t125-2, and the unit's overall verdict is FAIL,
so **AT-588 stays `open`**, not flipped to `fixed` — matching this checker's ledger discipline
("each one must actually be fixed by this unit or it stays open") and the fact that a live defect
was found in the exact code AT-588 shipped.

## FAILURES (cycle 1)

- [CT6] sev: high · `routes_runs.py`'s tiered dispatch (the dispatch behaviour CT6 requires)
  does not exist — `tiers_to_run()` is unused pure code · needs a HUMAN_GATE reconciling CT6
  against the ACTIVE `ui-run.md` RU3 before either contract or code changes · issue: ISS-t125-1
- [CT5, CT8] sev: high · a missing-credential row's `unblock_action` names every declared secret
  key missing anywhere in the whole FlowSpec, not just the one that row's flow needs, reproduced
  live with two flows/two secrets · scope `_auth_secret_keys`/`_missing_keys` per the relevant
  flow(s), add a two-flow/two-secret test · issue: ISS-t125-2

## EXPLANATION (cycle 1)

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
