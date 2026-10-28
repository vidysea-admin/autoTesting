# Verdict - signup-requests (coordinator B, Mode A, security trigger: auth)

**Verdict:** PASS
**Cycle checked:** 0
**Unit:** signup-requests, branch `fix/signup-requests`, commit 95b0ad10 off master 924d811a
**Judged against:** `qa/contracts/auth.md` (AU6, AU8, AU9, AU14, AU18, AU22, AU27, no-fire list), `qa/contracts/core-invariants.md`, CLAUDE.md design rules
**Checker:** fresh context, read-only toward src/ and tests/ (no source edits, no commit, no push, `qa/.paused` untouched, no `.env` read)

PASS carries three non-blocking findings (F1-F3) the maker or the coordinator should file as issues. None is a privilege escalation, a cross-user leak, a missed audit, or a CSRF gap.

## Commands I ran myself (inside the worktree, after the maker's last edit to routes_auth.py)

```
uv run pytest tests/test_ui_auth_*.py tests/test_ui_origin_guard.py tests/test_ui_signup_requests.py tests/test_portal_requests.py tests/test_portal_access.py
438 passed, 1 warning in 112.20s (0:01:52)

uv run ruff check src tests scripts
All checks passed!

uv run autotester doctor
doctor: clean
(3292 + 2 advisory decision-citation warnings, D-087, non-blocking, pre-existing)
```
Raw outputs: `.work/adv_signup/{test-run,ruff,doctor}` files (`.work_pytest_b.txt`, `.work_ruff_b.txt`, `.work_doctor_b.txt` under `.work/adv_signup/`).

Size limits (wc -l): accounts.py 290, routes_access_requests.py 161, video_portal_view.py 191, routes_auth.py 163, video_requests.py 176, admin_view.py 122, test_ui_signup_requests.py 209. All <= 300. Doctor (function <= 50, docstrings) is clean. The new functions are each under 15 lines.

## Adversarial probes (throwaway, `.work/adv_signup/test_adv.py`, not in tests/)

Run: `PYTHONPATH=tests uv run pytest .work/adv_signup/test_adv.py --rootdir=. -s`. Result: 28 cases; the only failures that expose product behaviour are the 4 parametrised F1 cases (`"²"`, 5000 digits, `99999999999999999999` as group_id; `99999999999999999999` as user_id). Two further early failures were bugs in my own probe (a waiting user sees their own email on their own waiting page; an anonymous GET answers 302 to login), and a corrected re-run passes.

| # | Attack | Result |
|---|---|---|
| adv1 | Non-admin `users.manage` holder approves into a group that carries `users.manage` (admin-only key) | 403, groups unchanged. PASS |
| adv2 | Holder of `project.view@own` approves into a group with `project.view@all` (scope widening) | 403, unchanged. PASS |
| (maker SR6) | Non-admin manager approves into Admin/CEO, and into Developer | 403, `signup.approve.refused` audited. PASS |
| adv3 | Approve / decline a disabled account | 400 both, nothing changes. PASS |
| adv4 | Decline the Admin account (grouped) | 400, still enabled. PASS |
| adv7 / 7b | `access.approve`-only reviewer, a waiting (groupless) user, anonymous: POST approve/decline and GET page | 403 / 302-to-login; reviewer's page lists no waiting emails; account unchanged. PASS |
| adv8 | CSRF: `Origin: http://evil.test`, `Origin: null`, `Sec-Fetch-Site: cross-site`, `Referer: evil`, on approve and decline; GET on the POST route | all 403 (GET 404/405), nothing changes. PASS |
| adv9 | 6 concurrent approvals of one waiting account into 6 different groups | exactly one 303, exactly one membership (BEGIN IMMEDIATE + in-transaction re-check). PASS |
| adv10 | Stored XSS: email `<svg/onload=alert(1)>@x.test` (passes `normalize_email`), group name `<b>bold</b>` | escaped on `/access-requests` and `/admin/users`. PASS |
| adv11 | Refusal page and audit file for secrets / tracebacks | none. PASS |
| adv12 | SMTP configured, transport raises `smtplib.SMTPServerDisconnected` (not a `TransportError`), and `select_transport` raising `RuntimeError` | signup still 303, account created. PASS |
| adv13 | Groupless signup notifies exactly once; a duplicate-email signup (400) does not notify | PASS |
| adv14 | Default video-request mail byte-identical; `body=""` falls back to the default | PASS |
| adv15 | Audit rows `signup.approve` and `signup.approve.refused` both written | PASS |
| adv5 | `group_id` = `"²"` (superscript), 5000 digits, `99999999999999999999` | **unhandled exception (500)**, see F1. Other values (`-1`, ` 3`, `1e3`, `0`, `3\n`, `٣`, fullwidth `３`) give 303/400. |
| adv6 | `user_id` in path = `99999999999999999999` | **OverflowError (500)**, see F1 (same on a pre-existing route). |

Route-table completeness (AU14): both new POST routes are in `PORTAL_POLICY` (`auth/policy.py:62-64`, `users.manage`) and pinned in `tests/test_ui_auth_policy_table.py:79-80`; `test_au14_every_policy_row_requires_exactly_its_pinned_key` and the route-enumeration tests are in the 438 passed. Origin guard (AU18) covers them globally (adv8).

## Findings

**F1 (low, robustness, new code) - an unhandled exception on a crafted `group_id` or `user_id`.**
`src/autotester/ui/routes_access_requests.py:121` guards with `raw.isdigit()`, then `:123` calls `int(raw)`. `str.isdigit()` is True for characters that `int()` rejects (`"²"`), so `int()` raises `ValueError` and the request ends in a 500. A digit string over 2^63 passes both and then raises `OverflowError` from sqlite in `approve_waiting` (`auth/accounts.py:~255`). Likewise a path `user_id` over 2^63 raises `OverflowError` at `accounts.get_user` (`auth/accounts.py:164`, reached from `routes_access_requests.py:113`). Reach: only an authenticated `users.manage` holder. No state change, no leak, no escalation. The pre-existing `/admin/users/{id}/{action}` has the same `user_id` overflow (probe adv16: it RAISES `OverflowError`), so the `user_id` half is an inherited pattern; the `isdigit()` guard is new and is strictly weaker than the existing `_ints` in `routes_admin.py:49-53` (`int()` inside try/except ValueError -> 400). Suggested fix: `try: gid = int(raw) except ValueError` plus a bound check (`0 < gid < 2**63`), returning the same 400 "choose a group"; add a SR3 case for `"²"`.

**F2 (note for the contract owner, not a unit defect) - the auth contract no-fire list says "No change to `stages/`".**
`auth.md` no-fire list (line 287) names `stages/`; this unit edits `stages/video_requests.py:151-170` (optional `subject` / `body`, default output byte-identical, verified by SR9 and adv14). That line was written for T-204's original build, and `video_requests.py` is a Group 10 module that the contract treats as out of scope for auth. I judged the edit acceptable as a scoped, backward-compatible extension, but the literal rule is violated; ask Umesh / the contract maintainer to scope that line (or confirm) rather than letting it pass silently.

**F3 (observation) - the signup mail is sent inside the signup request.**
`routes_auth.py:84-95,109-110`: `_tell_user_managers` runs synchronously before the response. A broken or slow SMTP server cannot block signup by exception (adv12 proves that), but only the transport's own timeout bounds the delay (`delivery/email.py:121` passes a `timeout`; I did not verify its default). Signup is rate-limited by `signup_limiter`, which also bounds the mail volume to admins. Not blocking; a background send would be cleaner.

## Other checks (no finding)

- **Escalation:** `approve_waiting` runs `access.require_may_regroup` inside the write transaction (`accounts.py` new block after `set_user_groups`): Admin/CEO membership stays admin-only (AU27), a grant needs every permission and scope the actor holds, and admin-only keys need Admin. `decline_waiting` uses `require_may_touch`. Actor `None` means the system / CLI, as for the existing functions.
- **State races:** `_require_waiting` re-checks enabled + no group inside the same `BEGIN IMMEDIATE` as the write (adv9, SR5).
- **Info leak (AU6, AU13):** the waiting list and the group picker render only when `authorize(who, USERS_MANAGE)`; non-manager response bodies hold no waiting email. Waiting users still get only the waiting page (AU6). `GET /access-requests` still needs `access.approve` (disclosed known limit; a users.manage-only holder uses the Waiting pill on `/admin/users`).
- **Audit (AU22):** success and refusal rows carry `{actor, target, action}`; the middleware line still records status; no body, password or session value (adv11, adv15).
- **Mail never blocks signup:** try/except Exception around `user_managers()` and `notify_approvers()`; the mail body names no one and carries only the origin-derived link; `Host` is covered by the AU19 allow-list.
- **Duplicated concepts:** one mailer reused (no second notifier); one `still waiting` check shared by approve and decline; `list_waiting` is the only waiting definition for the page, and the Waiting pill in `admin_view.py:39-44` repeats the predicate `not disabled and not groups` (minor, same one-line rule).
- **Independent senior-engineer review:** the manifest says the maker could not dispatch it; this check is not that review. Coordinator should still run the `senior-software-engineer` agent before close-out (lifecycle `review` rule).

## Re-derive

`PYTHONPATH=tests uv run pytest .work/adv_signup/test_adv.py --rootdir=. -s` inside the worktree (requires `.work/adv_signup/test_adv.py`, which is not committed and may be deleted after the verdict is read).
