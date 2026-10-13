# T-200 persona walk, round 2 (Mode D) - team-schedule.md "Persona walk"

Branch check/t200-walk after the fixes (S3c preview, S2 inline refusal, credentials link). Method: local uvicorn 127.0.0.1:55698,
scratch data root, login gate ON, seeded accounts (admin, owner = developer, viewer = tester with a shared relation, sub = sub-admin
assigned to one project), one headed Chromium (Playwright), local fixture site (tests/fixtures/login_site) on 127.0.0.1:8765, tick
driven by the real CLI `schedule tick --project fixture`. The fixture project HAS a case (navigate to login.html) and uses the mock
provider (no real model on this machine). Evidence: qa/evidence/browser-t200-walk/r2-*.png, r2-tick1.txt. No password value is on a
walked page. Servers and browser stopped. Note: /inbox is NOT on this branch (t201c is not in master's history here), so S11 was
checked on the run list (/projects/fixture/report) and the run page.

| Step | Result |
|---|---|
| S1 owner opens card, form present | PASS (r2-01) |
| S2 invalid time "25:99": inline on the card, role=alert, typed values kept, status 400, nothing saved | PASS (r2-02) |
| S3c next three fire times in the project tz before saving (Preview button; 3 rows, "IST", UTC beside) | PASS (r2-03); preview stored nothing |
| S3 save fixed daily; card shows mode, active, next three | PASS (r2-04) |
| S3b no-credentials project: pill NO_SECRETREF plus a link naming the Credentials page, link lands on /projects/nocred/env | PASS (r2-05, r2-06) |
| S8 viewer: card visible, no schedule form | PASS (r2-07) |
| S9 viewer save/pause/resume/delete -> 403 naming schedule.manage | PASS 4 of 4 |
| Subadmin, assigned project: fixed daily (preview, save = 2 steps), then custom one-off (preview, save = 2 steps) | PASS (r2-08..11) |
| Subadmin, unassigned project: GET 404, identical to a missing project; POST 404 | PASS (r2-12) |
| S10 tick fires the due slot | PASS: `fixture enqueued fixture:fixed:2026-10-13T13:05Z` (r2-tick1.txt, r2-13) |
| S11 run exists, trigger "schedule", requested_by = schedule owner, slot_key set, in the run list | PASS (r2-14, r2-15): run.json trigger=schedule, requested_by=owner@walk.test; run page "Started by owner@walk.test". The contract label is the owner, not the word "scheduled"; the run page does not print the trigger word. |

## Observations (not defects of this unit)
- The run's single case ended INCONCLUSIVE "execution errored: RuntimeError: cannot schedule new futures after interpreter
  shutdown" - the CLI tick process exits while its run threads still work (r2-15). The run record, requester and trigger are right;
  the execution inside the tick process is a separate defect to triage. Not judged here.
- Subadmin "find a skipped slot's reason in history" not walked (no skipped slot seeded); the round-1 refusal reason on the card
  (S13) passed.
- `--project` ticks write no heartbeat by design.

## Overall: PASS for S2, S3c, S3b link, subadmin, unassigned 404 and S11 (run exists with requester and trigger); /inbox absent on this branch.
