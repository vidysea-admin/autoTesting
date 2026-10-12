# Brief — t199-bug-loop-dry-run: T-199 tracker sheet mapping and sync, DRY RUN ONLY (queue row `t199b-sheet-sync-dryrun`, plan unit G8)

**Dispatch status: READY once its predecessors land (section 10); NOT dispatchable on today's master.** The contract exists
(`qa/contracts/team-bug-loop.md` TB8-TB14), the gate that limits it is answered, and every file this unit needs is named below. What blocks
it is order: `t199a-bug-loop` (G6, which owns the bug store this unit syncs) is unmerged and `t205-g10-headroom` (G1) has not been built.
Written 2026-10-11 by the readiness pass. Scope of this brief: **G8 only**. G6 (TB1-TB7) is a predecessor unit with its own build; its state is in section 4.

## 1. Policy and tier

Policy-Version: proportional-verification/2026-10-10.9
Tier: **L**. Trigger: data writes. The unit builds the code path that writes rows into a team's Google Sheet (TB9, TB10, TB13 are CRITICAL in the
contract, "an outward-facing write to a team's sheet"), plus a server-side `project.edit` confirmation gate. It also adds a schema (the per-project
binding) and a provider fallback whose payload must be header-only.
Dual check: no. No security/auth/tenancy/prod-write trigger with a real `path:line` exists: the only write target is an in-memory fake `SheetClient`
(no live client class is built, D-081 item 7), and the `project.edit` gate lives in a route file this unit creates (no line exists yet). If a later
unit adds a live `SheetClient`, that unit is `Dual check: required` on its `prod-write <path:line>` of the real adapter.

## 2. Root and base

Root: `D:/autoTesting`. Base: current `master` = `4f8f5da100931ebda1b26836304bfbd38460764b` at the time of writing. That sha will move: `land-t203-hosting`, `t205-g10-headroom` and
`t199a-bug-loop` all land before this unit, so **the builder must re-read `git -C D:/autoTesting rev-parse master` at dispatch and record that sha as the base in the manifest**.
Branch to build in: a new `wave/t199b-sheet-sync-dryrun` cut from that master tip, in its own worktree under `D:/autoTesting/.worktrees/t199b-sheet-sync-dryrun` (repo convention, e.g. `wave/g6-bug-core` at `.worktrees/g6-bug-core`).
Reason: D-080 item 1 makes origin/master the single trunk and says branches are inputs re-landed unit by unit; `wave/g6-bug-core` (head f8f59265) is 56 commits behind master with conflicts, so stacking on it would carry its conflicts and its still-open CONTINUE-NEEDED verdict into this unit.

## 3. Acceptance criteria

Source: `qa/contracts/team-bug-loop.md` (Status: DRAFT at contract time; G8's rows bind from G8's own `ready-for-check`, per its header). Criteria for THIS unit are TB8-TB14, copied verbatim below. TB1-TB7 belong to G6 and are not this unit's.
The contract's header says G8 is **CRITICAL for TB9, TB10, TB13** and HIGH elsewhere, and that all rows are verified `LOCAL` with a **fake `SheetClient`** (no live Google call, no live model call in the default suite).

### D-081 item 7 narrowing (applies on top of the contract; not a contract edit)

TB8-TB14 are proven on a fake client only. No `SheetClient` that reaches Google is built, imported or reachable from a CLI/route default. The live first write (HG-TB1) is held and is NOT part of this unit.

### Verbatim criteria

- **TB8 — The mapping is proposed, never guessed, and inert until confirmed.** From the sheet's **header row alone**, propose columns for
  `title, severity, screen, status, assignee, date, screenshot_link, bug_key`. Deterministic synonym matching first; a model fallback is
  allowed only with the header cells as the sole payload (the provider payload contains no data row). A column with two candidates or
  none is `unmapped`, with the candidates listed. `ColumnMapping.status` is `proposed | confirmed | stale`; only a named user holding
  `project.edit` on the project can confirm, recorded with who and when; every write path asserts `confirmed`. A header whose columns moved
  or were renamed makes the mapping `stale` and refuses writes until re-confirmed. `serves:` R47, R63, D-071 (5), O11. *LOCAL. Verify:* a
  fake client that reads only the header range (asserted from its call log); the provider-payload assertion; flip the status to
  `proposed` in a fixture, the write is refused; confirm as a user without `project.edit`, refused and the status unchanged; rename a
  header, `stale`. *Sabotage:* let `proposed` write, the refusal test goes red.
- **TB9 — CRITICAL. The first live write is shown, and confirmed, before it happens.** The write plan renders as exact cells (sheet, tab,
  row action, values). `first_write_confirmed_by` and `first_write_confirmed_at` are recorded against the **plan hash**; a changed plan
  (one cell, one row) needs a new confirmation. Confirming needs `project.edit`. `serves:` R48, D-071 (5), O11. *LOCAL. Verify:* the fake
  `SheetClient` records every call; assert **zero write calls** before confirmation, and zero again after a one-cell change to the
  plan. *Sabotage:* skip the hash comparison, the changed-plan test goes red.
- **TB10 — CRITICAL. A write adds or updates its own rows, nothing else.** Rows are located by the bug-key column. The client protocol
  has no delete operation. Unmapped columns are never touched. A cell whose current value differs from what we last wrote (a human edited
  it) is **not overwritten**: the bug gets `sync_conflict` and the conflict is listed on the tracker page. `serves:` R48, D-071 (5), O11.
  *LOCAL. Verify:* the protocol has no delete method (assert on the `Protocol`'s attributes); a fixture with an extra unmapped column keeps
  its value; edit a cell in the fake sheet between two syncs, the edit survives and the conflict is reported. *Sabotage:* write
  unconditionally, the human-edit test goes red.
- **TB11 — Idempotent and convergent.** Syncing the same bug set twice makes no duplicate rows. A crash after row k converges on retry with
  every row once. `serves:` R48, O11. *LOCAL. Verify:* sync twice and compare the fake sheet; inject a failure after row k and re-sync.
- **TB12 — A sheet outage is not a run failure.** Any sheet error sets `sync_status=error` with the last error and a retry time; the
  in-product tracker is updated regardless and stays authoritative; the run's result is unchanged; retries converge once the sheet is back.
  Sync status and last error are visible to `report.view` holders on the tracker page. `serves:` R49, O11. *LOCAL. Verify:* a fake client
  raising on every call, with a bug-producing run processed; the tracker has the bug, the run verdict is untouched, the status is visible;
  then a working client, and the sheet converges.
- **TB13 — CRITICAL. What is written is clean.** Every value passes `Redactor.scrub` before it leaves; the shown last error does too;
  screenshot links are authenticated product URLs (no public link, no signed URL that works without sign-in). The sheet id is fixed at
  confirmation, and changing it requires re-confirmation (TB9). `serves:` R50, O7, O11. *LOCAL. Verify:* a planted secret in a bug title
  and in an injected error string appears in neither the recorded write plan nor the tracker page; every link in the plan is on the
  product's own authenticated host; swapping the sheet id leaves the binding unconfirmed and refuses the write.
- **TB14 — Generic, not Pathlynks-shaped.** The same code serves two projects with different header layouts (a Pathlynks-Tracker-like
  fixture and an invented one) with no code change. The binding and mapping are stored per project under `projects/<slug>/`, and project A's
  binding is never read for project B. A header the code cannot map is `unmapped` and the project still works in-product. `serves:` R47,
  D-071 (5), O11. *LOCAL. Verify:* two fixtures, one test, both pass; a grep of `stages/tracker_*.py` finds no literal Pathlynks column name.

### Held row (not this unit; copied so the builder sees the boundary)

- **HG-TB1 — The live first write to the real Pathlynks Tracker.** The contract is proven on a fake `SheetClient`; the live step is a
  separate `HUMAN_GATE` row (`qa/gates/`, written by the checker when G8 reaches it). A named user holding `project.edit` is shown the plan
  as exact cells for the real sheet and confirms it; the mapping is agreed by Umesh or Mamta. An unexpected row count in the live sheet is a
  stop, not a retry. A G8 PASS never counts as this approval, and no agent presses it.

### Inherited rules (verbatim)

#### Persona walks and cross-platform (inherited by every row)

- G6 persona walk, **dev**: open the project, open the tracker, see a bug with its evidence, assign it, in a live browser with the
  hosted login. G8 persona walk, **subadmin**: paste the sheet link, review the mapping, see the first-write preview, confirm, in at most
  5 steps, and state that nothing was written before the confirm. Both are judged by the checker against a live browser per `docs/plan.md`.
- R65: store files, locks and markers use portable primitives; the lifecycle and mapping tests are OS-independent and run on Windows and,
  at T-203's deploy check, Ubuntu. No live Google or model call runs in the default suite.

### Out of scope (verbatim)

#### Out of scope / ignore

- Login, groups, the permission engine (T-204) and the queue (T-203): called, not built or judged here.
- Any new permission key (R63): a route that needs an unlisted key is a contract gap, raised to the checker, not worked around.
- A manual status override from the UI (statuses are machine-owned, TB2); deleting a bug; a bulk import of a sheet's existing rows.
- Two-way sync (sheet edits flowing back into AutoTester) beyond detecting a human edit as a conflict (TB10).
- Wording and visual polish beyond labelled, keyboard-operable controls (`auth.md` AU26).

### No-fire list (verbatim)

#### No-fire list (must NOT happen)

- No write to a sheet before a named `project.edit` holder confirmed the exact plan; none after the plan changed without a new confirm.
- No delete, no touch of an unmapped column, no overwrite of a human-edited cell.
- No bug closed, opened or counted by an INCONCLUSIVE, BLOCKED, NOT_RUN or verdict-less result.
- No sheet data row, secret, public link or signed URL sent to a provider or written to a sheet.
- No run failed, retried or blocked because the sheet was down.
- No permission key beyond the catalogue; no route that enforces only in the UI.

## 4. What exists and what is missing

Measured with git on 2026-10-11; master tip `4f8f5da100931ebda1b26836304bfbd38460764b`; the master working tree is dirty with other agents' files (listed in the dispatch snapshot) and none of that touches the paths below.

- **G8 code: nothing exists.** `grep -rn SheetClient src` finds nothing; none of `schema/tracker_binding.py`, `stages/tracker_mapping.py`, `stages/tracker_sheet.py`, `prompts/tracker_mapping_v1.md`, `ui/routes_tracker_binding.py`, `cli_tracker.py` exists on master or on any branch in `git branch -a`. No `tests/*tracker*` or `tests/*sheet*` file exists.
- **G6 core (predecessor): built, not merged, not PASS.** Branch `wave/g6-bug-core`, head `f8f59265`, 2 commits ahead of master / 56 behind (merge base `c09debd1`), worktree `.worktrees/g6-bug-core` clean. Files: `schema/tracked_bug.py` (82), `stages/bug_loop.py` (220), `stages/issues.py` +16 lines (258 total), `core/paths.py` +9, `schema/project.py` +6 (`bug_close_passes`), `tests/test_bug_loop.py` (235), `tests/test_bug_loop_close.py` (134), `tests/bug_loop_fixture.py` (65), manifest `qa/manifests/g6-bug-core.md`, checkpoint `qa/checkpoints/g6-bug-core.md`.
  Verdict `qa/verdicts/g6-bug-core.md` (branch copy): **CONTINUE-NEEDED, cycle 0**, TB1-TB6 all MET, 14/14 falsification rows, "remaining: full suite (combined G-core head)". TB7 (the tracker page, `ui/routes_tracker.py`) is "owed and not judged" and exists nowhere.
  Merge check (`git merge-tree`, read-only): conflicts in `docs/MAP.md` and `src/autotester/schema/project.py`; `core/paths.py` merges textually but the result is **309 lines against a 300 cap** (master's `core/paths.py` is already 300), so `doctor` goes red until G1 or a split frees room.
  Open probe findings from that verdict that touch this unit's input: P1 (medium) `process_run` writes its marker even when a run had no verdict yet, so a late verdict is dropped (`stages/bug_loop.py:197-199`); P2 per-bug vs per-case consecutive-pass reading is an open contract question. G8 reads `TrackedBug` as stored; it must not depend on those two behaviours.
- **`TrackedBug` has no sync fields** (`wave/g6-bug-core:src/autotester/schema/tracked_bug.py`): no `sync_status`, `sync_conflict`, last-written values or sheet row. TB10 says "the bug gets `sync_conflict`" and TB12 says `sync_status=error`. G6 owns `tracked_bug.py`, so this unit keeps sync state in **its own** model in `schema/tracker_binding.py` keyed by `bug_key` (builder decision, record it in the manifest; do not edit `tracked_bug.py`).
- **Reusable on master:** `core/redact.py` `Redactor.scrub` (:69) and `assert_no_raw_secrets` (:120); `core/ids.py` `content_id` (:121); `store/filestore.py` `write_json` (:34, atomic); `providers/base.py` `Provider` (:33); `schema/base.py` `Artifact` (:30). `stages/issues.py` is 242 lines on master.
- **Landing shape for G1 (not yet built):** `ui/routers.py`, `store/team_store.py`, `stages/run_launcher.py`, `schema/team_enums.py` all MISSING on master. `Project.tracker` does not exist on master (`schema/project.py` is 194 lines).
- **Auth:** there is no `auth/` package and no `authorize()` on master. `wave/t204-auth-fix1` (head `886936ab`, cycle 1 ready-for-check, not PASS) holds `ui/auth_middleware.py`; `unknown` how T-204's stub or engine will be called by the time this unit builds (QUEUE `t199b` row lists no `t204` dependency). `project.edit` must be enforced server-side per TB8/TB9; use the landed interface, or if none has landed, raise it to the checker as a contract gap and do not invent a permission shim.
- **Goal task:** `.goal/goal.json` T-199 `deps: [T-197]`, `done_check = uv run python scripts/check_deliverable.py --exists qa/verdicts/t-199-team-loop.md`, status pending. **AT-744 says** (`qa/issues.jsonl`, last row, status `fixed`, 2026-10-07, type `done-check-missing`): every pending task now carries a cmd `done_check` capable of failing; T-197..T-201 carry `--exists qa/verdicts/t-19N-team-loop.md`; the T-202..T-204 conversion was uncommitted at the time and it moves to `verified` only after a re-check on a committed tree. **Gap still open:** no unit writes a file called `qa/verdicts/t-199-team-loop.md` (the G6/G8 verdicts will be `qa/verdicts/t199a-bug-loop.md` / `qa/verdicts/t199b-sheet-sync-dryrun.md`), and `--exists` passes on any file of that name regardless of its verdict content. Also `qa/QUEUE.md` (t199b row note) says T-199 is not closed by this row until the live-write gate is answered or the checker amends the done_check. The builder does not touch `.goal/goal.json`; raise this to the checker.
- Plan-of-record rows: | G6 | `t199a-bug-loop` | T-199 | R43-R46 | E `stages/issues.py` (adapter, at most 58 lines); N `schema/tracked_bug.py`, `stages/bug_loop.py`, `ui/routes_tracker.py` | exhaustive transition table; same run processed twice; case deleted gives `stale`; INCONCLUSIVE/BLOCKED never closes; replayed runs count (D-072); three-run fixture | high | required (dev) | G1; G2 for the video-issue adapter |
  | G8 | `t199b-sheet-sync` | T-199 | R47-R50 | N `schema/tracker_binding.py`, `stages/tracker_mapping.py`, `stages/tracker_sheet.py`, `prompts/tracker_mapping_v1.md`, `ui/routes_tracker_binding.py`, `cli_tracker.py` | fake `SheetClient` with two header layouts; zero writes before confirmation; plan-hash change forces re-confirm; human-edited cell survives; outage leaves the tracker correct; mapping payload is header cells only | critical | required (subadmin) | G6; the live first write to the real Pathlynks Tracker is a HUMAN_GATE |

## 5. Files the builder will touch

Line counts are as of master `4f8f5da100931ebda1b26836304bfbd38460764b`. "New" files have no count yet and each must end at 300 lines or fewer.

| Path | New / existing | Lines now | What |
|---|---|---|---|
| `src/autotester/schema/tracker_binding.py` | new | - | `TrackerBinding`, `ColumnMapping` (`status`: `proposed | confirmed | stale`; who/when), `WritePlan` / plan hash, per-bug sync state (last-written values, sheet row, `sync_conflict`), `sync_status`, redacted `last_error`, retry time. `extra="forbid"`. |
| `src/autotester/stages/tracker_mapping.py` | new | - | Header-only propose/confirm/stale logic; deterministic synonyms first; model fallback via `Provider` with the header cells as the only payload. No literal Pathlynks column name. |
| `src/autotester/stages/tracker_sheet.py` | new | - | The `SheetClient` `Protocol` (no delete method), plan building, plan hash, first-write confirmation, idempotent sync, conflict detection, outage handling, redaction. Imports nothing that can reach the network. |
| `src/autotester/prompts/tracker_mapping_v1.md` | new | - | The fallback mapping prompt (a file, not an inline string). |
| `src/autotester/ui/routes_tracker_binding.py` | new | - | Bind a sheet, review mapping, preview the exact cells, confirm; module-level route-policy dict (`project.edit`); states "nothing written" until confirm. |
| `src/autotester/cli_tracker.py` | new | - | `autotester tracker ...` including `--dry-run` and `--output json` (T-174 conventions). Dry run is the only mode. |
| `src/autotester/ui/routers.py` | existing after G1 | MISSING on master | Fill the `tracker` stub router; do not add a second router list. |
| `src/autotester/cli.py` | existing | 295 | One sub-app registration (via G1's TF5 hook list if landed; else one `add_typer` line, which is 296 lines). |
| `src/autotester/core/paths.py` | existing | 300 | **Do not edit** (at the cap; G1 owns headroom). Use G1's landed binding-path helper; if none exists, derive `projects/<slug>/` from the existing `ProjectPaths(slug).dir` inside `store/team_store.py`'s helper or raise a contract gap. Do not create a second path-derivation site. |
| `tests/tracker_fakes.py` | new | - | `FakeSheetClient` (in-memory grid per tab, call log, no delete), a recording fake `Provider`, two invented header layouts. |
| `tests/test_tracker_mapping.py` | new | - | TB8, TB14 (proposed name; the contract names no G8 test file). |
| `tests/test_tracker_firstwrite.py` | new | - | TB9, TB10, the dry-run proofs in section 7 (proposed name). |
| `tests/test_tracker_sync.py` | new | - | TB11, TB12, TB13 (proposed name). |
| `tests/test_tracker_binding_ui.py` | new | - | Route gate, preview page, CLI dry run, no-live-client grep (proposed name). |
| `qa/manifests/t199b-sheet-sync-dryrun.md` | new | - | Evidence manifest, ends at `Status: ready-for-check`. |
| `docs/MAP.md` | existing, generated | 349 | `uv run autotester map`, last step. |

Not touched: `schema/tracked_bug.py`, `stages/bug_loop.py`, `stages/issues.py`, `ui/routes_tracker.py` (G6's), `schema/project.py`, `ui/project_view.py`, `ui/app.py`, `.goal/goal.json`, any `qa/contracts/` or `qa/gates/` file. `docs/ARCHITECTURE.md` gains rows only under a DECISIONS entry that authorizes the section (Lab Protocol); that entry is the maker/coordinator's, not the builder's.

## 6. Test scope

Run only these (exact files), plus lint and doctor. Replace `<n>` with the builder's actual node names; names below follow G6's `test_tbN_*` convention.

```
uv run pytest tests/test_tracker_mapping.py tests/test_tracker_firstwrite.py tests/test_tracker_sync.py tests/test_tracker_binding_ui.py
uv run pytest tests/test_bug_loop.py tests/test_bug_loop_close.py      # only the bug store this unit reads; must stay green, assertions unedited
uv run ruff check src/autotester/schema/tracker_binding.py src/autotester/stages/tracker_mapping.py src/autotester/stages/tracker_sheet.py src/autotester/ui/routes_tracker_binding.py src/autotester/cli_tracker.py tests/tracker_fakes.py tests/test_tracker_mapping.py tests/test_tracker_firstwrite.py tests/test_tracker_sync.py tests/test_tracker_binding_ui.py
uv run autotester doctor
```

Node prefixes: `test_tb8_*` ... `test_tb14_*`, one or more per criterion, plus `test_dryrun_*` for the section 7 proofs. All other tests belong to the checker's full suite.

## 7. Reachable test cases

All run in-process with `FakeSheetClient`; nothing contacts Google and nothing calls a live model (a recording fake `Provider` stands in). Happy path first.

**How the dry run proves the exact rows it would write while the sheet stays unchanged**

1. `FakeSheetClient` holds an in-memory grid per tab and logs every call by method name. Its `Protocol` has `read_header`, `read_column`, `append_row`, `update_cells` and **no delete** (TB10 asserts the attribute list).
2. `build_write_plan(bugs, binding, current_key_column)` is pure. It returns a `WritePlan`: sheet id, tab, and per bug a row action (`append` or `update row r`) with the **exact cell values** in mapped-column order, then `plan_hash = content_id(...)` over that canonical form.
3. A dry run (`sync(..., dry_run=True)`, the only mode the CLI and route expose) returns the plan and calls no write method. The test asserts, in this order: (a) the plan lists N rows with the exact cell strings expected for the two seeded bugs; (b) the fake's call log contains only `read_header` and `read_column` entries, zero `append_row` / `update_cells`; (c) a deep copy of the grid taken before equals the grid after, cell for cell; (d) the CLI `--output json` for the same input prints the same `plan_hash`.
4. **Plan == write proof.** On a second `FakeSheetClient` seeded identically, with the mapping confirmed and `first_write_confirmed_by/at` recorded against `plan_hash`, run the apply path. The test asserts `diff(grid_after, grid_before)` equals the dry run's plan cell for cell. This is the proof that the rows shown are exactly the rows a confirmed run would write, and it exists only against the fake (the apply function is not reachable from the CLI or route default).
5. **No live path exists.** A grep test over `src/autotester/stages/tracker_*.py`, `cli_tracker.py` and `ui/routes_tracker_binding.py` finds none of `subprocess`, `httpx`, `requests`, `urllib.request`, `googleapiclient`, `gspread`, `socket`; a transport-level guard (as in `consent.md` CN1) records zero outbound requests across the whole test module.

**Scenarios**

1. Happy: layout A (a Pathlynks-Tracker-like invented header: bug title / severity / page / status / assigned to / date reported / screenshot / bug id) maps all eight fields from the header row alone; the fake's log shows exactly one header-range read and no data-row read (TB8).
2. Happy: a named user with `project.edit` confirms; status becomes `confirmed` with who and when; the preview shows exact cells; the dry run changes nothing (items 1-3 above).
3. Happy: the apply path on the second fake writes only the previewed cells (item 4); first write recorded against the plan hash (TB9).
4. Changed plan: one cell differs (a bug title edited, or a third bug added) -> new hash -> the earlier confirmation no longer covers it -> zero write calls until re-confirmed (TB9).
5. Ambiguous header (two candidates for status) or missing column -> `unmapped` with the candidate list; the project still works in-product (TB8, TB14).
6. Header renamed or a column moved -> mapping `stale`; writes refused until re-confirmed (TB8).
7. Status forced to `proposed` -> write refused; confirm as a user without `project.edit` -> refused, status unchanged (TB8).
8. Human edit: a cell in the fake changes between two syncs -> not overwritten, a `sync_conflict` is recorded and listed; an extra unmapped column keeps its value (TB10).
9. Idempotent: sync twice -> no duplicate rows; inject a failure after row k, re-sync -> every row exactly once (TB11).
10. Outage: a fake raising on every call -> `sync_status=error`, redacted last error, retry time; the in-product bug store and the run's verdict are untouched; a working client then converges (TB12).
11. Clean writes: a planted secret in a bug title and in an injected error string appears in neither the recorded plan nor the page; every link in the plan is on the product's own authenticated host; swapping the sheet id leaves the binding unconfirmed and refuses the write (TB13).
12. Generic: the same test runs with layout B (invented: summary / priority / where / state / owner / logged / link / key) and no code change; grep of `stages/tracker_*.py` finds no literal Pathlynks column name; project A's binding is never read for project B (TB14).
13. Provider fallback payload: a recording fake `Provider` receives only the header cells (TB8).
14. Persona walk, subadmin (section 9).

## 8. Gate answers

- `qa/gates/t199-first-live-write.md` (verbatim): "**Status:** OPEN - deferred by the owner. No Answered line for the live write." and "Umesh (2026-10-10): "vo in future hogaa abhi nhi"." and "What is authorized now (D-081 item 7): T-199 builds and proves a DRY RUN only, on a fake `SheetClient`. The mapping preview may be shown. Zero live writes. The first live write needs a new answer here, with a named user confirming the preview and the column mapping agreed by Umesh or Mamta."
  **There is no `Answered:` line for the live write.** That is the intended state; this unit must not look for one and must not build the live path.
- `qa/gates/plan-approved-g10.md` (verbatim): "Approved -- Umesh, 2026-10-07 (chat), recorded as D-074." Its line on this unit: "Sheet sync to a team tracker is shown and confirmed before the first write."
- D-081 item 7 (verbatim, `docs/DECISIONS.md`): "**Pathlynks Tracker sheet: no live write now.** Umesh: "vo in future hogaa abhi nhi". T-199 builds and proves a dry run only; the first live write stays a HUMAN_GATE."
- D-081 item 4 (host and DNS): does not apply to this unit. No hosted check, no Ubuntu step.
- D-071 (5) widens T-199 to any project: mapping proposed on first use, shown for confirmation, first live write shown and confirmed, mapping stored per project (carried by TB8, TB9, TB14).
- The real Tracker sheet id is in `.work/google-ids-private.md`; the builder does not open it, does not read the real sheet's header and makes no call to Google Sheets.

## 9. UI surface and persona walk

UI surface: yes (a bind / mapping / preview / confirm screen, `ui/routes_tracker_binding.py`).
Persona walk: required (subadmin). User types from `docs/features/team-loop/intent.md`: admin, subadmin, dev, tester; the contract and the plan name **subadmin** for G8. The walk: paste the sheet link, review the mapping, see the first-write preview, confirm, in at most 5 steps, and the page states that nothing was written before the confirm. Judged by the checker in a live browser (Mode D). The link target is a fixture, not the real sheet.

## 10. Dependencies and conflicts

Must land first, in this order (from `qa/QUEUE.md`):
1. `land-t203-hosting` (conflicts with master in `ui/routes_runs.py`; touches `ui/app.py`, `core/env.py`) - owns those three files first.
2. `t205-g10-headroom` (G1 / T-205) - creates `ui/routers.py`, `stages/run_launcher.py`, `store/team_store.py`, `schema/team_enums.py`, and must free `core/paths.py` (300) and `schema/project.py` room.
3. `t197-pointers-review` (G2 / T-197; `goal.json` dep, and the video-issue adapter needs its output). Branch `wave/g2-review-core` head `faa02786` is cycle 1, not PASS, and conflicts with master in `docs/MAP.md`. No G8 code imports a G2 symbol; the dependency is the task-level one. If the coordinator waives it for G8, the video-found-bug rows simply do not appear in test fixtures.
4. `t199a-bug-loop` (G6): merge `wave/g6-bug-core` after a combined-head full suite and a fresh checker cycle, plus TB7 (`ui/routes_tracker.py`).
`t204-team-login` is not in the QUEUE `after` list for this row; the `project.edit` gate needs whatever identity interface exists then (section 4).

| Shared file | Used by Group 10 units | Owner for this unit |
|---|---|---|
| `src/autotester/core/paths.py` (300) | G1, G6 (+9 pending), G8, G3, G5 | `t205-g10-headroom`; this unit does not edit it |
| `src/autotester/schema/project.py` (194) | G1, G3, G5, G6 (`bug_close_passes`), G8 reads | `t205-g10-headroom` first, then G5/G6 sequentially; this unit does not edit it |
| `src/autotester/stages/issues.py` (242) | G6 only | `t199a-bug-loop` |
| `src/autotester/ui/routers.py` (new in G1) | every Group 10 UI unit | `t205-g10-headroom` creates; this unit fills the `tracker` stub only |
| `src/autotester/cli.py` (295) | G1 hook, G8 `tracker`, G5 `schedule`, G2 | `t205-g10-headroom` (TF5 hook); this unit appends one sub-app |
| `src/autotester/schema/tracked_bug.py`, `stages/bug_loop.py`, `ui/routes_tracker.py` | G6, G8 reads | `t199a-bug-loop` |
| `docs/MAP.md` | every unit | regenerated last at merge; no owner, never hand-edited |

## 11. Budget and process rules

Check budget: **45 min** (Tier L).
- Edit in place. Name the exact file and function before changing existing code. No `*_v2.py` / `*_new.py`, no second copy of a function (CLAUDE.md design rules). A regression is reverted to the last good git state, never stacked with a new fix.
- Design rules (enforced by `uv run autotester doctor`): file <= 300 lines, function <= 50 lines, module docstring states one job, every domain shape is a Pydantic model in `schema/` with `extra="forbid"`, prompts are files, all model calls go through `providers.base.Provider`.
- Credentials: values live only in the gitignored repo-root `.env`; code and tests name keys as `SecretRef`, never values. No secret in a log, plan, page, outbox file or error string (`Redactor.scrub`).
- The builder runs NO full suite (`uv run pytest` bare). It runs only the test files named in section 6, `uv run ruff check` on the files it changed, and `uv run autotester doctor`. No CLI `-q` on pytest (AT-503). The one full suite is run once, by the checker, at the integration head (G6 verdict, `wave/g6-bug-core:qa/verdicts/g6-bug-core.md`, "Full-suite status").
- Falsification (mutation) only in a throwaway copy outside the repo (for example `git archive` into the scratchpad, unique directory name per unit). Never perturb the bound worktree.
- Kill only PIDs the builder itself started (record each PID when launching; no `taskkill /IM`, no kill by port or by name). Other agents run servers and browsers in parallel on this machine.
- No `cd X && cmd`; use `git -C <dir>`, absolute paths or the tool's working directory.
- Never edit `qa/contracts/`, `docs/DECISIONS.md`, `qa/gates/`, `.claude/hooks/*`, `qa/hooks/*`, `.claude/settings.json`. Contract questions go verbatim to `qa/feedback-inbox.md`. Only `/checker` can PASS; the maker ends at `Status: ready-for-check` with `Fix cycle: N` in `qa/manifests/<slug>.md`.
- Commit before asking for a verdict (`qa/gates/commit-before-verdict.md`); `docs/MAP.md` is regenerated with `uv run autotester map` as the last step, not hand-edited (it conflicts across sibling branches, so regenerate at merge).
- No git push by the builder; the checker pushes `origin master` on PASS (CLAUDE.md "Push on PASS", D-007).
- Extra for this unit: no call to Google Sheets or any Google API, no `gws` invocation, no open of `.work/google-ids-private.md`; no live model call in the default suite; all tracker state under `projects/<slug>/` and the gitignored data root (`git check-ignore` must cover it, TF7).
