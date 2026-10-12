# Brief — t201-test-button: T-201 team on-demand Test button (queue row `t201b-test-button`, plan unit G7)

**Dispatch status: READY once its predecessors land (section 10); NOT dispatchable on today's master.** The contract exists
(`qa/contracts/team-test-button.md`, Status ACTIVE 2026-10-07, TT1-TT6 for this unit), all gates it needs are answered, and the files are named.
What blocks it is order: it needs the G1 launcher, the T-203 run queue, T-204 identity and the G4 delivery unit, none of which is on master.
Written 2026-10-11 by the readiness pass. Scope: **G7 `t201b-test-button` (TT1-TT6)**. The other half of goal task T-201, **G4 `t201a-report-delivery` (TT7-TT9)**,
is a predecessor unit that needs its own brief (none exists in `qa/briefs/` at the time of writing).

## 1. Policy and tier

Policy-Version: proportional-verification/2026-10-10.9
Tier: **L**. Triggers: auth (a state-changing route gated by `project.run`, Origin guard and session, TT1), tenancy-like scoping of who may start a run on which project (TT1 table), and an outward-facing run that can mutate production under `ALLOW_WRITES` (TT6). The contract itself states "Tier L (auth, outward-facing run, outward-facing email)".
Dual check: **required**. Trigger: `prod-write src/autotester/ui/routes_runs.py:162` (today's gate, `approval = _require_live_case_approval(...)`, which G1 moves into the launcher; the Test button's refusal-without-trace rule TT6 depends on exactly this check) and `auth src/autotester/ui/routes_runs.py:139` (`@router.post("/projects/{slug}/run")`, the existing run route the button must not weaken). The contract names the dual check for TT1, TT5, TT6 (and TT8, which is G4's).

## 2. Root and base

Root: `D:/autoTesting`. Base: current `master` = `4f8f5da100931ebda1b26836304bfbd38460764b` at the time of writing. It will move: `land-t203-hosting`, `t205-g10-headroom`, `t204-team-login`, `t201a-report-delivery` land first. **The builder re-reads `git -C D:/autoTesting rev-parse master` at dispatch and records that sha as the base in the manifest.**
Branch to build in: a new `wave/t201b-test-button` cut from that tip, worktree `D:/autoTesting/.worktrees/t201b-test-button`.
Reason: D-080 item 1 (origin/master is the single trunk; branches are inputs re-landed unit by unit). `wave/t203-hosting` is 68 commits behind / 6 ahead and conflicts with master in `ui/routes_runs.py`, and `wave/t204-auth-fix1` is still cycle 1 ready-for-check, so building on either would inherit unverified state.

## 3. Acceptance criteria

Source: `qa/contracts/team-test-button.md`, Status ACTIVE. This unit is G7: **TT1-TT6**, verbatim below. TT7-TT9 are G4's.
Contract criticality: CRITICAL for TT1, TT5, TT6 (and TT8); HIGH elsewhere. TT5 and TT6 can be `BLOCKED-CAPABILITY` (never PASS) until their dependencies exist; see the notes under the criteria.

### Verbatim criteria

- **TT1 — Authenticated, authorised, Origin-checked, and no trace on refusal (R56, R64, CRITICAL).**
  `POST /projects/{slug}/test` (the route name is the maker's; the **behaviour** is the contract) is refused, **with no `RunRequest`, no run
  directory, no queue entry, no browser and no model call**, in each of: an anonymous request (302 to `/auth/login`, `auth.md` AU16); a
  signed-in user without **`project.run` on that project** (403 whose body names `project.run`); a signed-in user whose project is not
  visible to them (the same 404 as a project that does not exist, AU13); a cross-origin POST carrying a valid session cookie (403 from the
  D-066 guard, which runs **before** authentication, AU18); an unknown slug (404). The route is declared in this unit's route-policy dict as
  `project.run` with the project resource (`team-foundation.md` TF4); the AU14 enumeration test passes with it present. A GET to the route
  changes nothing. `serves:` intent#O13, O15, spec R56, R64, `auth.md` AU12-AU16, AU18, `hosting.md` HO19.
  *Evidence (LOCAL):* `tests/test_team_run_gate.py` — the five cases above, each asserting the data-root file listing is byte-identical
  before and after, the queue is empty, and the recording browser factory and recording provider were never called; plus the four default
  groups x `{own, assigned, other}` projects table for 200/303 vs 403/404. *Mutation:* check permission after enqueue -> the empty-queue
  assertion fails; drop the Origin guard from the route -> the cross-origin case fails.

- **TT2 — The button is a request, not a run (R56).**
  A permitted press returns `303` to the run status page **within 2 s** with the browser factory untouched on that request; the work is
  done by the queue worker. The status page shows the status and, while `queued`, the **position**; it moves
  `queued -> running -> done | failed | refused | interrupted`, and is **readable without the worker** (it reads the persisted entry, not a
  worker handle). The project page shows the button only to a viewer who may use it, and the route enforces the permission regardless of
  what the page shows (the page hiding a button is not enforcement). `serves:` intent#O13, spec R56, `hosting.md` HO16.
  *Evidence (LOCAL):* `tests/test_team_run_status.py` — a fake runner that blocks on an event; assert response time < 2 s, the status
  sequence, the position while queued, and that the status page renders after the app object is re-created (persistence). *Mutation:* run the
  case inline in the request -> the < 2 s assertion fails.

- **TT3 — The run is attributable to the person who pressed it (R56).**
  The `RunRequest` **and the resulting `Run`** record `requested_by` (user id and email taken from the **session**, never from the request),
  `requested_at`, `trigger=manual`, `via=team_button`; the run's report header names who started it. A request carrying `requested_by`,
  `user`, `email` or `owner` in its body or query ignores them (TT8 asserts the same for the recipient). The fields are optional on `Run`
  (a `run.json` written before this unit still loads, `team-foundation.md` TF2). `serves:` intent#O13, O15, spec R56, `hosting.md` HO21.
  *Evidence (LOCAL):* `tests/test_team_run_attribution.py` — two sessions press, assert two different `requested_by` values on queue entry,
  `Run` and report header; a forged `requested_by=other@x` is ignored; load a golden pre-change `run.json`. *Mutation:* read
  `requested_by` from the form -> the forged-value test fails.

- **TT4 — It reuses the one G1 launcher, and the existing run behaviour is unchanged (R56, R57).**
  The queue worker started by the button calls **the single function in `stages/run_launcher.py`** (`team-foundation.md` TF1) — the same one
  `trigger_run` and the scheduler's runs use. This unit adds **no** function that builds a `Run`, starts a `BrowserSession`, or calls the
  pipeline (`stages/run_case_pipeline.py` / `_execute_with_trace`); the AST import test over `ui/routes_team_run.py` finds none of them;
  `doctor` finds no duplicate concept. `ui-run.md` **RU2** (no cases or no provider -> 400 before any browser), **RU3** (every case result
  and verdict persisted, a `Run` saved) and **RU4** (`.env` visible to the process) hold on the button path exactly as on the old path; the
  existing RU tests pass **with their assertions unedited**. *(RU1's "synchronous" wording is T-203's amendment, not this unit's.)*
  `serves:` intent#O13, spec R54, R56, `ui-run.md` RU2-RU4, `team-foundation.md` TF1.
  *Evidence (LOCAL):* `tests/test_team_run_launcher.py` (patch the launcher; press the button; assert it is called once with
  `trigger=manual` and the user); the AST import test; the existing `tests/test_ui_run*.py` unchanged; `uv run autotester doctor`.
  *Mutation:* add a second `Run(` construction site in the button route -> doctor or the grep test fails.

- **TT5 — The queue seam: the button enqueues and never bypasses T-203's rules (R57, CRITICAL).**
  Group 10 does not own the queue. A second press while the project already has an entry `queued` or `running` returns **the existing
  request and its position** (303 to its page; no second entry), and the per-project single flight and server-wide cap stay `hosting.md`
  HO17's. This unit asserts only that it **never** starts a run except through the queue, and **never** calls the worker, the launcher or
  `BrowserSession` from the request thread. Until T-203's queue lands, the unit is built and tested against **a fake queue that
  implements HO16's interface** (enqueue, get by id, list by project, status values); the real-queue integration is judged when T-203
  PASSes and is `BLOCKED-CAPABILITY`, never PASS, before then. `serves:` intent#O13, spec R57, `hosting.md` HO16, HO17.
  *Evidence (LOCAL):* `tests/test_team_run_queue_seam.py` — two presses of one project -> one entry and the same id returned; three
  projects against a fake cap of 2 -> the fake runner's observed concurrency <= 2 and the button unit contains no cap logic (grep for
  `max_concurrent_runs` in this unit's files finds none). *Mutation:* create a second entry on the second press -> the one-entry
  assertion fails.

- **TT6 — The same gate as a schedule: a credential-derived approval, or a refusal that names the state and leaves no trace (R60, CRITICAL).**
  The run proceeds only on an approval that covers (project, run_kind, target) under D-068's credential-derived rule (`team-schedule.md` TS5
  is the same check; one implementation, `team-foundation.md` TF2). Otherwise the request ends `refused` with the reason shown to the person
  who pressed it, naming the state (e.g. "`PATHLYNKS_USER_EMAIL` has no value; enter it on the Credentials page"; "no credential pair is
  declared for this project"), and: **zero requests reach the network (asserted at the transport, `consent.md` CN1), no run directory exists,
  no browser factory is called.** The refusal text contains **no credential value** and passes `Redactor.scrub`. A role never skips it: an admin
  pressing Test on an uncredentialed project is refused the same way (`auth.md` AU15). The approval's own bounds (`max_actions`,
  `wall_clock_s`) cap the run and name what it left unreached; **no extra cooldown** is built (gate `plan-approved-g10.md`). AT-570 (a
  live case needs a covering approval) is re-verified through the launcher (`team-foundation.md` TF2). **Dependency:** the credential-derived
  `covering_approval` is the D-068 implementation; until it lands this row is `BLOCKED-CAPABILITY`, not PASS. `serves:` intent#O13, O7,
  spec R60, D-068, `consent.md` CN1, `auth.md` AU15, `hosting.md` HO19.
  *Evidence (LOCAL):* `tests/test_team_run_approval.py` — three fixtures (no `SecretRef`; `SecretRef` with no value; provisioned) pressed by a
  Developer and by an Admin; assert the transport and browser counters are 0 in the first two, the `runs/` listing is unchanged, and the
  message names the state. *Mutation:* skip the approval check on the admin path -> the admin case fails.

### Notes on the two BLOCKED-CAPABILITY clauses (measured 2026-10-11)

- TT6's "credential-derived `covering_approval` ... until it lands this row is `BLOCKED-CAPABILITY`": the capability **has landed on master**. `stages/explore_consent.py:35` `covering_approval(..., secrets=, account_keys=)` implements D-068 and is called at `ui/routes_runs.py:92`; `git branch --merged master` lists `wave/d063-grant-budget`. The builder should treat TT6 as buildable, and the checker decides whether the clause is lifted.
- TT5's "real-queue integration is judged when T-203 PASSes and is `BLOCKED-CAPABILITY`, never PASS, before then": still true. `wave/t203-hosting` has a slice PASS (verdict `66f8b98c`) but is not merged. Build against the fake queue first; the real queue is wired after `land-t203-hosting`.

### Persona walk and boundaries (verbatim)

#### Persona walk (Mode D, the checker's own browser; judged once the pages exist)

`dev`: from the project page press **Test**, watch the status page, open the report, in <= 3 steps; then open **My reports** and find it.
Open the profile page, tick "Email me run reports", press Test again, and confirm the outbox (or, once credentials exist, the inbox of a
test account) holds exactly one message. Negative walks: no credentials (the message names the Credentials page); press while the project
is already queued (the existing request and its position are shown); a `tester` opens **My reports** and sees only shared ones.

### Out of scope (verbatim)

#### Out of scope / ignore

- The queue, concurrency cap, settings page, tick timer and the Ubuntu deploy (T-203); sign-up, sessions, groups (T-204).
- The live virtual-display (noVNC) view: T-203 owns exposing it behind the login (`hosting.md`); not re-tested here.
- Slack or any channel other than the inbox and email; per-user quotas or a cooldown between presses.
- The SMTP sender address and credentials (HUMAN_GATE); the real relay is judged at the go-live rehearsal (`hosting.md` HO27, SERVER-GATED).
- Comment, share and access-request objects (G9); the tracker (G6, G8).

### No-fire list (verbatim)

#### No-fire list (must NOT happen)

- No run, run directory, queue entry, browser or model call from a refused press; no run started outside the queue.
- No recipient read from a request; no email to a user who has not ticked the box or who cannot view that report.
- No new permission key; no route without a declared permission (AU14).
- No real SMTP connection in the default test suite or the default adapter; no attachment, screenshot, video, credential or page content in a message.
- No second function that builds a `Run` or starts a browser (one launcher).

## 4. What exists and what is missing

Measured 2026-10-11; master tip `4f8f5da100931ebda1b26836304bfbd38460764b`.

- **G7 code: nothing exists.** `ui/routes_team_run.py` is MISSING on master and on every branch; no `tests/test_team_run_*.py` exists. `ui/project_view.py` is 105 lines and has no Test button; the project page's Run button is built in `ui/app.py:284` and passed to `project_view._actions_card` (`:67`) at `app.py:291`. `ui/app.py` is **300 lines (at the cap)**.
- **Run route today:** `ui/routes_runs.py` (204 lines): `trigger_run` at `:139` is synchronous, runs the whole project in the request, and calls `_require_live_case_approval` at `:162` (`:75` def). It checks no login and no `project.run` permission (none exists on master).
- **Launcher (G1/T-205): not built.** `stages/run_launcher.py`, `ui/routers.py`, `store/team_store.py`, `schema/team_enums.py` MISSING. `Run` (`schema/run.py`, 121 lines) has no `requested_by` / `slot_key` / `via`; TF2 adds them in G1.
- **Queue (T-203): built, not merged.** `wave/t203-hosting` (head `66f8b98c`, 6 commits ahead / 68 behind, slice PASS cycle 1, 2026-10-10, `qa/verdicts/t203-hosting.md`). `schema/run_queue.py` `QueueEntry` has `{id, project, status, trigger, requested_by, enqueued_at, started_at, finished_at, reason, position}`, `QueueStatus` = queued / running / done / failed / refused / interrupted; `ui/run_queue.py` `RunQueue.submit(project, requested_by=...)`, `snapshot`, `get_queue()`. **Vocabulary mismatch to raise to the checker:** the branch's `trigger` is `Literal["button","schedule","api"]` and there is no `via`, `requested_at` or `team_button`, while this contract (TT3) and HO16 say `trigger=manual`, `via=team_button`, `requested_at`. Merge conflict with master in `docs/MAP.md` and `ui/routes_runs.py`; QUEUE `land-t203-hosting` is the row that re-lands it.
- **Identity (T-204): built, not merged.** `wave/t204-auth-fix1` head `886936ab`, cycle 1 ready-for-check after a cycle-0 FAIL; `wave/t204-auth` also holds a coordinator-B FAIL. No `auth/` on master. `unknown` which identity interface (stub or engine) exists when this unit builds. The contract names `authorize()`, keys `project.run` and `report.view` (no new key).
- **Schedule (G5): pure core only.** `wave/g5-schedule-core` head `29ce74e8`, 17 files (`schema/schedule.py`, `stages/scheduler.py`, ...), manifest `qa/manifests/g5-schedule-core.md` at `ready-for-check`, **no verdict file** on the branch; merge conflict in `docs/MAP.md` only. G7 imports nothing from it.
- **Delivery (G4): not built.** `schema/delivery.py`, `stages/report_delivery.py`, `delivery/` MISSING. The plan's G7 test column ("blocked run still delivers") needs G4's inbox.
- **AT-570:** `qa/issues.jsonl` last row for AT-570 is `status: verified` (fixed 2026-09-28, verified 2026-09-28), and the gate sits at `ui/routes_runs.py:75-95`. The goal.json T-201 note ("Prerequisite AT-570: ... checks no RunApproval today; close it first") is stale; `team-foundation.md` TF2 already orders the correction (G1: "closed in code, re-verified by G1"). `docs/plan.md` G1 row still lists "AT-570 test".
- **Goal task:** `.goal/goal.json` T-201 `deps: [T-200]`, `done_check = uv run python scripts/check_deliverable.py --exists qa/verdicts/t-201-team-loop.md`, status pending. **AT-744** (`qa/issues.jsonl`, last row, `fixed` 2026-10-07, `done-check-missing`) says every pending task now has a cmd `done_check` capable of failing and T-197..T-201 carry `--exists qa/verdicts/t-19N-team-loop.md`; it moves to `verified` only after a re-check on a committed tree. **Gap:** T-201 spans two units (G4 verdict `qa/verdicts/t201a-report-delivery.md`, G7 verdict `qa/verdicts/t201b-test-button.md`) and nothing produces `qa/verdicts/t-201-team-loop.md`; `--exists` passes on any file of that name whatever the verdict says. The builder does not touch `.goal/goal.json`; raise to the checker.
- Plan row: | G7 | `t201b-test-button` | T-201 | R56, R57, R60, R64 | E `ui/project_view.py` (button); N `ui/routes_team_run.py`; no queue code | unauthenticated POST makes no run dir; no `project.run` gives 403 naming it; identity from session; the second press returns the existing request; blocked run still delivers; the queue is a fake with T-203's interface | critical | required (dev) | G1, G4, G5's launcher use; T-204; T-203 queue |

## 5. Files the builder will touch

Line counts are as of master `4f8f5da100931ebda1b26836304bfbd38460764b`.

| Path | New / existing | Lines now | What |
|---|---|---|---|
| `src/autotester/ui/routes_team_run.py` | new (G1 may register an empty stub router of this name; read what landed) | - | `POST /projects/{slug}/test` (name is the maker's; behaviour is the contract), status page, module-level `ROUTE_POLICY` dict (`project.run`, project resource). Calls the launcher/queue seam only. <= 300 lines. |
| `src/autotester/ui/project_view.py` | existing | 105 | `_actions_card` (`:67`): show the Test button only to a viewer who may use it. The route enforces the permission regardless. |
| `src/autotester/ui/app.py` | existing | 300 | **Avoid.** `app.py:284-291` builds the run button and calls `_actions_card`; if the button needs a new argument there, that edit belongs to G1's router move (`t205`), which must free lines first. If `_actions_card` can obtain what it needs without an `app.py` edit, do that. |
| `src/autotester/ui/routers.py` | existing after G1 | MISSING on master | Fill the `team_run` stub only. |
| `tests/team_run_fakes.py` | new (proposed) | - | Fake queue implementing HO16's interface (enqueue, get by id, list by project, status values), blocking fake runner, recording browser factory and recording provider. |
| `tests/test_team_run_gate.py` | new | - | TT1 |
| `tests/test_team_run_status.py` | new | - | TT2 |
| `tests/test_team_run_attribution.py` | new | - | TT3 |
| `tests/test_team_run_launcher.py` | new | - | TT4 (incl. the AST import test over `ui/routes_team_run.py`) |
| `tests/test_team_run_queue_seam.py` | new | - | TT5 |
| `tests/test_team_run_approval.py` | new | - | TT6 |
| `qa/manifests/t201b-test-button.md` | new | - | Evidence manifest, `Status: ready-for-check`. |
| `docs/MAP.md` | existing, generated | 349 | `uv run autotester map`, last step. |

Not touched: `stages/run_launcher.py` (G1), `schema/run.py` (G1 adds the optional fields), `ui/routes_runs.py` (t203/G1), `ui/run_queue.py`, `schema/run_queue.py` (T-203), `delivery/*`, `schema/delivery.py`, `stages/report_delivery.py`, `ui/routes_inbox.py` (G4), `auth/*` (T-204), `stages/scheduler.py` (G5), `.goal/goal.json`, any `qa/contracts/` or `qa/gates/` file. The existing RU tests must pass with assertions unedited: `tests/test_ui_runs.py` (250), `tests/test_ui_runs_live_case_approval.py` (268), `tests/test_credential_run_approval.py` (287).

## 6. Test scope

Exact files (plus lint and doctor); the contract names the first six:

```
uv run pytest tests/test_team_run_gate.py tests/test_team_run_status.py tests/test_team_run_attribution.py tests/test_team_run_launcher.py tests/test_team_run_queue_seam.py tests/test_team_run_approval.py
uv run pytest tests/test_ui_runs.py tests/test_ui_runs_live_case_approval.py tests/test_credential_run_approval.py      # TT4: unedited, must stay green
uv run ruff check src/autotester/ui/routes_team_run.py src/autotester/ui/project_view.py tests/team_run_fakes.py tests/test_team_run_gate.py tests/test_team_run_status.py tests/test_team_run_attribution.py tests/test_team_run_launcher.py tests/test_team_run_queue_seam.py tests/test_team_run_approval.py
uv run autotester doctor
```

If G1's `tests/test_run_launcher*.py` exist after landing, they are G1's and are not re-run here.

## 7. Reachable test cases

All local. A recording transport and a recording browser factory prove "no trace"; the queue is the fake from `tests/team_run_fakes.py`; no real SMTP, no real browser run, no live model call.

1. Happy (TT1/TT2): a signed-in Developer with `project.run` on their own project presses Test; response is 303 to the run status page in under 2 s with the browser factory untouched; the page shows `queued` with its position, then `running`, then `done`; it renders again after the app object is re-created (persisted entry, not a worker handle).
2. Happy (TT3): two sessions press; the queue entry, the `Run` and the report header carry two different `requested_by` values taken from the session; a body or query carrying `requested_by`, `user`, `email` or `owner` is ignored; a pre-change golden `run.json` still loads.
3. Happy (TT4): patch the launcher; press once; it is called once with `trigger=manual` and the user; the AST import test over `ui/routes_team_run.py` finds no `Run(`, `BrowserSession`, `_execute_with_trace`, `run_case_pipeline`; the existing RU tests pass unedited.
4. Refusals with no trace (TT1): anonymous (302 to `/auth/login`), signed-in without `project.run` (403 naming `project.run`), project not visible to the user (the same 404 as a missing project), cross-origin POST with a valid cookie (403 from the D-066 guard, before authentication), unknown slug (404); each leaves the data-root file listing byte-identical, the queue empty, and the browser factory and provider uncalled. A GET changes nothing. Four default groups x own / assigned / other projects table.
5. Second press (TT5): two presses on one project give one entry and the same id; three projects against a fake cap of 2 give observed concurrency <= 2; grep finds no `max_concurrent_runs` in this unit's files; nothing is started except through the queue.
6. Approval refusal (TT6): three fixtures (no `SecretRef`; `SecretRef` with no value; provisioned) pressed by a Developer and by an Admin; the first two end `refused`, the message names the state ("`PATHLYNKS_USER_EMAIL` has no value; enter it on the Credentials page"), zero requests at the transport, `runs/` listing unchanged, no browser factory call; the text carries no credential value and passes `Redactor.scrub`; an Admin is refused the same way; the approval's own bounds cap a provisioned run.
7. Blocked run still reaches the presser's report/inbox entry: depends on G4 and is judged there; here assert only that the `refused` request is shown to the presser on the status page.
8. Mutations the checker will try in a throwaway copy (per contract): check permission after enqueue; drop the Origin guard; run the case inline; read `requested_by` from the form; add a second `Run(` construction site; create a second entry on the second press; skip the approval check on the admin path.
9. Persona walk, dev (section 9).

## 8. Gate answers

- `qa/gates/plan-approved-g10.md` (verbatim): "Approved -- Umesh, 2026-10-07 (chat), recorded as D-074." and "No per-user cooldown on Test" (Assumptions); "Project -> Test -> report (3)" steps for dev.
- `qa/gates/d063-cn5-vs-cn11.md` (verbatim): "Answered: 2026-10-07T03:17:22Z — B, widened — chat (Umesh): "agar credentials hai tho run krroo, approved maano … baar baar approval nhi chahiye. credentials de denaa sabse bada approval hai". Provisioned credentials for a project are the standing run approval; no per-run human approval. Recorded as D-068." (This is why the Test button adds no second prompt.)
- `qa/gates/write-policy-tier.md` (verbatim header lines): "**Answered by:** Umesh, 2026-09-27. Asked once; this file is the record so it is never asked again." and "**`ALLOW_WRITES`, on every target, production included.**" It is a gate file with no `Answered:` token, only these lines.
- `qa/gates/email-sender-credentials.md` (verbatim): "Answered: 2026-10-10 - A (credentials from d:/erp, AutoTester-prefixed keys) - D-081". It gates only `delivery/email.py` (G4), not this unit.
- `qa/gates/t203-host-and-dns.md` (verbatim): "Answered (local-machine part only): 2026-10-10 - host locally for now - D-081", and "STILL OPEN: the real server host and the DNS name. No Answered line for this part." Gates only T-206's hosted check; this unit's tests run locally.
- D-081 item 4 (verbatim): "**T-203 host and DNS: later; host on this machine for now.** Umesh: "krr denge but tu phle sabb run tho krr and for that time iss system mai host krkee use krr". T-203 proceeds as a local deployment on the dev machine. The server host and DNS remain an open human input and gate only the hosted check of T-206."
- D-081 item 7 (Tracker sheet, no live write) does not apply to this unit.
- D-081 item 3 (run approvals) is for the T-145 / T-154 live runs, not the Test button.

## 9. UI surface and persona walk

UI surface: yes (a Test button on the project page, a run status page, `project_view.py`).
Persona walk: required (dev). User types from `docs/features/team-loop/intent.md`: admin, subadmin, dev, tester; the contract and plan name **dev** for G7. From the contract: from the project page press Test, watch the status page, open the report in at most 3 steps, then find it under My reports (G4); negative walks: no credentials (the message names the Credentials page), press while already queued (existing request and position shown), a `tester` sees only shared reports. Mode D, the checker's own live browser, local server per D-081 item 4.

## 10. Dependencies and conflicts

Must land first (from `qa/QUEUE.md` `t201b-test-button` `after:` plus the contract):
1. `land-t203-hosting` - the queue; also owns `ui/routes_runs.py`, `ui/app.py`, `core/env.py` first.
2. `t205-g10-headroom` (G1) - launcher, `Run` optional fields, `ui/routers.py`, route-policy merge, `schema/team_enums.py`.
3. `t204-team-login` - identity and `authorize()`; until it lands the plan allows only a loopback-only single-user stub, and `unknown` what it looks like.
4. `t201a-report-delivery` (G4) - inbox, `DeliveryRecord`, the shared report label.
5. `t200-schedule` (G5) - ordering only: `goal.json` T-201 `deps: [T-200]` and the QUEUE row list it; no G5 symbol is imported by this unit. G5's `tick` and the button share the launcher and the approval check (TS5/TS6 = TT6/TT4).

| Shared file | Used by | Owner for this unit |
|---|---|---|
| `src/autotester/ui/project_view.py` (105) | G7 only among Group 10 units (QUEUE: "owner: ui/project_view.py: this row") | **this unit** |
| `src/autotester/ui/app.py` (300) | t203, t205 router move, t204 | `land-t203-hosting` then `t205`; this unit does not edit it |
| `src/autotester/ui/routes_runs.py` (204) | t203 (queue), t205 (launcher extraction) | `land-t203-hosting` then `t205`; not edited here |
| `src/autotester/ui/routers.py` (new in G1) | every Group 10 UI unit | `t205`; this unit fills the `team_run` stub |
| `src/autotester/schema/run.py` (121) | G1 adds `requested_by` / `slot_key` / `via` | `t205` (TF2); not edited here |
| `src/autotester/ui/routes_team_run.py` | G7 only | **this unit** (G1 may pre-create an empty stub) |
| `src/autotester/stages/run_launcher.py` | G1 creates; G5, G7 call | `t205`; not edited here |
| `docs/MAP.md` | every unit | regenerated last at merge |

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
- Extra for this unit: no real SMTP host is contacted by any test or default path (TT8 is G4's, but a Test press in a test must use the outbox adapter); no real browser run is launched by a test; every refused press asserts zero requests at the transport.
