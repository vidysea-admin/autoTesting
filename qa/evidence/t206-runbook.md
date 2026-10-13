# T-206 acceptance runbook (Group 10 end to end) - prep only

Prepared 2026-10-13 from `qa/contracts/team-loop-acceptance.md` (TA1-TA17, TAI1-TAI6), `docs/plan.md` G10, intent O8-O15, D-074, D-090, D-091.
Evidence only, no `src/` change (TAI1). Nothing here was executed; this is the procedure.
Status tags per step: READY (can run now) / BLOCKED(x) (waits on a task or an Umesh answer) / DEFERRED(x) (Ubuntu, D-090/D-091).

## 0. Facts the steps rely on (state at master 30bb5b03)

- Merged: T-197 (video review), T-198 a/b/c (intake, portal, gate), T-199 a/b (bug-loop core and run), T-200 a/b/wiring, T-201 a/b (delivery core, Test button), T-204 (login), T-205 (launcher). `scripts/serve_windows.ps1` exists (T-203 local).
- NOT in master: a tracker page (`ui/routes_tracker.py`) and the CSV/xlsx export (TB7, TB15); the T-199 task is still `pending`. `tests/acceptance/` and `rig.py` now exist (added on this branch). `projects/pathlynks` exists.
- Roles needed (Umesh answer, none recorded yet): test accounts for `admin`, `subadmin`, `dev`, `tester` (plus `pending`). Create them through the app's own sign-up and admin group screens (the first sign-up is admin, AU7). No password goes in any evidence file.
- Email: sender credentials are ANSWERED (gate `email-sender-credentials.md`, D-081 item 5; AUTOTESTER_SMTP_* in repo `.env`). Open for Umesh: is one real send required, and to which inbox (contract Open 2). Default: no; outbox plus loopback fake SMTP is the PASS evidence.
- Evidence naming: `qa/evidence/t206-<criterion>-*`, persona files `qa/evidence/persona-t206-<type>/persona-walk.md`, browser reports `qa/evidence/browser-t206-<type>-checker/report.json`. Every evidence file is scanned with `uv run python scripts/check_no_secrets.py qa/evidence/t206-*`.
- Common prerequisite P: the maker builds `tests/acceptance/rig.py` and `test_ta*.py` (the contract's own Verify commands). Until then every LOCAL pytest step is READY (rig built; passes locally, see section 4).
- CPU: no browser or full test suite while a hei-sweep A/B measurement window is active.

## 1. Local server for the live steps (TA3, TA15)

1. READY `powershell -File scripts/serve_windows.ps1 -DryRun` (capture to `qa/evidence/t206-ta03-server/dryrun.txt`). Pass: binds 127.0.0.1, data root outside the code tree, auth not disabled.
2. READY `powershell -File scripts/serve_windows.ps1 -DataRoot <fresh temp dir> -Port <free port>` in the background, then the same script with `-Check`. Pass: "healthz ok".
3. DEFERRED(D-090 item 3; HO39/HO40 need a real Scheduled Task install, not required for the local PASS) `scripts/install_windows_task.ps1`.

Never set `AUTOTESTER_AUTH_DISABLED`. Kill only the PID started; record it.

## 2. Criteria

### TA1 - rig is honest (CRITICAL egress half)
1. READY (rig built; passes locally, see section 4) `uv run pytest tests/acceptance/test_ta01_rig_honest.py` -> `qa/evidence/t206-ta01-pytest.txt`. Pass: green; closed seam set listed; egress guard fires on a non-loopback connect.
2. READY (rig built; passes locally, see section 4) Sabotage in a scratch copy only: patch a stage function in one scenario, then drop the guard; both must go red. Capture both outputs.

### TA2 - nothing happens before access (CRITICAL)
1. READY (rig built; passes locally, see section 4) `uv run pytest tests/acceptance/test_ta02_nothing_before_access.py`. Pass: data-root hash byte-identical after the whole-surface sweep as anonymous, `pending`, and forged Origin; seam logs empty.
2. READY (rig built; passes locally, see section 4) Sabotage: public POST route in a copy; flip the sweep to a signed-in `dev` (must go red on "changed").
3. READY (live; the checker creates the accounts on the local server through sign-up and the admin group screen) Live confirmation: admin places dev/subadmin/tester in groups; each next click reaches the default page; project `other` returns 404 for them. Evidence: screenshots under `browser-t206-*`.

### TA3 - real server process
1. READY (rig built; passes locally, see section 4) `uv run pytest tests/acceptance/test_ta03_real_server.py`. Pass: sign-up, sign-in, project, dev Test press, report opens; foreign Host refused; foreign Origin POST refused.
2. READY Start the server per section 1; probe `Invoke-WebRequest http://127.0.0.1:<port>/auth/login` (200) and a POST with `Origin: http://evil.example` (refused). Evidence `t206-ta03-server/probe.txt`.

### TA4 - intake becomes knowledge (O9)
1. READY (rig built; passes locally, see section 4) `uv run pytest tests/acceptance/test_ta04_intake_to_knowledge.py`. Pass: zip (2 videos, 1 doc, 1 hostile member) accounts for every member; 2 sources from the zip plus 1 from Drive each with uploader/time/origin; same bytes register nothing; FlowSpec holds DRAFT flows with `source_id`; a flow only in the video shows as "Another possibility"; `tester` and `pending` are refused.
2. READY (live; accounts as above) Live: sign in as `dev`, open the project, Add videos, upload a small zip of redacted derivative clips only, read the outcome table. Evidence: screenshot plus `autotester video list` output in `t206-ta04-live/`.
3. READY The Drive door is exercised with the fake `DriveClient` only (Drive identity gate answered: gws CLI login). No live Drive call by the checker.

### TA5 - pointer review of an intake source (O8)
1. READY (rig built; passes locally, see section 4) `uv run pytest tests/acceptance/test_ta05_review_of_intake.py`. Pass: summary plus 0-5 items each citing a second; `not_reviewed` spans named; provider log has derivatives only; zero calls when approval is missing.
2. BLOCKED(no review route or screen on master: the review runs from `autotester ingest review` only) Live UI with the fake provider on the stub product (never a real model on a real video): admin opens the source, enters three pointer lines, runs the review, reads the result. Evidence `t206-ta05-live/` (screenshot, review JSON).

### TA6 - Test button to queue/launcher to report, once (O12, O13)
1. READY (rig built; passes locally, see section 4) `uv run pytest tests/acceptance/test_ta06_button_to_report.py`. Pass (a)-(e): one request attributed to dev; second press returns the existing one; launcher log `trigger=button`; exactly one outbox message, to dev; a raising transport leaves the verdict unchanged; missing credential pair refuses with no run directory.
2. BLOCKED(no "Email me run reports" control, no delivery call from a finished run, no inbox on master) Live on the stub product with the defect ON: dev ticks "Email me run reports", presses Test (`POST /projects/{slug}/test`), opens `GET /projects/{slug}/test/{run_id}`; admin (not ticked) sees the report in the inbox but gets no mail. Evidence `t206-ta06-live/` (screenshots, outbox listing with names only).
3. READY Mail path: the test environment points `AUTOTESTER_SMTP_HOST` at 127.0.0.1 (loopback fake SMTP or outbox adapter), never the SES values.
4. BLOCKED(Umesh answer: is a real send required, and which inbox) Optional one real SES message. Default not required (contract Open 2). Never sent by a test or the checker.

### TA7 - failure becomes one bug, closes on evidence (O10)
1. READY (rig built; passes locally, see section 4) `uv run pytest tests/acceptance/test_ta07_failure_to_bug.py`. Pass: one `TrackedBug` with a stable key; second press raises count not a second bug; fixed only after two consecutive passes; INCONCLUSIVE closes nothing; reopen keeps the key; button and schedule failures share a key; reprocessing a run changes nothing; TB7 scoping holds.
2. BLOCKED(T-199 TB7 tracker page not built) Live: dev, subadmin, admin open the tracker page; tester sees a bug only if its report is shared; `other` shows nothing. Evidence screenshots.
3. READY Store-level check after the TA6 run: read `store/bug_store.py` BugStore and save key, count, last_seen, status only to `t206-ta07-bugs.txt`.

### TA8 - schedule fires once through the same launcher (O12)
1. READY (rig built; passes locally, see section 4) `uv run pytest tests/acceptance/test_ta08_schedule_to_report.py` with the injected clock. Pass: nothing before the slot; one enqueue at the slot (`trigger=schedule`, requested_by = owner); a second tick and a second scheduler instance enqueue nothing; `blocked_no_credentials` shows zero transport requests; a busy project gives `skipped_overlap`; `tester` cannot save.
2. BLOCKED(no schedule save route or schedule card on master) Live: subadmin saves a daily schedule on the stub project; the schedule card shows the next three fire times in project timezone; trigger one tick with the tick command documented in `qa/manifests/t200-schedule-wiring.md` (read it at run time); confirm one run and one inbox report. Evidence `t206-ta08-live/`.

### TA9 - tracker (the contract text is the OLD sheet dry run, see proposal 3)
Under D-090 the checks that realise O11 now are TB7 (page) and TB15 (export):
1. BLOCKED(T-199 TB7/TB15 not built) subadmin opens the tracker page; bugs from TA7/TA8 are listed with status, severity, screen.
2. BLOCKED(T-199 TB15 not built) Export CSV and xlsx; read both back; header order equals the Tracker layout; export twice and compare bytes (identical); a user without `report.view` gets not-found; a planted secret in a bug title is absent from both files.
3. BLOCKED(Umesh answer: Tracker sheet header row) Compare the export header to the real Tracker header row. Without it the layout check is against `schema/sheet_plan.py` only.
4. READY Standing limit: after the whole acceptance, `projects/pathlynks/project.json` has no tracker binding with `first_write_confirmed_by`, and no Google call was made. Evidence `t206-ta09-no-live-write.txt`.
5. DEFERRED(D-090 item 2) Sheet bind, mapping confirm, SheetClient write log (original TA9 body), real-sheet export.

### TA10 - share, request access, approve, comment (O14, O15)
1. READY (rig built; passes locally, see section 4) `uv run pytest tests/acceptance/test_ta10_share_to_comment.py`.
2. READY (live; accounts as above) Live: dev creates a share link (`POST /projects/{slug}/videos/{id}/share-link`); tester opens it, sees request-access naming who is asked, never the bytes; dev approves; tester watches and comments at second 42; admin promotes the comment to a pointer; rerun the review and confirm the pointer is included. Evidence `t206-ta10-live/`.

### TA11 - restart keeps the world, repeats nothing
1. READY (rig built; passes locally, see section 4) `uv run pytest tests/acceptance/test_ta11_restart_exactly_once.py`. Pass: canonical dump equal after rebuilding app and stores; re-tick, re-process, re-deliver add nothing.
2. READY Live: stop and restart the section 1 server on the same data root; list users, projects, runs, bugs, inbox (counts and ids only) before and after. Evidence `t206-ta11-restart.txt`.

### TA12 - no secret or product data leaks (CRITICAL)
1. READY (rig built; passes locally, see section 4) `uv run pytest tests/acceptance/test_ta12_no_leak.py`.
2. READY Run last: `uv run python scripts/check_no_secrets.py qa/evidence/t206-*`. Pass: OK; no student datum or credential in the pack.

### TA13 - zero egress, exact spend (CRITICAL)
1. READY (rig built; passes locally, see section 4) `uv run pytest tests/acceptance/test_ta13_zero_egress.py`. Pass: no non-loopback connect; provider call counts as expected; mail via outbox or loopback SMTP; Drive client fake.
2. READY During the live walks, record the server process's outbound connections (`Get-NetTCPConnection -OwningProcess <pid>`). Pass: loopback only. Evidence `t206-ta13-netstat.txt`.

### TA14 - each user type completes the goal; dead ends explain themselves
1. READY (rig built; passes locally, see section 4) `uv run pytest tests/acceptance/test_ta14_journeys_and_dead_ends.py`.
2. READY for the dead ends that exist (the stale-mapping row is removed by D-090, proposal 3) Live spot checks: 413 over-limit names the limit, non-video member named, no credentials names the Credentials page, double press shows the existing request, no-access page, waiting page, last-admin removal refused. Evidence screenshots.

### TA15 - persona walks in a live browser (Mode D)
Checker's own browser against the section 1 server; BLOCKED-CAPABILITY if no browser tool connects, never curl.
1. BLOCKED("Email me run reports" control not built) dev: add videos <= 3 steps; Test <= 3 steps; finds "Email me run reports" unaided. Files `persona-t206-dev/persona-walk.md`, `browser-t206-dev-checker/report.json`. Pass: no `high` finding, zero unexplained console errors, labelled keyboard-operable controls, masked secret inputs.
2. BLOCKED(no review UI on master) admin: review with pointers <= 4 steps; approve access <= 2; names the unreviewed spans unprompted. Files for `persona-t206-admin`.
3. READY (live; accounts as above) tester: reaches the shared video <= 3 steps from the mail link, comments at a second, sees nothing else. Files for `persona-t206-tester`.
4. BLOCKED(schedule UI and T-199 tracker not built) subadmin: schedule <= 3 steps with the next three fire times shown. The "bind a sheet in <= 5 steps" part is DEFERRED(D-090 item 2), see proposal 4.
5. DEFERRED(D-091; hosting HO34) Repeat the walks against the Ubuntu server URL.

### TA16 - redacted-video review vs the oracle (O8; LIVE-ARTIFACT)
1. BLOCKED(artifact missing: `qa/evidence/t206-review-live/recall.json` does not exist) The owner or maker produces it from the already-approved review of `src_e8fcdc4a15ce`, `src_44e2f1f6c64c`, `src_8540cc84081e` (D-067): redaction windows, provider request log (derivatives only), k of 13 high-severity oracle rows with each missed id, unconfirmed count, time-to-review, `not_reviewed` spans. Wording "measured on 3 videos", no threshold. Missing means HELD, not failed.
2. READY (once the file exists) `uv run python scripts/check_deliverable.py --exists qa/evidence/t206-review-live/recall.json`; re-derive k and the unconfirmed count from the id lists against `.work/pathlynks-dev-videos-oracle-2026-10-07.md` (local read only, gitignored). `scripts/score_video_issues.py` may do the arithmetic. No model call.

### TA17 - one Test press and one schedule tick on Pathlynks (LIVE-ARTIFACT)
1. BLOCKED(AT-891: is pathlynks.vidysea.com recorded as production in the approval; D-084 item 3) Every step below waits on this.
2. BLOCKED(AT-891) `uv run python scripts/check_crawl_approval.py pathlynks` exits 0; read the per-run approval row for each T-206 run.
3. BLOCKED(AT-891; T-145 Pathlynks report still pending) dev presses Test on Pathlynks with the `PATHLYNKS_USER_*` test account; report in the inbox; outbox message for a ticking user.
4. BLOCKED(AT-891; Umesh answer: clone project `pathlynks-acceptance` or the real project, contract Open 4) Schedule tick; one enqueue; report; bug rows.
5. BLOCKED(AT-891) Attribution audit (`requested_by` equals the signed-in dev). Run safety: test account only, runs serialised, one signed approval each, no tracker write; rerun `check_no_secrets.py`.

### Invariants
- TAI1 READY `git diff --stat 30bb5b03..HEAD -- src/` is empty at close.
- TAI2 BLOCKED(ruling needed: TAI2 forbids xfail, but the 13 xfail(strict) tests each name a missing-piece blocker, as the brief for this unit required; see manifest) `grep -rnE "xfail|skip\(|skipif|importorskip" tests/acceptance` finds nothing.
- TAI3 READY (rig built; passes locally, see section 4) `uv run pytest tests/acceptance` twice, once in reverse order.
- TAI4 READY `uv run autotester doctor` and `uv run ruff check src tests scripts`.
- TAI5 READY pathlib/no POSIX-only check by grep of `tests/acceptance` once it exists; the Ubuntu leg is DEFERRED(D-091).
- TAI6 READY Re-check that the cited unit ids still exist at close.

### Close-out
1. BLOCKED(all of the above) Manifest `qa/manifests/t206-g10-acceptance.md` to `ready-for-check`; checker verdict `qa/verdicts/t206-g10-acceptance.md`; `goal_cli done --task-id T-206`. The goal `done_check` names `t-206-g10-acceptance.md` (with a hyphen), a mismatch the contract already records.
2. DEFERRED(D-090 item 3, D-091) Hosted Ubuntu check (HO34-HO36, TA3/TA15 against the URL), as its own goal row.

## 3. Feedback-inbox proposals (contract not edited; for the maker to append to `qa/feedback-inbox.md`)

1. TA1 seam list. Replace `SheetClient (fake, call log, no delete method)` with the T-199 export module. Reason: D-090 item 2 builds an internal tracker plus CSV/xlsx export with no `SheetClient` use (TB15).
2. TA3 start command and AU24. TA3 cites HO11 (documented start command) and AU24; both are DEFERRED TO UBUNTU (D-090, D-091). Proposed: the literal command is `scripts/serve_windows.ps1` (HO39-HO46) and AU24 is dropped from `serves:`.
3. TA9 rewrite and its echoes. TA9 (bind a fake SheetClient, mapping confirm, write log, TB8-TB13) is a real-sheet flow deferred by D-090 item 2; TB8/TB9/TB10/TB13 bind at the later real-sheet export. Proposed TA9 = TB7 page plus TB15 export (CSV and xlsx header order, identical bytes on re-export, `report.view` scoping, planted-secret absence, `LiveWriteRefused` still raised) plus the standing no-binding limit. Echoes to amend: TA11 "re-sync the sheet" becomes "re-export gives identical bytes"; TA12 "fake sheet's write log and plan" becomes "export files"; TA13 "sheet client is the fake class" becomes "no sheet client is constructed"; TA14 "stale mapping blocks writes" is removed.
4. TA15 subadmin walk. "bind a sheet in <= 5 steps with the exact first write shown before confirm" is deferred (D-090). Proposed: "find the tracker and export it in <= 3 steps".
5. Held and Open items. "Hosted check on Ubuntu" is DEFERRED (D-090 item 3, D-091) and should be its own goal row (Open 3 default). Open 5 (test sheet in Drive) is moot under D-090 item 2. Open 3 second half: T-199's `done_check` should be amended to the export scope, since the dry-run and first-live-write scope is superseded. Open 1 (AT-891) and Open 2 (real email) stay open.
6. TAI5. "Ubuntu leg is the hosted check" should say DEFERRED(D-091), not part of the local PASS.


## 4. Status after the rig was built (2026-10-13)

Step counts (numbered steps and TAI rows above): READY 36, BLOCKED 19, DEFERRED 4. Before the rig: READY 15, BLOCKED 40, DEFERRED 4.

`uv run pytest tests/acceptance`: 55 passed, 13 xfailed (strict), run forward and in reverse file order. Each xfail names its blocker in its `reason`:
- no delivery call from a finished run, no "Email me run reports" control, no inbox route (TA6 c, d, TT7);
- T-199 tracker page and CSV/xlsx export not built (TA7 TB7, TA9);
- no schedule save route and no schedule card (TA8, TA14);
- no review route or screen, the review runs from the CLI (TA5);
- turning an intake source into DRAFT flows needs a model-backed video analysis (TA4 TV9, RC10);
- a Test press inside the separate server process would start a real browser (TA3, `run=False`).
Not rig-testable at all: TA16 (artifact missing) and TA17 (AT-891).
