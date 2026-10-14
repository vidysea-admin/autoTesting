# Manifest - t206-rig

**Unit:** T-206 / G10 acceptance rig: `tests/acceptance/rig.py` and the per-criterion local tests TA1-TA14 that `qa/contracts/team-loop-acceptance.md` and `qa/evidence/t206-runbook.md` name. Prerequisite P of the runbook. This manifest does NOT close T-206 (live walks, TA16, TA17 and the close-out manifest `t206-g10-acceptance` remain).
**Contract:** `qa/contracts/team-loop-acceptance.md` (TA1-TA14, TAI1-TAI6); reuses `tests/auth_harness.py`, `team_run_fakes.py`, `delivery_fakes.py`, `drive_fakes.py`, `video_review_fakes.py`, `run_approval_fixture.py`, `zip_fixtures.py`, `conftest.py::serve_dir`.
**Branch / base:** `wave/t206-runbook` on 22eac602; local master merged in fix cycle 3.
Tier: S (test files and evidence only, no `src/`)
Dual check: no
Fix cycle: 5
Executor: claude-sonnet-subagent (maker build subagent)
Code commit (pre-check sha): the commit that adds this file (`git log -1 -- qa/manifests/t206-rig.md`)
Status: ready-for-check

## What changed

| Path | One job |
|---|---|
| `tests/acceptance/rig.py` | the real app over a fresh root, login gate ON, per-role clients (admin, subadmin, dev, tester, pending) created with `accounts.signup` / `set_user_groups` / `set_owner` / `set_relation`, stub product on loopback with a switchable defect, egress guard, seam logs |
| `tests/acceptance/conftest.py` | `cold` (admin + pending) and `world` (full team + stub project) fixtures |
| `tests/acceptance/review_support.py` | intake uploads and the review run with the real approval gate (shared by TA4/5/10/12/13/14) |
| `tests/acceptance/schedule_support.py` | daily schedule on a project and the injected-clock instants (TA8, TA11, TA12, TA13) |
| `tests/acceptance/test_ta01 .. test_ta14` | one file per criterion (TA15 is a live browser walk, TA16/TA17 live artifacts: no file) |
| `qa/evidence/t206-runbook.md` | tags flipped; READY 15 -> 36, BLOCKED 40 -> 19, DEFERRED 4 -> 4; new section 4 |
| `qa/feedback-inbox.md` | eight findings for the checker (appended) |

No `src/` file changed (TAI1: `git diff --stat 22eac602..HEAD -- src/` is empty). No helper duplicated: the only new shared code is the rig, the stub-product grader (the one seam that decides PASS/FAIL from the loopback page) and the two small support modules.

## Verification run by the maker

- `uv run pytest tests/acceptance`: **55 passed, 13 xfailed**, then again with the files in reverse order: same result (TAI3). No full suite.
- `uv run ruff check src tests scripts`: clean. `uv run autotester doctor`: clean (advisory D-087 warnings only, pre-existing).
- No browser, no network, no external site. The only sockets are loopback (stub product, one uvicorn child in `test_ta03`, FakeDrive is in-process).

## Named seams (the closed set TA1 asserts)

Drive client (`routes_intake.drive_factory`), the judge/browser/grader for a run (`BrowserSession` calls and `run_and_grade_case_resilient`, via `team_run_fakes.patch_run_world`, the grader reading the loopback stub page), the model Provider (`RecordingProvider`) with its frame source and probe for the review, the run queue's worker spawner (held jobs), a cheap argon2 hasher, `smtplib` (forbidden), socket connect (guard).

## Fix cycle 2 (verdict cycle 1 FAIL: F1, F2, F3)

- F1: removed the TB7 xfail marks from test_ta07 and test_ta09; both run as real tests and pass. TB15 export also passes once the URL is the real `/tracker/export.csv` (the test used `/tracker.csv`); its xfail removed too.
- F2: every remaining xfail names a pending task or a real D-number (below).
- F3: test_ta03 server fixture /healthz deadline 60 s -> 180 s; assertion unchanged.
- Result: `uv run pytest tests/acceptance`: **58 passed, 10 xfailed**. Ruff clean, doctor clean.

## Remaining xfail(strict=True) tests (10), each with its open blocker

| Test | Blocker |
|---|---|
| TA3 test_dev_presses_test_in_the_server_process (`run=False`) | live walk (runbook TA15) / T-201 TL-5 (pending) |
| TA4 test_tv9_the_flowspec_holds_draft_flows | T-169 (pending) |
| TA5 test_admin_runs_the_review_from_the_source_page | T-169 (pending) |
| TA6 test_c_exactly_one_outbox_message | D-092/D-093 (email deferred to production), T-201 |
| TA6 test_c_the_dev_can_tick_email_me_run_reports | D-093 |
| TA6 test_d_a_raising_transport_leaves_the_verdict | D-092/D-093 |
| TA6 test_tt7_the_inbox_lists_the_report | T-201 (pending) |
| TA8 test_ts1_subadmin_saves_a_schedule | T-200 (pending) |
| TA8 test_ts5_the_schedule_card | T-200 (pending) |
| TA14 test_subadmin_schedules_and_sees_the_next_fire_times | T-200 (pending) |

All are strict=True. TAI2: each must be removed when its task lands; none may remain at T-206 PASS.

## Fix cycle 3 (local master merged: T-199 c/d, T-200 schedule UI, T-201 inbox, proposal review UI, hosting, model chain)

- Became real tests (xfail removed): TT7 `/inbox` (dev and admin list the run, tester does not), TS1 schedule save and tester refusal (owner stored), TS5 schedule card (`/projects/{slug}/schedule`, "Next run"), TA14 subadmin journey. TA8 no-credentials row now assigns the subadmin to `nocred` (the owner guard, HO24, runs before the credential gate and gave `refused`).
- Converted to skip (never pass here): TA6 outbox message, "Email me run reports" tick, raising transport (D-092/D-093, email deferred to production); TA3 server-process Test press (live walk TA15).
- Strict xfail kept (2, genuinely pending): TA4 TV9 and TA5 "Run review" button, both T-169. TAI2: remove when T-169 lands.
- Result forward and reverse file order: **62 passed, 4 skipped, 2 xfailed**. Ruff clean; doctor only the two pre-existing known-disputed warnings.
- Runbook counts: READY 41, BLOCKED 12, DEFERRED 6 (was 36/19/4).

## For the checker to rule on

1. **D-074 vs a rig:** no conflict; D-074's text does not say "evidence only". "Evidence and tests only" is the contract's header and TAI1, which allow `tests/acceptance/**`. Noted in `qa/feedback-inbox.md`.
2. **TAI2 vs the 13 xfails.** The brief required xfail with named blockers; TAI2 says none. Proposed reading in the inbox.
3. **TA12:** the Credentials page shows the value to `credentials.view` holders (admin); exempted for admin only and asserted absent for everyone else. Intended or defect?
4. **Wiring gap:** nothing calls `delivery/` or `bug_run.process_run` from a finished run, so TA6(c)(d) and TA7 are proved at the seam (rig calls `process_run`), not end to end.
5. **Direct writes:** the schedule is set on `project.json` (no save route); `.env` value, the stub project and `approvals`-free credential-derived approval are fixtures. Everything else enters through the app or the repo's account/store functions.

## Fix cycle 4 (TA5 re-examined after T-201 and T-199 closed)

- Those units added no video-review route (`/projects/{slug}/videos/{id}/review` does not exist; `/proposals/review` is case proposals). The TA5 xfail therefore cannot honestly come out without a `src/` change, which the contract forbids; it stays, reason sharpened. Unrelated to T-200 TS5.
- Added a real TA5 test: a tester granted access sees the media, gets no Run control and the review POST is refused, provider calls 0 (TV7 permission). TA5: 4 pass, 1 xfail.

## Fix cycle 5 (rebased on master 09f968d8; wave/run-review-route merged INTO this branch)

- NOTE: `wave/run-review-route` (96a96384) was NOT yet on master (only a branch); it is merged here so the route exists. This unit's own diff stays tests and evidence only; the `src/` lines in `git diff master` come solely from that branch and vanish once it reaches master.
- TA5: xfail removed; `test_admin_runs_the_review_from_the_source_page` posts to the real `/projects/{slug}/videos/{id}/review` (refused 403 with zero calls before approval; 303 and stored review after). TA5 5 pass.
- Result: `uv run pytest tests/acceptance`: 64 passed, 4 skipped, 1 xfailed. Ruff clean, doctor clean.
- Runbook TA17 step 1: AT-891 answered (production); a human-signed production approval is required per run.
- Locally proven: TA1-TA3 (server-process Test press is a live walk), TA4 (except TV9), TA5, TA6 (a,b; email halves skipped), TA7-TA14.
- Still not green, by design: TA4 TV9 xfail (T-169 pending; the analyze route does not create DRAFT flows); skips = TA3 server-process Test press (live walk TA15), TA6 email x3 (DEFERRED TO PRODUCTION D-092/D-093). Live evidence: TA16 (artifact missing), TA17 (needs signed prod approval), TA15 walks, hosted Ubuntu / T-203 host and DNS.
- TAI2 still unmet while the TA4 xfail and the skips stand; checker to rule.
