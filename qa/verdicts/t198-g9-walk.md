# T-198 G9 persona walk (Mode D) - team-intake.md "Persona walks", G9 (dev, tester, lead)

Cycle checked: 0 (master 53f069ed; branch check/t198-g9). Method: local uvicorn on 127.0.0.1:50439, scratch data root, login gate ON,
seeded test accounts (admin, sub=lead assigned to `demo`, dev=owner of `demo`, dev2=owner of `other`, tester, tester2, nogroup),
one headed Chromium (Playwright) at a time, local fixture video (an existing repo webm, 22 s, two copies with distinct bytes),
no external sites. Evidence: qa/evidence/browser-t198-g9/ (PNG per step + results.json; password inputs and the share-link input
masked, tokens redacted in results.json). Server stopped, browser closed.

| Step | Persona | Result |
|---|---|---|
| G1 Videos list and video page: player, share panel, labelled comment form | dev | PASS (d2, d3) |
| G2 Share video with an account via the labelled form (email, change, Save) | dev | PASS: tester@team.test listed under "Shared with" (d4) |
| G3 Create share link: 43-char token, shown once | dev | PASS (d5) |
| G4 Comment at 5 s; script/`onerror` comment rendered as text, no dialog fired | dev | PASS (d6; 0 dialogs) |
| G5 Comment at 9999 s refused | dev | PASS: 400 "past the end of the video (20 seconds)", nothing stored (d7); see D2 |
| G6 Promote a comment to a pointer: marker shown, comment stays, button gone (no second promotion) | dev | PASS (d8) |
| G7 Shared video in two clicks from sign-in (Videos, then the video); unshared video absent from "Shared with me" | tester | PASS (t1-t3) |
| G8 Comment click seeks the player (click at 0:05 -> currentTime 6.4 after 1.5 s of play) | tester | PASS (t3b) |
| G9 Tester comments on the shared video; no share panel, no "Make a pointer"; direct POST share 403, promote 404, nothing created | tester | PASS (t4) |
| G10 Unshared video by direct URL: request-access page, no `<video>`; `/media` full and `Range` GET 404, 26-byte body, no video bytes | tester | PASS (t5) |
| G11 Request access by keyboard (focus + Enter); sent page; reopening shows "waiting for a decision"; "My access requests" shows pending | tester | PASS (t6, t7) |
| G12 Owner finds the request on Access requests page and approves; replayed approve POSTs change nothing (one share) | dev | PASS (d9-d11) |
| G13 Another developer sees no request, direct approve 404, no access to the video | dev2 | PASS (x0, x1) |
| G14 Approved tester: video now in "Shared with me" (status approved), player present, `/media` 200 | tester | PASS (t8, t9) |
| G15 Lead: sees Videos and Access requests links; opens assigned-project video with share panel, comment form, "Make a pointer" | lead | PASS (l1-l3) |
| G16 Lead on an unassigned project's video: request-access page, no player, `/media` 404; `/admin/users` 403, `/admin/settings` 404 | lead | PASS (l4, l4b) |
| G17 Lead approves a tester's request for a video in an assigned project; requester then gets the player; lead promotes a comment | lead, tester2 | PASS (l5-l7, t10) |
| G18 Share link: signed out -> sign-in with `next` (no bytes); no-group account -> waiting page; member -> video; revoked and unknown tokens both 404 with identical body | anon, nogroup, tester | PASS (k1-k3) |
| G19 Owner declines a request: requester sees "declined, you can ask again", no share created | dev, tester2 | PASS (d12, t11) |
| G20 Admin controls not shown to tester | tester | PASS (home links: Projects, Videos only) |
| G21 Controls labelled and keyboard-operable | all | PASS: 0 unlabelled inputs/buttons/links on 9 pages walked; Tab order at_s -> Use current time -> text; share-email -> change -> Save |
| G22 Zero unexplained console errors | all | PASS with D1 (low): all other errors are the intended 400/403/404 refusals of this walk |

Not walked: admin persona on G9 pages (not specified for the browser walk); mail notification (SMTP not configured, by design).

## Defects
- D1 (low, open since the earlier walk): `GET /favicon.ico` answers 401 to an anonymous visitor, so every sign-in page logs a console error.
  src/autotester/auth/policy.py:69 declares it MEMBER while src/autotester/ui/app.py:71 serves a 204.
- D2 (low, usability): a refused comment (e.g. `at_s` past the end) lands on a generic error page whose only link is "Back to projects"
  (src/autotester/ui/error_pages.py:102), so the typed text is lost and the user is not returned to the video.
- Observation: tester sidebar shows "PROJECTS / No projects yet." next to a shared video; correct (no leakage) but may read as a fault.

## Overall: PASS (D1, D2 low, non-blocking)
