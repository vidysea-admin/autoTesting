# Contract — team-loop-acceptance: Group 10 end to end on a local deployment (G10, `t206-g10-acceptance`)

**Covers:** unit G10 `t206-g10-acceptance` (goal task T-206); closes AT-855 (the unit had no contract). Evidence and tests only (D-074): no `src/` change.
**Owner:** /checker. **Status:** ACTIVE (2026-10-12). Creation of a contract is human-approved under the checker skill; this file is
**PROPOSED until Umesh's one-time approval** (maker START rule), and it is buildable only once every predecessor is merged (`qa/QUEUE.md` `after:` list).
**Criticality:** CRITICAL (goal task). TA2, TA8, TA12 and TA13 are CRITICAL rows (access, the outward-facing limits, secrets, egress).
Tier is set by the diff (test files plus evidence = S); a checker may raise it only with a cited trigger (policy). No dual check: this unit
writes no security, auth or production-write code; the guards it exercises are dual-checked in their own units.
**Serves:** `docs/features/team-loop/intent.md` O8-O15 (and O6 only as an input, see Out of scope); `docs/spec.md` R32-R65; D-072, D-074, D-081, D-083.
**Depends on (cite, never restate):** `team-foundation.md` TF1-TF8 · `team-video-review.md` TV1-TV10 · `team-intake.md` TI1-TI11, TP1-TP6 ·
`team-bug-loop.md` TB1-TB14 · `team-schedule.md` TS1-TS7 · `team-test-button.md` TT1-TT9 · `auth.md` AU1-AU27 · `hosting.md` HO16-HO33 ·
`reconcile.md` RC10 · `consent.md` · `core-invariants.md` C5, C7, C9, C12.

## What this contract is, and is not

Each unit contract proves its own piece, with the neighbours faked. Nobody has proved that the pieces **compose**: that a video a developer
uploads becomes a review an admin reads, that the run a tester's colleague starts becomes a bug, a report and one email, that a schedule and
a button feed the same bug, and that a person who is not signed in or not in a group changes nothing anywhere. This file judges that, once,
on one deployment, per user type. It adds **no behaviour** and **restates no unit criterion**: where a unit row already owns a fact, the row
below cites it and asserts only the seam (the same object flowing through two units, or the same side effect counted across all of them).
A seam failure is filed against the unit that owns the failing side; it is never patched here (TAI2).

## Vocabulary (fixed so criteria are falsifiable)

- **The rig** = `tests/acceptance/rig.py` (helper module, imported by tests only). It starts the **real** `autotester.ui.app:app` (the same
  object the server serves) over a fresh temporary data root with auth ON (`AUTOTESTER_AUTH_DISABLED` unset), one HTTP client per user with its
  own cookie jar and the `Origin` header a browser sends. **State enters only through the app's own routes and CLI** (sign up, upload, press,
  save, confirm); the rig never writes users, sources, runs, bugs, schedules or inbox rows into the data root itself. The only direct writes are
  the gitignored `.env` fixture values and the stub product.
- **Seams** (the only things faked, each recording every call): the model `Provider` (fake, request log), `DriveClient`/gws runner (fake),
  the T-199 export module (CSV/xlsx files; no sheet client, TB15, D-090), the mail transport (outbox adapter; the in-process fake SMTP server on loopback is DEFERRED TO PRODUCTION with email, D-092 item 1), an
  injected clock and timezone table for the scheduler, and a **stub product** on loopback (a static site under `tests/fixtures/` served by
  `serve_dir`, or one under `tests/acceptance/`) with **one defect that a test switches on and off**. Nothing between the HTTP surface and a
  seam is replaced.
- **World** = the rig plus the people: `admin` (first account, local-dev rule AU7), `subadmin`, `dev`, `tester`, a fifth account with no group
  (`pending`), and the four default groups (AU11). A second project `other` assigned to nobody the scenarios use, to prove absence.
- **Canaries** = a secret canary (a recognisable string placed in the `.env` fixture as the provider key, the stub product's test password,
  the SMTP password and the sheet id) and a page canary (a recognisable string in stub-product page text that stands for product or student data).
- **Egress log** = every socket connect the process makes; a connect to a non-loopback address raises and is logged (TA1).
- **Class:** `LOCAL` = the checker re-runs it itself, no network, no cost. `LIVE-ARTIFACT` = the evidence comes from a run the owner or the maker
  made under an approval; the checker audits the artifacts and their provenance and **never starts a live run or a model call itself**.
  `SERVER-GATED` = needs the real host; listed under Held and not required for the local PASS.

## Criteria — A. The rig and the front door

- **TA1 — The rig is honest (CRITICAL for the egress half).** (a) No scenario test patches an `autotester.*` callable except the named seams
  (the grep/AST test lists the closed set); (b) the app under test is imported as `autotester.ui.app:app`, not rebuilt; (c) auth is ON; (d) the
  setup writes nothing to the data root except through the app's routes/CLI; (e) the egress guard works: an attempted connect to a
  non-loopback address raises and appears in the log. A rig that fakes the unit it claims to test, or whose guard cannot fire, makes every
  later row vacuous (C12). `serves:` intent#O7, C7, C12. *Class LOCAL. Verify:* `uv run pytest tests/acceptance/test_ta01_rig_honest.py`.
  *Sabotage:* in a copy, `monkeypatch.setattr` a stage function inside one scenario module, row (a) goes red naming the file; remove the guard
  installation, row (e) goes red.

- **TA2 — Nothing happens before access (CRITICAL).** With the world in its cold state, snapshot a canonical hash of the data root and the call
  logs of every seam. Then, as anonymous and as `pending` (signed up, no group), and again with a forged `Origin`: send **every state-changing
  Group 10 route** (enumerated from `app.routes` for the Group 10 prefixes: intake, review, pointers, test, schedule, tracker, binding, share,
  access requests, comments, profile) with plausible bodies. After the sweep the data-root hash is **byte-identical**, every seam log is empty,
  and no run directory, source, inbox row, outbox file, queue entry or slot record exists. The `pending` account sees only the sign-in and
  "waiting for access" screens (AU6, AU16). Then the admin puts `dev`, `subadmin`, `tester` in their groups and assigns the project; each user's
  **next click** reaches their default page, and `other` stays absent for `dev`, `subadmin` and `tester` (404, AU13). Per-route verdicts belong to
  AU14, TI10, TT1, TS1 and TP4; this row is the **whole-surface state diff** that no per-route table can show. `serves:` intent#O15, O7,
  spec R63, R64, `auth.md` AU6, AU12-AU14, AU16, AU18. *Class LOCAL. Verify:* `uv run pytest tests/acceptance/test_ta02_nothing_before_access.py`.
  *Sabotage:* in a copy, add one Group 10 POST route to the public set (or drop its session dependency), the hash comparison goes red and
  names the route; flip the sweep to a signed-in `dev` and the same test must go red on the "changed" side (proves the diff can see a change).

- **TA3 — The deployment under test is a real server process, not only an in-process app.** Using the local start command, the literal `scripts/serve_windows.ps1` (`hosting.md` HO39-HO46; HO11 is DEFERRED TO UBUNTU, D-090 item 3, D-091), start the server on a free loopback port over a
  fresh temporary data root and replay the core path over real HTTP with real `Host` and `Origin` headers: sign up the first account (admin),
  sign in, create a project, sign up `dev` and have the admin place them in a group, `dev` signs in and presses Test on the stub product
  (TA5's run), and the report opens. A request with a foreign `Host` is refused and one with a foreign `Origin` on a POST is refused (AU18,
  AU19). The checker kills only the PID it started and records it. Data root and logs are removed afterwards. `serves:` intent#O15, O13,
  `hosting.md` HO10, HO39-HO46, `auth.md` AU18, AU19 (AU24 is deferred to Ubuntu, D-091). *Class LOCAL (Windows). Verify:* `uv run pytest tests/acceptance/test_ta03_real_server.py`.
  *Sabotage:* in a copy, give the start command a wrong module path, the test goes red on "server did not answer /auth/login", not on a timeout
  alone; drop the Host allow-list, the foreign-Host assertion goes red.

## B. The chain, in the order a team uses it

- **TA4 — Intake becomes knowledge, with no approval step, from both doors.** `dev` (assigned) adds videos by (a) a zip of two videos, one
  document and one hostile member, and (b) a pasted Drive link served by the fake `DriveClient`. The outcome table accounts for every member
  (TI3, TI5); two sources are registered from the zip and one from Drive, each with uploader, time and origin (TI11); the same bytes added again
  register nothing new (TI4). Without any human approval, the ingest path runs and the project's FlowSpec holds the video flows as `DRAFT` with
  their `source_id` (TV9), `expand` generates cases from them, and the generated report lists a flow that exists only in the video as an
  **"Another possibility"** item (RC10), not an error. `tester` and `pending` cannot upload (TI10). The same source is the one the review
  (TA5) and the share link (TA9) use later. `serves:` intent#O9, O3, spec R39-R42, R37, `team-intake.md` TI3-TI5, TI10, TI11,
  `team-video-review.md` TV9, `reconcile.md` RC10. *Class LOCAL. Verify:* `uv run pytest tests/acceptance/test_ta04_intake_to_knowledge.py`.
  *Sabotage:* in a copy, make the Drive branch register through a different function that omits `origin`, the origin assertion goes red; add a
  review-approval requirement to the ingest call, "no approval step" goes red.

- **TA5 — A pointer review of an intake source returns a traced confirm-list.** `admin` opens a registered source from TA4 (one from each door)
  and runs a review with three pointer lines using the fake `Provider`. The result has a summary and 0-5 items, each citing a second inside the
  video (TV3, TV4), names the stretches nobody looked at (TV2), and quotes narration only verbatim (TV5). The provider request log shows
  only redacted derivatives and that the per-use approval was checked before the first call (TV7); with the approval missing the call count is
  zero. `tester` can read a stored review once the video is shared and has no Run control (TV7 permission). Rows above are unit-owned; this row
  asserts they hold for a source that arrived through **intake**, not through a hand-registered fixture, and that a review ran on a source
  registered by someone other than the reviewer. `serves:` intent#O8, spec R32-R38, `team-video-review.md` TV2-TV5, TV7.
  *Class LOCAL. Verify:* `uv run pytest tests/acceptance/test_ta05_review_of_intake.py`. *Sabotage:* in a copy, let the review read the
  original path instead of the derivative, the provider-log assertion goes red; remove the approval check, the zero-call assertion goes red.

- **TA6 — The Test button runs the real queue and launcher and the report reaches the right people, once.** With the defect ON, `dev` (who ticked
  "Email me run reports") presses Test on the stub project; `admin` has not ticked. (a) One run request exists, attributed to `dev` from the
  session; a second press returns the existing request (TT2, TT3). (b) The run goes through the T-203 queue and the single launcher (one call
  site; the launcher log shows `trigger=button`, TF1, TT4, TT5), the case fails, and the report opens for `dev` and `admin` and is absent for
  `tester` and `other`'s members (TT7). (c) The label in the inbox and the report page is the same stored value (TT7). **DEFERRED TO PRODUCTION (D-092 item 1):** the outbox half of (c) (exactly one message, to `dev`, none to `admin`, the same label in the message; TT8) and (d) (a raising mail transport leaves the verdict unchanged; TT9) are not judged for T-206; the website inbox entry for `dev` and `admin` still is. (e) The stub product's credential pair is declared, so no second approval prompt appears (D-068); with the
  pair removed the press is refused naming the Credentials page and leaves no run directory (TT6). `serves:` intent#O13, O12, spec R54, R56-R60,
  `team-test-button.md` TT2-TT9, `team-foundation.md` TF1, `hosting.md` HO16, HO25-HO29. *Class LOCAL. Verify:*
  `uv run pytest tests/acceptance/test_ta06_button_to_report.py`. *Sabotage:* in a copy, read the recipient from the form body, a forged
  `to=` shows up in the outbox and (c) goes red; send to every project member, (c) goes red on "none to admin".

- **TA7 — A failure becomes one bug, whichever door it came through, and closes on evidence.** From TA6's failing run: exactly one `TrackedBug`
  exists with the stable key (TB1). A second button press (defect still ON) updates that bug (count 2, `last_seen`), not a second one. Switch the
  defect OFF: after one passing run the bug is still open, after the second consecutive passing run it is `fixed` listing the closing run and
  verdict ids (TB2, TB4); an INCONCLUSIVE run in between closes nothing (TB3). Re-open the defect: the same key is `reopened`. A **scheduled**
  failure (TA8) and a **button** failure of the same case share the one key. Processing a run twice changes nothing (TB6). `dev`, `subadmin` and
  `admin` see the tracker; `tester` sees a bug only if its evidence report is shared with them; `other` shows nothing (TB7). `serves:`
  intent#O10, spec R43-R46, `team-bug-loop.md` TB1-TB4, TB6, TB7. *Class LOCAL. Verify:*
  `uv run pytest tests/acceptance/test_ta07_failure_to_bug.py`. *Sabotage:* in a copy, derive the key from the run id, the second press opens a
  duplicate and the single-bug assertion goes red; count INCONCLUSIVE as a pass, the "closes nothing" assertion goes red.

- **TA8 — A schedule fires once, through the same launcher, and feeds the same bug and the same inbox.** `subadmin` saves a fixed daily schedule
  on the assigned project (UTC, TS1, HO22). With the injected clock before the slot a tick enqueues nothing; at the slot one tick enqueues one
  entry (`trigger=schedule`, `requested_by` = the schedule owner); a second tick and a tick from a second scheduler instance enqueue nothing
  (TS2, HO23); a restart between two ticks of the same slot still fires once (TA11). The run executes through the queue and the launcher
  recorded in TA6 (TS6), its failure updates TA7's bug (count +1, same key) and its report lands in the owner's website inbox (the email copy for an owner who ticked is DEFERRED TO PRODUCTION, D-092 item 1). A project without a credential pair records `blocked_no_credentials` with **zero** requests at the transport and shows the slot
  on the schedule card (TS5). A second, busy project's slot is `skipped_overlap` (TS4). `tester` cannot save a schedule (TS1). `serves:`
  intent#O12, O13, O10, spec R51-R55, `team-schedule.md` TS1, TS2, TS4-TS6, `hosting.md` HO22-HO24. *Class LOCAL. Verify:*
  `uv run pytest tests/acceptance/test_ta08_schedule_to_report.py`. *Sabotage:* in a copy, let the tick call the executor directly, the
  launcher-log assertion goes red; key the marker on the wall clock at tick time, the second-tick assertion goes red.

- **TA9 — The internal tracker and its export; no sheet is bound or written (CRITICAL; rewritten per D-090 item 2, D-092).** The bugs of TA7 and TA8
  are the data. `subadmin` opens the TB7 tracker page and exports it (TB15): CSV and xlsx hold the current `TRACKER_COLUMNS` header names in order
  (D-092 item 3: matching the real sheet is fixed at real-sheet export time), the cell values match the bugs, re-exporting the same set yields
  identical bytes, a user without `report.view` gets not-found, a planted secret in a bug title is absent from both files, and `LiveWriteRefused`
  is still raised by the live path. TB8, TB9, TB10 and TB13 bind at the later real-sheet export and are not judged here. **The standing limit:** no real sheet is contacted (TA13), and after the whole acceptance
  `projects/pathlynks/` holds no tracker binding with a confirmed first write (`first_write_confirmed_by` absent or null) — the first live write
  stays the HUMAN_GATE of D-081 item 7. `serves:` intent#O11, O10, O7, spec R47-R50, `team-bug-loop.md` TB7, TB15. *Class LOCAL. Verify:*
  `uv run pytest tests/acceptance/test_ta09_tracker_export.py` (it also reads `projects/pathlynks/project.json` and asserts the binding clause).
  *Sabotage:* in a copy, reorder one export column, the header-order assertion goes red; construct a sheet client in the export path, TA13 goes red.

- **TA10 — Share, request access, approve, comment: the tester's whole loop, and the comment reaches the review.** `tester` opens the share
  link of `dev`'s video after signing in and sees the request-access page naming who will be asked, never the bytes (TP1, TP3). The request
  reaches `dev` (owner, scope `own`) and `admin`, not `tester` and not `subadmin` of another project (TP5). `dev` approves; the next click of
  `tester` shows the video; `tester` comments at second 42; `dev` and `admin` see the comment at 42 and a user without access does not (TP2).
  `admin` promotes the comment to a pointer, the comment stays, and TA5's review run now includes that pointer (TP6 into TV2). `serves:`
  intent#O14, O15, O8, spec R61-R63, `team-intake.md` TP1-TP3, TP5, TP6. *Class LOCAL. Verify:*
  `uv run pytest tests/acceptance/test_ta10_share_to_comment.py`. *Sabotage:* in a copy, approve by the requester's own id, the "request reaches
  the owner, tester cannot self-approve" assertion goes red; drop the promoted pointer from the review input, the review-includes-pointer
  assertion goes red.

## C. Across the whole loop

- **TA11 — Restart keeps the world and repeats nothing.** After TA4-TA10, build a new app and store objects on the same data root (what a
  process restart does) and compare a canonical dump (users, groups, assignments, sources, reviews, runs, bugs, schedule markers and records,
  inbox rows, delivery records, shares, access requests, comments, bindings, settings): equal. Then tick the same slot, re-process the last run,
  re-export the tracker and re-deliver: **no new run, no second bug row, identical export bytes, no second inbox row** (an outbox message count applies only once email is built, D-092 item 1). A run that was
  queued and not started at the moment of the restart is either resumed once or shown as interrupted, never lost silently (HO4 owns the
  mechanism). `serves:` intent#O12, O10, O13, spec R52, R65, `hosting.md` HO4, HO23, `team-bug-loop.md` TB6, TB11. *Class LOCAL. Verify:*
  `uv run pytest tests/acceptance/test_ta11_restart_exactly_once.py`. *Sabotage:* in a copy, keep the slot marker in memory only, the
  no-new-run assertion goes red; clear the processed-run marker on start, the single-bug assertion goes red.

- **TA12 — No secret and no product data leaves where it must not (CRITICAL).** After TA2-TA11, the secret canary is absent from: every file
  under the data root, the outbox (if present), the export files, the provider request log, the captured application log, stdout and
  stderr, every page body the rig fetched (except the credentials pages when fetched by an account holding `credentials.view`, which AU21 and D-034 show by design; those pages are never screenshotted or copied into `qa/evidence/t206-*`, and the same page fetched by every other role must not contain it), and `qa/evidence/t206-*`. The page canary is absent from the outbox (if present) and the export files (it may appear
  in the provider log only where TV7's redaction and approval allow the page text to go). `uv run python scripts/check_no_secrets.py` over
  `qa/evidence/t206-*` and the manifest reports OK. No student data and no credential value is in the evidence pack. `serves:` intent#O7,
  `core-invariants.md` C5, spec R16, R36, `team-test-button.md` TT9, `team-bug-loop.md` TB13. *Class LOCAL. Verify:*
  `uv run pytest tests/acceptance/test_ta12_no_leak.py` and `uv run python scripts/check_no_secrets.py qa/evidence/t206-*` (the checker passes
  the evidence files explicitly). *Sabotage:* in a copy, write the SMTP password into one outbox header, the canary scan goes red naming the
  file; write the page canary into one sheet cell, the page-canary assertion goes red.

- **TA13 — Zero egress, and the spend is exactly what the scenario implies (CRITICAL).** Over the whole run the egress log has **no** connect to a
  non-loopback address: no real SMTP host, no Google host, no model API host, no Pathlynks host. Provider call counts per scenario equal the
  expected number (review: the planned frames and no more, bounded by TV7's cap; every other scenario: zero except the fake judge/expansion
  calls the pipeline makes, each counted and listed). No mail transport other than the outbox adapter is used (D-092 item 1), no sheet client is constructed (D-090 item 2), the Drive client is the fake class. `serves:` intent#O7, spec R36, R59, `core-invariants.md` C5, C12. *Class LOCAL.
  Verify:* `uv run pytest tests/acceptance/test_ta13_zero_egress.py`. *Sabotage:* in a copy, add one `urllib.request.urlopen("https://example.com")`
  on the delivery path, the egress assertion goes red naming the host; raise the review frame cap, the spend assertion goes red.

- **TA14 — Each user type completes the goal the intent gave them, and each stated dead end explains itself.** Over the world, as HTTP journeys
  (clicks counted later in TA15), for every user type: `dev` — Add videos, then Test, then report; `tester` — share link, watch, comment;
  `subadmin` — schedule, then find the tracker and export it; `admin` — review with pointers, approve access. Then every negative path that
  `docs/spec.md` lists per user type yields the stated page or message, never a blank page, a 500 or a stack trace: over-limit upload names the
  limit (413); a non-video member is named; Drive permission denied names the sharing step; no credentials names the Credentials page; a Test
  press while queued shows the existing request; no access shows request-access and says who is asked; signed up but no group shows the waiting
  page; an unassigned project is absent; `skipped_overlap`, `blocked_no_credentials` and a stale scheduler are visible on the schedule card; a
  pointer past the end is reported, not clamped; removing the last admin is refused. `serves:`
  intent#O8-O15, `docs/spec.md` "Group 10 screens and flows" negative paths. *Class LOCAL. Verify:*
  `uv run pytest tests/acceptance/test_ta14_journeys_and_dead_ends.py`. *Sabotage:* in a copy, make one refusal return a bare 500, the
  "no stack trace, names the reason" assertion goes red for that row; make `dev` land on an empty page after login, the journey goes red.

## D. Live browser and live artifacts

- **TA15 — Persona walks in the checker's own browser on the local deployment (Mode D).** The checker drives its own browser against the TA3
  server over the TA2-TA10 world (the stub product), never the maker's screenshots. Walks: **dev** (the plan's required type): add videos in
  <= 3 steps, Test in <= 3 steps, (finding the "Email me run reports" tick is DEFERRED TO PRODUCTION, D-092 item 1); **admin** (required): review with pointers in <= 4 steps,
  approve access in <= 2, understands which spans were not reviewed without being told; **tester** (added here; one of the four confirmed
  types): reaches the shared video in <= 3 steps from the mail link, comments at a second, sees nothing else; **subadmin** (added here): schedule
  in <= 3 steps with the next three fire times shown in the project timezone, find the tracker and export it in <= 3 steps (the bind-a-sheet walk is deferred to real-sheet export, D-090). Each walk records screen, what was tried, what blocked, severity in
  `qa/evidence/persona-t206-<type>/persona-walk.md`; a `high` finding is a FAIL line. Zero unexplained console errors per page; every form
  control labelled and keyboard-operable; secret inputs masked. `serves:` intent#O8-O15, spec user types (`dev`, `tester`, `subadmin`, `admin`),
  `auth.md` AU26. *Class LOCAL (checker Mode D; BLOCKED-CAPABILITY if no browser tool connects, never a curl substitute). Verify:* evidence under
  `qa/evidence/browser-t206-*-checker/report.json` written by the checker. *Sabotage:* none runnable by the checker; the criterion fails on a
  missing report.json, a missing persona-walk.md for any of the four types, or a `high` finding.

- **TA16 — The redacted-video review is measured against the oracle, in numbers (LIVE-ARTIFACT).** The evidence pack holds the output of the
  already-approved live review of the three redacted Navnit videos (sources `src_e8fcdc4a15ce`, `src_44e2f1f6c64c`, `src_8540cc84081e`, per-use
  Gemini approval recorded 2026-10-07, D-067): the redaction windows applied, a provider-request log showing derivatives only, and the numbers
  of `team-video-review.md` "Live acceptance": recall against the 13 high-severity oracle rows (k of 13, each missed row listed by id), items
  with no human counterpart (counted as unconfirmed, never as true or false positives), time-to-review, and the `not_reviewed` spans. The wording
  is "measured on 3 videos", never "matches a human"; **no pass threshold exists** (intent Q3 carried; a low recall is reported, not patched).
  The checker audits file presence, internal consistency (k equals the number of oracle ids marked found), and the approval row's scope; it
  **does not call a model**. Missing evidence is HELD for the owner, not failed. `serves:` intent#O8, O7, `team-video-review.md` "Live
  acceptance", TV7. *Class LIVE-ARTIFACT. Verify:* `uv run python scripts/check_deliverable.py --exists qa/evidence/t206-review-live/recall.json`
  then the checker reads the file and re-derives k and the unconfirmed count from the listed ids (oracle: `.work/pathlynks-dev-videos-oracle-2026-10-07.md`,
  gitignored, read locally only). *Sabotage:* edit one found id out of the list in a copy, the derived k no longer equals the stated k and the
  audit fails.

- **TA17 — One Test press and one schedule tick on Pathlynks, by the team path, with the test account (LIVE-ARTIFACT, gated on AT-891).**
  The evidence pack holds: the signed `RunApproval` row(s) naming the target and scope for the run(s) (`uv run python scripts/check_crawl_approval.py pathlynks`
  exits 0 for the crawl and the checker reads the per-run row for each T-206 run); the Pathlynks report of T-145 that D-081 item 2 puts first;
  a **Test press by a signed-in `dev`** on a Pathlynks project with the `PATHLYNKS_USER_*` test account, attributed to that user, its report in the
  website inbox (the outbox message is DEFERRED TO PRODUCTION, D-092 item 1); a **schedule tick on the REAL `pathlynks` project** with the same
  `PATHLYNKS_USER_*` keys (D-092 item 2; not a clone), subject to the project's `write_policy` and approval rules as the code enforces them (D-088:
  the first crawl is read-only), that enqueues once and produces a report; the bug rows those runs produced.
  Run safety: test account only, `write_policy` as the owner set it (D-053), runs serialised and one signed approval each (D-081 item 3), no
  live Tracker write, no credential or student data in any artifact. The checker audits artifacts, provenance and the no-leak scan; it starts
  no Pathlynks run. `serves:` intent#O9-O13, O7, spec R53, R56, D-068, D-081. *Class LIVE-ARTIFACT. Verify:* `uv run python scripts/check_crawl_approval.py pathlynks`
  plus the checker's artifact audit of `qa/evidence/t206-pathlynks-*`. *Sabotage:* point the Test-press record at a different `requested_by`
  than the signed-in dev in a copy, the attribution audit fails. **HELD until Umesh answers AT-891** (whether `pathlynks.vidysea.com` is recorded as
  production in the approval; no typing rerun before it is answered, D-084 item 3).

## Invariants

- **TAI1 — No product code.** `git diff --stat <base>..HEAD -- src/` is empty for this unit. The unit adds only `tests/acceptance/**`,
  `qa/evidence/t206-*`, `qa/evidence/persona-t206-*`, `qa/evidence/browser-t206-*-checker/` and `qa/manifests/t206-g10-acceptance.md`. A gap
  that needs product code is filed on the owning unit's contract (maker: `CORE-REQUEST` or inbox) and T-206 stays unmet. *Sabotage:* touch one
  `src/` file, the diff-stat check goes red.
- **TAI2 — Nothing is softened and nothing is skipped.** `grep -rnE "skip\(|skipif|importorskip" tests/acceptance` finds nothing, and `xfail` is allowed ONLY as `xfail(strict=True)` whose reason names a task id that is still `pending` in `.goal/goal.json` (or a D-number that defers the row); a bare reason, `run=False` with no task, or a blocker that has landed is a FAIL (a landed blocker turns the row into XPASS, which strict makes red, and the marker must come off the same day). T-206 cannot reach `checked-PASS` while any xfail remains (checker, 2026-10-13, ruling on the t206-rig questions); no
  assertion is weakened to make a seam pass (the checker reads the diff since the last check, C7). A red seam is an issue on the owning unit.
  *Sabotage:* add a `skipif` to one test, the grep goes red.
- **TAI3 — Deterministic.** `uv run pytest tests/acceptance` passes twice in a row on fresh temporary roots, once with the test files in reverse
  order, with the clock injected (no `sleep` on wall time longer than the bounded waits the rig names). Flaky = FAIL (repeat only per the flaky rule).
- **TAI4 — Design rules.** `uv run autotester doctor` and `uv run ruff check src tests scripts` pass; each new file <= 300 lines, each function
  <= 50, one-job docstring on every module in `tests/acceptance/`.
- **TAI5 — Windows and Ubuntu.** The acceptance code uses `pathlib`, no POSIX-only module, no hardcoded drive letter or `/tmp` (R65). The Ubuntu
  leg is the hosted check below and is not part of the local PASS.
- **TAI6 — Stable ids and cited, not copied.** Each row names the unit criterion ids it composes; a unit row renumbered later makes this
  contract stale and the checker amends it at the next sweep (staleness, check 3).

## Held (HUMAN_GATE or SERVER-GATED, not a checker PASS)

- **Hosted check on Ubuntu** = `hosting.md` HO34 (team walkthrough, dev and tester walks), HO35 (queue rehearsal), HO36 (backup and restore
  drill), plus this contract's TA3 and TA15 repeated against the server URL. Gate `qa/gates/t203-host-and-dns.md` has no `Answered:` line for
  the real host and DNS (local part answered, D-081 item 4, D-083 item 4). DEFERRED TO UBUNTU (D-090 item 3, D-091) and its own goal row, not part of the local PASS; required before anyone says the
  hosted team can use it.
- **Live Tracker write** = the first write to the real Pathlynks Tracker (`qa/gates/t199-first-live-write.md`, no `Answered:` line; D-081 item
  7). Excluded from T-206.
- **Email delivery of reports** = DEFERRED TO PRODUCTION (the Ubuntu server, D-092 item 1), like Docker (D-090, D-091). Neither the outbox
  message, the in-process SMTP path nor a live SES send (D-083 item 1) is T-206 evidence. Website reports suffice now.

## Close-out

T-206 closes on a checker PASS verdict `qa/verdicts/t206-g10-acceptance.md` with `Cycle checked` equal to the manifest's `Fix cycle`, through
`goal_cli done --task-id T-206`. The goal's `done_check` names `qa/verdicts/t-206-g10-acceptance.md` (with a hyphen after the `t`) and only tests
that a file exists (`check_deliverable.py --exists`); no unit verdict in this repo is named that way, and existence does not judge content. This is
recorded for the maker and the goal owner, not worked around here.

## Out of scope / ignore

- Everything a unit contract owns (cited above): upload limits and zip attacks, route-by-route permission tables, the lifecycle table, the
  mapping synonym rules, the queue's own fairness, password hashing. This file re-tests none of them in isolation.
- **O6, the comparison against an expert human tester.** Plan G10 lists O6 against this unit. By Umesh's 2026-09-27 answer the PASS/FAIL there
  is his own, after he compares AutoTester's report with a human tester's list that was written without sight of the report (D-081 item 2,
  `bench.md` K6-K9, T-136, T-169). T-206 supplies the live Pathlynks run as an input and computes nothing about O6.
- Wording, colours and layout beyond the persona-walk steps. Slack or chat delivery, multi-company, auto-fix of bugs (spec Out of scope).
- Performance and capacity (HO8, HO20). The Docker image and HTTPS (HO1-HO14).

## No-fire list (must NOT happen)

- No live write to the real Pathlynks Tracker sheet, and no write to any real sheet (a "test tracker" in the owner's Drive included, see Open).
- No real email is sent by any test or by the checker; no connect to an SMTP host that is not loopback (email itself is DEFERRED TO PRODUCTION, D-092 item 1).
- No model call on a real video by any test or by the checker; the live review of TA16 is an audited artifact.
- No credential of a real user: the test accounts only. No secret, cookie, token or student datum in any evidence file, log or message.
- No change to `src/`, `qa/contracts/`, `docs/DECISIONS.md` or `qa/gates/` by the unit; no new dependency.

## Open for the owner (HUMAN_GATE-REQUESTs; nothing here is decided by the checker)

1. **AT-891 (blocks TA17).** Is `pathlynks.vidysea.com` recorded as production in the run approval? D-084 item 3 says no typing rerun happens
   before this is answered. Until then TA17 is HELD and T-206 cannot PASS.
2. ~~Does a real email count as required evidence?~~ **ANSWERED (Umesh, 2026-10-13, D-092 item 1):** email delivery is DEFERRED TO PRODUCTION; no email evidence is required for T-206.
3. **Does T-206 close on the local PASS, or stay open until the hosted check?** *(Hosted half DEFERRED TO UBUNTU, D-090 item 3, D-091: default accepted as its own goal row; the T-199 `done_check` amendment to the export scope is still the goal owner's.)* Default proposed: close the **local scope** by splitting the hosted
   check into its own goal row (HO34-HO36, TA3/TA15 against the URL), because the host and DNS are yours and have no date. Also: the T-199 goal
   task cannot close while the first-live-write gate is open, and T-206 depends on T-199; say whether T-199's `done_check` is amended to the
   dry-run scope or T-206's `deps` drop it.
4. ~~Where do the live schedule tick and Test press run?~~ **ANSWERED (Umesh, 2026-10-13, D-092 item 2):** on the REAL `pathlynks` project with the
   `PATHLYNKS_USER_*` test credentials, subject to its `write_policy` and approval rules as enforced in code (D-088). No clone. The real
   project then carries the schedule until it is removed; the evidence pack records who removed or kept it.
5. **MOOT (D-090 item 2: the internal tracker plus export replaces it).** D-083 item 3 (the "test tracker sheet in Drive"). The maker read it as: one first live write may go to a test sheet AutoTester creates.
   You have not confirmed. This contract treats even that as outside T-206 (no real sheet at all); say if T-206 should include it.
6. **Reading of D-074 "evidence only, no code".** This contract reads it as no `src/` change, with test code under `tests/acceptance/` allowed
   because the dry-run, restart and zero-egress claims cannot be evidenced by a screenshot. Confirm, or name the other form of evidence you want.
7. **Carried, not new:** the numeric pass line for review recall (intent Q3) stays unset; TA16 reports numbers only.

## Amendment log (append-only; git history is the version)

- 2026-10-12 · initial (proposed, awaiting the owner's approval of a new contract) · checker · closes AT-855. Authored from the brief
  `qa/briefs/t206-g10-acceptance.md`, `docs/plan.md` G10, `docs/features/team-loop/intent.md`, the Group 10 unit contracts, and D-072, D-074, D-081
  through D-085. Tightened vs the plan row: persona walks cover all four confirmed user types (the plan names dev and admin). No unit criterion
  was restated; each row cites the ids it composes.
- 2026-10-13 - owner-authorized (D-092, Umesh chat; D-090, D-091; /checker) - **Email deferred** (item 1): TA6 (c) outbox half and (d), the TA8
  email clause, the TA15 tick-box finding, the TA17 outbox message, the Held "real email" row, and Open 2 are DEFERRED TO PRODUCTION; the website
  inbox halves stay. **Schedule tick on the real `pathlynks` project** (item 2): TA17 and Open 4 answered, no clone. **Tracker export header
  names** (item 3): TA9 uses the current `TRACKER_COLUMNS`. **Six proposals folded** from the maker's runbook (`qa/evidence/t206-runbook.md`,
  branch `wave/t206-runbook`, section 3): (1) the TA1 seam list replaces `SheetClient` with the T-199 export module; (2) TA3 start command is
  `scripts/serve_windows.ps1` (HO39-HO46) and AU24 leaves `serves:`; (3) TA9 rewritten to TB7 plus TB15 export, with the echoes in TA11
  (re-export gives identical bytes), TA12 (export files), TA13 (no sheet client constructed) and TA14 (stale-mapping clause removed) amended;
  (4) the TA15 subadmin walk is "find the tracker and export it in <= 3 steps"; (5) the hosted Ubuntu check is DEFERRED (D-090 item 3, D-091) as
  its own goal row, Open 5 is moot, and T-199's `done_check` amendment stays with the goal owner (Open 1 AT-891 stays open); (6) the Ubuntu leg
  is no part of the local PASS. No safety criterion weakened: TA2, TA12, TA13 remain CRITICAL and the live-write ban is unchanged.
  **Links:** D-092; D-090; D-091; T-206.
