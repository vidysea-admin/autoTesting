# T-198 persona walk (Mode D) - team-intake.md "Persona walks" for G3 intake

Cycle checked: 0 (manifest qa/manifests/t198c.md, Fix cycle 0; branch check/t198-walk on check/t198c f8c811f9)
Method: local `uvicorn autotester.ui.app:app` on 127.0.0.1:57121, scratch data root, login gate ON, seeded test accounts
(admin, sub, dev=project owner, dev2, tester, tester2, nogroup; password is the test-suite fixture one), one headed Chromium
(Playwright) at a time, local fixture zips/videos only. Evidence: qa/evidence/browser-t198-persona/ (PNG per step + results.json).
No secret fields appear on the pages walked; password inputs are masked in screenshots. Server stopped, browser closed.

| Step | Persona | Result |
|---|---|---|
| 1 Sign in, open Sources: upload forms present, labelled | dev | PASS (d1, d2) |
| 2 Upload a single video | dev | PASS (d3; row appears in list with uploader) |
| 3 Upload good.zip (2 videos) | dev | PASS (first run: "2 registered"; rerun shows "2 duplicate", d4) |
| 4 Upload zip with a bad member, read outcome table | dev | PASS: FILE/RESULT/WHY table, `ok.mp4 registered`, `notes.exe skipped - not a recording (.exe)` (d5) |
| 5 Paste a non-Drive link | dev | PASS: "Not a Drive link" refusal, no network call (d7). A real Drive fetch was NOT walked (needs live gws login; SERVER-GATED) |
| 6 Hit the size limit message | dev | PASS: limit set to 1 MiB, page states it, 2 MiB upload -> "larger than the 1 MiB limit the administrator set" (d8) |
| 7 Keyboard: label -> file input -> Upload button by Tab | dev | PASS |
| 8 Project not visible, no forms, direct POST upload/drive | tester, dev2 | PASS: 404 page, no forms, direct POSTs 404, nothing written (t1, x1) |
| 9 Account in no group | nogroup | PASS: "Waiting for an administrator", direct POSTs 403 (n1) |
| 10 Admin view: forms, all sources, admin links | admin | PASS (a1-a3); /admin/users 200 |
| 11 Controls labelled | all | PASS: 0 unlabelled inputs/buttons/links on every walked page |
| 12 Zero unexplained console errors | all | PARTIAL, see D1 (other errors are the expected 400/401/403/404/413 of the refusals above) |
| 13 `lead` (sub-admin) and tester-with-shared-video paths | sub, tester | NOT WALKED in the browser (sub covered by tests/test_intake_gate_auth.py; sharing is T-198b's walk) |

## Defects
- D1 (low, cosmetic): `GET /favicon.ico` answers 401 to an anonymous visitor, so every sign-in page logs a console error.
  src/autotester/auth/policy.py:69 declares it MEMBER while src/autotester/ui/app.py:71 serves a 204. Make it public or exempt.
- Observation: a tester or other developer who cannot view the project gets the project-less 404 page (correct, no existence leak).
- Observation: the first-admin-on-loopback rule did not apply to my seeded admin because other accounts already existed in the
  scratch store; admin was put in the Admin/CEO group via accounts.set_user_groups. Not a product defect.

## Overall: PASS with D1 (low) open; steps 5 (live Drive) and 13 not walked.
