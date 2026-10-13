# Stale open-issue audit 2026-10-12 (read-only triage)

Scope: qa/issues.jsonl rows with status=open and severity high or medium (149 rows: 31 high, 118 medium). Verified against origin/master only; FIXED-ON-MASTER rows cite commits confirmed ancestors of origin/master (or a master-tree check). Fixes that exist only on unmerged branches are FIX-PENDING-ON-BRANCH.

NOTE: qa/issues.jsonl reuses ids (e.g. AT-548, AT-549, AT-745, AT-710 each appear on more than one row), so rows must be keyed by id+title, not id alone. Closing any row is a checker job; this report does not edit the ledger.

Counts: FIX-PENDING-ON-BRANCH 10, STILL-OPEN 56, FIXED-ON-MASTER 28, NEEDS-HUMAN 18, NOT-CODE 37

| id | sev | class | evidence |
|---|---|---|---|
| AT-113 | high | FIXED-ON-MASTER | merge 8fd182d4 + 9f651068 (cycle 4 PASS) and 3d7e1c72 drain-deferred unreachable aborts crawl; tests/test_crawl_unreachable.py |
| AT-583 | high | FIXED-ON-MASTER | T-190 49593d9e: schema/user_persona.py + Case.user_persona_ref (schema/case.py:38) |
| AT-584 | high | FIXED-ON-MASTER | 49593d9e adds stages/ux_advisory.py advisory UX findings by persona (never alters verdict); partial vs original ask |
| AT-683 | high | FIXED-ON-MASTER | cli_crawl.py:242-256 approve bounds min=1 default 200 and rejects non-positive; commit 1fdba241 (AT-570/AT-660) |
| AT-710 | high | FIXED-ON-MASTER | L9 citation resolver ledger/citations.py (24d6323b); D-056 now exists docs/DECISIONS.md:1569; at710 closed 3fcfb4c2 |
| AT-733 | high | FIXED-ON-MASTER | b07cc727 + verdict at733-bounded.md PASS; run_execution.py _wipe_entry_profile fails closed before browser start |
| AT-740 | high | FIXED-ON-MASTER | 9daa5a02 repointed gate citations to NOT YET WRITTEN; write-policy D-entry itself still unwritten (separate) |
| AT-773 | high | FIXED-ON-MASTER | 50f0de0f + merge 6ee02779 on master; grade.py:93 PASS with ASSERTION_FAILED/unmet forced FAIL; verdict at773-judge-rule.md |
| AT-887 | high | FIXED-ON-MASTER | a773f972 at887-crawl-to-flows checked-PASS; explore_merge.merge_screens_and_flows + stages/explore_flows.py flows_from_crawl |
| AT-888 | high | FIXED-ON-MASTER | 55816796 fix(browser) failed case no longer takes shared session down; verdict qa/verdicts/at888-session-survives-failure.md |
| ISS-t168-damage-control-report-1 | high | FIXED-ON-MASTER | unified_report.py:262-265 scrubs object via scrub_obj before render (DC4); commits 72a7ecae..869cf16e r2 B PASS |
| ISS-t191-run-video-2 | high | FIXED-ON-MASTER | 8f577aef merge t191 reachable run video cycle-2 PASS 16/16 (05eb41e4 serves kept videos on run page) |
| AT-399 | medium | FIXED-ON-MASTER | da6fa635 + 54e6b47a loop_status handles future-dated ticks; verdict at399-loop-status-integrity.md PASS; stamp text itself not validated |
| AT-407 | medium | FIXED-ON-MASTER | 5e9ae807 re-tracked tests/test_flake_probe.py; git ls-files confirms; cited in verdict at396 |
| AT-582 | medium | FIXED-ON-MASTER | 8c1f05cb + merge 73a89d74 (t183-export-reason); fix_hint used 7x in stages/report_export.py |
| AT-587 | medium | FIXED-ON-MASTER | eac530a2 T-191 record_video on FAIL/inconclusive (browser/session.py, launch.py); checked PASS |
| AT-588 | medium | FIXED-ON-MASTER | 2e397500 + 62a45c6a; stages/catalog.py has oauth carryover pack; qa/verdicts/t125-catalog.md VERDICT PASS |
| AT-630 | medium | FIXED-ON-MASTER | ed26fb16 (AT-673) hook now uses Get-ManifestStatus last Status heading (mc-sessionstart.ps1:92-94) |
| AT-669 | medium | FIXED-ON-MASTER | Field readers anchored in mc-sessionstart.ps1 (Get-ManifestStatus/Get-CycleNumber); ed26fb16, at673 cycle 3 PASS 311d322f |
| AT-673 | medium | FIXED-ON-MASTER | qa/hooks/mc-sessionstart.ps1 Get-ManifestStatus anchors the field; ed26fb16, verdict at673 cycle 3 PASS 311d322f |
| AT-728 | medium | FIXED-ON-MASTER | Recovered by ffbea539 on master (t171 coverage build); .claude/worktrees dir no longer exists |
| AT-743 | medium | FIXED-ON-MASTER | tests/test_goal_contract_registration.py passes on master now (ran per-file, 2 passed) |
| AT-769 | medium | FIXED-ON-MASTER | same test passes on master (grant_live_case_approval at line 86); 6b808ba2 |
| AT-792 | medium | FIXED-ON-MASTER | merge 238a1b7c at792-stale-rc2-test (RC2 test supplies its transcript); later full-suite verdicts still list it as known red so confirm solo |
| AT-855 | medium | FIXED-ON-MASTER | 1c52bf71 added qa/contracts/team-loop-acceptance.md covering T-206 |
| ISS-d063-grant-budget-1 | medium | FIXED-ON-MASTER | 2e9b3bf8 AT-759: explore_consent.covering_approval uses human rows only unless project.secrets via credential path |
| ISS-d063-grant-budget-2 | medium | FIXED-ON-MASTER | a2c6124a D-066 Origin/CSRF guard + 2e9b3bf8 AT-758 Host allow-list on master (ui/credential_guard.py, app.py); chain not rerun |
| ISS-t171-goal-pin-1 | medium | FIXED-ON-MASTER | test_ui_runs_serial_entry_mix_live.py now grants approval (grant_live_case_approval); passes on master per-file run |
| AT-109 | medium | FIX-PENDING-ON-BRANCH wave/crawl-to-flows | 8c86348d (2026-10-12) explore_merge.py+expand.py name screens a re-crawl no longer sees; tests/test_crawl_to_flows.py; no checker verdict yet |
| AT-655 | medium | FIX-PENDING-ON-BRANCH wave/bench-untimed-trial | schema/bench.py:81 duration_s float/None + unavailable_reason; commit 805a533f (bench AT-655 tests) |
| AT-734 | medium | FIX-PENDING-ON-BRANCH wave/ui-run-hygiene | Fix 25f92a8f only on wave/ui-run-hygiene, not master; video.py:200 except-return None and :223 __exit__ return True remain |
| AT-735 | medium | FIX-PENDING-ON-BRANCH wave/ui-run-hygiene | prune_old_videos now at stages/run_launcher.py:288 after save_run, still unguarded; fix 25f92a8f not on master |
| AT-787 | medium | FIX-PENDING-ON-BRANCH wave/at787-bundle-wiring | Wiring commit fe360bea only on origin/wave/at787-bundle-wiring, not master; no build_failure_bundle caller in src |
| AT-889 | medium | FIX-PENDING-ON-BRANCH wave/crawl-unreachable | 3d7e1c72 race-free login precheck (AT-113, AT-889); verify stop_reason cause appended if wanted |
| AT-892 | medium | FIX-PENDING-ON-BRANCH wave/judge-oracle | 447b8ee7 escape target text in ai_judge evidence rows; tests/test_ai_evidence_escape.py |
| AT-898 | medium | FIX-PENDING-ON-BRANCH wave/release-cli | 0241df34 stages/release.py derive_flow_plans + save_flow_plan after gate; tests/test_cli_release.py |
| AT-899 | medium | FIX-PENDING-ON-BRANCH wave/release-cli | 0241df34 cli_release.py clearer pause output (5 files, 54 test lines); closing lines not individually verified |
| AT-900 | medium | FIX-PENDING-ON-BRANCH wave/release-cli | 0241df34 core/paths.py run_dir uses safe_name(run_id) raising UnsafeName; other commands taking run id not audited |
| AT-644 | high | STILL-OPEN | Umesh approved guard (3ebe893f) but no truncation guard found in loop_status.py/hooks; needs DECISIONS entry then build |
| AT-645 | high | STILL-OPEN | qa/issues.jsonl still has duplicate ids (AT-288..291 AT-547..552 AT-710 AT-745 etc) |
| AT-651 | high | STILL-OPEN | No second-environment model in schema/project.py; only docs/gate answers (4502d8ab, 068e639e) |
| AT-653 | high | STILL-OPEN | Only criteria strengthened (cb337e04, 6f7846c9); recall ordering fix blocked on decisions append; no code |
| AT-656 | high | STILL-OPEN | No duplicate-id guard; qa/issues.jsonl still has dup ids (AT-288-291 AT-547-552 AT-710 AT-745) |
| AT-676 | high | STILL-OPEN | .gitattributes still qa/issues.jsonl merge=union; no id-uniqueness check in ledger/checks.py or doctor.py |
| AT-711 | high | STILL-OPEN | No contract rule binding capability row to HEAD+status digest (grep rev-parse HEAD in contracts empty); only AT-700 instance fixed |
| AT-718 | high | STILL-OPEN | Gates now cite WP-DECISION (NOT YET WRITTEN); the write-policy decision entry still unwritten; recurrence AT-740 repointed in 9daa5a02 |
| AT-840 | high | STILL-OPEN | stages/grade.py has no mask_pii/mask call; image policy needs Umesh (HUMAN_GATE part) |
| AT-112 | medium | STILL-OPEN | explore_consent.py/explore.py still never pass production= to require_approval for CRAWL; no production predicate in src |
| AT-196 | medium | STILL-OPEN | tests/test_explore_live.py:139 still asserts only ('aborted_dialog','explored') |
| AT-318 | medium | STILL-OPEN | doctor._python_files globs src/ only; scripts/ still outside file/function-length rules |
| AT-375 | medium | STILL-OPEN | No collision-safe id allocator in scripts/ or src (only ledger/checks.py detection); AT-293 remedy still unwritten in code |
| AT-379 | medium | STILL-OPEN | Verdict FAIL (only one of two directions closed); later AT-408/416 commits 7b1f9c30 553e8fac 15e14023 help but no verdict closes AT-379 |
| AT-382 | medium | STILL-OPEN | loop_status.py still only explains open gap via qa/.paused; resume still deletes it so closed gaps read SLEEP |
| AT-417 | medium | STILL-OPEN | clip-path+scroller case pinned xfail(strict) in tests/test_browser_scroll_invariance.py; at423 verdict says open |
| AT-507 | medium | STILL-OPEN | docs/ARCHITECTURE.md is again exactly 150 lines (cap 150) despite d7298b53 trim; zero headroom |
| AT-518 | medium | STILL-OPEN | Whole-suite flake in test_flake_probe_real_process child.pid; later notes 533e0826 926e8016 show unresolved under load |
| AT-586 | medium | STILL-OPEN | stages/expand.py has no scenario/variant matrix; no commit found; only filing of AT-638 criteria |
| AT-616 | medium | STILL-OPEN | Red-before-fix of AT-608/609 regression_checks unaddressed; no fix commit found |
| AT-623 | medium | STILL-OPEN | qa/hooks/mc-sessionstart.ps1:181 snapshot call still unbounded (try/uv run, no timeout); loop-status call is bounded |
| AT-650 | medium | STILL-OPEN | stages/explore_safety.py:47-52 password check is label substring only; enumerate.js roleOf returns textbox for password input; no fix commit |
| AT-657 | medium | STILL-OPEN | mc-sessionstart.ps1:121 still arms AUTO-CONTINUE on sweepAge -gt 120; no OFF state |
| AT-666 | medium | STILL-OPEN | Not folded into criteria; T-166/167/168 owned; (b) needs N set by Umesh |
| AT-680 | medium | STILL-OPEN | Serial path _run_cases_serially passes session.budget (wall clock) but no per-case try_consume; verdict at570 accepted as shipped-with-row |
| AT-682 | medium | STILL-OPEN | No UI/report render of Run.bounds found in src (only AT-570 verdict notes it stays open) |
| AT-696 | medium | STILL-OPEN | mc-sessionstart.ps1 has no worktree enumeration (grep worktree = 0 hits) |
| AT-697 | medium | STILL-OPEN | doctor.py:195 check_generated_fresh still compares disk to render, no git blob compare |
| AT-699 | medium | STILL-OPEN | No sweep stamp writer in src/scripts for qa/.last-sweep append-only log |
| AT-727 | medium | STILL-OPEN | No doctor/sweep check that Changes-authorized contract files exist (needs new-module authorization too) |
| AT-736 | medium | STILL-OPEN | session.py start() still no cleanup if launch_persistent_context raises; no fix commit on master |
| AT-794 | medium | STILL-OPEN | run_ux_advisory has no caller in src (only report_export imports other helpers) |
| AT-830 | medium | STILL-OPEN | core/redact.py mask_pii has no percent-decode handling and tests contain no %40 case |
| AT-850 | medium | STILL-OPEN | require_reviewed(spec) still unconditional at expand.py:144/202/212 and eval_compiler.py:99 |
| AT-851 | medium | STILL-OPEN | mc-sessionstart.ps1:109 still counts only / TODO / cells |
| AT-854 | medium | STILL-OPEN | qa/loop.md:37 still says max 3 cycles; no quota/no-progress text |
| AT-858 | medium | STILL-OPEN | test_mc_sessionstart_loop_status.py:140 subprocess.run text=True with no encoding; no fix commit |
| AT-925 | medium | STILL-OPEN | No formula guard in core/excel.py or ai_report.py; no fix commit (needs contract line first) |
| AT-928 | medium | STILL-OPEN | Proposed issue filed 4353e168, no fix commit; failure_bundle trace path not shown to scrub_obj before dumps |
| AT-929 | medium | STILL-OPEN | No scrub in store layer (grep scrub store/ empty); proposed issue only |
| AT-943 | medium | STILL-OPEN | stages/schedule_store.py purge_project still catches OSError only (line 23) and uses .purge-uuid stage dir |
| AT-956 | medium | STILL-OPEN | tests/test_run_launcher_approval.py has only allow-list pin for priorities; no priorities x no-approval rows |
| AT-967 | medium | STILL-OPEN | No test for dotted run ids in records_for_run (only run-1 forms in tests/test_delivery_failure.py) |
| AT-979 | medium | STILL-OPEN | Proposed issue only; no fix commit for case_changed replay stamping |
| AT-980 | medium | STILL-OPEN | bug_store snapshot still globs bev_*.json only; no legacy handling |
| AT-981 | medium | STILL-OPEN | Proposed issue; sheet_plan scrubs bug_values (line 82) but CellChange.before and sheet_has unverified; no fix commit; live slice |
| AT-982 | medium | STILL-OPEN | Proposed issue for future live sheet slice; no fix commit |
| AT-983 | medium | STILL-OPEN | sheet_write.py:77 still relies on client.live flag only; no fix commit |
| AT-984 | medium | STILL-OPEN | Proposed issue for future live sheet slice; no fix commit |
| ISS-at335-followup-tolerance-scope | medium | STILL-OPEN | No commit after d625205e narrowing RETURN_SETTLE_TOLERANCE for terminal rung; follow-up only filed |
| ISS-at639-1 | medium | STILL-OPEN | media/chunks.py has per-chunk CHUNK_TIMEOUT_S only; no aggregate deadline in stages/media_prep.py |
| ISS-at673-1 | medium | STILL-OPEN | Balanced quoted heading over-read accepted by D-058 (removal); no committed test guarding it; Get-CycleNumber unchanged |
| ISS-d063-grant-budget-3 | medium | STILL-OPEN | explore_consent.py human path _require(human,...) still probes=0 default; only credential path passes probes |
| ISS-t164-1 | medium | STILL-OPEN | tests/test_flake_probe_real_process.py still present; no commit fixing the hung grandchild test found |
| ISS-t165-crawl-traversal-a8 | medium | STILL-OPEN | Deleted-second-state-at-shared-URL silence; filed in t165 PASS verdict, no fix commit |
| ISS-t168-damage-control-report-2 | medium | STILL-OPEN | load_api (unified_report.py:149-162) returns Unavailable only when no results and no crawl network; no NETWORK-row check |
| AT-253 | high | NEEDS-HUMAN | run_with_fallback still has no src callers; 7cc756fa gated wiring as runtime/cost decision |
| AT-281 | high | NEEDS-HUMAN | GRILL: T-169 acceptance thresholds need Umesh approval; carried across many sweeps |
| AT-654 | high | NEEDS-HUMAN | Product decision D-029 dev-only vs production typing; gate written 3c9cb374; stages/explore_consent.py:44-51 unchanged |
| AT-668 | high | NEEDS-HUMAN | HUMAN_GATE: decisions-append-guard.ps1:92-94 still lists only .claude/hooks, scripts/append_decision.ps1, settings.json; qa/hooks unprotected |
| AT-674 | high | NEEDS-HUMAN | Provisioning approval key and signed grant is Umesh-only; approvals.jsonl now 7 rows/4 signed, .env present, T-122 state unclear |
| AT-118 | medium | NEEDS-HUMAN | Upstream D:/ai_os goal skill criticality.py, outside repo (file not even present at that path) |
| AT-327 | medium | NEEDS-HUMAN | doctor duplicate rule still src-only; verdict at324 says filed for a decision on C3 scope not a fix |
| AT-376 | medium | NEEDS-HUMAN | Upstream MC-003 data_boundary.py in D:/ai_os gitignore scan; outside repo |
| AT-377 | medium | NEEDS-HUMAN | Product decision: downgrade vs label partial-evidence verdicts; grade.py only labels; bug_loop.py:117 uses the flag |
| AT-529 | medium | NEEDS-HUMAN | Pathlynks production credential 401 then 200 unexplained; HUMAN_GATE Umesh credentials |
| AT-665 | medium | NEEDS-HUMAN | HUMAN_GATE: what recording-corpus ingest should produce; not folded |
| AT-694 | medium | NEEDS-HUMAN | Wiring check_no_secrets into adapter/hook is enforcement path needing Approved-by Umesh; not in qa/adapter.json verify |
| AT-752 | medium | NEEDS-HUMAN | ERP_Issues_Trainers.xlsx truth sheet missing on disk; only Umesh can supply |
| AT-860 | medium | NEEDS-HUMAN | Defect in D:/ai_os checker shard_suite.py outside this repo |
| AT-868 | medium | NEEDS-HUMAN | T-203 backlog (non-root, per-user scoping, backup.sh, linux evidence) depends on T-204 permission model; tracking item, not closable |
| AT-891 | medium | NEEDS-HUMAN | production flag on appr_ce61e4420ac9 vs dev/prod host naming is a human decision (HUMAN_GATE); no commit addresses it |
| AT-927 | medium | NEEDS-HUMAN | Owner decision on T-155 behavioural writer/call surface; export_ai_report has no caller in src |
| ISS-t192-url-pattern-heal-1 | medium | NEEDS-HUMAN | Ratification gate opened (ae4e21e2) on whether ingest map satisfies t135 answer B |
| AT-663 | high | NOT-CODE | Folded as contract coverage.md V9 (sweep-2026-09-28); no code change |
| AT-672 | high | NOT-CODE | Machine disk issue; C: now 23G free of 100G (78% used); no code fix |
| AT-692 | high | NOT-CODE | Process rule (redirect verify output, never pipe); C12 pipe row added 45477b03; verdicts follow it |
| AT-712 | high | NOT-CODE | Close-out back-reference process; instance rows re-annotated in 83218eb7; no code |
| AT-820 | high | NOT-CODE | Process incident: builder host-wide taskkill; no code fix; kill-only-recorded-PIDs policy |
| AT-282 | medium | NOT-CODE | Checker-runtime env issue (uv cache and pytest basetemp ACL under another user); no repo code fix |
| AT-360 | medium | NOT-CODE | Evidence-quality note on mutations.json M5; filed-not-charged in PASS verdict 8edad518 |
| AT-381 | medium | NOT-CODE | Finding that five past outages were never filed; loop-status tool (9040a1a9, PASS 5c2b8f21) already measures them |
| AT-402 | medium | NOT-CODE | Structural-erosion signal on visual_order.js churn; no code fix |
| AT-415 | medium | NOT-CODE | Governance: gate premise re-derivation; process item |
| AT-421 | medium | NOT-CODE | Governance: ledger row premise rot; process item |
| AT-448 | medium | NOT-CODE | Ledger fixed-vs-verified backlog count; sweep/process item |
| AT-460 | medium | NOT-CODE | Signal: explore.py at 300 cap; now 286 lines; human decision |
| AT-484 | medium | NOT-CODE | Process: qa/.last-tick staleness across sessions |
| AT-488 | medium | NOT-CODE | Erosion signal: scripts/mutation_check.py now 416 lines, scripts still outside doctor size rules (see AT-318) |
| AT-502 | medium | NOT-CODE | Erosion signal flake_probe.py churn; now 254 lines; no fix required |
| AT-544 | medium | NOT-CODE | Ledger now current: docs/FEATURES.jsonl last row F-083 dated 2026-10-12; stale-ledger signal resolved |
| AT-548 | medium | NOT-CODE | Ledger claim only; F-044 row now exists (source-adapters, 2026-09-22) but is not a correction row; commit message untraceable, no code fix |
| AT-549 | medium | NOT-CODE | Governance; x10b re-passed cycle 3 in commit 99841a9c/529746b2 so stall closed; no code |
| AT-558 | medium | NOT-CODE | Worktree env (.venv certifi/hooks) process issue; not repo code |
| AT-567 | medium | NOT-CODE | Signal only; 3 of 4 files split (b0ef27a); helpers.py now 292, explore_node.py 299 lines (still 1 under cap) |
| AT-634 | medium | NOT-CODE | Ledger regression_check metadata debt (grew to 69); no code fix |
| AT-642 | medium | NOT-CODE | target.md reconciled 2026-09-27 (line 265 notes 47/70 correction); doc only |
| AT-643 | medium | NOT-CODE | Governance/process (unjudged worktree commits); t125 and at408-416 since judged PASS |
| AT-648 | medium | NOT-CODE | Process; x10b re-pass checked-PASS cycle 3 commits 529746b2/99841a9c |
| AT-658 | medium | NOT-CODE | Process/repo hygiene; git stash list is now empty on master (landmine gone); rule item only |
| AT-662 | medium | NOT-CODE | Contract LS6 (loop-status.md:52) added baf5c718; hook now reads all status spellings; data normalization is process |
| AT-664 | medium | NOT-CODE | Folded as contract ui.md U15 (sweep-2026-09-28); duplicate-id aspect tracked under AT-676 |
| AT-708 | medium | NOT-CODE | Id-reservation process; adapter reserve_id=kernel declared; QUEUE reservation wording governance |
| AT-709 | medium | NOT-CODE | Dispatch-template wording (process); no template carries the framing line |
| AT-717 | medium | NOT-CODE | Process note on git commit --only; instance in 10ccf757; no guard code |
| AT-745 | medium | NOT-CODE | Stalled at113 cycle-3 manifest/diagnosis process item; needs maker/gate action not code |
| AT-746 | medium | NOT-CODE | Gate-file ledger hygiene: at638 and pathlynks-user-account-first still have no Answered: line (grep count 0); t125/t192 have one |
| AT-747 | medium | NOT-CODE | feedback-inbox.md now 5870 lines; fold-in/ledger hygiene item |
| AT-750 | medium | NOT-CODE | Needs a solo idle-machine re-run to classify; timing bounds ruled in 807db636 (AT-757); later verdicts say AT-750 test did not fail |
| AT-853 | medium | NOT-CODE | goal.json done_check / unit slug naming mismatch; goal-tracker governance |
| ISS-at408-416-1 | medium | NOT-CODE | Manifest accuracy/test-coverage note; checker PASS cycle 1 edbee6b2 (low sev in verdict) |
