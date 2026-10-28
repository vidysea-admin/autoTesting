# Manifest - signup-requests

**Status:** checked-PASS (dual A+B cycle 0: qa/verdicts/signup-requests.md + signup-requests.b.md; senior review Warning, non-blocking F1 follow-up)
**Fix cycle:** 0
**Issues addressed:** Umesh 2026-10-28 (live Cloud Run): a person who signs up lands on the waiting-for-admin page but the admin never sees a request (account umeshsugara@vidysea.com ACTIVE, zero groups; `/access-requests` listed only video share-link requests; nothing notified admins).
**Branch:** `fix/signup-requests` (worktree `D:/autoTesting/.claude/worktrees/agent-accf8a0414496c0ce`, off master 924d811a)

## What changed
- `auth/accounts.py`: `list_waiting()` (enabled, no group), `user_managers()` (emails of enabled users.manage holders), `approve_waiting(user_id, group_id, actor)` and `decline_waiting(user_id, actor)`. Both re-check "still waiting" inside their own write transaction (so approve/decline cannot overwrite an already-decided account), approve reuses `access.require_may_regroup` (no Admin/CEO and no group beyond the actor's rights), decline reuses `access.require_may_touch` and ends the sessions.
- `ui/routes_access_requests.py`: `/access-requests` renders a "New accounts waiting" card only for a users.manage holder; `POST /access-requests/accounts/{user_id}/approve` (form `group_id`) and `.../decline`; refusals are re-rendered on the page (400, or 403 for NotAllowed) and audited as `signup.approve.refused` / `signup.decline.refused`; successes as `signup.approve` / `signup.decline` via `auth.audit.record_action`. Both POSTs sit behind the existing global origin guard (cross-site -> 403).
- `ui/video_portal_view.py`: `approver_requests_page` takes optional `waiting`, `groups`, `message` (section hidden when `waiting` is None).
- `auth/policy.py`: two new rows, `users.manage`.
- `stages/video_requests.py`: `notify_approvers` gets optional `subject` / `body` (template with `{link}`); the default mail is byte-identical.
- `ui/routes_auth.py`: after a signup that joins no group, `_tell_user_managers` calls `notify_approvers(user_managers(), <base>/access-requests, ...)`; any failure is logged by class and never blocks the signup. Mail only goes out when SMTP is configured (existing behaviour).
- `ui/admin_view.py`: groupless, enabled accounts show a `Waiting` pill on `/admin/users`.
- `tests/test_ui_auth_policy_table.py`: pinned the two new rows. New `tests/test_ui_signup_requests.py` (16 tests, SR1-SR9).

## Known limits (for the checker)
- `GET /access-requests` still requires `access.approve` (unchanged policy row), so the new section is seen by a person holding both `access.approve` and `users.manage` (Admin/CEO has both). A users.manage-only holder uses `/admin/users`, which now shows the Waiting pill.
- The signup mail names no one (a link only), same as the video-request mail. No mail is sent without SMTP config.
- Independent senior-engineer review was not run by the maker (agent dispatch blocked in this seat by the compact-handoff hook); left for `/checker`.

## Verify (run in the worktree)
`uv run pytest tests/test_ui_signup_requests.py tests/test_ui_auth_policy_table.py` BEFORE the src change (src reverted to master, tests kept):
```
FAILED tests/test_ui_signup_requests.py::test_sr1_... test_sr2_... test_sr3_(x2) test_sr4_... test_sr5_(x2) test_sr6_... test_sr8_... test_sr9_(x3)
FAILED tests/test_ui_auth_policy_table.py::test_au14_every_policy_row_requires_exactly_its_pinned_key
13 failed, 3 passed, 1 warning in 80.89s (0:01:20)
```
`uv run pytest tests/test_ui_auth_*.py tests/test_ui_origin_guard.py tests/test_ui_signup_requests.py tests/test_portal_requests.py tests/test_portal_access.py` AFTER:
```
438 passed, 1 warning in 113.72s (0:01:53)
```
`uv run ruff check src tests scripts`:
```
All checks passed!
```
`uv run autotester doctor`:
```
doctor: clean
```
(advisory decision-citation warnings pre-exist and are non-blocking per D-087.)
File sizes: accounts.py 290, routes_access_requests.py 161, video_portal_view.py 191, routes_auth.py 163 (all <= 300).
