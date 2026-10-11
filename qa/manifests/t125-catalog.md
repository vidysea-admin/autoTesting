# Manifest — t125-catalog

**Contract:** `qa/contracts/catalog.md` (CT1-CT8, D-039), extended with the AT-588 standard packs.
**Goal task:** T-125 — the test catalog: what applies, what is runnable, what is blocked and why
(+ cheap->expensive ordering).
**Date:** 2026-09-27
**Fix cycle:** 4 (the one scoped cycle D-051 authorises after CT9; no cycle 5)
**Status:** checked-PASS (integration rework, dual PASS: qa/verdicts/t125-catalog.md + t125-catalog.b.md)
**Policy-Version:** proportional-verification/2026-10-06.6 (NO pin existed in this manifest; latest pin in qa/ is .6; the dispatch brief cites ".7" -- orchestrator to confirm which)
**Tier:** L
**Dual check:** required (diff touches HMAC run-approval, D-018/CN10 = security trigger; permits ONE checker full suite)
**Source:** 62a45c6a41fa1640411996c54d14042e92267f4f (branch codex/t125-cycle4)
**Persona walk:** skip — **internal-tool audience**, not "no UI surface". ISS-t125-4 is right that
my earlier wording was false: `ui/routes_catalog.py` IS a real UI route in this diff. The skip stands
on the audience (an operator diagnostic table, not a Vidysea end-user screen) and the checker's own
Mode D walk covered the page both cycles.
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


---

# Cycle 2 — fixing exactly what the cycle-1 verdict listed

**Verdict answered:** `qa/verdicts/t125-catalog.md` (cycle 1, FAIL, 5/8 — CT5, CT6, CT8 failed),
committed `3da63550`. Both filed issues are addressed below; **neither is disputed.** The checker
re-derived CT1-CT8 against the whole catalog rather than only the AT-588 delta, which is what
surfaced them, and it was right to: the cycle-1 manifest's "no gaps found" on CT6 was false.

## ISS-t125-2 (CT5/CT8) — FIXED

**The defect, restated in my own words so the fix can be judged against it:** `catalog()` computed
one global `missing_auth_keys` across every flow, and both `_entry_for()` and `_pack_entries()`
joined that whole list into `unblock_action`. So every blocked row advertised the union of every
unset key in the project. An `auth_wrong_creds` row told the operator to set `GOOGLE_SIGNUP_TOKEN`,
which does nothing for signing in, and the OAuth pack named `DEMO_PASSWORD`, which its flow never
reads. The checker is right that this is worse than vague: an operator who follows a two-action
instruction and finds one of them irrelevant learns the row cannot be trusted.

**Why no existing test caught it:** every fixture had exactly one credential-consuming flow, so a
union and a correctly scoped answer are byte-identical. The bug needed two flows to exist at all —
which is why the checker found it in a live Mode D walk and not in the suite.

**The fix** (`src/autotester/stages/catalog.py`, edited in place):
- `_auth_secret_keys(spec, *, only=None)` — the walk now takes an optional set of flow ids.
- `_oauth_signup_flow_ids(spec)` — new; returns the ids of flows carrying the Pack-1 signal.
  `_has_oauth_signup_carryover()` is now one line over it, so the pack's applicability rule and its
  key-scoping rule cannot drift apart (one concept, one place).
- `catalog()` computes **two scopes**: the OAuth pack names the missing keys of the flows that
  signal OAuth; the generic auth classes name the missing keys of every *other* flow.

**The judgement in it, stated for the checker rather than buried.** "Which flow is this row about"
is not written in any contract. I used the module's own existing signal vocabulary rather than
inventing a keyword classifier for "is this a sign-in flow": the OAuth pack is about the flow that
signs up through Google, and the generic auth classes are about the product's own credential form,
i.e. every other flow. **Named consequence:** a project whose only flow is the OAuth one has no
"other" flow, so the auth classes fall back to that spec's keys — an empty action would read as
"nothing unblocks this row", which is a worse lie than a broad one. That fallback has its own test
so it cannot be mistaken for an accident. If the checker judges this scoping rule wrong, the fix is
the rule, not the plumbing.

## ISS-t125-1 (CT6) — NOT FIXED, GATED, and I am not choosing

`tiers_to_run()` is correct, tested and **unused**; `trigger_run()` runs every case unconditionally.
CT6 as written is a claim about dispatch behaviour that does not exist. But honouring CT6 means
filtering which cases run, which breaks **ACTIVE** `qa/contracts/ui-run.md` RU3 ("every case on
file") and weakens F-058's pinned-regression guarantee that a known bug's case runs every time.

Two ACTIVE contracts want opposite things, `qa/contracts/` is checker-owned, and D-039's
`Changes-authorized` does not cover `ui-run.md`. Choosing here would be the maker amending ground
truth to pass its own unit. Written up with four options and the cost of each in
**`qa/gates/t125-ct6-tiered-dispatch-vs-ru3.md`**; `tiers_to_run()` is left in place and unused
(deleting pre-empts one option, wiring pre-empts another). ISS-t125-1 stays `open`.

**Whether that makes CT6 gated rather than failed is the checker's call, not mine.** If the checker
holds CT6 FAIL until Umesh answers, that is a correct verdict and this unit does not PASS this cycle.

## Also accepted from the verdict, without argument

- The cycle-1 "test split" phrasing was imprecise — `git diff cfc13b0b 2e397500 -- tests/test_catalog.py`
  is empty, nothing was split out. No coverage was lost. The checker filed no issue; recorded here
  so the wording is not repeated.

## How to verify (commands + expected)

- `uv run pytest tests/test_catalog.py tests/test_catalog_packs.py tests/test_ui_catalog.py` → exit 0, **40 passed** (37 at cycle 1 + 3 new)
- `uv run ruff check src tests scripts` → exit 0, `All checks passed!`
- `uv run autotester doctor` → exit 0, `doctor: clean`
- `wc -l src/autotester/stages/catalog.py tests/test_catalog_packs.py` → 296 and 267 (both under the C2 300 cap; catalog.py at 296 means any further growth needs a split)

## Actual outputs (maker's own run, in the bound worktree)

```
$ uv run pytest tests/test_catalog.py tests/test_catalog_packs.py tests/test_ui_catalog.py
........................................                                 [100%]
40 passed, 1 warning in 2.81s

$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester doctor
doctor: clean
```

## Capability coverage — cycle 2's new claims

| capability (one line) | the check that covers it | the falsifying edit | observed (pasted runner output) |
|---|---|---|---|
| An auth CaseClass row names only the keys of the product's own credential flows — never a sign-up-only key | `tests/test_catalog_packs.py::test_an_auth_row_does_not_advertise_a_signup_only_key` | in `catalog()`, collapse the two scopes back to one union (`missing_oauth = _missing_keys(project, _auth_secret_keys(spec))` / `missing_auth = missing_oauth`) — single file, single hunk | GREEN before: `2 passed, 10 deselected in 3.99s` · RED after: `AssertionError: auth_wrong_creds names a sign-up-only key: 'set DEMO_PASSWORD, GOOGLE_SIGNUP_TOKEN in the repo-root .env'` — **byte-for-byte the string the checker reported from its live walk** |
| The OAuth pack names only its own flow's keys — never a login-only key | `tests/test_catalog_packs.py::test_the_oauth_pack_does_not_advertise_a_login_only_key` | the same single hunk | RED after: `AssertionError: the OAuth pack names a login-only key: 'set DEMO_PASSWORD, GOOGLE_SIGNUP_TOKEN in the repo-root .env'` / `2 failed, 10 deselected in 0.29s` |
| A spec whose every flow is the OAuth one still names its keys rather than an empty action | `tests/test_catalog_packs.py::test_an_oauth_only_spec_still_names_its_keys_rather_than_nothing` | not independently falsified — see the gap below | (see gap) |

**Where the perturbation ran.** `…/scratchpad/t125-falsify`, built with
`tar --exclude=.git --exclude=.venv --exclude=.worktrees --exclude=__pycache__ --exclude=.pytest_cache`,
outside the bound root, own fresh venv. Proven to resolve its own source first:
`…\scratchpad\t125-falsify\src\autotester\stages\catalog.py`. **The `__pycache__` exclusion is new
and deliberate** — a copied `.pyc`'s `co_filename` is baked to the source tree's path, which made
earlier units' falsification tracebacks print the worktree path and look like a rule violation. Root
cause and proof are in `qa/feedback-inbox.md` (2026-09-27); the at626 checker reproduced and
confirmed the same cause independently.

## Gaps stated, not hidden

- **The OAuth-only fallback row is not independently falsified.** Breaking it means removing the
  `or None` in `_auth_secret_keys(spec, only=other_ids or None)`, which makes `only=set()` match no
  flow and the action empty — the test does fail then, but that edit also changes the *other* two
  rows' behaviour, so it is not an isolating single-claim falsification. Left honest rather than
  claimed: the row has a test, not an isolation proof.
- **No live Mode D walk by the maker this cycle.** The fix is in the pure catalog stage and the
  checker's own Mode D fixture is now reproduced as two unit tests, but the rendered page was not
  re-walked by me. The checker should re-walk it — the defect was only ever visible in a live page.
- **CT6 remains unmet** (gated above), so this cycle cannot honestly claim 8/8.
- **Full suite not run by the maker** — sibling checkers were holding the machine. `AT-627`
  (`test_flake_probe_real_process.py`) remains a pre-existing environmental flake, not chargeable;
  the at626 checker's own 1615s full-suite run confirmed it is the only failure on master.
- **AT-588's ledger row stays `open`**, as the checker left it — the same code path was implicated
  in ISS-t125-2 and the checker owns that flip.


---

# Cycle 3 — my own cycle-2 fix caused a worse defect; this reverses its shape

**Verdict answered:** `qa/verdicts/t125-catalog.md` (cycle 2, FAIL, 5/8), committed `5eb9cebf`.
**Nothing in it is disputed.** ISS-t125-3 is a defect I introduced in cycle 2, and the checker's
severity (`high`) is right: cycle 1's bug was visible and misleading, mine was **invisible**.

## ISS-t125-3 — FIXED, by reversing the cycle-2 mistake rather than patching around it

**What I got wrong, stated plainly.** ISS-t125-2 was a complaint about the **wording** of a blocked
row — `auth_wrong_creds` told the operator to set a sign-up-only key. I fixed it by scoping the key
list per flow, and then used that same narrowed list for **both** the wording *and* the
blocked/runnable decision. Narrowing the wording was the fix; narrowing the gate was never asked
for and was never safe. A single flow that both clicks "Sign up with Google" **and** fills the
product's own password is classified OAuth, so under cycle 2 its key left the auth scope entirely,
`missing_auth` came back empty, and `auth_wrong_creds` rendered a green `runnable` pill while the
only secret the project declares was unset. The case would then fail for real at run time — which
is exactly the failure mode AutoTester exists to prevent, shipped by AutoTester's own catalog.

**The asymmetry that decides the fix.** Over-naming a key is noisy; under-naming one is invisible.
So the two concerns are separated and only one of them is allowed to narrow:

- **The gate never narrows.** Every `blocked`/`runnable` decision — CaseClass rows *and* the OAuth
  pack — is taken against `_missing_keys(project, _auth_secret_keys(spec))`, i.e. every key the
  approved spec declares. A flow being an OAuth flow can no longer remove a requirement.
- **Only the wording is scoped**, via `name_keys`, falling back to the whole set when scoping would
  empty it (an empty action reads as "nothing unblocks this row", a worse lie than a broad one).

`_entry_for` and `_pack_entries` now take `blocking_keys` positionally and `name_keys` by keyword,
so the distinction is visible at both call sites instead of living in one variable's name.

**I applied it to the pack as well as the rows, which the issue did not ask for.** The pack had the
same shape latent: its gate used the OAuth-scoped list, so an OAuth-signal flow whose credential is
filled in a *different* flow would have claimed runnable with that key unset. Same one-line rule,
so fixing only the reported half would have left a known twin in place. **Stated as a gap below:
that twin is not independently tested** — the fixture that isolates it does not exist yet.

## Also from the verdict, accepted without argument

- **ISS-t125-4 (low).** My "no UI surface" persona-walk reason was false — `ui/routes_catalog.py` is
  a real UI route in this diff. Corrected in the header to cite the **internal-tool audience**,
  which is the defensible reason. No code change; the wording was the defect.
- **The checker's 3/3 capability reproduction beat my own manifest.** I claimed the OAuth-only
  fallback row could not be isolated; the checker found the narrower single-hunk edit
  (`only=other_ids or None` → `only=other_ids`) that isolates it cleanly. Recorded because I was
  wrong in the direction that flatters the maker — I called a row unfalsifiable rather than looking
  harder. Cycle 3 removes that expression anyway (`only=other_ids`, with the fallback now explicit
  as `missing_other or blocking`).

## CT6 — unchanged, still gated, still not mine to decide

`qa/gates/t125-ct6-tiered-dispatch-vs-ru3.md` is unanswered, so CT6 cannot reach PASS this cycle
either. The checker independently verified the conflict is real on both sides and found no missing
fifth option. `tiers_to_run()` stays in place, unwired, docstring disclosure intact. **This unit
cannot reach 8/8 on any cycle without Umesh's answer** — and cycle 3 is the last of three, which is
a fact about the cap, not a reason to weaken a criterion to fit inside it.

## How to verify (commands + expected)

- `uv run pytest tests/test_catalog.py tests/test_catalog_packs.py tests/test_ui_catalog.py` → exit 0, **41 passed** (40 at cycle 2 + 1 new)
- `uv run pytest` (full suite) → **1 failed, 2050 passed**, and the one failure is **AT-627**,
  proven below to be pre-existing and not chargeable to this unit. Stated as the real
  expectation rather than "exit 0", which would have been a false claim.
- `uv run ruff check src tests scripts` → exit 0, `All checks passed!`
- `uv run autotester doctor` → exit 0, `doctor: clean`
- `wc -l src/autotester/stages/catalog.py tests/test_catalog_packs.py` → **300 and 300** — both now
  exactly at the C2 cap (see the gap on file pressure below)

## Actual outputs (maker's own run, in the bound worktree)

```
$ uv run pytest tests/test_catalog.py tests/test_catalog_packs.py tests/test_ui_catalog.py
.........................................                                [100%]
41 passed, 1 warning in 0.63s

$ uv run pytest                      # full suite, in the bound worktree
FAILED tests/test_flake_probe_real_process.py::test_run_once_kills_a_real_hung_process_and_its_real_grandchild
1 failed, 2050 passed, 5 skipped, 32 xfailed, 15 warnings in 840.81s (0:14:00)

$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester doctor
doctor: clean
```

**The single failure is AT-627 (`low`, `open`), and I proved that rather than asserting it.** Its
ledger row names this exact test and this exact mechanism: the spawned grandchild must write a pid
file before `flake_probe.run_once`'s 10 s timeout kills the tree, and under CPU contention it is
never scheduled in time, so `pid_file.read_text()` raises `FileNotFoundError` instead of reaching
the kill-tree assertion. Observed failure is that `FileNotFoundError` from `pathlib.py:1044`.

Two independent reasons it is not chargeable to this unit:

1. **It reproduces on `master`, where none of this unit's changes exist** — `uv run pytest
   tests/test_flake_probe_real_process.py` in the main checkout: `1 failed, 1 passed in 11.16s`,
   same test, same error. A defect present without the diff is not caused by the diff.
2. **Zero coupling.** This unit changes `stages/catalog.py` and `tests/test_catalog_packs.py`; the
   failing test spawns real OS processes through `scripts/flake_probe.py` and imports nothing from
   the catalog stage.

The machine was genuinely loaded — a checker on another unit was running its own full suite
concurrently — which is precisely AT-627's stated trigger. **The arithmetic also ties out against
the checker's own cycle-2 run** (`2050 passed, 5 skipped, 32 xfailed, exit 0`): this unit adds
exactly one test, so 2051 collected, 2050 passed, 1 failed.

**A trap in my own command construction, recorded because it nearly produced a false green.** I ran
the three verify commands as one grouped shell command, so the reported exit code was
`autotester doctor`'s — `0` — while pytest inside it had failed. The harness said "exit code 0" and
that was true of the group and false of the suite. I read the pytest summary line rather than
trusting the group's status, which is the only reason this was caught; a future tick should run
pytest as its own command so its exit code cannot be masked.

## Capability coverage — cycle 3's new claim

| capability (one line) | the check that covers it | the falsifying edit | observed (pasted runner output) |
|---|---|---|---|
| A credential requirement never disappears because the flow needing it also carries an OAuth signal — the blocked/runnable gate is taken against every key the spec declares | `tests/test_catalog_packs.py::test_a_hybrid_oauth_and_password_flow_still_blocks_the_auth_rows` | in `catalog()`, narrow the gate back to the scoped list: `_entry_for(cc, project, blocking, …)` → `_entry_for(cc, project, missing_other, …)` — single file, single hunk, reproducing cycle 2's exact mistake | GREEN before: `2 passed, 11 deselected in 0.11s` · RED after: `AssertionError: auth_wrong_creds claims runnable while HYBRID_PASSWORD is unset` / `assert True is False` / `2 failed, 11 deselected in 0.22s` — **the checker's own sentence from its live Mode D walk, reproduced as a unit assertion** · restored: `2 passed, 11 deselected in 0.09s` |

**The second failing test is disclosed, not hidden.** That one hunk also reds
`test_an_oauth_only_spec_still_names_its_keys_rather_than_nothing`, because both rows depend on the
same non-narrowing gate — they are two consequences of one claim, not two claims. It is a
single-hunk edit whose named test fails for the stated reason; it is not an isolating edit in the
strict one-test sense, and I am not calling it one.

**Where the perturbation ran.** `…/scratchpad/t125c3-falsify`, built with **`git archive`** rather
than `tar` — an archive of a tree contains no `__pycache__` or `.pytest_cache` at all, so the
`co_filename` artifact that made earlier units' tracebacks print the worktree path cannot recur by
construction instead of by remembering to add an exclude. Verified empty of both caches, own fresh
venv, proven to resolve its own source:
`…\scratchpad\t125c3-falsify\src\autotester\stages\catalog.py`. Bound worktree verified intact
afterwards — `git status --short` showed only this unit's two modified files and
`_entry_for(cc, project, blocking` still present at :271.

## Gaps stated, not hidden

- **The pack-side twin is fixed but not independently tested.** The rows' hole had a real repro from
  the checker; the pack's equivalent (an OAuth-signal flow whose credential is filled in a different
  flow) is closed by the same one-line rule but has no fixture proving it, because both files are
  now **exactly at the 300-line C2 cap** and I would not silently exceed it. The checker should
  treat that row as reasoned, not demonstrated.
- **File pressure is now the binding constraint on this unit, and it is a real signal.**
  `catalog.py` and `test_catalog_packs.py` both sit at exactly 300. I trimmed comment prose to fit
  rather than split mid-final-cycle, which is the smaller risk but not the better answer. The
  responsibility split (the credential-scoping helpers are one concept: "which keys does this row
  need") is filed in `qa/feedback-inbox.md` for the checker rather than attempted here.
- **The union recurs, by contract shape, in a case the checker chose not to file.** Two ordinary
  non-OAuth login flows needing different keys still produce a union in the *wording* — with one
  row per `CaseClass` (CT2) the row is not about any single flow, so there is no "own flow" to scope
  to. The gate is correct there; only the text is broad. Whether CT2's one-row-per-class shape
  should change is a contract question I must not answer for my own unit.
- **CT6 remains unmet and gated**, so this cycle claims 7/8 at best, not 8/8.
- **`AT-588`'s ledger row stays `open`**, as the checker left it — the checker owns that flip.

**Status: cycle-3 FAILED — unit STALLED at its 3-cycle cap. NOT merged.**

/checker cycle 3, verdict `qa/verdicts/t125-catalog.md` (`Cycle checked: 3`), commit `a27f9794`:
**FAIL, 5/8.** CT1/CT2/CT3/CT4/CT7 PASS · **CT5 and CT8 FAIL on a new cause** · CT6 **GATED**.

- **ISS-t125-3 is genuinely fixed** and the checker flipped it to `verified` after re-walking it
  live with its own `demo-hybrid` fixture. That part of cycle 3 worked.
- **But the fix over-corrects — `ISS-t125-5` (high, open).** The gate now uses every key the spec
  declares with no restriction, so a login flow whose own password is *set* is wrongly blocked
  because an unrelated flow (an OAuth sign-up, or even an admin-import flow) has an unset secret.
  The checker reproduced it twice, unit-level and in a live browser walk. It is not an edge case:
  any spec with more than one credential-consuming flow trips it — which is exactly the shape
  AT-588 ships (login + OAuth carry-over).
- **The checker also settled two things in my favour, on its own evidence.** The untested pack-side
  twin is acceptable (rows and pack share one literal `blocking` value, and its probe confirms they
  share the identical defect, which is what a shared mechanism predicts). And my "two consequences
  of one claim" coverage argument holds — reproduced in its own throwaway copy, genuinely one claim.
  It also verified the AT-627 exculpation independently and confirmed no reasoning was lost to the
  300-line trim.

**Three cycles, three answers to one question, each breaking something new** — cycle 1 named a union
(visible, misleading), cycle 2 lost a requirement entirely (invisible, ships a failing case), cycle 3
blocks rows that are fine (false positives). Cycles 2 and 3 are both mine.

**The cause is that the contract never says which secret belongs to which row.** `catalog.md`'s CT5
and CT8 judge the blocked state and its `unblock_action`, so a checker can prove an answer wrong
without the contract defining a right one — every cycle was a guess at unwritten ground truth. That
is why **no cycle 4 has been started**: a fourth guess is not better than the third, and the cap is
being respected rather than quietly exceeded.

**Open for Umesh:** `qa/gates/t125-stalled-at-cycle-cap.md` (on master), four costed options —
specify relevance in the contract then one scoped cycle · revert cycles 2–3 to `cfc13b0b` per the
standing regression rule · drop the credential gate from the catalog · amend CT2's
one-row-per-`CaseClass` shape. **`qa/gates/t125-ct6-tiered-dispatch-vs-ru3.md` remains open and is a
second, independent reason this unit cannot reach 8/8.**

**Blast radius: none.** `src/autotester/stages/catalog.py` does not exist on `master` — the whole
stage and both regressions live only on this branch, which stays unmerged and un-reverted (reverting
would pre-empt two of the four options; merging would ship ISS-t125-5).

## Cycle4 — current scoped continuation, 2026-10-01

**Status:** verification-in-progress (NOT ready-for-check)
**Fix cycle:** 4 — exactly one exceptional scoped cycle authorized by D-051 after written CT9; no cycle5.
**Contract:** qa/contracts/catalog.md CT1–CT9; ui-run.md RU1–RU4; parallel-run.md PR7; consent.md CN10; core-invariants C1/C2/C3/C5/C7/C12.
**Goal task:** T-125, pending; no maker close or PASS.
**Branch:** codex/t125-cycle4; candidate D:/autoTesting/.worktrees/t125-cycle4; baseline bd2fe8f4d9a9fa87552e8a3999eb27cb52f8addf.
**Historical record:** preceding text recovered unchanged from ac66b4f54e8ca54e1f8084a894210ae2f0e862bd:qa/manifests/t125-catalog.md. Its cycle1–3 results and then-open gates are historical, not current claims. The source worktrees and dd579805 dirty successor manifest remain untouched.
**Current authorizations:** D-039 recovered catalog/schema/page/tests, D-051 one scoped cycle4 after CT9, D-058 order only/no skipping; independently approved revised recovery plan and CT1 Project.created_at rule (root review receipts in .work/t125-recovery-inventory.md).

### Actual current change

- Recovered schema/catalog.py, stages/catalog.py, ui/routes_catalog.py and registered existing catalog tests from pinned dd579805; individually reconcile current app import/router and project_detail navigation.
- catalog() uses existing expand.applicable_classes to derive class feeding flows; sorted declared placeholder keys determine each row gate/wording. One presence-only missing-key read; OAuth pack scope stays its actual flow IDs. Full Catalog JSON uses stable Project.created_at on all three branches.
- tiers_to_run returns static/behavioural/adversarial regardless of counts. Real trigger snapshots every stored case/entry flag and joins/cleans each tier before the next; pinned and catalog-blocked stored cases still persist.
- One approval-snapshot RunBudget spans all tiers/entry/serial/parallel legs; normal workers debit only in parallel_run._run_one. Entry-only parallel tiers validate approval correspondence before debit/wipe/session. Denied cases persist exact exhaustion RawResult and deterministic INCONCLUSIVE verdict without judge/browser/profile removal.
- Run.catalog_runnable_counts requires exactly three nonnegative strict-integer measurements, including zeros. Run view calls them catalog runnable-class counts; legacy None displays NOT_RECORDED, independently of result/case totals.
- Tests discriminate full JSON timestamps, structural credential union/no-keyword relevance, empty-tier ordering, real mixed nine-case trigger, pinned/blocked persistence, two-worker completion/session-close barrier, one trace span, all-leg action/deadline denial, mismatch no effects, measured/legacy counts and malformed schema measurements. Revised recovered UI/pack expectations follow independently derived CT9; fixtures preserved.

### Exact measured verification to date

Root owned the runtime lane, with root .venv interpreter and candidate/src package binding independently printed; --no-sync --offline, project-local UV cache/fresh basetemp and test-only signing key. No native browser/provider/network/real-product calls.

- RED: uv run --no-sync --offline pytest tests/test_catalog.py tests/test_ui_runs_serial_entry_order.py tests/test_ui_runs_parallel_crash_recovery.py --basetemp=D:/autoTesting/.work/t125-red-temp-0707 --tb=short --junitxml=D:/autoTesting/.work/t125-red-0707.xml. Native exit1, 27 failed/19 passed/0 errors, 1 warning, 2.11s. Timestamp, relevance, helper ordering, real tier dispatch, shared all-leg budget/deadline and barrier failures reached assertions. Genuine403 refusal text was independently corrected from max_actions to actual --max-actions9/--wall-clock72, without weakening preflight. Initial UV-cache/pytest-temp ACL failures are environmental and not intended RED.
- GREEN scoped7modules: uv run --no-sync --offline pytest tests/test_catalog.py tests/test_catalog_packs.py tests/test_ui_catalog.py tests/test_ui_runs_serial_entry_order.py tests/test_ui_runs_parallel_crash_recovery.py tests/test_schema.py tests/test_ui_report.py --basetemp=D:/autoTesting/.work/t125-green-temp-0714 --tb=short --junitxml=D:/autoTesting/.work/t125-green-0714.xml. Root native exit0, 101 passed/0 failed/0 errors, 1 warning, 5.33s; actual XML read back.
- Broader six fixture suites: uv run --no-sync --offline pytest tests/test_ui_runs_serial_resilience.py tests/test_ui_runs_parallel_trace.py tests/test_parallel_run.py tests/test_parallel_run_approval.py tests/test_parallel_run_session_crash.py tests/test_run_trace.py --basetemp=D:/autoTesting/.work/t125-broader-temp-0715 --tb=short --junitxml=D:/autoTesting/.work/t125-broader-0715.xml. Root native exit0, 35 passed/0 failed/0 errors, 6 warnings, 2.46s; actual XML read back.
- Lint: root full scoped lint found7 I001 import-order findings in three changed test files. Authorized formatting command D:/autoTesting/.venv/Scripts/ruff.exe check --select I --fix tests/test_catalog.py tests/test_ui_runs_parallel_crash_recovery.py tests/test_ui_runs_serial_entry_order.py -> native exit0, Found7 errors (7 fixed,0 remaining). This is formatting, NOT a substitute for full lint re-run. Removed one obsolete test_catalog section comment after import formatting to retain300-line cap. Re-run pending root.
- Static git diff --check native exit0 before formatting; final re-run/hash receipt follows. No contract/enforcement/architecture/base-schema edits or wholesale branch merge.
- Full lint re-run: root reports uv run --no-sync --offline ruff check src tests scripts -> native exit0, All checks passed (after import formatting).
- Doctor: root reports8 findings — ledger-row-missing T171 (1), stale MAP/SNAPSHOT (2), D061 dangling references at733 manifest41/47, at113.b verdict209/281, SNAPSHOT44 (5). Fresh independent STATIC doctor review attributes7 to baseline and1 to newly stale MAP caused by recovered catalog rows; this is not a doctor rerun or final exculpation/PASS. T171 remains separate unresolved. Exact existing root D061 staging file identified and matches canonical history; governed append-only recovery + autogenerated MAP/SNAPSHOT proposal recorded in .work/t125-recovery-inventory.md, not yet applied. No citations/history edits, decision replacement or blanket waiver.
- Post-format repass: uv run --no-sync --offline pytest tests/test_catalog.py tests/test_catalog_packs.py tests/test_ui_catalog.py tests/test_ui_runs_serial_entry_order.py tests/test_ui_runs_parallel_crash_recovery.py tests/test_schema.py tests/test_ui_report.py --basetemp=D:/autoTesting/.work/t125-format-temp-0716 --tb=short --junitxml=D:/autoTesting/.work/t125-format-0716.xml. Root actual native exit0, 101 passed,1warning,5.02s. Root fullruff remains native0 All checks passed.

### Remaining acceptance, not claimed

Additional safe ledger neighbor verification 2026-10-05: root executed `uv run --no-sync --offline pytest tests/test_ledger.py --basetemp=D:/autoTesting/.work/t171-ledger-recovery-1005 --tb=short --junitxml=D:/autoTesting/.work/t171-ledger-recovery-1005.xml` bound to candidate/src and root interpreter with no-env test guard and plugins disabled. Native exit0, `24 passed in 1.42s`; root independently parsed XML:24 tests,0 failures,0 errors,time1.377. This validates existing ledger neighbor behavior only, not missing T125 browser/full-suite requirements.

2026-10-05 continuation: independent corrected CT6 proof retained in root qa/evidence/t125-cycle4-restore-2026-10-05.md. Root independently parsed all four ct6-*-1005.xml receipts: 2 green, 2 intended executed-ID assertion failures with zero errors, 2 restored green, 2 original-test green. Checker reports exact raw-byte restoration and zero mismatches across 466 candidate/scratch paths. This supersedes the earlier schema-error mutation limitation only for the corrected executed-set proof, not all other criteria.

Missing T-171 ledger close-out recovered through existing `uv run --no-sync --offline autotester ledger add` in candidate: native exit0, F-067 live permission-surface-coverage, T-171 and cycle2 verdict reference, grounded prefilled reason explicitly pending human confirmation. Existing CLI regenerated SNAPSHOT; FEATURES diff exactly one appended row. Subsequent `uv run --no-sync --offline autotester doctor` process71099 terminated native exit0: `doctor: clean`. Root read resulting row/diff. Independent static bookkeeping review dispatched. This is candidate-local doctor evidence, not full pytest, browser evidence, committed freshness, or T-125 PASS.

Full adapter suite uv run pytest, doctor closure/individual attribution, fresh cycle4 checker, required single-hunk green→intendedRED→restore→green capability proofs, and actual safe local visible-browser CT8/Run/report acceptance remain. TestClient/fake collaborator checks are not live-browser acceptance or provider-quality measurements. No manifest ready-for-check, unit PASS, contract ACTIVE flip, goal closure, commit or push yet.

**Snapshot:** all source/test hashes and line counts in root .work/t125-recovery-inventory.md Phase2 snapshot; three import-formatted test hashes supersede initial freeze (catalog 2FA7299B7CFF90F30FF463467D43F89F2BC486C9ACC30E27E15A6BFA298310D2; parallel_crash F6661E33B8299D6FF4A4421614D3374C07F6591BFF3AF3B31B904D3976D8206E; serial_entry 87164314302F0CF18A490DABBA46CD4957195D22C258A3958364D7D64EE04137).

## Status (cycle4): verification-in-progress

### 2026-10-05 generated-document verification receipt

Fresh static reviewer /root/review_t125_ct6_oracle independently approved the F-067 bookkeeping scope: exactly one appended row with prior rows unchanged; correct T-171 cycle2 PASS/task correspondence; qualified prefilled reason and generated SNAPSHOT consistent with L2/L3. Reviewer also independently checked all four CT6 XML hashes, both named assertion failures and the two edited files' restored hashes. Full466 comparison remains the executing checker's retained evidence, not duplicated by static reviewer. This is narrow static approval only; no product PASS.

Root ran the approved existing generators from this candidate with root interpreter, candidate PYTHONPATH, offline/no-sync UV, AUTOTESTER_ROOT bound here and PYTEST_CURRENT_TEST set to the no-env guard. `autotester map` regenerated MAP; `autotester snapshot` wrote 44 lines; `autotester doctor` terminated native exit 1 with exactly one violation: missing high-value feature ledger row for T-171. MAP diff is 11 additions/2 removals; regenerated SNAPSHOT has no remaining diff. D-061 dangling-reference and generated-freshness findings no longer appear. This does not waive the remaining doctor violation or establish full-suite/browser acceptance. Independent CT6 corrected executed-set mutation verification is in progress; no PASS or task closure.

QA/docs recovery environment addendum: root authorized exact canonical D061 append using existing original staging file via append_decision.ps1. Standard nested Windows powershell -File attempt nativeexit1 because its existing policy disallows scripts; script never executed and decision history hash/prefix unchanged. No policy bypass/change or alternate append executed. Existing tool-shell pwsh has RemoteSigned; its standard -NoProfile -File proposal is awaiting root review. MAP/SNAPSHOT regeneration remains unexecuted pending history recovery and runtime-lane availability. Product source/tests remain frozen.

Canonical history recovery completed under separately approved standard existing toolruntime pwsh -NoProfile -File invocation (no policyflags/change). Rechecked exact existing original entry F36BCE and normalized prefix before script; nativeexit0 APPENDED:D061. Candidate first165025bytes retain exact original9DAABAA hash; normalized full candidatehistory equals canonical root; diff24added0removed; candidateposthash482E090A15438ACA6E134121AA8D55542CE7FA0CD7309477AB1138905B8C9C80, original staging unchanged. This is recovery of prior AT113 history, never new T125/AT113 authority, goal change or citation replacement. MAP/SNAPSHOT still await fixture lane; doctor not rerun, T171 unresolved.

## Cycle 4 builder close-out (2026-10-07) -- ready-for-check

**Source:** `62a45c6a` on `codex/t125-cycle4` (base bd2fe8f4). Commit holds schema/stage/route/test files of the
recovered catalog plus the cycle-4 run-path work and `docs/MAP.md`. **NOT committed on purpose:**
`src/autotester/ui/app.py` (coordinator constraint: another session edits it; the uncommitted diff is the
`routes_catalog` router registration + "Test catalog" link on `project_detail`, without it
`tests/test_ui_catalog.py` cannot reach the page), and T-171/AT-113 bookkeeping owned by other units
(`.goal/goal.json`, `docs/DECISIONS.md` D-061 recovery, `docs/FEATURES.jsonl` F-067, `docs/SNAPSHOT.md`).

**CT6(4) built:** `stages/catalog.py::failures_first` (:255-271, uses `TIER_BY_CLASS`/`TIER_ORDER`), called by
`ui/routes_report.py::_sections` (:152-160) from `run_view`. Test:
`tests/test_ui_report.py::test_run_view_lists_cheap_tier_failures_first_ahead_of_passes`.
CT6(1)-(3) (dispatch order, never skip, per-tier counts incl. 0) in `ui/routes_runs.py::_execute_with_trace`
and `Run.catalog_runnable_counts`. Gap found and closed this cycle: the shared-budget approval snapshot
(`run_budget.py`, `approval.model_copy(deep=True)`) had no test (mutation survived); added
`tests/test_parallel_run_approval.py::test_budget_owns_a_snapshot_of_its_approval_not_the_callers_live_object`.

**Builder evidence (worktree, `uv run --no-sync --offline`, test-only AUTOTESTER_APPROVAL_KEY):**
- affected tests (33 files: catalog x3, schema, report, ui_runs*, parallel_run*, run_trace, pinned, run_case_pipeline*, report_export*, ui, sidebar, dashboard, execute*, cases, flow_diagram, video route/export): `283 passed, 1 skipped, 7 warnings in 24.78s` (before the one added test; the file holding it: `10 passed`).
- `ruff check src tests scripts`: All checks passed. `autotester doctor`: clean (run with the full uncommitted bookkeeping present; the committed tree alone omits F-067/D-061/SNAPSHOT/goal.json, which belong to T-171/AT-113).
- full suite NOT run (suite_runs=0); reserved for the checker's one allowed run.

**Falsification (scratch copy only; single-hunk; green -> red -> restored green):**
| # | Criterion | Mutation | Mutant result |
|---|---|---|---|
| 0 | CT6(4) | `failures_first` rank -> `return 0` | RED test_run_view_lists_cheap_tier_failures_first_ahead_of_passes |
| 1 | CT6(4) | `_sections` no failures section | RED same test |
| 2 | CT6(1) | `tiers_to_run` reversed | RED 21 (test_tiers_to_run_*, real_trigger_orders_tiers[1]) |
| 3 | CT6(2) | `tiers_to_run` drops 0-runnable tiers | RED 21 (keeps_all_tiers_when_static_is_blocked, entry_cases_start..., real_trigger[1]) |
| 4 | CT6(3) | count map omits zero tiers | RED 3 (real_trigger[1],[2], entry_cases_start...) |
| 5 | CT6(3) | `Run` validator accepts partial counts | RED 2 (test_catalog_counts_reject_malformed_measurements) |
| 6 | CT9(b) | union keys spec-wide (`only=` dropped) | RED test_an_oauth_only_unset_secret_blocks_the_pack_not_the_login_rows |
| 7 | CT9(a)/CT5 | credential gate disabled | RED 8 (missing_credential_names_the_key..., same_class_union..., auth_rows_union...) |
| 8 | CT1 | `created_at` unstable on approved branch | RED test_catalog_is_pure_same_inputs_same_output[approved] |
| 9 | CN10 | `RunBudget.require_approval` no-op | RED test_parallel_entry_only_rejects_mismatched_budget_before_any_effect |
| 10 | CN10 | entry-case budget debit removed | RED 16 (test_internal_execution_spends_one_budget_across_tiers_and_all_legs[...]) |
| 11 | CN10 | approval not deep-copied | first run SURVIVED (green); after added test: RED test_budget_owns_a_snapshot_... |
Each restored to byte-identical source and re-run green (counts in the scratch log). CT9(c) (keyword rule) not mutated by me: no
keyword path exists in `_auth_secret_keys`; covered by `test_same_class_union_includes_secret_fills_with_arbitrary_field_names` only.

`Metrics: start=2026-10-07T15:05 end=2026-10-07T15:20 wall_min=15 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=12 cycle=4 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-06.6`

## Integration rework (2026-10-07)

Merging `codex/t125-cycle4` onto origin/master (`d4c369b0`, which carries d063's aggregate `RunBudget`
f7adb2b9 / 20594b23 / a2c6124a) conflicted in five files. d063's accounting is the merged authority;
T-125 aligns to it. Branch `integrate/t125`, merge commit below. No source guard of d063/D-066/D-068 was weakened.

**Per-file resolution**
- `stages/run_budget.py`, `stages/parallel_run.py`: origin's version verbatim (finite/non-negative limit
  validation, `_stop_reason`/`stop_reason`, `check_start()`, `matches()`, `reserve = budget is None`).
- `ui/run_execution.py`: origin's version, plus ONE added guard at the top of `_run_cases_in_parallel`:
  `if not budget.matches(approval): raise ValueError("shared budget does not match approval")`. An entry-only
  tier returns before `run_cases`, so origin's own `matches()` check never ran for it; this closes that hole
  with the existing `matches()` (CN10, T-125's `test_parallel_entry_only_rejects_mismatched_budget_before_any_effect`).
- `ui/routes_runs.py`: origin's `budget=` keyword, EXECUTE stage `failed` on `stop_reason`, `account_keys` and
  the 5-arg `_require_live_case_approval`; T-125's tier loop (`tiers_to_run`, `TIER_BY_CLASS`,
  `catalog_snapshot`, `Run.catalog_runnable_counts`) wrapped around them, one `RunBudget` built once outside the loop.
- `tests/test_parallel_run_approval.py`: both sides' tests kept (d063's four plus T-125's snapshot test).
- `ui/app.py` (auto-merged, 301 lines): module docstring's last two lines joined, 300 lines, no behaviour change.

**Dropped:** T-125's `RunBudget.require_approval()`. It duplicated d063's `matches()` (one concept, one place);
the deep-copy snapshot it relied on already exists in origin's `RunBudget.__init__`.

**Not re-expressed: the per-case `action_cost` reservation** (T-125's `try_consume(actions=action_cost(case))`
in `_run_entry_case`/`_run_cases_serially`). d063 charges actions per executed step in `stages/execute.py`
(`budget.check(actions=1)`) and `trigger_run` grants `max_actions = sum(action_cost)`; adding the case-level
charge would double-spend and exhaust every real run at about half its grant.

**Protected test change** `tests/test_ui_runs_serial_entry_order.py` (checker to re-judge):
- helper `_patch_tier_execution.run`: ADDED `session.budget.check(actions=1)` (one mocked step spent through
  the real d063 budget API) so exhaustion actually happens with mocks.
- `test_parallel_entry_only_rejects_mismatched_budget_before_any_effect`: call changed from positional
  `..., mismatched, budget)` to the d063 keyword `budget=budget`. Assertions unchanged.
- `test_internal_execution_spends_one_budget_across_tiers_and_all_legs` (16 params), before -> after:
  - per-case error text `== "run budget exhausted before this case could start"` -> `f"run budget exhausted: {reason}" in error`
    with `reason` = `max_actions` (allowance) or `wall_clock_s` (deadline), and outcome still ERRORED. Why: d063
    reports the brake by `stop_reason`, not a reservation string.
  - session count: formula `1 if deadline or allowance==1 else (3 if width==1 else 4)` -> derived from the admitted set:
    admitted entries + (distinct admitted-normal tiers if width==1, else admitted normals). Why: d063 starts no
    browser for a refused case (`check_start()` raises before `start()`), so the old reservation-era counts differ.
  - wipe count: `0/1/2` by branch -> `== number of entry cases`. Why: d063's `_run_entry_case` wipes the profile before
    consulting the budget.
  - ADDED: the EXECUTE span is exactly one, `status == "failed"`, error names the brake.
  - UNCHANGED: admitted-case set and order (`expected`), every case persisted (never-skip), grade events == admitted,
    verdict set == result set, refused cases INCONCLUSIVE.
  - Mutation: `RunBudget(approval)` rebuilt inside the tier loop -> 16 RED (one shared budget across tiers still pinned).

**Verification (integrate/t125 worktree):** 44 affected test files `498 passed, 1 skipped`; `ruff check src tests scripts`
All checks passed; `autotester doctor` clean. Full suite NOT yet run (maker step 6c, to follow the dual re-check).

**Contract wording that now mismatches.** `qa/contracts/catalog.md` states no reservation criterion; the nearest criterion
is `qa/contracts/consent.md:255-258` ("One aggregate budget ... Stop on a brake, identify the brake and record
stopped/truncated truth"), which the merged result satisfies as written. The reservation claim lives only in this
manifest's cycle-4 evidence ("all-leg action/deadline denial", line 548; mutation #10 "entry-case budget debit removed",
#9 `RunBudget.require_approval` no-op), which is superseded by this section. Proposed clarification for the checker to
amend at consent.md:255 (append): "Actions are spent per executed step through `RunBudget.check(actions=...)`, never by
a case-level pre-charge. A case refused by an exhausted budget still persists its own ERRORED result and INCONCLUSIVE
verdict naming the brake (`run budget exhausted: <stop_reason>`); no case is skipped, and the EXECUTE stage is recorded
`failed`."
