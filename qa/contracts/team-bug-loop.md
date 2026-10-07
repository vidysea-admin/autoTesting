# Contract — team-bug-loop: the tracked-bug loop (G6) and tracker sheet sync (G8)

**Covers:** goal task T-199, split by D-070 part 4 into **G6 `t199a-bug-loop`** (TB1-TB7, R43-R46) and **G8 `t199b-sheet-sync`**
(TB8-TB14, R47-R50), widened to any project by D-071 (5). **Owner:** /checker. **Status:** DRAFT. It goes ACTIVE on the maker's first
`ready-for-check` of G6; G8's rows bind from G8's own `ready-for-check`. Creation is human-approved (checker SKILL, "Contract maintenance"):
this file is authored from the maker's proposal (`.work/plan-g10/contract-proposal-T-199.md`) plus the Group 10 plan gate.
**Criticality:** G6 HIGH. G8 CRITICAL for TB9, TB10, TB13 (an outward-facing write to a team's sheet); HIGH elsewhere.
**Serves:** intent O10, O11, O3, O7, O15; spec R43-R50, R63 (no new permission keys), R65; D-071 (5), D-072.
**Depends on:** `grade.md` (only the grader owns a verdict), `execute.md` (pinned regression, R15), `auth.md` (AU11-AU14 and the
closed key catalogue), `core-invariants.md` C5, C7, `consent.md`. **Does not duplicate:** T-204 owns login, groups and the
`authorize()` engine; T-203 owns the queue and settings. This contract calls them.
**Code (expected, none exists yet):** G6 — `stages/issues.py` (the adapter, edit in place, at most 58 added lines), new
`schema/tracked_bug.py`, `stages/bug_loop.py`, `ui/routes_tracker.py`. G8 — new `schema/tracker_binding.py`,
`stages/tracker_mapping.py`, `stages/tracker_sheet.py`, `prompts/tracker_mapping_v1.md`, `ui/routes_tracker_binding.py`,
`cli_tracker.py`. **Tests:** none yet.

## Why it exists

A failure that is re-reported every run buries the team; a bug that closes because a run could not judge is a lie; and a sheet that an
agent writes to without being asked is the team's own data damaged by a tool. This contract refuses all three: one bug per failure, a
state machine that only a graded verdict moves, and a sheet that is touched only after a named user has seen the exact cells.

## Verification classes

`LOCAL` = the checker runs it on the dev host with fixtures and a **fake `SheetClient`** (no live Google call, no live model call in the
default suite). `HUMAN_GATE` = a named human decides; it is never PASSed by the checker (see "Held").

## Permission rulings (no new keys, R63)

Every route below is enforced **server-side** through T-204's `authorize(user, key, resource)` (AU12) and falls under the route-enumeration
default-deny test (AU14). A hidden button is not enforcement.

| Action | Key | Scopes that can satisfy it |
|---|---|---|
| View the tracker page, a bug, its evidence link, sync status and last error | `report.view` | all, assigned, own, shared (resolved by AU12) |
| Edit a bug's assignee | `project.edit` | all, assigned, own |
| Bind, re-map, confirm or re-confirm a sheet; confirm the first write | `project.edit` | all, assigned, own |

Statuses are **machine-owned** (TB2); no UI route sets `status`. A user without the key gets the same not-found a non-member gets (AU13).

## Criteria

### A. In-product bug loop (G6, T-199a)

- **TB1 — The bug key is stable.** `bug_key = content_id(project, case_id, failing criterion id)` for a case failure, and the
  `Issue.id` fingerprint for a video-found issue. It never includes a run id, a time, a path, or a screenshot hash. Three runs failing the
  same criterion are one bug; two failing criteria on one case are two bugs; a secret value planted in the case text does not appear in the
  key. `serves:` R43, O10. *LOCAL. Verify:* the three cases above as a parametrised test. *Sabotage:* hash the run id into the key, the
  one-bug assertion goes red.
- **TB2 — The lifecycle is a table, tested over every cell.** `(none, FAIL)->open` · `(open, FAIL)->open`, count+1, `last_seen`
  updated · `(open, PASS x k)->open` for `k < N` · `(open, PASS x N)->fixed` · `(fixed, FAIL)->reopened` ·
  `(any, INCONCLUSIVE | BLOCKED | NOT_RUN)->unchanged`. **N = 2 consecutive passing verdicts**, a stored configuration value with that
  default (the plan gate's assumption); a PASS verdict is "consecutive" only if no FAIL falls between. `serves:` R44, O10. *LOCAL.
  Verify:* parametrised over states x verdict kinds, asserting state, count and the `first_seen`/`last_seen` pair per cell; a run that
  could not judge neither closes nor opens. *Sabotage:* count INCONCLUSIVE as a pass, the `unchanged` rows go red; set N to 1, the
  `k < N` row goes red.
- **TB3 — Verdicts only, replayed runs included.** The loop reads `Verdict` and never `RawResult`. A replayed run (D-072) carries a judge
  verdict and counts like any other. A result with no verdict changes nothing. A PASS counts toward closing only when its verdict cites
  evidence (the grade rule is not weakened). `serves:` R46, R44, O3. *LOCAL. Verify:* feed a `RawResult`-only run, a replayed run with a
  verdict, and a PASS verdict without evidence; assert, in order, no change, counted, not counted. *Sabotage:* read the raw result's
  status, the first case goes red.
- **TB4 — An honest close.** A `fixed` bug lists the run ids and verdict ids that closed it. If its case was deleted or its criterion
  changed, it becomes `stale`, never `fixed`. Closing a bug never deletes its pinned regression case (R15, `execute.md`). `serves:` R44,
  R15, O10. *LOCAL. Verify:* close a bug and read the two id lists back; delete the case after a FAIL and process the next run, state is
  `stale`; pin a case, close its bug, the case still exists and `delete_case` still refuses.
- **TB5 — The adapter lives in `stages/issues.py`, in place.** The conversion `Issue -> TrackedBug` is edited into the existing
  `stages/issues.py` (at most 58 added lines), is the **only** place that derives a key from an `Issue`, and keeps the file at or under
  300 lines. `serves:` R43, design rules (CLAUDE.md), O10. *LOCAL. Verify:* `git diff --stat` on that file against its base shows the added
  line count; `uv run autotester doctor` is green (file length, one concept one place); a grep finds no second key function.
  **Landing note:** the file is 242 lines at contract time, so 58 added lines is exactly the headroom; a larger adapter is a split-first
  gate, not a pass.
- **TB6 — Idempotent per run.** Processing run R twice yields the same bug set, counts and lifecycle states (a processed-run marker, built
  with portable file operations, R65). A crash between two bugs of one run converges on retry with no double count. `serves:` R46, R65.
  *LOCAL. Verify:* process the same run twice and compare the stores byte for byte; inject a failure after bug 1 of 2 and re-run. Run the
  same tests on Windows and, at T-203's deploy check, Ubuntu. *Sabotage:* drop the marker, the count doubles and the test goes red.
- **TB7 — The tracker page, scoped by `report.view` and edited by `project.edit`.** The page lists bugs with status, severity, screen,
  assignee, first/last seen, count and an evidence link, with filters by status and severity. Viewing needs `report.view` over the project
  per AU12; a holder of `report.view@shared` only sees bugs whose latest evidence run report is shared with them; a user with no scope
  gets not-found, not a list (AU13). The evidence link resolves only behind the login. Editing the assignee needs `project.edit`
  server-side; the assignee is a project member or free text; a user with `report.view` but not `project.edit` gets 403 on the edit route
  and the value is unchanged. `serves:` R45, R63, AU12-AU14, O10, O15. *LOCAL. Verify:* a table over the four default groups (admin,
  subadmin, developer, tester) x {list, evidence link, assignee edit} x {own project, assigned project, unassigned project, shared run};
  the route-enumeration test lists the new routes as guarded; `curl` of the evidence link without a session is refused. *Sabotage:* gate
  the edit on the view key only, the tester row goes red.

### B. Tracker binding and sheet sync (G8, T-199b)

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

## Held (HUMAN_GATE, not a checker PASS)

- **HG-TB1 — The live first write to the real Pathlynks Tracker.** The contract is proven on a fake `SheetClient`; the live step is a
  separate `HUMAN_GATE` row (`qa/gates/`, written by the checker when G8 reaches it). A named user holding `project.edit` is shown the plan
  as exact cells for the real sheet and confirms it; the mapping is agreed by Umesh or Mamta. An unexpected row count in the live sheet is a
  stop, not a retry. A G8 PASS never counts as this approval, and no agent presses it.

## Persona walks and cross-platform (inherited by every row)

- G6 persona walk, **dev**: open the project, open the tracker, see a bug with its evidence, assign it, in a live browser with the
  hosted login. G8 persona walk, **subadmin**: paste the sheet link, review the mapping, see the first-write preview, confirm, in at most
  5 steps, and state that nothing was written before the confirm. Both are judged by the checker against a live browser per `docs/plan.md`.
- R65: store files, locks and markers use portable primitives; the lifecycle and mapping tests are OS-independent and run on Windows and,
  at T-203's deploy check, Ubuntu. No live Google or model call runs in the default suite.

## Out of scope / ignore

- Login, groups, the permission engine (T-204) and the queue (T-203): called, not built or judged here.
- Any new permission key (R63): a route that needs an unlisted key is a contract gap, raised to the checker, not worked around.
- A manual status override from the UI (statuses are machine-owned, TB2); deleting a bug; a bulk import of a sheet's existing rows.
- Two-way sync (sheet edits flowing back into AutoTester) beyond detecting a human edit as a conflict (TB10).
- Wording and visual polish beyond labelled, keyboard-operable controls (`auth.md` AU26).

## No-fire list (must NOT happen)

- No write to a sheet before a named `project.edit` holder confirmed the exact plan; none after the plan changed without a new confirm.
- No delete, no touch of an unmapped column, no overwrite of a human-edited cell.
- No bug closed, opened or counted by an INCONCLUSIVE, BLOCKED, NOT_RUN or verdict-less result.
- No sheet data row, secret, public link or signed URL sent to a provider or written to a sheet.
- No run failed, retried or blocked because the sheet was down.
- No permission key beyond the catalogue; no route that enforces only in the UI.

## Amendment log (append-only; git history is the version)

- 2026-10-07 · init · authored by /checker from the maker's T-199 proposal (`.work/plan-g10/contract-proposal-T-199.md`), spec
  R43-R50 and R63, `docs/plan.md` G6 and G8, `qa/gates/plan-approved-g10.md`, D-071 (5) and D-072. Changes against the proposal: the
  adapter row is TB5 (the proposal's "closing never deletes the pinned case" moved into TB4); permission rulings are fixed to
  `report.view` (view) and `project.edit` (assignee edit, binding, confirmation) with no new keys; N is 2 consecutive passes; the live
  first write is `HG-TB1`; the proposal's persona-walk (TB15) and Windows/Ubuntu (TB16) rows are folded in as inherited rules.
  DRAFT until G6's first checker PASS.
