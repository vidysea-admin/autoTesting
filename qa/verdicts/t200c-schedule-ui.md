# Verdict - t200c-schedule-ui (independent checker)

Cycle checked: 1
Head checked: 6d0436ee
VERDICT: FAIL (one blocking design-rule defect; functional criteria pass)

## Criteria
- TS1 routes + card (GET project.view; save/pause/resume/delete POST schedule.manage): PASS. policy.py:36,62,79-80; routes_schedule.py; schedule_view.py. Save goes through ScheduleConfig.parse_for_save (400 names field, nothing stored); delete uses existing purge_project.
- TS1 "403 naming schedule.manage": RULING below. Tests assert status only (test_schedule_routes.py:65-74,176).
- Auth only via central policy: PASS. No parallel check; can_manage() only drives read-only rendering through authorize().
- One concept one place: PASS. Reuses schedule store/wiring/schema; no new key.
- Pinned-key table (test_ui_auth_escalation.py): PASS legitimate. Adds exactly "/schedule" to the GET project.view tuple and 4 POST rows for schedule.manage; nothing removed or weakened.
- Design rules: FAIL. `autotester doctor` reports file-too-long: tests/test_ui_auth_escalation.py is 302 lines (> 300). The maker's "doctor clean" claim is wrong. All new files <=300, functions <=50, no new models.
- Tests: 144 passed (schedule_routes, routers_list, ui_auth_escalation, schedule_model/wiring/marker/gate). ruff clean.

## Ruling on the 403 message
Contract TS1 literally says "403 naming schedule.manage". The shared T-204 gate (ui/auth_middleware.py:110) says only "you do not have permission for this action", for every key. Not met literally. Changing the shared gate message is out of this unit's scope; the clean resolution is a contract-wording change (the policy row names the key; the response need not) via qa/feedback-inbox.md, or a T-204 follow-up. Not blocking by itself; flagged for Umesh/contract owner.

## Defects
1. tests/test_ui_auth_escalation.py: 302 lines > 300 (doctor violation). Fix: split by responsibility or trim 2 lines.

## T-200 task-level criteria still unmet after this unit
- Persona walk (Mode D) - needs browser.
- HO24 owner disabled/deleted/lacking project.run -> slot refused.
- TS5/TS7 owner inbox and email delivery (waits on T-201 and email gate).
- Delete-project wiring (no whole-project delete path calls purge_project).
- 403-naming wording (above), and the "DELETE" method in TS1 evidence is POST /delete here (accepted).
- Task-level re-check of T-200.
