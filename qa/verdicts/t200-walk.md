# T-200 persona walk (Mode D) - team-schedule.md "Persona walk"

Branch check/t200-walk on wave/t200c-schedule-ui 6409bb5e. Method: local uvicorn 127.0.0.1:55698, scratch data root, login gate ON,
seeded accounts (admin, owner = developer owning the project, viewer = tester with a shared relation, sub), one headed Chromium
(Playwright), local fixture site (tests/fixtures/login_site) on 127.0.0.1:8765, tick driven by the real CLI `schedule tick --project`.
Evidence: qa/evidence/browser-t200-walk/ (PNG per step, tick1.txt, tick2.txt, results.json). No password field is on any walked page
except sign-in (not screenshotted with a value). Email items deferred per D-092. Server stopped, browser closed. /inbox does not exist
on this branch, so the run list (/projects/fixture/report) was used.

| Step | Result |
|---|---|
| S1 owner opens the schedule card, form present | PASS (02) |
| S2 invalid time "25:99": nothing saved, field named | PASS on "nothing saved, fixed_at named"; FAIL on "inline": see D1 (03) |
| S3 save fixed daily schedule; card shows mode, active, next run | PASS (04) |
| S3b project with no credentials: blocked reason | PASS: card shows `credentials: NO_SECRETREF` pill; it does not name the Credentials page (see D3) |
| S3c next three fire times in project tz before saving | FAIL: card shows a single "Next run" (D2) |
| S4 pause / S5 resume / S6 delete | PASS / PASS / PASS (05-07) |
| S7 save custom one-offs on a credentialed project | PASS (09), credentials PROVISIONED |
| S8 viewer sees the card with no editable control | PASS (10) |
| S9 viewer save/pause/resume/delete -> 403 naming schedule.manage | PASS (4 of 4; fetch from the viewer's browser session) |
| S10 tick fires the due slot | PASS: `fixture enqueued fixture:custom:...` rc 0; history row "enqueued" (11) |
| S11 run appears with requester "scheduled" | NOT OBSERVED: the fixture project has no cases, so the run was refused at start ("project 'fixture' has no cases to run") and the run list says "no runs yet" (12). Requester/trigger stamping not walked in the browser. |
| S12 owner disabled, tick again -> slot refused | PASS: rc 2, `refused ... owner_refused: the schedule's owner is disabled or no longer exists` (tick2.txt) |
| S13 schedule paused with reason on the card | PASS: "Next run: paused", history row `refused owner_refused...` (13) |
| S14 controls labelled (owner, viewer, admin) | PASS, 0 unlabelled controls |
| S15 console errors | PASS: only the expected 400 (S2) and four 403s (S9) |

## Defects
- D1 (low): invalid value gives a full "400 Bad Request" error page with "Back to projects", not an inline refusal on the schedule page.
  src/autotester/ui/routes_schedule.py:89 (`raise HTTPException(400, ...)`).
- D2 (medium vs contract): no preview of the next three fire times before saving; the card shows one "Next run".
  src/autotester/ui/schedule_view.py:94 (`_status`) and `_form`.
- D3 (low): blocked-credentials state is a bare pill (`NO_SECRETREF`); the card does not say "declare them on the Credentials page"
  (the sentence exists in src/autotester/stages/schedule_gate.py:26 but is only shown in a refused slot's record).
- Observation: `--project` ticks write no heartbeat by design, so the card says `scheduler: NEVER_TICKED` after them.
- Not walked: subadmin persona, unassigned-project 404, S11 requester label (needs a fixture with cases).

## Overall: PARTIAL. S3c FAIL (D2), S2 inline FAIL (D1), S11 not observed; HO24, 403 and pause/resume/delete steps PASS.
