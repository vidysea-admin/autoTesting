# Verdict - land-t203-hosting (cycle 0)

Cycle checked: 0 · Policy-Version: proportional-verification/2026-10-10.9 · bound to D:/autoTesting · checked code fddbf469 (branch HEAD 05b8b7ba, manifest-only on top) · checker: claude-sonnet-subagent coordinator + 1 Sonnet sub-checker (persona walk)
Executor under check: claude-sonnet-subagent (maker build subagent); self != executor.

## Plan
Tier L single check (Dual check: no). Checks: 4c diff scope; HO verify commands (affected set + ruff + doctor); falsifications in copies; conftest ruling; queue slot accounting (own tests + own falsification); ledger audit; persona walk in a real headless browser (sub-checker, port 8123, scratch root under the worktree `.work/`); Docker rows are BLOCKED-CAPABILITY (`docker info`: cannot connect to dockerDesktopLinuxEngine).
Dispatch-blocker scan: no security/auth/tenancy/prod-write trigger in the diff (no login, session, permission or production-data write; `core/env.py` only treats an empty inherited value as unset). Dual check: no stands.

VERDICT: PASS
SCOREBOARD: in-scope rows HO1 HO2 HO3 HO7 HO9 HO10 HO11 HO13 HO14 HO15 HO16 HO17 HO18 HO19 HO20 HO21 HO37 HO38: 10 MET on their LOCAL evidence, 8 PARTIAL (named later-unit or server/Linux halves), 0 not met. Invariants: none-touched.
TIER: L (concurrency `ui/run_queue.py`; config `docker/compose.prod.yml`, `.env.example`; env loading `core/env.py:66`; protected-file edit `tests/conftest.py`). No raise to a dual check.

Rows (evidence is mine, rerun on fddbf469 in the worktree):
- MET: HO1 HO2 HO9 HO14 HO16 HO17 HO18 HO20 HO37 HO38 (LOCAL halves). 297 passed in 190 s over the brief section 6 set + test_ui_report, test_ui_report_no_runs, test_ui_sources (`uv run pytest -p no:xdist ...`); `ruff check src tests scripts` clean; `autotester doctor` clean; `scripts/check_no_secrets.py docker .env.example` 0 leaks.
- PARTIAL: HO3 (healthz reads the package root, tested; container run BLOCKED), HO7 (overlay publishes 8000 on `127.0.0.1` only by default and nothing else, `docker/compose.prod.yml:25`; the contract says not published, and `AUTOTESTER_BIND=0.0.0.0` is the documented interim; nmap/ss SERVER-GATED), HO10 (Windows pass; `qa/evidence/t203-linux-run.md` absent), HO11 (guide-vs-code tests; literal follow-through not run), HO13 (config tests; TLS/HSTS and the startup mode log SERVER-GATED; HOSTED/COOKIE_SECURE read nowhere yet), HO15 (model/store/validation/audit/precedence; the `settings.manage` page waits for T-204), HO19 (credential/provider/consent gates re-run at start; the `project.run` recheck waits for T-204), HO21 (requested_by/trigger stored; per-user scoping waits for T-204).
- BLOCKED-CAPABILITY (no Docker daemon): HO1/HO2 BUILD-HOST halves, HO3 container, HO10 Linux run. Not in this unit: HO4 HO5 HO6 HO8 HO12 HO22-HO36.

FAILURES: none.
CAPABILITY-COVERAGE: floor met by 4 rows reproduced by me (copies outside the tree, each green before, red after):
- HO18 slot release (own test file, not the builder's): `_finish` start-next skipped unless `DONE` -> `test_crash_refuse_exit_each_frees_slot_and_project_for_the_next_waiter` red (`r2` stays QUEUED after `r1` crashed); 3 sibling tests (60-press threaded stress, restart with entries on disk) stay green.
- HO17 cap compare `>=` -> `>`: 9 failed of 24 (`test_two_members_pressing_test_in_the_same_instant...`, `test_a_project_mashing...` among them); 24 passed unmutated.
- HO2 `os.environ.get(key)` -> `key in os.environ`: `test_an_empty_inherited_value_does_not_shadow_the_data_env_file` red; 6 passed unmutated.
- HO1 drop `**/.env` from `.dockerignore`: `test_dockerignore_keeps_secrets_and_pr...` red; 10 passed unmutated.
Builder falsifications (HO19 catalog kwarg, HO16 id minted after gates) not re-run by me; the HO16 source change is covered by the unchanged master test in the 297 run.
LIVE-BROWSER: D:/autoTesting/qa/evidence/browser-land-t203-hosting-2026-10-11-checker/ (persona-walk.md, report.json, 14 screenshots; headless Chromium, 1 context, loopback 8123, server stopped, nothing listening). Browser lane: tick --ceilings `lane=browser cap=1`; the other agent's browser was not touched.

## Rulings
1. conftest.py: +34 lines, 0 removed. One new autouse fixture `_inline_run_queue` (conftest.py:59-91) replaces `run_queue._QUEUE` per test with a queue whose spawn runs inline and re-raises a runner crash (RunRefused stays quiet). No existing fixture, guard or assertion line changed; nothing skipped, loosened or deselected. It does hide the real queue from every test, so threading is covered only by `test_run_queue.py` (`test_default_thread_worker_does_not_block_the_caller...`) and my threaded stress run. No guard weakened.
2. Slot accounting: claim, start-mark and release all happen under one `_lock`; `_work` frees in `finally` for Exception, RunRefused, SystemExit and CancelledError. My 60-press threaded stress (3 projects, cap 2, random sleeps, every 7th run raising) peaked at 2 total and 1 per project and left nothing QUEUED or RUNNING. Restart with entries on disk: RUNNING -> INTERRUPTED with a reason, never re-executed, its project freed and the waiter started. A cancelled queued entry: no cancel API exists (contract: out of scope); not applicable. Residual (question, not a FAIL): a spawn that itself raises (thread cannot start) would leave the entry RUNNING until restart; AT-870 already notes the failed-write case.
3. Ledger: AT-862..AT-873 appended after an identical 854-row prefix; all 12 parse with every required field; no id collides with master (master now ends at AT-861); no existing row changed; statuses equal the PASS commit 66f8b98c (862-866 fixed, 867-873 open); the 12 titles/evidence equal the old rows, and the one ref inside text (AT-870 -> AT-865) is renumbered consistently. AT-862..866 are `fixed` with no `regression_check` (low).
4. full-suite trigger: tests/conftest.py edited (the autouse fixture runs on every test, and `ui/routes_runs.py` / `ui/app.py` are shared with T-205 and T-204). Not run here.

Merge notes: `git merge-tree master wave/land-t203-hosting` is clean; `docs/MAP.md` and `qa/issues.jsonl` changed on both sides (MAP.md is generated: re-run `autotester map` after the merge, then doctor).

PROPOSED-ISSUE (low, the maker mints ids; no AT id used here to avoid the AT-862..873 block):
- P1 {"severity":"low","feature":"hosting","title":"Queue panel does not show requested_by or trigger although the manifest says 'recorded and shown'; HO21 wants a user to see their own requests","evidence":"src/autotester/ui/run_queue_view.py:25-31"}
- P2 {"severity":"low","feature":"hosting","title":"Report page with no finished run shows the queue panel (RUNNING/QUEUED) above 'no runs yet'","evidence":"src/autotester/ui/routes_report.py:219-225"}
- P3 {"severity":"low","feature":"hosting","title":"Raising max_concurrent_runs does not start a waiting entry until the next press or a finish; the T-204 settings save must nudge the queue (HO17 'raising the cap starts the waiting one')","evidence":"src/autotester/ui/run_queue.py: _take_startable callers are submit, recover, _finish only"}
- P4 {"severity":"low","feature":"hosting","title":"Interrupted reason says 'press Test again' but the button reads 'Run tests'; 400/429 are bare error pages; Time column has no date; queue table overflows its card at 390 px","evidence":"src/autotester/ui/run_queue.py:112; qa/evidence/browser-land-t203-hosting-2026-10-11-checker/persona-walk.md"}
- P5 {"severity":"low","feature":"hosting","title":"Fixed rows AT-862..AT-866 carry no regression_check (sweep 1c)","evidence":"qa/issues.jsonl on wave/land-t203-hosting"}
- P6 {"severity":"low","feature":"hosting","title":"HO16 text says redirect to a run page; code redirects 303 to /projects/{slug}/report (the queue panel shows the position). Contract wording to amend together with AT-869","evidence":"src/autotester/ui/routes_runs.py:212"}

## Persona walk (summary)
Tester: a real press on a project with no AI key gives an immediate bare 400 and queues nothing; with the gates stubbed, Run by keyboard -> 303 to report, RUNNING; server cap -> gamma QUEUED #1; same-project presses QUEUED #2-#4; the 5th press gets 429 with the reason; after release gamma flipped QUEUED -> RUNNING by meta refresh in 5.2 s, FIFO held, all ended DONE. Developer: queue panel readable, long reasons wrap on desktop, restart reason shows INTERRUPTED. Console errors: only the two expected 400/429 resource errors; 0 JS errors. Findings are P1, P2, P4 (none high). Re-walk after T-204 (login redirect).

EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: Every in-scope row is MET on its local evidence or PARTIAL on a named half that the contract assigns to T-204, a Linux run, Docker or the server; none is passed beyond its evidence. The merge resolution in routes_runs.py and the submit(run_id) change are covered by the unchanged master test, 297 tests and four falsifications. Findings are low and carried as PROPOSED-ISSUE lines.
Metrics: start=2026-10-10T20:14:48Z end=2026-10-10T20:30:00Z wall_min=15 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=4 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=900 mutants=0 defects_unit=0 defects_6c=0
full-suite trigger: tests/conftest.py edited
