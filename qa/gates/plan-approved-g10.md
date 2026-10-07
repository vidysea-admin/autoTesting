# PLAN gate — Group 10 "Team loop" (T-197..T-201), maker init step 2b

**Asked:** 2026-10-07 · **Owner:** Umesh · Artifacts: `docs/features/team-loop/intent.md`, `docs/intent.md` (O8-O15), `docs/spec.md` (R32-R65), `docs/plan.md` (units G1-G10). Built on D-070, D-071, D-072.

## What Group 10 will build (plain language)
Developers upload a video, a zip, or a pasted Google Drive link into their project and AutoTester turns each into a source. A reviewer gives timestamps and 2-3 pointers and gets a summary plus a 4-5 row confirm-list that cites the second. Failures become one tracked bug that updates on re-test and closes after passes. A project runs by button, at a fixed time, or at a custom time. Reports appear on the website and are emailed only to people who ticked the box. A video has a share link; people without access can request it; people with access comment at timestamps. Sheet sync to a team tracker is shown and confirmed before the first write.

## Not built here (other tasks own it)
T-204: sign-up, sessions, groups, ticking permissions, user/group/assignment screens. T-203: Ubuntu deploy, run queue, concurrency setting (default 2), settings page (upload limit default 2 GB), tick timer. Group 10 calls them and does not duplicate them. The checker's `auth.md` and `hosting.md` (D-072) already hold the permission list, default groups and the schedule, report-email and upload rows; this plan follows them.

## User types and navigation (default groups from your answer)
- **admin (CEO/Admin):** sees everything, approves anyone. Open video -> add pointers -> Review -> read rows (4 steps). Access requests -> approve (2).
- **subadmin:** only assigned projects. Schedule -> mode and time -> Save (3). Bind tracker sheet in 5 steps with a preview.
- **dev:** own videos, approves access to them. Add videos -> file/zip/Drive link -> outcome table (3). Project -> Test -> report (3).
- **tester:** sees only what is shared, can comment. Open link -> watch -> comment (3). No access shows "request access".

## Units, in order
G1 headroom + one run launcher (T-205 new) · G2 pointers and review (T-197) · G3 zip and Drive intake (T-198) · G4 report delivery, website + email preference (T-201) · G5 schedule (T-200) · G6 bug loop (T-199) · G7 Test button (T-201) · G8 sheet sync (T-199) · G9 share, access requests, comments (T-198) · G10 acceptance (T-206 new). G2-G4 run in parallel after G1.

## Assumptions I made (reply only to change them)
Bug closes after 2 consecutive passes. Email checkbox defaults off. "Custom time" means one or more date-times you pick, each fires once. A share can cover a project or one video. No per-user cooldown on Test. Zip caps 5 GB, 20 videos. Developers see only their own videos plus shared ones. Review needs a per-project, per-provider approval before a video goes to a model.

## Still open (none blocks the plan)
1. Email sender address and SMTP/Google credentials (blocks only the email adapter).
2. Which Google account the server uses to fetch Drive links.
3. `org_id` on every row for a later multi-company move: PARKED, not built unless you say so.

## Answer
Approved -- Umesh, 2026-10-07 (chat), recorded as D-074.
