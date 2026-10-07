# Spec — AutoTester

**Purpose:** the requirements (R1-R65) mapped to the outcomes they serve and the contract that judges each one, plus the navigation flow per user type.
**Open me when:** deriving a contract criterion, picking a unit, or deciding which user types a persona walk must cover.

<!-- PLAN phase step 3, BACKFILL. Requirements below are derived from docs/intent.md and from the
     criteria already living in qa/contracts/ (checker-owned). Where a contract already states a
     rule, this file points at it rather than restating it — one concept, one place. -->

**Intent:** docs/intent.md (backfill, 2026-09-27; Team loop O8-O15 added 2026-10-07) · **Status:** draft — R1-R31 awaiting approval; R32-R65 (Group 10) await `qa/gates/plan-approved-g10.md`

## Requirements

| id | requirement | serves | priority | contract |
|---|---|---|---|---|
| R1 | Onboard a product from one form: URL, credential refs, evals, conditions, use cases, sources | O1 | must | `ui.md`, `pathlynks-onboarding.md` ✅ |
| R2 | Learn flows from teaching material (video, audio, doc, email, Drive, text) into one evidence model | O1 | must | `ingest.md`, `source-adapters.md`, `video-learning.md` ✅ |
| R3 | Discover flows without teaching material, by bounded crawl from URL + credentials | O1 | must | `explore.md` ✅, `crawl-traversal.md` 🎯 |
| R4 | Nothing drives off an unreviewed FlowSpec — a human review gate stands between learning and testing | O3 | must | `review-gate.md` ✅ |
| R5 | Keep a durable per-product model across runs, with change detection and dated history | O1 | must | `portal-persona.md` ✅ |
| R6 | Maintain the exploration frontier: every action from a state is exercised or explicitly accounted for as pending / blocked / unsafe / unsupported / skipped — never silently dropped | O4 | must | `crawl-traversal.md` 🎯 |
| R7 | Generate best / worst / edge cases per applicable CaseClass, with source traceability | O2 | must | `expand.md` ✅, eval compiler 🎯 |
| R8 | Say which case classes are runnable, which are blocked, and the one action that unblocks each | O4 | must | `catalog.md` 🎯 |
| R9 | Execute in a real visible browser; the executor only observes, it never grades | O2, O3 | must | `execute.md`, `run-case-pipeline.md` ✅ |
| R10 | Grade with an independent stateless judge that sees the screenshots and rejects a fake pass | O3 | must | `grade.md` ✅ |
| R11 | Capture first-party API/network traffic as evidence; a test may assert expected calls | O3 | must | `network-assertions.md` ✅ |
| R12 | Report every failure with its criterion, judge reason, fix_hint and repro steps, in HTML and Excel | O3 | must | `report-export.md`, `ui-report.md` ✅ |
| R13 | Coverage reports exercised-vs-discovered and keeps untested branches visible | O4 | must | `coverage.md` ✅ |
| R14 | Raise a VideoRequest when a screen is not understood, instead of guessing | O5 | must | `coverage.md` ✅ |
| R15 | A known bug becomes a pinned regression case that runs every time and cannot be deleted | O2 | must | `execute.md` ✅ |
| R16 | Credential boundary: SecretRef only, fill-time substitution inside allowed domains, masked in screenshots/logs/video/prompts | O7 | must | `browser-and-secrets.md` ✅ |
| R17 | Consent: writes and crawls of a real product need a RunApproval; no approval means zero requests, asserted at the transport | O7 | must | `consent.md` ✅ |
| R18 | Resumable pipeline: durable per-stage checkpoints, a crash resumes at the first non-done stage | O2 | must | `orchestrator.md` ✅ |
| R19 | Redacted per-run trace (stage + LLM spans: model, tokens, latency, cost) | O3 | must | `run-trace.md` ✅ |
| R20 | Parallel case execution in isolated browser contexts, bounded by measured RAM/CPU | O2 | should | `parallel-run.md` ✅ |
| R21 | Commit/release-triggered regression against the last trusted baseline, with consent and resumable retries | O2 | must | 🎯 T-167 |
| R22 | One unified damage-control report: regression diff, API failures, workflows, screenshots, Excel | O3 | must | 🎯 T-168 |
| R23 | Persist and replay a generated script with semantic locators and declared test-id priority | O2 | should | 🎯 T-176 |
| R24 | Atomic failure bundle + case priority p0–p3 + human pruning before LLM spend | O3 | should | 🎯 T-178 |
| R25 | CLI contract (`--output json`, documented exit codes, `--dry-run`) + MCP server | O2 | should | 🎯 T-174 |
| R26 | Agent layer: a lead tester plus subagents over deterministic stage tools; guards live in the tools, not the model; kept only on measured gain | O2 | should | `agent-layer.md` 🎯 |
| R27 | Permission-surface coverage: every reachable control exercised or listed blocked-with-reason | O4 | must | 🎯 T-171 |
| R28 | Advisory UX findings with a UserPersona, severity-scored, that NEVER change PASS/FAIL | O3 | should | `persona-ux-advisory.md` 🎯 |
| R29 | Run video on FAIL/INCONCLUSIVE only, last 20 kept, secrets masked exactly as in screenshots | O3 | should | `run-video.md` 🎯 |
| R30 | Below-the-UI AI-target checks: read-only discovery, deterministic signals, a check registry, behavioural checks graded by the existing judge | O3 | should | 🎯 T-150–T-153 |
| R31 | Two-mode acceptance measured against a human on bugs / false positives / coverage / time | O6 | must | `bench.md` ✅ engine, 🎯 numbers |
| R32 | Accept a pointer file or form per video: approximate timestamps (`12:30`, `1:02:03`, `~12:30`, `12:30-14:00`) and 2-3 free-text pointers. A line that does not parse is returned with its line number and reason, never dropped | O8 | must | `team-video-review.md` TV1 (proposed) |
| R33 | Return a typed review: flow summary plus a confirm-list of at most 5 items, each `time / screen / seen / suggestion / severity`, each citing a second inside the recording and the source id | O8, O3 | must | TV3, TV4 |
| R34 | Pointers prioritise and never exclude: the whole recording is analysed at base depth, pointer windows at higher density, and a `not_reviewed` list names every span with no analysed frames | O8, O4 | must | TV2 |
| R35 | Each item carries a provenance label (`pointer`, `narration`, `visual`, `suspected`). Narration items quote the transcript verbatim, else they are downgraded to `suspected`. Silence or an unreadable transcript is never reported as "nothing said" | O3 | must | TV5, TV6 |
| R36 | Redaction before egress: blackout/mute windows are applied before any frame or audio reaches an external model, a recorded per-use approval exists for (project, provider), and the unredacted original is never passed | O7 | must | TV7 |
| R37 | Video-derived flows enter the FlowSpec as DRAFT that never blocks case generation (D-070 part 2). Every flow is kept: ideal, narrated, variant. Reconciliation against the product KG belongs to T-166; this unit keeps narrated intent and provenance | O8, O9 | must | TV9 |
| R38 | Persist the review as a typed artifact with a content-derived id (same source, pointers and transcript gives the same id); viewable on the video page, exportable as Markdown and HTML | O8 | should | TV10 |
| R39 | Zip intake: expand in a staging directory with member-count, per-file, total-uncompressed and ratio caps. Refuse traversal, absolute and drive-letter paths, symlinks, device entries and nested archives, under both Windows and Ubuntu path rules. One source per video; non-video members listed as skipped with a reason | O9 | must | `team-intake.md` TI1-TI5 |
| R40 | Google Drive link: the user pastes a Drive file, folder or zip link (or id) and the system fetches it through the existing `gws` auth: stage under the working directory, verify size and md5, copy to a stable project path, register. A zip goes through R39 | O9 | must | TI7, TI8 |
| R41 | Uploads are bounded while streaming: an over-limit body is refused with 413 before it is buffered and temp files are removed on abort. The limit is an **admin setting, default 2 GB per video** (zip limits likewise), read from the server settings that T-203 owns | O9 | must | TI9 |
| R42 | Every source records who supplied it, when and from where (zip member or Drive id). Intake routes require a signed-in member with `video.upload` on that project | O9, O15 | must | TI10, TI11 |
| R43 | Bug key is stable: derived from project plus the failing case/criterion (or the video issue fingerprint), never from run id, time or screenshot. The same failure across runs is one bug | O10 | must | `team-bug-loop.md` TB1 |
| R44 | Lifecycle: `open` on first FAIL; re-fail updates last-seen and count; N consecutive PASS verdicts set `fixed`; a FAIL after `fixed` is `reopened`; blocked/inconclusive/not-run never changes state | O10 | must | TB2, TB3 |
| R45 | In-product tracker page: bugs with status, severity, screen, assignee, first/last seen, count and evidence links; filters; assignee is a project member or free text. Visible per `report.view` and project scope | O10, O15 | must | TB7 |
| R46 | The bug loop reads graded verdicts only (replayed runs included, D-072) and is idempotent per run id | O10, O3 | must | TB3, TB6 |
| R47 | Tracker binding for any project: the user supplies a sheet; AutoTester reads only the header row, proposes a column mapping, marks ambiguous or missing columns `unmapped` with candidates, and activates nothing until a named user holding `project.edit` on the project confirms. A moved or renamed header makes the mapping `stale` | O11 | must | TB8, TB14 |
| R48 | First live write is previewed as exact cells and confirmed by a named user, bound to the plan hash. Later writes only append or update rows carrying our bug key; never delete, never touch unmapped columns, never overwrite a cell a human edited since our last write (flag a conflict) | O11 | must | TB9, TB10, TB11 |
| R49 | A sheet failure degrades, it does not fail: the in-product tracker stays authoritative, sync status and last error are visible, retries converge, no run fails because the sheet is down | O11 | must | TB12 |
| R50 | Anything written to a sheet passes `Redactor.scrub`; screenshot links are authenticated product URLs, never public links | O7, O11 | must | TB13 |
| R51 | Per-project schedule with three modes (D-072 item 9; `qa/contracts/hosting.md` HO22): **manual** (button only, the default), **fixed** (one daily `HH:MM`) and **custom** (a time the user selects: a one-off date-time, or a weekly set of weekdays plus `HH:MM`). IANA timezone per schedule (default `AUTOTESTER_TIMEZONE`, else UTC), DST-correct. Invalid input (25:00, unknown zone, past one-off, empty weekday set) is refused and stores nothing. Needs `schedule.manage` on the project | O12 | must | `hosting.md` HO22 + `team-schedule.md` TS1 (proposed) |
| R52 | A slot fires exactly once even with two concurrent ticks; a slot missed while the server was down fires at most one catch-up inside a grace window (default 60 minutes), otherwise it is recorded `missed`, never backfilled; a slot that finds the previous run still going is recorded `skipped_overlap`. The marker is atomic on Windows and Ubuntu | O12 | must | TS2, TS3, TS4 |
| R53 | A scheduled run proceeds only on a credential-derived approval (D-068). Without a declared credential pair it is recorded `blocked_no_credentials`, sends zero requests and notifies the schedule owner | O12, O7 | must | TS5 |
| R54 | A scheduled run uses the same launcher as a manual run and as the Test button, and records its trigger plus slot key. No second runner exists. It enters the **T-203 run queue**; it does not start browsers itself | O12 | must | TS6 |
| R55 | A scheduler that has not ticked for two intervals is shown as stale; a crashed scheduled run is reported failed with its cause, never absent | O12, O4 | must | TS7 |
| R56 | Test button on the project page: a signed-in member with `project.run` on that project enqueues a `RunRequest` attributed to them and returns at once; the status page shows queued, running, finished, failed, blocked | O13, O15 | must | `team-test-button.md` TT1-TT3 |
| R57 | Group 10 only **enqueues**. One active run per project, the server-wide concurrency cap (an admin setting, default 2) and the queue are T-203's; this group shows the queue position and returns the existing request when the same project is already queued or running | O13 | must | TT5 (seam on T-203's queue contract) |
| R58 | The report is shown on the website (project report and "My reports"), and also emailed to the identity that pressed the button (or to the schedule owner and subscribers) **only if that user ticked their email preference** (profile checkbox, default off). A recipient field in the request is ignored. Blocked, failed and low-coverage runs are delivered with that label | O13, O4 | must | TT7, TT8 |
| R59 | Delivery failure is recorded and visible and never changes the run's verdict; no message carries a secret or a link that works without sign-in | O13, O7 | must | TT9 |
| R60 | The Test button is gated exactly like a schedule: credential-derived approval, refusal text names the state, no run directory on refusal; the approval's own bounds cap each run | O13, O7 | must | TT6 |
| R61 | Video page inside a project with a non-guessable share link that still requires sign-in. A person without access sees "request access"; the request goes to those who may approve it: the video's uploader, a sub-admin of the project, or an admin | O14 | should | `team-intake.md` TP1, TP3, TP5 |
| R62 | Timestamped comments (second offset, text, author), visible to everyone with access; edit/delete own; a comment can be promoted to a pointer. Needs `comment.create` | O14 | should | TP2, TP6 |
| R63 | Group 10 uses the permission keys and scopes in `qa/contracts/auth.md` (closed catalogue, scopes `all`, `assigned`, `own`, `shared`) and requests no new keys; it enforces them server-side on every route through T-204's engine. The UI hiding a button is not enforcement. A route needing an unlisted key is a contract gap to raise with the checker | O15 | must | `auth.md` AU11-AU14 + TP4 (proposed) |
| R64 | Every Group 10 page and state-changing route requires a signed-in member. T-204 is the mechanism; Group 10 consumes its identity and permission interface and implements no login, session, group editor or sign-up | O15, O7 | must | TT1, TI10 |
| R65 | New modules run on Windows (development) and Ubuntu (production): no POSIX-only calls, path-safety tests cover both separators and drive letters, atomic file markers use portable primitives. T-203's deploy check runs the Group 10 tests on Ubuntu | O9, O12 | must | cross-cutting criterion in each contract |

✅ = shipped and checker-verified · 🎯 = target. R31's numbers are gated on Umesh (credentials
plus the trainer truth sheet). R32-R65 are the Group 10 "Team loop" requirements
(contract names are proposals the checker folds in; none exists yet).

## Navigation flow per user type

### `dev`
- **Entry:** the run view for the run their commit triggered.
- **Main goal in ≤ 3 steps:** run view → failing case → its criterion + judge reason + repro steps.
- **Must understand without being taught:** which cases failed; why the judge said so; how to
  reproduce it locally; what was NOT covered by this run.
- **Happy path:** all cases PASS, and the run view still names the coverage that stayed unexplored.
- **Negative paths:** a case is INCONCLUSIVE (evidence too weak to judge) · the browser crashed
  mid-case and only that case is affected · no baseline exists to diff against.

### `tester`
- **Entry:** the onboarding form.
- **Main goal in ≤ 6 steps:** onboard → add sources or start a crawl → review the FlowSpec →
  review the catalog (runnable vs blocked) → prune the proposed cases → run.
- **Must understand without being taught:** that nothing runs off an unreviewed spec; which cases
  are blocked and the one action that unblocks each; which credentials are needed, and that only
  a key name is ever stored.
- **Happy path:** a freshly onboarded product reaches its first real run without touching a CLI.
- **Negative paths:** a domain outside `allowed_domains` · a crawl refused for want of consent ·
  a screen the model does not know → VideoRequest · a credential pasted into a case step (refused).

### `lead`
- **Entry:** the home dashboard.
- **Main goal in ≤ 2 steps:** dashboard → the damage-control report for the latest run.
- **Must understand without being taught:** what broke since the last trusted baseline; what was
  never explored; the confidence label on each finding; the trust number against a human.
- **Negative paths:** a report whose coverage is low must not read as green.

### `trainer`
- **Entry:** the sources page for a product, or a VideoRequest link.
- **Main goal in ≤ 3 steps:** open the request → see which screen is missing → upload the recording.
- **Must understand without being taught:** exactly which screen or flow is missing, and why.
- **Negative paths:** an unreadable or silent recording is reported as unreadable, never as an
  empty-but-verified transcript.

### `release-manager`
- **Entry:** the release/regression trigger.
- **Main goal in ≤ 2 steps:** trigger the approved suite → approve the consent gate → verdict.
- **Must understand without being taught:** which product and account the run touches; that
  `write_policy` bounds what it may do; that the run resumes rather than restarting after a crash.
- **Negative paths:** approval absent or expired → zero requests sent · run interrupted → resumes
  at the first non-done stage.

## Group 10 — user types, permissions and navigation (2026-10-07)

Audience stays `internal-tool`, so persona walks cover 1-2 user types per unit. `lead` (confirmed) holds
the Admin group in practice. `admin` and `subadmin` are Umesh's default group names; `dev` and `tester`
are confirmed types.

### What T-204, T-203 and Group 10 each own (so nothing is built twice)

| concern | owner | Group 10 does |
|---|---|---|
| email+password sign-up, session, logout; first admin is the `AUTOTESTER_FIRST_ADMIN_EMAIL` account on a hosted server and the first account only in local dev (`auth.md` AU7); admin can disable/delete/change any account | **T-204** | consumes an `authenticated_user()` dependency returning `{id, email, display_name}` |
| groups, ticking permissions, adding users to groups, assigning users to projects, the permission engine (a key plus a `ResourceRef`, scopes `all`, `assigned`, `own`, `shared`), the `credentials.view` permission | **T-204** | uses the keys below; calls the engine on every route |
| the admin screens for users, groups and project assignment | **T-204** | none |
| Docker/Ubuntu deploy, deploy guide, HTTPS, persistent store, Host allow-list (AT-758) | **T-203** | none |
| run queue, one-active-run-per-project, server-wide concurrency setting (default 2), the async run request and status | **T-203** | enqueues; shows position; unit G1 extracts the one `run_launcher.py` that T-203's queue worker calls |
| server settings store and admin Settings page: upload limit (default 2 GB), zip caps, concurrency | **T-203** | reads the upload and zip limits; registers their keys |
| the scheduler tick driver (systemd timer on Ubuntu; Task Scheduler or manual on Windows) | **T-203** ships the timer unit | owns `autotester schedule tick` and the schedule screen |
| video intake, review, bugs, tracker, sheet sync, schedule, Test button, report delivery (website + email preference), video share / access requests / comments | **Group 10** | everything else in R32-R65 |

### Permission keys Group 10 uses (the closed catalogue and the default groups are `qa/contracts/auth.md`, which governs)

Group 10 requests no new keys. Scopes: `all`; `assigned` (the user is in the project's assignees); `own` (the user created the
project or video); `shared` (the user is in the resource's `shared_with`). Defaults, per `auth.md`: **Admin/CEO** has every key at
`@all`; **Sub-admin** the project, report, video, access, comment and schedule keys at `@assigned`; **Developer** the same at
`@own` plus view, report, video and comment at `@shared`; **Tester** `project.view`, `report.view`, `video.view` and
`comment.create` at `@shared` only. An admin can tick any box for any group.

| Group 10 action | key | notes |
|---|---|---|
| open a project, its runs and library | `project.view` | a project the user may not view answers 404 |
| watch a video | `video.view` | |
| upload a file or zip, or paste a Drive link | `video.upload` | |
| add or remove `shared_with` on a video or project | `video.share` | the share link needs sign-in |
| approve an access request | `access.approve` | a developer approves only requests on their own videos (`@own`); a sub-admin in assigned projects; admin anyone |
| comment at a timestamp | `comment.create` | |
| press Test | `project.run` | the credential-derived approval still applies (D-068) |
| set the schedule | `schedule.manage` | |
| read a run report and the tracker | `report.view` | the tracker is a view of run reports |
| run a pointer review; bind a tracker sheet | `project.edit` (plus `video.view` for review) | a tester holds neither, so cannot spend model cost or write a sheet |
| email me reports | none (own profile) | recipient must still hold `report.view` at send time (`hosting.md` HO26) |

Owned elsewhere: `users.manage`, `groups.manage`, `project.assign`, `credentials.view` and `credentials.edit` (T-204); `settings.manage`,
`live.view` (T-204 grants, T-203 serves) . A new account with no group sees only the sign-in and "waiting for access" screens.

### `dev` (Developer group)
- **Entry:** project Videos page ("Add videos"), or the report link for a run they pressed.
- **Main goal in <= 3 steps:** Add videos -> choose file, zip, or paste a Drive link -> one row per video with its outcome.
- **Test goal in <= 3 steps:** project page -> Test -> status page -> report (failing case, criterion, judge reason, repro).
- **Must understand without being taught:** which zip member was skipped and why; that a Drive link needs sharing granted to the server's Google account; what the report did NOT cover; where to tick "email me reports".
- **Negative paths:** over the upload limit (413 naming the limit) - member is not a video - Drive permission denied - no credentials declared (names the Credentials page) - Test pressed while this project is already queued (shows the existing request) - someone asks for access to their video (they approve it).

### `tester` (Tester group)
- **Entry:** a video share link in an email, or "Shared with me".
- **Main goal in <= 3 steps:** open the link (sign in) -> watch -> comment at a second.
- **Must understand without being taught:** they see only what was shared; a comment jumps to its second for everyone.
- **Negative paths:** no access (request-access page, says who will be asked) - signed up but in no group (waiting-for-access page) - a project that was not shared is simply absent, not "forbidden".

### `subadmin` (Sub-admin group)
- **Entry:** project page, Schedule card, or Access requests.
- **Main goal in <= 3 steps:** Schedule -> pick manual / fixed / custom and the time -> see the next three fire times in the project's timezone -> Save.
- **Second goal in <= 5 steps:** bind the tracker sheet: paste link -> review mapping -> fix `unmapped` -> see the exact first write -> confirm.
- **Must understand without being taught:** a skipped or blocked slot shows with its reason; nothing is written to the sheet before the preview is confirmed; a human edit in the sheet is never overwritten.
- **Negative paths:** no credential pair (schedule saves, slots show `blocked_no_credentials`) - previous run still going (`skipped_overlap`) - scheduler stale - header changed in the sheet (mapping `stale`) - a project they are not assigned to is absent.

### `admin` (CEO / Admin group; `lead` in practice)
- **Entry:** a video share link, the dashboard, or Access requests.
- **Review goal in <= 4 steps:** open the video -> type 2-3 pointers with timestamps -> Review -> read the summary and the 4-5 confirm-list rows.
- **Approve goal in <= 2 steps:** Access requests -> approve, for any video in any project.
- **Must understand without being taught:** each row jumps to its second; the page names the stretches nobody looked at; narration quotes are verbatim; who ran what and why a schedule did not fire.
- **Negative paths:** a pointer past the end of the video (reported, not clamped) - a transcript that could not be read (stated, not silent) - a change that would leave the system with no admin (refused by T-204).

## Group 10 screens and flows

| id | screen | who | flows |
|---|---|---|---|
| G1 | Project Videos (library; Add videos: file, zip, Drive link; outcome table) | dev, subadmin, admin | F1 |
| G2 | Video page (player, pointers box, review, comments, share link) | all with access | F2, F7 |
| G3 | Review result (summary, confirm-list, not-reviewed spans, provenance chips) | admin, dev | F2 |
| G4 | Tracker (bugs, filters, evidence, sync status) | per `report.view` | F3 |
| G5 | Tracker settings (sheet link, mapping proposal, first-write preview) | subadmin, admin | F4 |
| G6 | Schedule card and history (manual / fixed / custom) | subadmin, admin | F5 |
| G7 | Project page with Test button and run status | dev, subadmin, admin | F6 |
| G8 | My reports (website inbox) with the "email me reports" checkbox | all | F6 |
| G9 | Access requests (approve or decline, per `access.approve`) | dev (own), subadmin, admin | F7 |

Users, groups and project assignment (T-204) and Settings (T-203) are those units' screens, not G-screens.

- **F1 intake:** G1 -> pick file / zip / Drive link -> staged and validated against the admin limit -> per-member outcome table -> sources registered -> ingested into the product KG.
- **F2 review:** G2 -> pointers -> per-use approval check for the model provider (recorded once per project and provider) -> review job -> G3.
- **F3 bug loop:** run finishes -> verdicts -> bug loop -> G4 updates -> (if bound and confirmed) sheet sync.
- **F4 bind a sheet:** G5 paste link -> header read -> mapping proposed -> user edits and confirms -> write plan shown -> confirm -> first write -> later syncs automatic.
- **F5 schedule:** G6 save -> tick fires slot -> approval check -> enqueue on the T-203 queue -> run via the shared launcher -> report on the website and email to those who ticked; failure paths recorded in history.
- **F6 test on demand:** G7 Test -> RunRequest (identity from session) -> queue -> run -> report in G8, and email if the clicker ticked it.
- **F7 share and comment:** G2 share link -> sign-in -> allowed? view : "request access" -> approver acts on G9 -> comments.

## Flow → user types map

| flow | user types |
|---|---|
| onboarding + intake | tester |
| teaching / sources / VideoRequest | trainer, tester |
| crawl + consent | tester, release-manager |
| FlowSpec review gate | tester |
| catalog + case pruning | tester |
| run trigger + run view | dev, release-manager |
| report + coverage + damage control | lead, dev |
| settings / providers / .env editor | tester |
| video intake (file, zip, Drive link) | dev, subadmin, admin |
| review with pointers | admin, dev |
| bug loop + tracker | dev, subadmin, admin; tester (shared) |
| bind a sheet | subadmin, admin |
| schedule | subadmin, admin |
| test on demand + reports | dev, subadmin, admin |
| share, access requests, comments | dev, tester, subadmin, admin |

## Out of scope (now)

- T-154 bounded adversarial pass and T-155 its tiered report — held pending a separate approval
  (Umesh, 2026-09-27). No probe traffic is sent in this push.
Decision claim D-041: "**Refused:** \"regenerate tests instead of maintaining them\" (docs/research/testsprite-2026-09.md §6)." <!-- decision-claim: {"id":"D-041","what":"**Refused:** \"regenerate tests instead of maintaining them\" (docs/research/testsprite-2026-09.md §6)."} -->
Decision claim D-041: "**Deferred to Umesh:** the differential base-vs-head oracle (research item E). It needs two deployable builds of the app under test." <!-- decision-claim: {"id":"D-041","what":"**Deferred to Umesh:** the differential base-vs-head oracle (research item E). It needs two deployable builds of the app under test."} -->
- Any run against a live user's credentials, or any write to production Mongo.
- **Group 10:** the company org-chart hierarchy beyond the four default groups (CEO > ... > sub-admin as a
  tree); Slack delivery and two-way chat; sheet providers other than Google Sheets (the binding interface
  is provider-agnostic); auto-fix of bugs, auto-assignment by code ownership, in-browser video editing;
  external (non-Vidysea) teams; multi-company `org_id` (PARKED). Reconciliation of video flows against the
  crawled KG is T-166, the any-model provider T-202, hosting and the run queue T-203, login and groups
  T-204: each is its own task and Group 10 consumes their seams.

## Seeds

- `qa/adapter.json` `personas` ← one entry per user type above (seeded by T-190).
- `qa/scenarios/<feature>.csv` ← one row per happy/negative path above.
