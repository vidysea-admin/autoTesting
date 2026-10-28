# Verdict - signup-requests

**Verdict:** PASS
**Cycle checked:** 0
**Checker:** coordinator A (Mode A, security trigger: auth). Worktree `D:/autoTesting/.claude/worktrees/agent-accf8a0414496c0ce`, branch `fix/signup-requests`, commit 95b0ad10 (off master 924d811a). Read-only toward source; no commit, no push, `qa/.paused` untouched, no `.env` read.
**Judged against:** `qa/contracts/auth.md` (AU6, AU8, AU9, AU10, AU14, AU18, AU19, AU22, AU27), `qa/contracts/core-invariants.md`, CLAUDE.md design rules.

## Verify commands, re-run by the checker (after the maker's last edit to routes_auth.py)

`uv run pytest tests/test_ui_auth_*.py tests/test_ui_origin_guard.py tests/test_ui_signup_requests.py tests/test_portal_requests.py tests/test_portal_access.py`
```
438 passed, 1 warning in 108.59s (0:01:48)
exit 0
```
`uv run ruff check src tests scripts`
```
All checks passed!
```
`uv run autotester doctor`
```
... (advisory decision-citation-* warnings only, D-087 non-blocking)
doctor: clean
```
Sizes (lines): accounts.py 290, routes_access_requests.py 161, video_portal_view.py 191, routes_auth.py 163, video_requests.py 176, admin_view.py 122, policy.py 205, tests/test_ui_signup_requests.py 209. All <= 300. New functions all well under 50 lines; module docstrings unchanged and still true.

## Adversarial probes (temporary test file, deleted afterwards; no source edited)

| Probe | Result |
|---|---|
| Approve a **disabled** account (UI route) | 400, no membership added; decline of a disabled account also 400 |
| Approve an **already-grouped** account | 400 (maker's SR5), unchanged |
| `users.manage`-only manager approves into **Admin/CEO** | 403, nothing stored, audited `signup.approve.refused` (SR6 + probe) |
| Same manager approves into a group beyond their rights (Developer) | 403 (SR6) |
| Same manager approves into an empty-permission group | 303, allowed (correct: nothing minted beyond what they hold) |
| Admin approves into Admin/CEO | 303 (AU27: admin may) |
| Waiting (no-group) user POSTs approve for another waiting account | 403, nothing stored; their `GET /access-requests` is 403 |
| Anonymous POST approve | 401 |
| Refusal re-render for a manager: body leaks video requests? | No: `pending_for` filters by `authorize` (video text absent) |
| Mutation: `access.require_may_regroup` made a no-op | SR6 fails (guard is load-bearing) |
| Mutation: `_require_waiting` made a no-op | SR5 fails (guard is load-bearing) |
| Mutation: route-level `_manager()` made a no-op | SR2 still passes: the central policy row is the primary gate, `_manager()` is defence in depth (see finding 4) |
| Cross-site POST (Origin evil.test) to approve and decline | 403 (SR7); the global Origin guard (AU18) covers them with no per-route code |

## Findings

Blocking: none.

1. **WARNING (non-blocking, robustness) - 500 on crafted `group_id`.** `src/autotester/ui/routes_access_requests.py:121` validates with `str.isdigit()`, which accepts non-ASCII digits (for example superscript two) and arbitrarily long digit strings. `int()` then raises ValueError, and a value above int64 reaches sqlite and raises OverflowError. Probed as an authenticated Admin: `group_id` = superscript two, 5000 nines, and 99999999999999999999 each returned **500**, with no state change (the transaction never opens an insert). Authenticated `users.manage` holder only, no data effect, so not blocking. Fix suggestion: reuse `routes_admin.py:49 _ints` style (`try int(); except ValueError -> 400`) and bound the value, then add one SR3 case. For the maker's next cycle, if any.
2. **NOTE - mail volume on open signup.** `routes_auth.py:84-110` mails every `users.manage` holder on each groupless signup. Open signup is bounded only by `signup_limiter` per client address (existing, AU6), and mail is sent synchronously with `SMTP_TIMEOUT_SECONDS = 15.0` (`delivery/email.py:44`) per recipient. Failure is caught and logged by class (`routes_auth.py:90-95`), and mail only goes out when SMTP is configured, so signup is never blocked by an error, but a slow SMTP server could delay the signup response. Acceptable; flag for a later unit if signup abuse appears.
3. **NOTE - link host.** The mail link is built from `request.base_url` (`routes_auth.py:88`). It is trustworthy because the AU19 Host allow-list refuses unlisted Hosts before routing, so an unauthenticated signup cannot plant an attacker host in an admin mail. This holds only while AU19 stays in force (hosted mode requires the allow-list, AU20).
4. **NOTE - redundant guard.** `routes_access_requests.py:103 _manager()` duplicates the policy-table check; mutation shows no test depends on it. Keep as defence in depth, no action.
5. **NOTE - duplicated SQL shape.** `accounts.py:153 user_managers()` repeats the memberships/group_permissions join already present in `video_requests.py:139` (`approvers`) and `sessions.py:75`, differing only in the permission key. Three near-copies now; a later cleanup unit could extract one "emails holding permission X" helper. Not a violation of "a class or function defined in two modules" (different function, different key), so non-blocking.
6. **NOTE - audit detail.** `signup.approve` records actor, target and action only (`routes_access_requests.py:131`), not which group was granted, consistent with the existing admin membership audit. A 404 target (no such account) is not audited, but nothing changes. Meets AU22 as written.
7. **Observation matching the manifest's known limit.** `GET /access-requests` still needs `access.approve`; a `users.manage`-only holder gets 403 there but can act via the POST routes and sees the Waiting pill on `/admin/users`. Consistent with AU8; no leak, and non-managers never get the "New accounts waiting" section or any waiting email (SR2 plus `routes_access_requests.py:86-95`: `waiting` is None unless `authorize(users.manage)`).

## Criteria walk

- Privilege escalation via approve: closed. `approve_waiting` (`accounts.py:246`) reuses `require_may_regroup` and so AU27 (Admin/CEO admin-only, grant only held permissions, admin-only keys). Verified by SR6, the probes and the mutation.
- Disabled or already-grouped target: refused inside the same `BEGIN IMMEDIATE` transaction that writes (`_require_waiting`, `accounts.py:237`), so there is no check-then-act window.
- CSRF/origin: both POSTs are behind the global Origin guard (AU18); SR7 proves 403.
- Route-table completeness (AU14): both new rows are in `PORTAL_POLICY` (`policy.py:62-64`) keyed `users.manage`; `test_au14_every_policy_row_requires_exactly_its_pinned_key` and the route-enumeration tests pass in the 438.
- Audit coverage: success and refusal audited for both verbs. Decline also ends sessions in the same transaction.
- Mail never blocks signup: outer `try/except Exception` plus per-address catch in `notify_approvers`; SR9 proves signup 303 on a raising notifier. Default video-request mail byte-identical (SR9 third test).
- Info leaks to non-managers: none found (see finding 7).
- XSS: email, group name and message go through `esc()` in `video_portal_view.py`.
- File/function size and duplicated concepts: within limits; see finding 5.

## Residual risk

The maker did not run the independent senior-engineer review (manifest note); this checker covered correctness and security independently by re-running the suite and adversarial probes, but did not substitute an Approve/Warning/Block from that agent. Finding 1 is the only code defect found and is non-blocking.
