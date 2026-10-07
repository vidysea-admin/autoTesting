# Plan — AutoTester, remaining units

**Purpose:** the 26 remaining work units (refreshed 2026-10-07 from `.goal/goal.json`: 59 of 90 tasks done, 31 pending) in dependency order — files touched, how each is tested, criticality, persona walk — and the tasks held on a human gate.
**Open me when:** picking the next unit or wave, or asking what is deliberately not being built right now.

<!-- PLAN phase step 4, BACKFILL. Covers only what is NOT yet shipped; M0–M6 units are already
     checker-PASSed and live in docs/FEATURES.jsonl. Rows become qa/QUEUE.md TODO rows.
     2026-10-07 refresh (AT-744..756 drift): the 2026-09-27 list said "26 units"; nine of them have
     since closed (T-195, T-185, AT-335, T-186, T-189, T-191, T-192, T-150, T-171) and group 10 + the
     D-071 tasks were added. The count happens to be 26 again, but it is a different 26. -->

**Spec:** docs/spec.md (backfill, 2026-09-27; Group 10 R32-R65 added 2026-10-07) · **Status:** draft; Group 10 units G1-G10 await `qa/gates/plan-approved-g10.md`

**Scope decisions (Umesh, 2026-09-27):** build order = everything, max parallel, bounded only by
measured RAM. Track C is built through C3 only; T-154 (adversarial pass) and T-155 (its report)
are **held for a separate approval** — no probe traffic in this push.

**What D-070 (Umesh, 2026-10-07) changed in this plan:**
- **T-125 and T-165 are unblocked.** The native-egress sandbox precondition is dropped: AutoTester
  runs a local visible browser and the full suite directly on whatever machine it is installed on,
  against any product given by URL plus supplied credentials (not Pathlynks-specific). The gate files
  carry `Answered: 2026-10-07`. T-125 cycle 4 and AT-113 cycle 4 (T-165) are the next runs. T-165 is
  **not done**: AT-113 cycle 3 FAILed/STALLED and cycle 4 is pending.
- **The FlowSpec review gate no longer blocks.** Video flows are reconciled by the system (each video's
  own knowledge graph is re-mapped onto the crawl's product KG; every flow kept, differences
  highlighted for developers). The DRAFT status stays as a label only and never blocks case
  generation from reconciled flows. This lands inside T-166; contract text comes through the
  checker's inbox fold-in, not this file.
- **Group 10 "Team loop" (T-197..T-201) is the top priority**, ahead of groups 5-9. Its scope widens
  to an in-product developer portal (T-198, grill in progress).
- **The tracker loop (T-199) is a parked must-have:** an in-product tracker with auto-validation and a
  Test button anyone can press. It is parked, not dropped, and not allowed to fall off the plan.
- **Push on checker PASS** (D-007 restated): everything built and validated is committed and pushed.

**What D-072 (Umesh, 2026-10-07) changed in this plan:** every Group 10 answer is in. Login is email and
password with open sign-up and admin moderation (T-204); access is AWS-IAM-style groups with checkbox
permissions, defaults CEO/Admin, Sub-admin, Developer, Tester; reports go on the website plus email by a
per-user checkbox; a schedule starts on a button, a fixed time or a custom time; the upload limit is an admin
setting (default 2 GB) and a Google Drive link is accepted; concurrency is a server setting (default 2);
production is Ubuntu, development stays on Windows; replay is still graded; new modules for T-176, T-202,
T-203, T-204 and Group 10 are authorized. Rows 1-5 below are now summaries; the build units are G1-G10 in
"Group 10 build units".

## Units (in dependency order; independent rows run in the same wave)

Group 10 first (top priority). Every group-10 unit goes through the maker PLAN gate first
(`docs/intent.md` → `/grill` → spec → plan → `qa/gates/plan-approved.md`); slugs here are proposed.

| # | unit slug | task | requirements | files it touches | how it is tested | criticality | persona walk | depends on |
|---|---|---|---|---|---|---|---|---|
| 1 | `t197-video-ingest-pointers` | T-197 | R32-R38 | see unit G2 | oracle `.work/pathlynks-dev-videos-oracle-2026-10-07.md` over the three Navnit sources; flow summary + 4-5 point confirm-list | high | required (admin) | G1 |
| 2 | `t198-developer-video-intake` | T-198 | R39-R42, R61-R63 | units G3 (zip, Drive link) and G9 (portal: share, access requests, comments) | safe zip expansion, one source per video, Drive link fetched by the system, admin-set limit; portal route table | high | required (dev, tester) | G1; T-204 |
| 3 | `t200-scheduled-autotest` | T-200 | R51-R55 | unit G5 | manual / fixed / custom; must respect the credential-derived approval (D-068); enqueues on T-203's queue | critical | required (subadmin) | G1, G4 |
| 4 | `t199-bug-loop-tracker` | T-199 | R43-R50 | units G6 (in-product) and G8 (sheet sync) | stable bug key; re-test updates, pass closes; mapping proposed then user-confirmed; first live write shown and confirmed (HUMAN_GATE) | high | required (dev, subadmin) | 1 |
| 5 | `t201-team-test-button` | T-201 | R56-R60 | units G4 (report delivery) and G7 (Test button) | report on the website, plus email if the user ticked it; AT-570 re-verified in G1 | critical | required (dev) | 3; T-204; T-203 queue |
| 6 | `t125-catalog` | T-125 | R8 | catalog module + schema | cycle 4 under D-051; pytest; blocked entries name their one unblocking action; CT6 amended to tier ordering + reporting (D-071) | low | skip (backend) | — |
| 7 | `t165-crawl-completion-c4` | T-165 | R3, R6 | `stages/explore.py` + crawl schema (`at113-crawl-completion`) | cycle 4: frontier exhaustion proven on a live crawl; every bound names what it left unreached | critical | skip (crawl engine) | — |
| 8 | `t151-track-c1-discovery` | T-151 | R30 | Track C discovery module | one narrow extra cycle (D-071: one scan-path deadline test, repair checker B only); every Signal cites a real `file:line`; no model chooses which checks run | high | skip (read-only discovery) | — |
| 9 | `t196-l10-citation-subject` | T-196 | governance | doctor rule L10 | a citing line's subject must match the cited entry's `What:`; still BUILDING | critical | skip (governance) | — |
| 10 | `at518-grandchild-pid-flake` | AT-518 | infra | probe process teardown | probe kill proven, not argued | medium | skip (infra) | — |
| 11 | `t190-persona-ux-advisory` | T-190 | R28 | `schema/user_persona.py`, grade/report surfaces | pytest: a UX finding can never change a PASS/FAIL; severity scored | high | required (lead, tester) | mini-grill first |
| 12 | `t202-any-model-provider` | T-202 | D-071 | LiteLLM-backed `Provider` behind `providers.base.Provider` | Gemini / Claude / OpenAI / Ollama / OpenAI-compatible chosen by config; `litellm` authorized in this unit only | high | skip (provider) | — |
| 13 | `t204-team-login` | T-204 | D-072 | email+password sign-up, session, groups with checkbox permissions, `require_permission` with scopes (`all`, `assigned`, `own`, `shared`), `credentials.view` (admin only by default), admin screens for users, groups, assignment; Group 10 consumes it, builds none of it | unauthenticated request to any page or state-changing route refused; new account has no access until in a group; first account becomes admin only in local dev, while on the hosted server only the `AUTOTESTER_FIRST_ADMIN_EMAIL` account is promoted and an unset variable promotes nobody (CLI bootstrap) (amended D-074, 2026-10-07); admin can disable, delete and change any account; saved credential values visible only with `credentials.view`; sessions never in logs | high | required (dev, tester) | G1 (router list) |
| 14 | `t174-cli-mcp` | T-174 | R25 | CLI modules + new MCP entry point | documented exit codes asserted; `--dry-run` sends nothing; MCP tools answer; `mcp` SDK authorized (D-071) | high | skip (CLI/MCP) | 6 |
| 15 | `t178-failure-bundle` | T-178 | R24 | `schema/` bundle model, report surfaces | bundle is atomic and replayable; pruning happens before LLM spend | high | required (dev) | 6 |
| 16 | `t179-deep-agents-lead` | T-179 | R26 | new `agents/` package wrapping existing stages as tools | guards proven to live in the tools, not the model; skills loaded via `skills=` | high | skip (agent layer) | — |
| 17 | `t176-script-replay` | T-176 | R23 | `Script` / `case.script_ref`, locator layer | a replayed script reproduces the run; semantic locators preferred over CSS | high | skip (engine) | 7 |
| 18 | `t166-eval-compiler-kg` | T-166 | R7 | `stages/expand.py`, new KG artifact; video KG reconciled onto the product KG (D-070) | every generated eval traces to its source; component PASS cannot hide workflow failure; every flow kept, differences highlighted | high | skip (engine) | 6, 7 |
| 19 | `t180-subagents` | T-180 | R26 | `agents/` | the grader subagent holds no action tools (C7); judge vendor named, warned when it matches | high | skip (agent layer) | 16 |
| 20 | `t152-track-c2-registry` | T-152 | R30 | check registry reusing T-125's Catalog | kind→checks is a literal table a checker can re-derive | low | skip | 6, 8 |
| 21 | `t177-browser-use-fallback` | T-177 | R23 | actuator + revived `agent_loop.run_with_fallback` | an unknown screen is driven with typed outputs; AT-253 dead code is alive | high | skip (actuator) | 17 |
| 22 | `t167-langgraph-regression` | T-167 | R21 | `stages/orchestrate.py` → LangGraph 1.x | a release trigger runs the approved suite; consent via `interrupt()`; resumes after a crash | critical | required (release-manager) | 18 |
| 23 | `t181-agent-gain-measured` | T-181 | R26 | `agents/` + bench | measured gain vs the plain pipeline on a fixture; per-run token/cost budget enforced | high | skip (measurement) | 19 |
| 24 | `t153-track-c3-behavioural` | T-153 | R30 | behavioural checks over a captured run | the capturer never grades (C7); every capture scrubbed before a judge sees it | high | skip | 20 |
| 25 | `t168-damage-control-report` | T-168 | R22 | report layer | blocked/unvisited never renders as pass; one operator-readable report | high | required (lead) | 7, 22 |
| 26 | `t203-hosted-website` | T-203 | D-071, D-072 | Docker image and Ubuntu deploy guide (dev stays on Windows; code runs on both), HTTPS, persistent store, Host allow-list (AT-758) with `AUTOTESTER_ALLOWED_ORIGINS`/`_HOSTS`, **run queue** (one run per project, server-wide concurrency setting default 2), **server settings and admin Settings page** (upload limit default 2 GB, zip caps), tick timer unit; domain comes later | UI runs on Ubuntu for the Vidysea teams; Group 10 tests pass on Ubuntu; no secret baked into the image; queue obeys the setting; server host and DNS remain a HUMAN_GATE before first deploy | critical | required (dev) | 13, G1 |

Closed since the 2026-09-27 list (no longer in this plan): T-195, T-185, AT-335, T-186, T-189,
T-191, T-192, T-150, T-171 (all checker-PASS or fixed; see `docs/FEATURES.jsonl`).

## Held / blocked (not in this plan's waves)

| task | why |
|---|---|
| T-154, T-155 | Umesh 2026-09-27: build C1–C3, hold the adversarial pass for a separate approval; firing it needs a per-run approval naming target and consent scope |
| T-122, T-145 | needs TEST-account **ERP** credentials. Corrected 2026-09-27: a gitignored **repo-root** `.env` does exist and holds `PATHLYNKS_USER_*` / `PATHLYNKS_COUNSELLOR_*` key names, so Pathlynks-targeted live work is credential-capable — but `ERP_EMAIL`/`ERP_PASSWORD` are absent from every store and no `projects/*/.env` exists, which is what T-122's gate (D-048) names as its unblock condition. T-145 additionally needs a fresh D-018 RunApproval per run |
| T-136 | `ERP_Issues_Trainers.xlsx` truth sheet is not on disk (AT-752, 2026-10-07: restore it or amend the criterion) |
| T-169 | depends on all three above |

No longer held (D-070, 2026-10-07): T-125 and T-165 (runtime egress gate answered), and the FlowSpec
review gate (status label only). Answered by D-072: the T-204 login mechanism (email and password) and the Group 10 access model.
Still owed a human answer: the T-203 host and DNS, the email sender and credentials, the Google identity for
Drive links, and the first live write of T-199.

## Group 10 build units (G1-G10) — refreshed with Umesh's answers, 2026-10-07 (D-072)

This section replaces the single-row sketches in units 1-5 above. Spec: R32-R65. Intent: O8-O15
(`docs/features/team-loop/intent.md`). The draft contract proposals live in `.work/plan-g10/` (scratch)
and are handed to the checker through `qa/feedback-inbox.md` after approval.

**Findings that shape the units (measured on origin/master 642ab4bd, `wc -l`):**
1. **Files Group 10 would extend are at the 300-line cap:** `ui/app.py` 300, `schema/enums.py` 300,
   `store/project_store.py` 300, `ui/routes_report.py` 300, `stages/report_export.py` 299, `cli.py` 295,
   `cli_video.py` 286, `core/paths.py` 287, `stages/ingest.py` 277. Room exists in `schema/project.py` (167),
   `ui/routes_runs.py` (193), `sources/drive.py` (204), `ui/routes_sources.py` (261), `ui/helpers.py` (253).
   So the bulk of the work is new split modules. **D-072 item 2 already authorizes the Group 10 split
   modules** (each at most 300 lines with a one-job docstring, judged by the checker), so no bundled
   authorization gate is needed.
2. **`app.py` has no room for a router line.** T-203 and T-204 also add routes. G1 therefore lands first and
   moves router registration to a list in `ui/routers.py`; whoever of T-203, T-204 or G1 lands first creates it.
3. **`trigger_run` is synchronous** (`ui/routes_runs.py`, `ui-run.md` RU1: "no background job queue"). The
   async request, the queue and the concurrency cap are **T-203's**; the checker amends RU1 for that unit.
   G1 extracts the one `run_launcher.py` the queue worker, the scheduler and the button all call.
4. **AT-570 reads closed in code** (`routes_runs.py` `_require_live_case_approval`); G1 re-verifies it and the
   stale T-201 note is corrected. What still gates scheduled and button runs is the **D-068
   implementation** (credential-derived approval), owned by the `d063-grant-budget` branch.
5. **D-070 part 4 vs the T-199 goal row:** T-199 splits into an in-product tracker first (G6) and sheet
   sync second (G8). **D-070 part 3 vs D-071:** the role hierarchy question is closed by D-072: groups with
   checkbox permissions, owned by T-204.

**Contracts already written by the checker (6f351e11, per D-072):** `qa/contracts/auth.md` (T-204, permission catalogue and default groups, AU*), `qa/contracts/hosting.md` (T-203, HO1-HO21 and HO34-HO38; plus Group 10 rows HO22-HO24 schedule -> G5, HO25-HO29 report on the website and email checkbox -> G4, HO30-HO33 upload limit and Drive link -> G3). Those rows govern; the proposals in `.work/plan-g10/` keep only what they do not state (pointer review, bug loop, sheet sync, Test button, portal objects). The permission keys in the units below are `auth.md`'s.

**Ownership (spec.md "What T-204, T-203 and Group 10 each own"):** T-204 = sign-up, sessions, groups,
permissions, scope check, `credentials.view`, admin screens for users/groups/assignment. T-203 = Ubuntu
deploy and guide, run queue, concurrency setting (default 2), server settings and Settings page (upload
limit default 2 GB), Host allow-list, the tick timer unit. Group 10 builds neither; it registers
permission keys as data, calls `require_permission`, enqueues runs, and reads the limits.

| # | unit slug | task | reqs | files it touches (E = edit in place, N = new) | how it is tested | criticality | persona walk | depends on |
|---|---|---|---|---|---|---|---|---|
| G1 | `g10-0-headroom` | T-205 (new row) | R63, R65 | E `ui/app.py` (router list out), `core/paths.py` (+helpers), `schema/project.py` (`schedule`, `tracker` optional), `ui/routes_runs.py` (launcher out); N `ui/routers.py`, `stages/run_launcher.py`, `store/team_store.py`, `schema/team_enums.py` (or split `enums.py`; checker rules) | pytest + `autotester doctor`; routers register in the same order as before; manual run and `trigger_run` call the one launcher; AT-570 test; `project.json` round-trips with and without the new fields | medium | skip | - |
| G2 | `t197-pointers-review` | T-197 | R32-R38 | E `cli_video.py` (`--pointers`, delegate), `stages/ingest.py` (hook only); N `schema/video_pointer.py`, `schema/video_review.py`, `stages/video_pointers.py`, `stages/video_review.py`, `prompts/video_review_v1.md`, `cli_video_review.py`, `ui/routes_video_review.py` | table-driven grammar tests; fake Provider records requested frame times (coverage superset proof); hallucinated seconds and fake quotes (downgrade proof); redaction proof; live acceptance on the 3 redacted Navnit videos against the 13-row oracle (per-use Gemini approval recorded 2026-10-07) | high | required (admin) | G1 |
| G3 | `t198a-zip-drive-intake` | T-198 | R39-R42, R65 | E `sources/drive.py` (link parse + `fetch_to_stable_path`), `cli_video.py` (`fetch-drive`), `ui/routes_sources.py` (zip and Drive-link branches delegate), `schema/project.py` (`Source.uploaded_by/at/origin`); N `sources/zip_intake.py` | zip-slip, symlink, device, bomb, nested-zip, crash-mid-expansion, corrupt-member fixtures with a sentinel outside staging, on Windows and Linux path rules; fake `DriveClient` per failure class; `hosting.md` HO30-HO33; streaming limit read from the settings value (2 GB default) | high | required (dev) | G1; T-204 identity (until then loopback-only stub); T-203 settings (until then a typed default) |
| G4 | `t201a-report-delivery` | T-201 | R58, R59 | N `schema/delivery.py` (`DeliveryRecord`, `NotificationPref`), `stages/report_delivery.py`, `delivery/inbox.py` (website), `delivery/email.py` (behind the email gate), `ui/routes_inbox.py` | message and page share one computed label; forged recipient ignored; `hosting.md` HO25-HO29; per-user email checkbox (default off) decides email; delivery failure leaves the verdict unchanged; no secret or sign-in-free link in a message | high | required (dev) | G1; T-204 identity; email adapter waits on the sender/credentials gate |
| G5 | `t200-schedule` | T-200 | R51-R55 | N `schema/schedule.py`, `stages/scheduler.py`, `cli_schedule.py`, `ui/routes_schedule.py`; E `schema/project.py` | `hosting.md` HO22-HO24 plus pure `due()` over manual/fixed/custom with injected clock and timezone table; two concurrent ticks fire one run; kill-and-resume catch-up; no credential gives zero requests at the transport; the tick enqueues on T-203's queue and the one launcher is used; atomic marker on both OSes | critical | required (subadmin) | G1, G4; D-068 implementation; T-203 queue for integration (pure parts start earlier) |
| G6 | `t199a-bug-loop` | T-199 | R43-R46 | E `stages/issues.py` (adapter, at most 58 lines); N `schema/tracked_bug.py`, `stages/bug_loop.py`, `ui/routes_tracker.py` | exhaustive transition table; same run processed twice; case deleted gives `stale`; INCONCLUSIVE/BLOCKED never closes; replayed runs count (D-072); three-run fixture | high | required (dev) | G1; G2 for the video-issue adapter |
| G7 | `t201b-test-button` | T-201 | R56, R57, R60, R64 | E `ui/project_view.py` (button); N `ui/routes_team_run.py`; no queue code | unauthenticated POST makes no run dir; no `project.run` gives 403 naming it; identity from session; the second press returns the existing request; blocked run still delivers; the queue is a fake with T-203's interface | critical | required (dev) | G1, G4, G5's launcher use; T-204; T-203 queue |
| G8 | `t199b-sheet-sync` | T-199 | R47-R50 | N `schema/tracker_binding.py`, `stages/tracker_mapping.py`, `stages/tracker_sheet.py`, `prompts/tracker_mapping_v1.md`, `ui/routes_tracker_binding.py`, `cli_tracker.py` | fake `SheetClient` with two header layouts; zero writes before confirmation; plan-hash change forces re-confirm; human-edited cell survives; outage leaves the tracker correct; mapping payload is header cells only | critical | required (subadmin) | G6; the live first write to the real Pathlynks Tracker is a HUMAN_GATE |
| G9 | `t198b-dev-portal` | T-198 | R61-R63 | N `schema/video_share.py` (`Share`, `AccessRequest`, `VideoComment`), `stages/video_access.py`, `ui/routes_video_portal.py`, `ui/routes_access_requests.py`; E `ui/routes_video.py` | route-by-route permission table with the UI ignored; non-member gets request-access and never the bytes; `access.approve` scoped `own` for a developer, `assigned` for a sub-admin, `all` for admin; comment offsets validated; share link needs sign-in | high | required (dev, tester) | G3; T-204 |
| G10 | `g10-acceptance` | T-206 (new row) | O8-O15, O6 | none; evidence only | end to end on Pathlynks: redacted videos, reviews, bugs, a schedule tick, a Test press, reports on the website and by email for a user who ticked it; review recall against the oracle as numbers; persona walks in a live browser; Ubuntu run once T-203 deploys | critical | required (dev, admin) | G2-G9; T-203 for the hosted check |

**Waves:** after G1, run G2, G3 and G4 in parallel. Then G5, G6 and G7 (G5 and G7 integrate with T-203's queue,
so their pure parts start first). Then G8 and G9 in parallel, then G10. **Slices:** S5 = G1-G4, S6 = G5-G7,
S7 = G8-G10. Until T-204 lands, units that need identity run on a loopback-only single-user stub that
refuses to start on a non-loopback host.

**HUMAN_GATEs inside the group:** (1) email sender address and credentials (gates only `delivery/email.py`);
(2) the Google identity the server uses for Drive links (gates only the live Drive fetch); (3) the first live
write to the real Pathlynks Tracker (preview confirmed by a named user, mapping agreed by Umesh or Mamta;
G8's PASS is proven on a fake sheet); (4) T-203's server host and DNS (gates only G10's hosted check).

**Group 10 risks:** (1) review quality (O8) is measured against a human; a poor recall is reported as a
number, not patched into a pass. (2) Zip and upload handling on a hosted server is an attack surface;
senior-software-engineer review is mandatory on G3 and on G9's route table. (3) A schedule that fires against a
product nobody watches: mitigated by credential-derived approval, single-flight and the stale-scheduler marker.
(4) Sheet writes are outward-facing; confirmed mapping, plan-hash first write, append/update only. (5) Two
sessions building T-203/T-204 and Group 10 at once will collide on `ui/app.py`; G1 first, then everyone registers
through `ui/routers.py`.

## Persona walk rule

Required when a unit adds or changes a screen, a navigation path or a user-facing flow, or touches
onboarding/sign-in/payment. High criticality alone does not trigger one — the unit must also touch
a UI surface. Audience is `internal-tool`, so a required walk covers 1–2 user types, not all of them.

## Release slices

- **S0** — units 1–5 = Group 10 "Team loop", top priority, built as G1-G10 (slices S5 = G1-G4, S6 = G5-G7,
  S7 = G8-G10). It builds on T-204 (row 13) and T-203 (row 26) and does not duplicate them.
- **S1** — units 6–10: the unblocked spine (T-125 cycle 4, AT-113 cycle 4 for T-165), T-151's narrow
  extra cycle, T-196, AT-518. These run beside S0, not after it.
- **S2** — units 11–16: UX advisory, any-model provider, team login, the CLI/MCP surface, the failure
  bundle, the agent-layer skeleton.
- **S3** — units 17–21: script replay, the eval compiler + KG (with video-KG reconciliation),
  subagents, Track C2, the browser-use fallback.
- **S4** — units 22–26: LangGraph regression, the measured agent gain, Track C3, the unified
  damage-control report, and the hosted website go-live.

## Risks

1. **RAM is the binding parallelism ceiling** (3.9 GB free of 23.7 measured 2026-09-27) — waves get
   trimmed to what fits, so "max parallel" is bounded by the machine, not by the plan. Noticed in
   each tick's `concurrent peak=` line.
2. **T-165 is still the spine, and it is not done** — units 17, 18 and (through them) 22 and 25 sit
   behind it, and AT-113 has already FAILed three cycles. A stall there stalls S3 and S4. Noticed as a
   STALLED stamp with a `qa/debug/` report; AT-745 records that cycle 3 has no diagnosis file.
3. **The buildable queue can spin without closing a unit** (AT-755: three sweeps ended EXHAUSTED with
   the same top three). Group 10 as top priority is the answer; if no S0 unit closes in two sweeps,
   that is a HUMAN_GATE, not another tick.
4. **The agent layer may not earn its place** — T-181 measures it against the plain pipeline, and a
   negative result means it is removed, not patched. Noticed in T-181's own bench numbers.
5. **The tracker loop (T-199) writes to a team sheet** — outward-facing; first live write is confirmed
   by a human. Parked must-have means it is not dropped, not that it ships unreviewed.

## T-190 concrete PLAN proposal — 2026-10-06

Status: proposed, not implementation-approved or shipped. This supplements unit10/R28;
it does not replace the canonical goal dependencies or turn an advisory finding into a
functional verdict. Product direction is already answered A in
`qa/gates/meeting-user-persona-ux-judging.md`; do not ask that question again.
The implementation/count preview and review receipts live in the existing
`qa/manifests/t190-plan-preparation.md`.

The contract's five required plan choices are:

1. Use the project's configured functional judge through the existing Provider registry,
   with a separate UX prompt/output schema. Preserve vendor/model/fallback order; the UI's
   currently hardcoded provider is not evidence of correct configuration resolution.
2. Proposed opt-in default:20 physical call attempts per run, serial across eligible cases,
   failed attempts and retries spent. This is not a money/token ceiling. Enforce the shared
   budget below retry/redirect/fallback dispatch; unsupported transport/output-limit
   capabilities refuse before a call with a typed reason. Record exhausted remaining cases
   as advisory skipped_budget; functional results remain unchanged. The numeric limit,
   payload/output limits and complete installed-adapter wiring still need plan approval.
3. Persist one typed `projects/<slug>/runs/<run_id>/ux_report.json`, separately from result
   and verdict files. Include per-case findings, exact evidence path/step, severity, effective
   conditions and safe error/skip status. Absent, malformed and incomplete are distinct;
   exports must never turn a failed UX load into a completed empty report.
4. Store typed personas in `projects/<slug>/user_personas.jsonl`; attach optional refs on
   both Project and Case, case override first. Validate project-local ids, guard complete
   snapshot values before persistence, and preserve refs during fixed-step construction.
5. `ux_enabled=False` by default. Explicit opt-in snapshots run inputs, then performs one
   read-only UX pass after functional results/verdicts persist, in stable case order. No
   rerun of product actions; advisory failure must not abort functional reporting.

Condition claims are evidence-local:measure each successful screenshot's capture interval,
not merely equal start/end samples for the case. Unknown/unsupported locale or device
conditions cannot support persona findings. Keep Verdict/Judgment and functional rubric
construction untouched; require byte-identical functional verdicts with and without UX.

Exact creation approval was requested once for the six proposed schema/stage/store/prompt/test
paths listed in the manifest. It remains pending; no file is created by this proposal.
The remaining implementation gate is a complete independently approved candidate patch/count
proof plus installed-provider budget fidelity. These engineering obligations, full-suite,
falsification, export/browser checks and final independent acceptance remain mandatory.
No paid run, live write, contract change, architecture change or product PASS is authorized here.
