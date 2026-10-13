# Manifest - t206-rig

**Unit:** T-206 / G10 acceptance rig: `tests/acceptance/rig.py` and the per-criterion local tests TA1-TA14 that `qa/contracts/team-loop-acceptance.md` and `qa/evidence/t206-runbook.md` name. Prerequisite P of the runbook. This manifest does NOT close T-206 (live walks, TA16, TA17 and the close-out manifest `t206-g10-acceptance` remain).
**Contract:** `qa/contracts/team-loop-acceptance.md` (TA1-TA14, TAI1-TAI6); reuses `tests/auth_harness.py`, `team_run_fakes.py`, `delivery_fakes.py`, `drive_fakes.py`, `video_review_fakes.py`, `run_approval_fixture.py`, `zip_fixtures.py`, `conftest.py::serve_dir`.
**Branch / base:** `wave/t206-runbook` on 22eac602.
Tier: S (test files and evidence only, no `src/`)
Dual check: no
Fix cycle: 1
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

## xfail(strict) tests, each with its blocker (13)

TA3 Test press inside the server process (`run=False`: would start a real browser) · TA4 intake to DRAFT flows / "Another possibility" (no offline model-backed analysis) · TA5 "Run review" UI (no route) · TA6 outbox message, "Email me run reports" control, raising transport, inbox (delivery not called from a run; no preference route; no inbox) · TA7 tracker page TB7 · TA8 schedule save route, schedule card · TA9 tracker page, export TB15 · TA14 subadmin schedule journey. When the missing unit lands the strict xfail fails (XPASS) and forces the marker off.

## For the checker to rule on

1. **D-074 vs a rig:** no conflict; D-074's text does not say "evidence only". "Evidence and tests only" is the contract's header and TAI1, which allow `tests/acceptance/**`. Noted in `qa/feedback-inbox.md`.
2. **TAI2 vs the 13 xfails.** The brief required xfail with named blockers; TAI2 says none. Proposed reading in the inbox.
3. **TA12:** the Credentials page shows the value to `credentials.view` holders (admin); exempted for admin only and asserted absent for everyone else. Intended or defect?
4. **Wiring gap:** nothing calls `delivery/` or `bug_run.process_run` from a finished run, so TA6(c)(d) and TA7 are proved at the seam (rig calls `process_run`), not end to end.
5. **Direct writes:** the schedule is set on `project.json` (no save route); `.env` value, the stub project and `approvals`-free credential-derived approval are fixtures. Everything else enters through the app or the repo's account/store functions.
