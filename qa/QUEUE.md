# qa/QUEUE.md — checker sweep queue (top-3 recommended next units)

- GRILL: real two-mode acceptance thresholds for D-023/T-169 (AT-281) -- unanswered; the contract covers it by a pointer only. (2026-10-11 sweep: the AT-218 GRILL line and the intent Q1 GRILL line were removed, both answered: `qa/gates/at218-vacuous-guard-class.md` 2026-09-26, `docs/intent.md` Q1 2026-10-07.)

## Approved 2026-10-10 (D-081): buildable rows, dependency order (added by d081-plan-refresh)

Owner's instruction (D-081, 2026-10-10): run all remaining work. Each row below is `approved: 2026-10-10`. Rows are in dependency order; rows on separate lanes may run in parallel. Worktrees and branches named in a row are INPUTS to re-land unit by unit, never state to merge wholesale (D-080 item 1). Lanes follow `qa/adapter.json` `parallel.lanes` (code max 4, browser max 1). `unknown` marks a fact the repo does not state; the maker resolves it at plan time. Group 10 follows the wave order of `docs/plan.md` (G1; G2, G3, G4; G5, G6, G7; G8, G9; G10), with the T-203 re-land first because it and G1 both edit `ui/routes_runs.py` and `ui/app.py`.

- [ ] t145-pathlynks-live-report - live bounded crawl of pathlynks.vidysea.com with the PATHLYNKS_USER_* test account, then cases, execution, grading and the exported report delivered to Umesh (FIRST ROW)
  approved: 2026-10-10 (D-081; the owner asked for all remaining work to run)
  class: live-run; criticality: critical (dual check)
  files: projects/pathlynks/project.json (write_policy -> allow_writes, authorized by D-081 and qa/gates/write-policy-tier.md), projects/pathlynks/** (crawl, flowspec.json, cases, runs, signed RunApproval rows), qa/evidence/t145-*; no src/ change expected
  schema: no
  surface: production pathlynks.vidysea.com in a visible browser; CLI crawl, approve, run and report export; one report delivered to Umesh
  consumes: repo-root .env keys PATHLYNKS_USER_LOGIN_URL/_EMAIL/_PASSWORD and AUTOTESTER_APPROVAL_KEY; qa/gates/d081-run-approvals.md; qa/gates/d081-pathlynks-report-first.md; qa/gates/write-policy-tier.md; D-018 per-run RunApproval; untracked projects/pathlynks/crawl/ and flowspec.json already on disk (decide reuse vs fresh crawl at plan time)
  lanes: browser
  after: none (T-122 and T-144 done)
  owner: this row alone owns projects/pathlynks/**; no other row writes there until it closes
  note: each run writes its own signed row naming target and scope (the approval is the authority for the row, not a replacement); the report goes to Umesh BEFORE any human bug list exists, so T-136 recall stays unavailable until an independent list exists

- [x] land-integrate-combined - re-land integrate/combined (at780-pii, at780-harden); on current master it fails doctor because stages/reconcile.py reaches 302 lines (limit 300)
  closed: 2026-10-11, merged fc0e95b0 (on master); dual check PASS cycle 0, qa/verdicts/land-integrate-combined.md and land-integrate-combined.b.md (checked 23e694a9). The '302 lines' remark in the title is stale: doctor reports no line-limit violation.
  approved: 2026-10-10 (D-081; the owner asked for all remaining work to run)
  class: re-land; criticality: high
  files: src/autotester/stages/reconcile.py (298 on master; split or trim to 300 or fewer), src/autotester/core/redact.py, tests/test_reconcile_pii.py, tests/test_redact_pii.py, docs/MAP.md (regenerate with `autotester map`)
  schema: no
  surface: internal pipeline (PII redaction in reconcile); no UI
  consumes: branch integrate/combined (8 commits ahead of master) as INPUT only; qa/verdicts for at780-pii and at780-harden (dual PASS cycle 0; a matching cycle is needed on the new commit); D-080 item 1 (merge only the exact commit a checker PASS reviewed)
  lanes: code
  after: none
  owner: stages/reconcile.py: this row; any other row touching reconcile.py waits
  note: a fresh checker cycle on the re-landed commit; doctor, ruff and the affected tests must be clean

- [x] land-t203-hosting - re-land wave/t203-hosting as a LOCAL deployment (D-081 item 4); it conflicts with master in ui/routes_runs.py and reuses issue ids AT-782..AT-793, which must be renumbered
  closed: 2026-10-11, merged 82bc4954 (on master); PASS cycle 0, qa/verdicts/land-t203-hosting.md (checked fddbf469). The issue-id renumber is done: rows are AT-862..AT-873 (manifest line 21). Rows that say 'after: land-t203-hosting' are unblocked.
  approved: 2026-10-10 (D-081; the owner asked for all remaining work to run)
  class: re-land; criticality: critical
  files: Dockerfile, docker/Caddyfile, docker/DEPLOY.md, docker/compose.prod.yml, docker/entrypoint.sh, .env.example, .gitattributes, src/autotester/core/env.py, schema/run_queue.py, schema/server_settings.py, store/server_settings.py, ui/app.py, ui/routes_live.py, ui/routes_report.py, ui/routes_runs.py, ui/routes_sources.py, ui/run_queue.py, ui/run_queue_view.py, tests/conftest.py (protected file), tests/test_env_loading.py, test_hosting_config.py, test_hosting_deploy.py, test_run_queue.py, test_run_queue_resilience.py, test_server_settings.py, test_ui_runs_queue.py, docs/MAP.md, qa/issues.jsonl rows AT-782..AT-793 (renumber; the checker owns issue status)
  schema: yes
  surface: local run queue and server settings on the dev machine; Docker image and compose are deliverables, not deployed
  consumes: branch wave/t203-hosting (6 commits ahead, slice PASS) as INPUT only; qa/contracts/hosting.md; D-081 item 4 (no server host or DNS needed); D-080 item 1
  lanes: code
  after: none (land BEFORE t205 so ui/routes_runs.py and ui/app.py are resolved once)
  owner: ui/routes_runs.py, ui/app.py, core/env.py: this row first, then t205, then t204
  note: ui/app.py is at the 300-line cap; keep the router-list move for t205 and resolve the conflict by taking master's app.py plus the minimum line the queue needs; the maker records the choice

- [ ] t205-g10-headroom - G1 / T-205: one run launcher, router list out of ui/app.py, optional schedule and tracker fields; re-verify AT-570
  approved: 2026-10-10 (D-081; the owner asked for all remaining work to run)
  class: refactor; criticality: medium
  files: E src/autotester/ui/app.py, core/paths.py, schema/project.py, ui/routes_runs.py; N ui/routers.py, stages/run_launcher.py, store/team_store.py, schema/team_enums.py (or a split of schema/enums.py, checker rules)
  schema: yes
  surface: no user-facing change; routers register in the same order as before
  consumes: docs/plan.md G1; qa/contracts/team-foundation.md; D-072 split-module authorization (each file 300 lines or fewer)
  lanes: code
  after: land-t203-hosting
  owner: ui/app.py, ui/routes_runs.py, schema/project.py, core/paths.py: this row owns them until PASS; every Group 10 row after it edits them only after it lands

- [ ] t197-pointers-review - G2 / T-197: video ingest with human timestamp pointers -> flow summary and a 4-5 point confirm-list
  approved: 2026-10-10 (D-081; the owner asked for all remaining work to run)
  class: feature; criticality: high
  files: E src/autotester/cli_video.py, stages/ingest.py (hook only); N schema/video_pointer.py, schema/video_review.py, stages/video_pointers.py, stages/video_review.py, prompts/video_review_v1.md, cli_video_review.py, ui/routes_video_review.py, tests/test_video_pointers*.py (names unknown)
  schema: yes
  surface: CLI `ingest video --pointers`; admin review page (persona walk: admin)
  consumes: qa/contracts/team-video-review.md; oracle .work/pathlynks-dev-videos-oracle-2026-10-07.md (13 rows); three redacted Navnit videos; per-use Gemini approval recorded 2026-10-07; D-072
  lanes: code, browser
  after: t205-g10-headroom
  owner: cli_video.py: this row before t198a-zip-drive-intake

- [ ] t198a-zip-drive-intake - G3 / T-198: safe zip expansion to one source per video; `ingest fetch-drive <fileId>` over sources/drive.py
  approved: 2026-10-10 (D-081; the owner asked for all remaining work to run)
  class: feature; criticality: high
  files: E src/autotester/sources/drive.py, cli_video.py, ui/routes_sources.py, schema/project.py (Source.uploaded_by/at/origin); N sources/zip_intake.py, tests for zip-slip, symlink, device, bomb, nested-zip and corrupt-member fixtures (names unknown)
  schema: yes
  surface: zip and Drive-link upload on the sources page (persona walk: dev); CLI fetch-drive
  consumes: qa/contracts/team-intake.md, hosting.md HO30-HO33; gws CLI login (qa/gates/drive-identity.md, answered); admin upload limit typed default 2 GB until the T-203 settings land; identity from a loopback-only stub until t204
  lanes: code, browser
  after: t205-g10-headroom; t197-pointers-review (cli_video.py)
  owner: cli_video.py after t197; schema/project.py after t205; ui/routes_sources.py shared with land-t203-hosting (which lands first)
  note: senior-software-engineer review is mandatory (zip handling is an attack surface); the live Drive fetch uses gws and no token is copied into the repo

- [ ] t202-any-model-provider - T-202: LiteLLM-backed Provider behind providers.base.Provider (Gemini, Claude, OpenAI, Ollama, OpenAI-compatible chosen by config)
  status: PASS, unmerged, waiting on gate qa/gates/t168-new-modules.md (dual check PASS cycle 0 at 94c569c0, qa/verdicts/t202-any-model-provider.a.md and .b.md, wave/t202-any-model-provider; new modules and the litellm dependency). Row stays open.
  approved: 2026-10-10 (D-081; the owner asked for all remaining work to run)
  class: feature; criticality: high
  files: N src/autotester/providers/ litellm module (file name unknown), providers/__init__.py (registry), pyproject.toml and uv.lock (litellm authorized in this unit only, D-071/D-072), tests/test_providers_litellm*.py (unknown)
  schema: no
  surface: provider config; `autotester providers` output
  consumes: qa/contracts/providers-litellm.md; D-071; D-072 (new module authorization); worktrees t202-litellm and codex-t202-completion as INPUT only
  lanes: code
  after: none
  owner: pyproject.toml and uv.lock: this row, t167 (langgraph), t174 (mcp), t179 (deepagents) each add a dependency; serialize them, one lock-file writer at a time

- [ ] t204-team-login - T-204: email+password sign-up, sessions, groups with checkbox permissions, require_permission with scopes, credentials.view, admin screens
  approved: 2026-10-10 (D-081; the owner asked for all remaining work to run)
  class: feature; criticality: high
  files: N auth, session, group and permission modules plus admin routes (names unknown; new modules authorized by D-072), E ui/routers.py (after t205), core/env.py (AUTOTESTER_FIRST_ADMIN_EMAIL), tests/test_auth*.py (unknown)
  schema: yes
  surface: sign-up, sign-in and admin screens for users, groups and assignment (persona walk: dev, tester); every page and state-changing route refuses unauthenticated requests
  consumes: qa/contracts/auth.md; D-072; D-074 (first-admin rule); worktrees t204-auth and t204-b* as INPUT only
  lanes: code, browser
  after: t205-g10-headroom; land-t203-hosting (core/env.py)
  owner: core/env.py after land-t203-hosting; ui/routers.py after t205
  note: the login mechanism is NOT a HUMAN_GATE (answered by D-072)

- [ ] t199a-bug-loop - G6 / T-199: in-product bug loop (stable bug key, transitions, stale, replayed runs count)
  approved: 2026-10-10 (D-081; the owner asked for all remaining work to run)
  class: feature; criticality: high
  files: E src/autotester/stages/issues.py (adapter, 58 lines at most); N schema/tracked_bug.py, stages/bug_loop.py, ui/routes_tracker.py, tests/test_bug_loop*.py (unknown)
  schema: yes
  surface: tracker page (persona walk: dev)
  consumes: qa/contracts/team-bug-loop.md; docs/plan.md G6; the video-issue adapter needs t197 output
  lanes: code, browser
  after: t205-g10-headroom; t197-pointers-review
  owner: stages/issues.py: this row

- [ ] t199b-sheet-sync-dryrun - G8 / T-199: tracker sheet mapping and sync, DRY RUN ONLY (D-081 item 7); the first live write stays a HUMAN_GATE
  approved: 2026-10-10 (D-081; the owner asked for all remaining work to run)
  class: feature; criticality: critical
  files: N schema/tracker_binding.py, stages/tracker_mapping.py, stages/tracker_sheet.py, prompts/tracker_mapping_v1.md, ui/routes_tracker_binding.py, cli_tracker.py, tests with a fake SheetClient (names unknown)
  schema: yes
  surface: mapping preview and confirm screen (persona walk: subadmin); zero live sheet writes
  consumes: qa/contracts/team-bug-loop.md; fake SheetClient with two header layouts; the real Pathlynks Tracker sheet is NOT touched (qa/gates/t199-first-live-write.md, OPEN)
  lanes: code, browser
  after: t199a-bug-loop
  owner: none beyond new files
  note: PASS is proven on a fake sheet; task T-199 is not closed by this row until the live-write gate is answered or the checker amends the done_check

- [ ] t201a-report-delivery - G4 / T-201: report delivery on the website inbox and by email behind a per-user checkbox
  approved: 2026-10-10 (D-081; the owner asked for all remaining work to run)
  class: feature; criticality: high
  files: N schema/delivery.py, stages/report_delivery.py, delivery/inbox.py, delivery/email.py, ui/routes_inbox.py, tests (names unknown)
  schema: yes
  surface: inbox page and a notification-preference checkbox (persona walk: dev); email only when the user ticked it
  consumes: qa/contracts/hosting.md HO25-HO29; AWS SES SMTP values copied from d:/erp into repo-root .env under AutoTester-prefixed keys (key names unknown until written; qa/gates/email-sender-credentials.md, answered); identity from the t204 stub until t204 lands
  lanes: code, browser
  after: t205-g10-headroom
  owner: none beyond new files
  note: email values are never printed or committed and are declared as SecretRef keys

- [ ] t200-schedule - G5 / T-200: scheduled auto-test (manual, fixed or custom time) with single-flight and credential-derived approval
  status: partial. t200a-schedule-core merged 7e0ef5b9 (PASS, qa/verdicts/t200a-schedule-core.md; does not close T-200). t200b FAIL at cycle 0 (qa/verdicts/t200b-scheduled-test.md, 0d9a3b56); fix cycle 1 built on wave/t200b-scheduled-test (6d6bc318), awaiting check. Row stays open.
  approved: 2026-10-10 (D-081; the owner asked for all remaining work to run)
  class: feature; criticality: critical
  files: N schema/schedule.py, stages/scheduler.py, cli_schedule.py, ui/routes_schedule.py, tests (names unknown); E schema/project.py
  schema: yes
  surface: schedule screen (persona walk: subadmin); enqueues on the run queue
  consumes: qa/contracts/team-schedule.md, hosting.md HO22-HO24; the D-068 credential-derived approval implementation lives on branch d063-grant-budget (landed status unknown); run queue from land-t203-hosting
  lanes: code, browser
  after: t205-g10-headroom; t201a-report-delivery; land-t203-hosting (queue)
  owner: schema/project.py after t205

- [ ] t201b-test-button - G7 / T-201: team on-demand Test button, report to whoever pressed it
  approved: 2026-10-10 (D-081; the owner asked for all remaining work to run)
  class: feature; criticality: critical
  files: E src/autotester/ui/project_view.py; N ui/routes_team_run.py, tests (names unknown); no queue code
  schema: no
  surface: Test button on the project page (persona walk: dev); an unauthenticated POST makes no run directory
  consumes: qa/contracts/team-test-button.md; run queue (land-t203-hosting); identity (t204); delivery (t201a); launcher (t205)
  lanes: code, browser
  after: t201a-report-delivery; t200-schedule; t204-team-login; land-t203-hosting
  owner: ui/project_view.py: this row

- [ ] t198b-dev-portal - G9 / T-198: developer video portal (share, access requests, timestamped comments)
  approved: 2026-10-10 (D-081; the owner asked for all remaining work to run)
  class: feature; criticality: high
  files: N schema/video_share.py, stages/video_access.py, ui/routes_video_portal.py, ui/routes_access_requests.py, tests (names unknown); E ui/routes_video.py
  schema: yes
  surface: share link, request-access and comments (persona walk: dev, tester)
  consumes: qa/contracts/team-intake.md; route-by-route permission table with the UI ignored; access.approve scopes own, assigned, all
  lanes: code, browser
  after: t198a-zip-drive-intake; t204-team-login
  owner: ui/routes_video.py: this row
  note: senior-software-engineer review is mandatory on the route table; ui/routes_video.py has no feature trio yet (AT-748)

- [ ] t203-local-deploy - T-203 remainder after the slice lands: local deployment complete (queue, settings page, upload limit, tick timer, deploy guide); the hosted check waits on the real host
  approved: 2026-10-10 (D-081; the owner asked for all remaining work to run)
  class: feature; criticality: critical
  files: unknown (depends on what the landed slice covers; the branch diff shows no tick-timer unit and no Settings route, so likely a new docker/ tick unit and E ui/routes_settings.py); docker/DEPLOY.md
  schema: unknown
  surface: runs on this machine for now (D-081 item 4); the Ubuntu server check is gated
  consumes: qa/contracts/hosting.md HO1-HO38; qa/gates/t203-host-and-dns.md (OPEN for the real host and DNS)
  lanes: code, browser
  after: land-t203-hosting; t204-team-login
  owner: ui/routes_settings.py: this row
  note: the open host and DNS gate blocks only the hosted check of T-206, not this build

- [ ] t206-g10-acceptance - G10 / T-206: Group 10 acceptance end to end on Pathlynks (evidence only)
  approved: 2026-10-10 (D-081; the owner asked for all remaining work to run)
  class: acceptance; criticality: critical
  files: none (evidence only: qa/evidence/t206-*)
  schema: no
  surface: live browser persona walks on Pathlynks: redacted videos, reviews, bugs, a schedule tick, a Test press, reports on the website and by email
  consumes: all Group 10 rows; qa/gates/t203-host-and-dns.md (the hosted and Ubuntu part stays gated); the live Tracker write is NOT part of it (gate open)
  lanes: browser
  after: t197-pointers-review; t198a-zip-drive-intake; t198b-dev-portal; t199a-bug-loop; t199b-sheet-sync-dryrun; t200-schedule; t201a-report-delivery; t201b-test-button; t203-local-deploy
  owner: none

- [x] t153-track-c3-behavioural - T-153: Track C3 behavioural checks against a captured run, graded by the existing independent judge
  closed: 2026-10-11, merged 349f3e97 (on master); dual check PASS cycle 0, qa/verdicts/t153-behavioural-checks.a.md and .b.md.
  approved: 2026-10-10 (D-081; the owner asked for all remaining work to run)
  class: feature; criticality: high
  files: unknown (candidates: src/autotester/schema/ai_check.py, stages/ai_catalog.py; the new capture module name is unknown); branch codex/t153-completion and worktrees t152-153, t153-checkB are INPUT only
  schema: unknown
  surface: AI-target checks; no UI
  consumes: qa/contracts/ai-target.md; C7 (the capturer never grades); Redactor.scrub and assert_no_raw_secrets before any judge
  lanes: code
  after: none (T-152 done)
  owner: unknown

- [x] t154-track-c4-adversarial - T-154: Track C4 bounded adversarial pass behind consent gate 2, against Pathlynks under the D-081 full approval
  closed: 2026-10-11, build merged bfec5567 (on master); dual check PASS cycle 0, qa/verdicts/t154-adversarial-pass.a.md and .b.md. T-154 itself stays pending on AT-917 (adapter allowlist); see the Candidates section 'T-154 close-out'.
  approved: 2026-10-10 (D-081; the owner asked for all remaining work to run)
  class: feature; criticality: critical (dual check)
  files: unknown (new probe-set files and stage; scripts/adversarial_proof.py is the done_check target and may not exist yet)
  schema: unknown
  surface: bounded adversarial probes at pathlynks.vidysea.com with the PATHLYNKS_USER_* account; probe cap, allowed_domains only, production named explicitly
  consumes: qa/contracts/adversarial.md; qa/gates/d081-run-approvals.md (answered); D-017 (no Garak, PyRIT or DeepTeam); per-run signed RunApproval row; no approval means zero requests at the transport
  lanes: code, browser
  after: t153-track-c3-behavioural
  owner: unknown
  note: no longer held for a separate approval (D-081 item 3); each firing still needs its own signed row naming target and scope

- [ ] t155-track-c5-report - T-155: Track C5 unified AI test report grouped by tier with judge reason strings
  status: PASS, unmerged, waiting on gate qa/gates/t168-new-modules.md (qa/verdicts/t155-ai-report.md, PASS cycle 0 at a4308b35, wave/t155-ai-report; new module stages/ai_report.py). Row stays open.
  approved: 2026-10-10 (D-081; the owner asked for all remaining work to run)
  class: feature; criticality: low
  files: unknown (reuses core/excel.py autosize_columns; stages/report_export.py is 299 lines, so a new split module is likely)
  schema: unknown
  surface: report export
  consumes: qa/contracts/ai-target.md; blocked checks render as blocked with a reason, never as passes
  lanes: code
  after: t154-track-c4-adversarial
  owner: unknown

- [ ] t178-failure-bundle - T-178 (FB4, FB5): case priority p0-p3 and human pruning of proposals before provider spend
  status: PASS, unmerged, waiting on gate qa/gates/at792-round-cap.md (dual check PASS at 297207ff, qa/verdicts/t178-failure-bundle-fb4-fb5.r1.a.md and .r1.b.md, wave/t178-failure-bundle-fb4-fb5). Row stays open.
  approved: 2026-10-10 (D-081; the owner asked for all remaining work to run)
  class: feature; criticality: high
  files: E src/autotester/schema/case.py (priority), store/project_store.py (AT the 300-line cap: delete_case must still refuse pinned cases, so a split is needed), stages/failure_bundle.py (209 lines), stages/review.py or expand.py (proposal staging; exact file unknown), tests/test_failure_bundle*.py (unknown); worktrees t178 and codex-t178-completion are INPUT only
  schema: yes
  surface: case-list priority selector; proposal approve and prune step (persona walk: dev)
  consumes: qa/contracts/failure-bundle.md FB4, FB5 (FB1-FB3 already in); qa/contracts/review-gate.md
  lanes: code, browser
  after: none (T-125 done)
  owner: store/project_store.py: this row

- [ ] t174-cli-mcp - T-174: CLI contract (--output json, documented exit codes, --dry-run) plus the AutoTester MCP server
  approved: 2026-10-10 (D-081; the owner asked for all remaining work to run)
  class: feature; criticality: high
  files: E src/autotester/cli.py (295 lines, near cap); N CLI modules and MCP entry point (names unknown); pyproject.toml and uv.lock (mcp SDK authorized by D-071); worktrees t174 and codex-t174-* are INPUT only
  schema: unknown
  surface: CLI exit codes, JSON output, MCP tools
  consumes: qa/contracts/cli-mcp.md; D-071
  lanes: code
  after: none (T-125 done)
  owner: cli.py: this row; pyproject.toml and uv.lock: serialize with t202

- [ ] t177-browser-use-fallback - T-177: browser-use fallback actuator for unknown screens; revive agent_loop.run_with_fallback
  approved: 2026-10-10 (D-081; the owner asked for all remaining work to run)
  class: feature; criticality: high
  files: E src/autotester/stages/agent_loop.py; N actuator module (name unknown); possible pyproject.toml dependency (unknown); worktrees t177 and t177f are INPUT only
  schema: unknown
  surface: unknown screens driven with typed outputs
  consumes: qa/contracts/agent-fallback.md AF1-AF6; qa/gates/at253-agent-fallback-wiring.md; T-176 script replay (done)
  lanes: code, browser
  after: none (T-176 done)
  owner: stages/agent_loop.py: this row

- [x] t167-langgraph-regression - T-167: release-triggered visible-browser regression on LangGraph 1.x with consent via interrupt() and crash-resume
  closed: 2026-10-11, build merged 476666d6 (on master); dual check PASS cycle 2, qa/verdicts/t167-release-regression.r2.a.md and .r2.b.md (checked 1b6f07e7). T-167 stays open on AT-898 (no FlowPlan producer, RR6); see the Candidates section 'T-167 close-out'.
  approved: 2026-10-10 (D-081; the owner asked for all remaining work to run)
  class: feature; criticality: critical
  files: E src/autotester/stages/orchestrate.py and orchestrate_runners.py; a new graph module is possible (unknown); pyproject.toml and uv.lock (langgraph 1.x); worktree t167 is INPUT only
  schema: unknown
  surface: release trigger; consent interrupt (persona walk: release-manager)
  consumes: qa/contracts/release-regression.md, orchestrator.md; the agentic architecture standard (LangGraph 1.x)
  lanes: code, browser
  after: none (T-166 and T-110 done)
  owner: stages/orchestrate.py: this row; pyproject.toml and uv.lock: serialize with t202

- [ ] t168-damage-control-report - T-168: unified damage-control report (regression diff, API failures, workflows, screenshots)
  status: PASS, unmerged, waiting on gate qa/gates/t168-new-modules.md (dual check PASS cycle 2 at 4b93d952, qa/verdicts/t168-damage-control-report.r2.a.md and .r2.b.md, wave/t168-damage-control-report). Row stays open.
  approved: 2026-10-10 (D-081; the owner asked for all remaining work to run)
  class: feature; criticality: high
  files: unknown (report layer; stages/report_export.py is 299 lines, so a split module is likely)
  schema: unknown
  surface: operator-readable report; blocked or unvisited never renders as pass (persona walk: lead)
  consumes: qa/contracts/damage-control-report.md
  lanes: code, browser
  after: t167-langgraph-regression
  owner: unknown

- [ ] t179-deep-agents-lead - T-179: Deep Agents lead tester wrapping existing stages as tools
  approved: 2026-10-10 (D-081; the owner asked for all remaining work to run)
  class: feature; criticality: high
  files: N src/autotester/agents/ package (module names unknown); pyproject.toml and uv.lock (deepagents; gate d042 answered 2026-09-24)
  schema: unknown
  surface: agent layer; guards live in the tools, not the model
  consumes: qa/contracts/agent-layer.md; qa/gates/d042-deep-agents.md (answered)
  lanes: code
  after: none (T-170, T-172, T-175 done)
  owner: agents/: this row, then t180, then t181; pyproject.toml and uv.lock: serialize with t202

- [ ] t180-subagents - T-180: subagents (explorer, test-designer, runner, independent grader with no action tools)
  approved: 2026-10-10 (D-081; the owner asked for all remaining work to run)
  class: feature; criticality: high
  files: N and E under src/autotester/agents/ (names unknown)
  schema: unknown
  surface: agent layer
  consumes: qa/contracts/agent-layer.md; C7
  lanes: code
  after: t179-deep-agents-lead
  owner: agents/: after t179

- [ ] t181-agent-gain-measured - T-181: agent guardrails and measured gain vs the plain pipeline on a fixture
  approved: 2026-10-10 (D-081; the owner asked for all remaining work to run)
  class: measurement; criticality: high
  files: src/autotester/agents/ plus schema/bench.py and stages/bench.py (E, exact edits unknown)
  schema: unknown
  surface: bench numbers on a fixture; per-run token and cost budget enforced
  consumes: qa/contracts/agent-layer.md; qa/contracts/bench.md
  lanes: code
  after: t180-subagents
  owner: agents/ and bench: after t180
  note: a negative measured gain means the layer is removed, not patched (docs/plan.md risk 4)

- [ ] t196-l10-citation-subject - T-196: doctor rule L10, a citing line's claimed subject must match the cited entry's What:
  approved: 2026-10-10 (D-081; the owner asked for all remaining work to run)
  class: governance; criticality: critical
  files: unknown (doctor rule in src/autotester/doctor.py or a rule module, plus tests); worktrees t196-citation-subjects and codex-t196-completion and qa/gates/t196-l10-coverage.md are INPUT only
  schema: no
  surface: autotester doctor output
  consumes: qa/contracts/living-ledger.md; qa/gates/t196-l10-coverage.md; D-068 (decision citations)
  lanes: code
  after: none
  owner: src/autotester/doctor.py: this row

- [ ] at733-bounded - AT-733 re-planned as ONE bounded unit with a cycle cap (D-080 item 6): a silent profile-cleanup failure must not let a logged-out entry case run logged in
  status: PASS, unmerged, waiting on gate qa/gates/at792-round-cap.md (qa/verdicts/at733-bounded.md, PASS cycle 0, wave/at733-bounded). Row stays open.
  approved: 2026-10-10 (D-081; the owner asked for all remaining work to run)
  class: fix; criticality: high (dual check, false-PASS prevention)
  files: E src/autotester/ui/run_execution.py (_run_entry_case; the wipe error is suppressed with ignore_errors, then browser startup), tests/test_*run_execution* (unknown); candidate branch codex/at733-entry-cleanup (6e0134b7, NOT merged) is INPUT only
  schema: no
  surface: UI run of a logged-out entry case
  consumes: qa/contracts/ui-run.md RU1/RU3 (entry-profile amendment); core-invariants C7 and C12; AT-733 stays open in qa/issues.jsonl (the checker sets status)
  lanes: code
  after: none
  owner: ui/run_execution.py: this row
  note: cycle cap: 2 fix cycles at most (the normal cap), then STALLED to a human; the old open-ended unit at733-entry-cleanup is stopped and is not a precedent

Not buildable (open human gates; kept out of the buildable list):

- [!] t136-bench-scoring - NOT BUILDABLE: T-136 (recall, FP rate, time on Pathlynks) is held on the OPEN gate qa/gates/t136-independent-human-list.md. It needs a human bug list written by a tester who has not seen AutoTester's report, or by Umesh before he opens it (D-081 item 2; AT-653; bench.md K6-K9). A list written after the report yields FP rate but not recall.
- [!] t169-two-mode-acceptance - NOT BUILDABLE: T-169 depends on T-136 (same open gate), T-145 and T-168. Held on qa/gates/t136-independent-human-list.md.

---

## Human-asked, above the TODO rows (2026-10-07 sweep consolidation)

| Row | State |
|---|---|
| Group 10: T-197, T-198, T-199, T-200, T-201 | human-asked D-067 (Umesh, chat 2026-10-07, top priority); blocked on PLAN gate (intent -> grill -> spec -> plan) before any build. Not sweep findings. They have no contract, spec or intent coverage yet (expected: the PLAN gate authorizes it), and the pending tasks lack done_checks (AT-744, maker-owned, red suite test). Also absent from target.md and docs/plan.md (AT-729/AT-738 family). No code before `qa/gates/plan-approved.md` covers them. |

No `HOLD:` line this sweep: no failure is traced, with evidence, to a checked-PASS feature's changed files.

2026-10-01 bounded Mode B full-goal triage — EXHAUSTED (partial seven-check sweep, not CLEAN).
Report: `qa/verdicts/sweep-2026-10-01-bounded-goal-triage.md`. Preserve all older queue history below.

## Current independent next units (supersedes obsolete recommendations below)

| Priority | Unit | State and evidence |
|---|---|---|
| 1 | TODO: AT-733 logged-out entry-profile cleanup honesty | Existing `ui/run_execution.py:55::_run_entry_case`, suppressed wipe error at67 then browser startup at70; canonical open/high AT-733; C12/RU1/RU3. Existing-file red-first plan, no T-165/live-account dependency. |
| 2 | TODO: T-125 catalog scoped cycle4 resume | D-051 answered; CT9 written; CT6 order-only stands under D-058 point2. Recover/identify existing branch artifact before fresh plan/checker; no discard/recreate/merge authorization. |
| 3 | TODO: T-151 deterministic discovery/context | T-150 done; ai-target AI1/AI8 and D-017 named stages. Synthetic in-root fixtures first, ordinary independent plan/new-file scope validation; no real-target firing authorization. |

AT-113 cycle3 STALLED + FAIL remains held on `qa/gates/at113-cycle3-recovery.md` (Decision pending). No additional cycle, contract weakening or release. T-165 pending makes T-176/T-166/T-168 dependent, not free. T-171 is already done with checked-PASS cycle2; missing done_check/ledger metadata is separate debt, NOT a task-resume instruction. Other independent work continues; the whole reusable platform/two-target acceptance objective is unchanged. Uncovered sweep dimensions are listed in the report.

## Candidates (human picks) — 2026-10-11 at758-759-host-allowlist close-out (checker, from the dual-check PROPOSED-ISSUE lines)

Never built until a human moves one out of this section with `approved: <date>`. AT-758, AT-759, AT-760 and AT-761 are now `fixed` (merged 02c5f016). AT-920, AT-921 and AT-924 are test-environment rows, ledger-only and not candidates. All rows below are low as filed by both coordinators; none is browser-reachable today.

| Priority | Candidate | Ref |
|---|---|---|
| priority: security | Refuse a websocket scope with a disallowed Host in `_OriginGuard` (`ui/helpers.py:274`), so a future websocket route cannot reopen AT-758. No websocket route exists today. | AT-919 |
| priority: security | Match the raw Host against a strict pattern before `urlparse` and optionally refuse an absolute-form request target (`ui/helpers.py:233`); a tab or CR inside Host is currently stripped. Not browser-reachable. | AT-922 |
| priority: security | Refuse duplicate Referer and Sec-Fetch-Site headers in `origin_refusal` (still last-wins; Host and Origin are fixed by AT-761). | AT-923 |

## Candidates (human picks) — 2026-10-11 T-154 close-out (checker, from the dual-check PROPOSED-ISSUE lines)

Never built until a human moves one out of this section with `approved: <date>`. Rows AT-909, AT-911, AT-914, AT-915 and AT-918 are ledger-only and are not candidates. T-154 stays pending (adapter allowlist, AT-917; no live adversarial pass has been made).

| Priority | Candidate | Ref |
|---|---|---|
| priority: security | Validate `probe_sets` names as single safe path components and assert the resolved path stays under `prompts/probes`: `../outside` loaded and sent a .md from outside the probe directory on the only probe-sending path (operator-controlled, no CLI yet). Severity low as filed by coordinator B. | AT-912 |
| priority: security | Owner decision: is an adversarial `RunApproval` single-use? Today 3 passes on one `max_probes=4` row sent 12 probes (replayable until expiry). AD2 words the bound per run, so it is within the contract. | AT-913 |
| priority: security | Require a per-send timeout when the real sender is built: `wall_clock_s` is checked only between sends, so one hung send is unbounded. Do before the first live pass. | AT-911 |
| low (owner-confirm) | Confirm `PROBE_CEILING=50`, the five probe categories and the probe text, and the Pathlynks endpoint string and production status (CN7), before any live firing. | AT-916 |
| low (process) | Add `uv run python scripts/adversarial_proof.py` to `qa/adapter.json` `read_only_allowlist` (enforcement/config path, needs an authorizing D-entry) so T-154's done_check can run and close the task. | AT-917 |
| low | Make refusals uniform: one exception family, and a `refusals.jsonl` row (true requested count) for host, secret, probe-file and bad `wall_clock_s` refusals. | AT-910 |
| low (test-gap) | Pin the wall-clock refusal, the exact-ceiling case, and the refusal-log scrub of `target=` and `reason=`. | AT-914, AT-915 |

## Candidates (human picks) — 2026-10-11 T-167 close-out (checker, from the dual-check PROPOSED-ISSUE lines)

Never built until a human moves one out of this section with `approved: <date>`. Eight low rows (AT-901..AT-908) are ledger-only and are not candidates.

| Priority | Candidate | Ref |
|---|---|---|
| priority: security | Validate `--run-id` as a single safe path component before any write: `ProjectPaths.run_dir` joins it unchecked, so `../escaped` created a directory outside `runs/` and more `..` segments reach outside the project. Raised from low to medium by the checker. | AT-900 |
| priority: S1/S2 (medium, goal-coverage) | Add the FlowPlan producer: nothing in src/ writes a FlowPlan, so a real `autotester release` reports every flow `not run` (RR6; T-167 stays open until this lands). | AT-898 |
| medium | Make the release pause, approve and decline output usable: show what is approved, give a next step, no 'finished' after decline, no raw traceback. | AT-899 |

## Candidates (human picks) — 2026-10-11 T-153 close-out (checker, from the dual-check PROPOSED-ISSUE lines)

Never built until a human moves one out of this section with `approved: <date>`. Five low rows (AT-893..AT-897) are ledger-only and are not candidates.

| Priority | Candidate | Ref |
|---|---|---|
| priority: security | Escape or fence the target's response text in `stages/ai_judge.py::_evidence` so it cannot forge evidence rows in the judge prompt (reproduced: a response carrying `- [network] tools_called[0]: ...` renders as a real evidence line and can steer a JUDGED check). Medium. | AT-892 |

## Candidates (human picks) — 2026-10-11 T-145 live-run review (checker, read-only, report `.work/pathlynks-report/`)

Never built until a human moves one out of this section with `approved: <date>`. Findings about the product under test (Pathlynks) are not ledger rows and are listed in the checker's report only. Existing open rows that already cover a T-145 claim and were not duplicated: AT-773 (judge PASSes a failed assertion), AT-774 (retired cases are run), AT-840 (judge sends prompts and screenshots with no mask), AT-654 (no setting yields typing on production; this is why 11 typing actions were refused), AT-113 (screen the crawler cannot return to).

| Priority | Candidate | Ref |
|---|---|---|
| priority: security (data boundary) | Mask or guard `stages/expand.py::build_expand_prompt` before `provider.act`; the T-145 expand sent 42 step values (4 email-shaped, 2 phone-shaped) to the provider unmasked. Pairs with AT-840 (judge screenshots). | AT-890, AT-840 |
| priority: S1/S2 (high) | One failed case must not take the rest of a tier down: 34 of the 37 inconclusive cases failed on a dead browser. Prove the cause with two passing shared-session cases first, then fix `browser/video.py` `end_case_video` and add a session restart. Without this a rerun still tests nothing. | AT-888 |
| priority: S1/S2 (high) | Turn a crawl's screens into reviewable student flows so `expand` has something to expand, and warn before a run when no case's first target exists on the crawled surface. | AT-887 |
| priority: security (consent record) | HUMAN_GATE for Umesh: is `pathlynks.vidysea.com` production? Approval `appr_ce61e4420ac9` is signed `production: false`; the gate file and the T-145 row say production, `project.json` says dev. Inert this run (no typing), live the moment typing is enabled. | AT-891, AT-654 |
| medium | AT-226 precheck races a client-side redirect on a live session; `login_failed` carries no cause. | AT-889 |

## Candidates (human picks) — 2026-10-11 sweep (Mode B sharded, window 72fafe7c..4f8f5da1, master 057b6dbb)

Never built until a human moves one out of this section with `approved: <date>`. **BACKSTOP RED** on 4f8f5da1 (2836 passed, 20 skipped, 4 failed, 4 shards, 2301 s): no `backstop:` stamp, so the next sweep with a changed tree is a backstop run again. **No `HOLD:` line:** no behavioural regression or security defect is traced to a checked-PASS feature's changed files. The one deterministic red (AT-792) is a stale test of a contract-conformant product; the other three are load-sensitive and unresolved (AT-750, AT-725, AT-858). `qa/checkpoints/baseline-reds.md` was not created (see AT-750). No new S1/S2 or security row this sweep; the carried S1/S2 rows below in the 2026-10-07 section stand (its first row, AT-744, is now fixed but see AT-853).

| Priority | Candidate | Ref |
|---|---|---|
| medium (top 1) | Make the suite green: repair the stale `test_rc2_ingest_video_keeps_narration_on_screen_text_and_exit_screen` by passing a Transcript that contains the narration (RC3 holds, no assertion weakened), and fix the hook-output decode failure behind `test_hook_prints_the_report_and_exits_zero_on_a_healthy_log` (test encoding plus hook UTF-8 output). | AT-792, AT-858 |
| medium (top 2) | Remove the unconditional `require_reviewed` from `stages/expand.py:137` and `stages/eval_compiler.py:96` so a reconciled DRAFT spec generates, per review-gate R5 and D-070 item 2. | AT-850 |
| medium (top 3) | Fix the maker-owned bookkeeping that misleads the loop: `Queue TODO: 0` counts only `\| TODO \|` cells while 29 `- [ ]` rows exist, and T-197..T-206 done_checks name verdict files no unit produces and pass on a FAIL verdict. | AT-851, AT-853 |
| medium | `qa/loop.md` contradicts the policy (cap 3 vs 2, no no-progress or quota pause state, pre-D-081 HUMAN_GATE). | AT-854, AT-754 |
| medium | T-206 has no contract criterion; checker authors one before it is built. | AT-855 |
| medium | Shared checker tool `shard_suite.py` doubles `-q` against this repo's `addopts`; out of repo, human-gated. | AT-860 |
| low | Load-sensitive reds need one idle-host solo run on a git archive of the baseline sha before they can be recorded as baseline reds; redact scan trend 3.43 s to 9.14 s. | AT-750, AT-725 |
| low | Row hygiene: mc-precommit false `ready-for-check` warnings, north_star still names ERP first, intent Q4 unticked, catalog screen without an intent trio, `report_export` silent skip, 16 files at 298-300 lines. | AT-852, AT-856, AT-857, AT-861, AT-859, AT-739 |

Closed this sweep: AT-745 (at113 cycle 4 PASS, merged). Annotated: AT-634 (3 more rows without `regression_check`), AT-656 (AT-772 byte-identical duplicate), AT-649, AT-746 (4 gates without a literal `Answered:`), AT-281.

## Candidates (human picks) — 2026-10-07 sweep, report `qa/sweeps/2026-10-07-sweep.md`

Candidates are never built until a human moves one out of this section with `approved: <date>`. Source: sharded Mode B (3 shards + consolidation), window 2aed300e..72fafe7c, working tree dirty.

| Priority | Candidate | Ref |
|---|---|---|
| priority: S1/S2 | Pending goal tasks T-197..T-201 have no done_check; `test_every_pending_task_actually_has_a_done_check` fails deterministically and keeps the suite red. Maker-owned and in progress; listed so it is not lost. | AT-744 (high) |
| priority: S1/S2 | `data_boundary.py` exits 1 (adapter.json declares no `data_class`). Standing, accepted posture, wontfix, exemption recorded in `qa/contracts/core-invariants.md` (AT-365 list entry). NOT refiled. | AT-365 (wontfix) |
| medium | AT-113 cycle 3 STALLED, gate answered 2026-10-05, no maker action since 2026-10-06 and no `qa/debug/at113-cycle3.md`. Reread the gate file before reopening. | AT-745 |
| medium | One solo re-run on an idle tree for the 4 load-or-regression suite failures: `test_crawl_inventory_live` STOPPED_BOUND (possible AT-113-era regression), mc_sessionstart 60 s timeouts, redact_wrap_perf 3.83 s, `video_parallel_sweep` 'A never finished closing' (possible ISS-t191-run-video-1 regression). Not a HOLD. | AT-750, ISS-t151-target-discovery-6, AT-725 |
| medium | RULING (checker, 2026-10-07): the AT-750 solo re-run found 4 load flakes, no regression. Loosen via ONE env-scaled helper `timing_scale()` (AUTOTESTER_TIMING_SCALE, default 1.0, clamp [1.0, 4.0], can only loosen): crawl_inventory_live:103 wall_clock_s 240, mc_sessionstart:142 timeout 60, redact_wrap_perf:192 bound 3.0 (the :209 scaling guard stays untouched), video_parallel_sweep:42 `_WAIT_S` 30; sweeps run with scale 2. Tier L protected change, one checker; load marker and keep-as-is rejected. Exact change and checker tests are in the ledger row. Not built until a human approves. | AT-757, AT-750, AT-725 |
| medium | Gates showing ANSWERED without an `Answered:` line (at638, t125-stalled, pathlynks-user-account-first); t192 narrowed-command ratification is genuinely OPEN and Umesh's. | AT-746, AT-285 |
| medium | `qa/feedback-inbox.md` is 5802 lines; about 20 sections from 2026-10-05/06 unfolded. Fold or archive. | AT-747 |
| medium | T-136 truth sheet `ERP_Issues_Trainers.xlsx` missing on disk. | AT-752 |
| medium | Roadmap and plan text stale against goal.json (target.md T-165 marked done while pending; T-120/T-150/T-171/T-185 unchecked; T-196..T-201 missing; plan.md 'draft', '26 remaining', 8 done tasks listed as remaining, T-165 shown buildable). Already filed, carried. | AT-729, AT-738, AT-642, AT-731 |
| medium | Ledger debt carried: 459 of 508 fixed rows lack `regression_check`; 11 duplicate ids (AT-288..291, AT-547..552) unreconciled. | AT-634, AT-656, AT-676 |
| low | `ui/routes_video.py` added after plan approval with no feature trio or Persona walk line (arguably T-191's fix cycle). | AT-748 |
| low | Delegation ledger has no record rows since 2026-09-27 (~15 Claude-built units). | AT-749 |
| low | Two `test_cli_harness_safety` failures were contamination by a concurrent `ingest prep`, not a CLI bug. | AT-751 |
| low | CLAUDE.md 'Credentials' (AT-570 open, pre-D-068) and `explore.md:614` 'explicit per-run' need a D-entry before the edit. | AT-753 |
| low | doctor not clean: root-clutter `at113-fixture-wn6g4n_e`, `pytest-of-unknown`; stale `docs/MAP.md`. | AT-756 |
| low | `qa/loop.md` HUMAN_GATE example stale; three EXHAUSTED sweeps with the same top-3 and no unit closed (loop-spin). | AT-754, AT-755 |
| low | `explore_node.py` sits at exactly 300 lines (cap), carried. | AT-567 |

GRILL candidates (not rows to build): the three intent questions Q1/Q3/Q4 in `docs/intent.md` have been open over 7 days (Q1 row already below; Q3/Q4 listed with it); D-067 moved the goal, so either one GRILL for group-10 scope or accept the PLAN gate's own grill as that grill (Umesh decides).

`ISS-ingest-fields-1` (high) was fixed and merged in 72fafe7c with checked-PASS cycle 0; it is in the ledger as `fixed`, nothing to do.

---

2026-09-30 bounded crawl-recovery sweep addendum (preserves previous queue):
1. AT-113 / T-165 reopen: independently reproduced completed/0 actions/one aborted_error;
   fix new and legacy completion truth, frontier exhaustion and persona deletion honesty first.
2. Generic authenticated recovery using existing return_to/replay seams; truthful failure alone
   does not satisfy authenticated end-to-end crawling.
3. T-171 permission-surface coverage (carry the prior work/recovery priority).
Report and proposed existing-file plan: `qa/verdicts/sweep-2026-09-30-crawl-recovery.md`.
at673 cycle 3 is checked-PASS with matching verdict; ISS-at673-1 already owns detector debt.

Refreshed by `/checker sweep` **2026-09-29T12:28Z** (system clock, `date -u`, not typed — AT-399), HEAD
`ade87168` (D-057). Bound strictly to `D:/autoTesting`. **Single-agent sweep** — measured ceiling this tick
2.81 GB free RAM, the same constraint the 2026-09-28T12:35 sweep stated, so the 3-shard split was not
available. Full report: `qa/verdicts/sweep-2026-09-29.md`. Supersedes the 2026-09-28T12:32Z queue. **D-057 (Umesh, 2026-09-29) is folded in:** the CT6 gate and the AT-710 new-module gate are both ANSWERED.

**What changed since that queue:** D-057 answered both open gates (below); the four D-054 contract files exist (so the ISS-at638-remainder-1
HUMAN_GATE line is gone — it was answered 2026-09-27 and fixed 2026-09-28); D-041's four unwritten
contracts now exist too (AT-726); `at710` was built, falsified and **held** at a new-module gate
(`qa/gates/new-module-authorization.md`, unanswered); the approval-surface cluster stands as re-triaged.

## TOP-3 BUILDABLE NEXT UNITS

| # | Unit | Why |
|---|---|---|
| 1 | **T-171 permission-surface — RESUME, do not restart.** `.claude/worktrees/agent-a34c44eb5901959f8` holds 10 files (+249/-19) of **uncommitted** crawl-coverage and explore-safety work from 2026-09-28 18:12, tied to a manifest that exists only inside that worktree, untracked, with `tests/test_permission_coverage.py` (AT-728, corrected). Criteria exist and are ungated: `qa/contracts/permission-surface.md` PS1-PS4 (DRAFT, D-054) plus `coverage.md` V9 (AT-663). Commit that work and its manifest to a wave branch so master can see them, then build. | Serves O4 directly and Umesh's verbatim 2026-09-23 ask ("jo account mai dunga usme jitni permission hogi uthi tho testing ho hi jaani chaiyee"). It is also the one item where finished-looking work is one `worktree remove` from being lost. RAM-bound: one build at a time at 2.81 GB. |
| 2 | **T-176 script-replay.** Criteria written today: `qa/contracts/script-replay.md` SR1-SR5. Free behind T-165 (done). `Case.script_ref` and `Script` already exist and are unwired, so this is wiring, not invention. **It was never gated** — the maker's 2026-09-29 tick listed "T-176: no authorizing contract", but D-041 authorized the file on 2026-09-24 (AT-726). T-177 (`agent-fallback.md` AF1-AF6) follows it. | Highest-value ungated unit: it turns every regression run from N provider calls into zero, and SR5 encodes D-041's refusal of "regenerate instead of maintain". |
| 3 | **T-125 cycle 4 -- submit it for check, and judge it against CT6 (narrowed) and CT9 (new).** Build to recover: `worktree-agent-aca539b488be4c248`, 12 ahead (manifest `t125-test-catalog.md`, `ready-for-check`, uncommitted edit, no verdict; master carries neither, so the hook cannot see it). **D-057 makes CT6 PASSable:** it is now 'dispatch in tier order, report each tier's runnable count, never skip' and no longer conflicts with RU3/F-058; the build must wire `tiers_to_run()` (not yet in `src/` on master) into `routes_runs.py::trigger_run` as ordering only. **New precondition met this sweep:** D-051 asked for a written relevance rule before cycle 4 and none existed (AT-732); CT9 now states it. Expect the check to open on CT9(b) (`4636e832`) and CT6(2) (executed set == `list_cases()`). | T-125 gates T-152, T-166, T-174 and T-178; `cli-mcp.md` and `failure-bundle.md` wait behind it. Merge note: `wave/t125-catalog` holds a 2026-09-27 catalog.md amendment master lacks; the two log tails will conflict and both entries stay. |

## HELD on a human — one line each, not build rows

- **AT-710 is OFF the human list (D-057, Umesh 2026-09-29):** `src/autotester/ledger/citations.py` and its own test module are authorized for AT-710 ONLY. AT-697 and AT-727 meet the new-module gate again on their own merits (the standing-rule variant was not chosen). The build is held in `.work/at710/` and resumes under the maker. **AT-718 has happened AGAIN (AT-740):** the seven write-policy citations were re-pointed to `D-057 (NOT YET WRITTEN)`, and D-057 was then appended on 2026-09-29 for a different subject (the three answers). They resolve to the wrong entry a second time; the write-policy entry, once written, is `D-058` or later. This is the exact case `check_decision_citations` exists to catch, and its fixture (c) in `living-ledger.md` names the now-spent id.
- **HUMAN (classifier-blocked): the approval-derivation unit** — AT-674 (`core/env.py::ensure_approval_key`) + AT-683 (`cli_crawl.py::approve_cmd` real min=1 defaults). Fully authorized by Umesh's 2026-09-28 answer; both halves were reported blocked by the harness classifier. Blocks T-122.
- **HUMAN_GATE (AT-668/AT-669):** the guard-the-guards protection does not cover `qa/hooks/*` — needs an `Approved-by` DECISIONS entry before the wiring fix lands.
- **Umesh's, still open:** `qa/gates/t192-narrowed-command-ratification.md`. (`t125-ct6-tiered-dispatch-vs-ru3.md` is ANSWERED, D-057; the maker records its `Answered:` line.)

## Also real, not in the top 3 only for space

AT-733 (high: `ui/run_execution.py:67` wipes the logged-out profile with `ignore_errors=True`, so a locked profile lets a logged-out case PASS logged in); AT-734/735/736 (video, post-save prune and session-start failure paths); AT-727 (nothing checks that an authorized contract file exists — twice now misread as a human gate);
AT-731 (T-185 still `pending` after its PASS, merge and green done_check — one `goal_cli done`);
AT-729/AT-730 (target.md, plan.md and the at638-remainder manifest still say things that stopped being
true on 2026-09-27); AT-645/AT-656/AT-676 (recurring `qa/issues.jsonl` duplicate-id debt — 10 ids still
carry two rows); AT-711; AT-644; AT-634 (rows fixed without a `regression_check`, now 69, was 31).

## GRILL — human decision, not a build row (carried)

- GRILL (AT-402): structure-before-code review of `visual_order.js`. Carried.

**Explicitly NOT judged this sweep:** `at673` (`qa/manifests/at673-sessionstart-unclosed-detector.md`,
`qa/hooks/mc-sessionstart.ps1`, `tests/test_mc_sessionstart_unclosed.py`) and rows AT-713/714/715 and
AT-722..725 — a concurrent Mode A checker owns it. Commit `8ea308ee` (its cycle-2 build) is the only
in-window commit that touched `src`/`tests`/`scripts`/`qa/hooks`, and it belongs to that check.
