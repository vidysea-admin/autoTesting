# Verdict - t206-rig
Cycle checked: 1
Verdict: FAIL
Head checked: 3ee8202b (ea25d946 + master merge; only qa/feedback-inbox.md conflicted, both sides kept)

## Rulings
1. D-074 text is items (a)-(e) and says nothing of "evidence only"; the rule is the contract header and TAI1, which allow `tests/acceptance/**`. A test rig is allowed. `git diff --stat 22eac602..HEAD -- src/` is empty.
2. TAI2 amended (contract folded): strict xfail only while the named task id is still pending (or a D-number defers the row); no xfail may remain at T-206 PASS.
3. Credentials page: `routes_credentials.py` renders stored values only when `show_values` (credentials.view, AU21/D-034, admin by default); everyone else sees set/not set. That is the approved design, not a defect, and the CLAUDE.md boundary (no value in prompt/log/screenshot) is not breached by the page. TA12 amended: admin credentials pages exempt from the page-body canary scan, never screenshotted or copied into evidence. No issue logged.

## Findings
- F1 (blocking): master now has `ui/routes_tracker.py` (T-199 TB7). Run on the merged tree: `test_ta07 ...::test_tb7_dev_subadmin_admin_see_the_tracker_tester_only_shared_other_nothing` and `test_ta09 ...::test_tb7_subadmin_opens_the_tracker_page_and_sees_status_severity_screen` XPASS(strict) = FAILED. Remove the marker and make them pass; re-check TB15 export too.
- F2 (blocking): xfail reasons on TA3 (`run=False`), TA4 and TA5 name no pending task. Name one (or a D-number) or turn the row into a DEFERRED/live-walk note (TA3 is really a live-walk item). TA6/TA8/TA14 reasons cite T-200/T-201 mostly; TA6 email rows are deferred by D-092/D-093, so cite those, not "blocked".
- F3 (TAI3): `test_ta03_real_server.py::test_a_foreign_host_and_a_foreign_origin_post_are_refused` ERRORED (server fixture 60 s /healthz deadline) under CPU load from the live Chrome worker; widen to 180 s.
- OK: reuses auth_harness/team_run_fakes/delivery_fakes/drive_fakes/video_review_fakes; roles created via accounts/set_relation; sockets loopback (127.0.0.1); sleeps bounded; no file over 300 lines.

## Ran
`uv run pytest tests/acceptance` on merged tree: 54 passed, 11 xfailed, 2 failed (F1), 1 error (F3), 328 s. Reverse-order, ruff and doctor runs were still queued behind the loaded CPU and are not counted.

---
# Cycle 6
Cycle checked: 6
Verdict: FAIL (single blocker: TAI2 skips; TA4 re-run owed after TV9 fix cycle 2 lands)
Head checked: bc0ee74a (detached worktree, PYTHONPATH=worktree src, import path verified)

## Rulings
1. TAI1: `git diff master -- src` is noisy (6 files) only because the branch is behind master. `git diff master...HEAD -- src` is exactly the TV9 commit a5b7621b: `stages/analysis_flows.py` (+49) and `ui/routes_sources.py` (+2). The rig adds no product code of its own. Acceptable on condition TV9 merges first: once it is on master the three-dot diff is empty. Until then TAI1 holds only transitively; re-check after TV9 lands.
2. TA1 seam: `monkeypatch.setitem(providers._REGISTRY, "mock", ...)` plus project vision = "mock" is the model Provider seam the contract names ("the model Provider (fake, request log)"), not patching an `autotester.*` callable: no function is replaced, the project config selects a registry id and the fake instance is returned for it. It is the same seam by a different door than `routes_runs.for_role`. "mock" is already registered, so naming it in project config needs no patch for default responses; the patch is only to inject a scripted MockProvider with a request log. Acceptable. Nit (non-blocking): the TA1(a) AST test only inspects `setattr` string targets, so `setitem(providers._REGISTRY` is invisible to it; add it to CLOSED_SEAMS handling so the closed set is real.
3. TAI2: FAIL as worded. `grep -E "skip\(|skipif|importorskip"` matches 4 `@pytest.mark.skip` (TA3 server-process Test press; TA6 email x3). TAI2 permits only strict xfail naming a pending task or D-number; it has no allowance for skip, and a decision-deferred or live-only row is not exempt. What satisfies it: delete those 4 test functions from tests/acceptance and carry them as DEFERRED / live-walk rows in the runbook (TA15 walk; D-092/D-093 email), as the cycle 1 ruling said; or the Approver amends TAI2 to allow decision-cited skip. The checker does not self-amend a relaxation.
4. Locally proven: TA1-TA14 each have a green LOCAL test. TA4 is green only against the old TV9 (a5b7621b); re-run after TV9 cycle 2 (1b81a133) merges. TA15 is live-walk, not local. TA6 email half and TA3 server-process Test press are not proven.

## Ran
tests/acceptance + test_analysis_flows + test_ui_sources: 77 passed, 4 skipped, 0 failed, 90 s. ruff: clean. doctor: rc 0. `git merge-tree master HEAD`: clean, no conflicts. Reverse-order/second run not repeated this cycle (TAI3 unchanged since cycle 5).

---
# Cycle 7
Cycle checked: 7
Verdict: PASS (rig, local part). Task-level T-206 NOT closed.
Head checked: 8b0f95ef (based on 502feb93; master is now 93d6eb1a, merge-tree against it is clean)

## Rulings
1. TAI1: `git diff master...HEAD -- src` is empty. TAI2: grep for skip/skipif/importorskip/xfail in tests/acceptance finds nothing; the 4 skips are deleted and carried as runbook rows (TA3 LIVE-WALK for TA15; TA6 email DEFERRED, D-092/D-093).
2. The strict xfail in tests/test_analysis_flows.py (TV9 clause 2, expand over DRAFT, D-073/R5) is outside tests/acceptance, so TAI2 does not bind it, and it names a D-number that defers it. It does not block the rig PASS and TA4 does not depend on it. It is TV9's own held item, not T-206's.
3. TAI3: acceptance suite green three ways: normal 79-run combined, second run 65 passed, reverse file order 65 passed.

## Ran
acceptance + analysis_flows + ui_sources: 79 passed, 1 xfailed. acceptance alone twice: 65 passed each; reverse order: 65 passed. ruff clean, doctor rc 0.

## Remaining for task-level T-206
TA15/TA16/TA17 live evidence (incl. TA3 server-process Test press), hosted Ubuntu check (TAI5), the email rows once D-092/D-093 lift, and TV9 clause 2 on its human gate (Umesh).
