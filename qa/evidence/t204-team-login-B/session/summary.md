# t204-team-login blind security check B (session / auth, families A-F)

Code under test: worktree `.worktrees/t204-team-login` at aa6fec2e, against `qa/contracts/auth.md`.

**summary.md was not written.** The Write tool refused it ("Subagents should return findings as text, not write report files"). I did not route around that, so this reply is the summary. The scripts and raw outputs are in `D:/autoTesting/qa/evidence/t204-team-login-B/session/`:
- `common.py` and `run.sh`
- `famA_session.py`, `famB_passwords.py`, `famB2_limits.py`, `famB3_threshold.py`, `famB4_timing.py`
- `famC_ratelimit.py`, `famC2_tail.py`, `famC3_cap.py`
- `famD_privilege.py`, `famE_firstadmin.py`, `famE2_tail.py`, `famF_audit.py`
- one `.out` file per script

Method: in-process fastapi TestClient, plus scratch-env subprocesses for the CLI and env-var cases. No browser, network or pytest. No real data, no `.env` read, nothing under the worktree edited. My scratch dir is deleted; I removed only that one.

## Findings (ranked)

**Medium**
1. **A `users.manage` holder who is not Admin can take over non-Admin accounts that hold more permissions than it does (D).**
   - It reset the passwords of a Sub-admin and of a `settings.manage` account, then logged in as them. The `settings.manage` account got 200 on `/settings/providers`, where the manager got 403. This sidesteps "grant only what you hold".
   - Evidence: `accounts.py:147-151` and `access.py:142-149` protect only Admin/CEO targets.
2. **`bind_host()` only reads `sys.argv` and `UVICORN_HOST` (E).**
   - Evidence: `config.py:25-33`. gunicorn `-b 0.0.0.0`, hypercorn, `fastapi run` and `uvicorn.run(host=)` all look like 127.0.0.1.
   - In that state `AUTOTESTER_AUTH_DISABLED=1` is honoured, and anonymous requests get 200 on `/admin/users`, `/admin/groups`, `/settings/providers`, `/onboard`, `/live` and `/docs`.
   - An anonymous POST creating a `settings.manage` group returned 303.
   - The shipped entrypoint passes `--host 0.0.0.0` in argv, so it is caught there, and `HOSTED=1` also refuses.
3. **Ownership of `AUTOTESTER_FIRST_ADMIN_EMAIL` is not proven (E, by design).** There is no email verification, so whoever signs up first with that address, using any password, becomes admin. The CLI bootstrap can recover by resetting the password.
4. **A proxy that trusts everything lets anyone bypass the per-address limit (C, conditional).** With `ProxyHeadersMiddleware(trusted_hosts="*")` (the equivalent of `FORWARDED_ALLOW_IPS=*`), a varied `X-Forwarded-For` gave 40 failures with no 429. With the default trust (127.0.0.1) and the proxy elsewhere it is ignored.

**Low/Medium**
5. **AU27's last bullet is not met (D).** A refused attempt writes only a request line `{email,method,path,status:403}`, with no `{actor,target,action}` line. `routes_admin.py:76-78` returns before `audit.record_action`.
6. **Behind a single-address proxy (the Caddy topology), the limits work against everyone (C).** Everything arrives from the proxy address, so 21 failures by anyone lock out all users, admins included. Ten signups lock out signup for everyone (`routes_auth.py:52` and `:73`). Separately, anyone can lock a known account with 5 wrong logins.

**Low**
7. A non-admin can rename an Admin/CEO account's display name (`accounts.py:154-159`; `set_display_name` takes no actor).
8. A non-admin `groups.manage` holder can delete the default Tester group and untick everything from Developer and Sub-admin. Developers then get 403 on `/`, and only an Admin can restore. AU10 and AU27 restrict only additions.
9. Login, signup and failed-login write action lines only, with no `{method,path,status}` line (AU22). The 400 and 429 refusals leave no trace: 21 failed logins gave 20 lines. The audit file has no size bound.
10. The 429 has no `Retry-After` header, although `.env.example` says it does.
11. **Timing oracle for accounts with legacy hashes (B).** A user with a cheap hash (t=1, m=8) takes a median of 16.5 ms on a wrong password, against about 113 ms for every other case.
12. Unicode email lookalikes create distinct accounts. Fullwidth, Turkish i and NFC vs NFD all do; the Kelvin sign collapses to `k`.
13. Account enumeration: a duplicate signup returns 400 "already exists", and a project share to an existing email returns 303 while an unknown one returns 400. AU6 permits the signup refusal.
14. No global signup cap: 40 signups from 40 addresses all succeeded. At 50,000 live keys each `record_failure` is O(n), about 30 ms under the global lock, and new keys stop being tracked. That needs about 2,500 distinct addresses in the 600 s window.
15. Ids of 99999999999999999999 on `/admin/users/<id>/name` and `/admin/groups/<id>` return 500 (an unhandled SQLite overflow), for an authorized admin only.

**Info**
- A refused request carrying an expired but known token deletes that session row (a write on a refused request).
- The audit file mode is not owner-only (666 on Windows). AU23's owner-only requirement covers the store only.

## Family outcomes

- **A. Session: PASS.**
  - Local http gives `at_session; HttpOnly; Max-Age=43200; Path=/; SameSite=lax`. An https base URL or hosted mode gives `__Host-at_session` plus Secure. There is no Domain attribute in any case.
  - Fixation: a preset cookie is never adopted. The store holds only a 64-character SHA-256.
  - GET logout gives 405; POST logout deletes the row and clears both cookie names.
  - Tampered, truncated, 100 KB and unicode cookie values all give 401. In hosted mode only the `__Host-` name is read.
  - Disable, group change and password reset take effect on the next request.
  - Concurrent sessions are independent, and sessions survive a restart.
  - `SESSION_HOURS` is clamped to 1..168.
- **B. Passwords: PASS on storage, leaks and AU2 equality, with the Low findings above.**
  - Hashes are argon2id with m=65536, t=3, p=4, and each user gets a distinct salt.
  - The canary was absent from sqlite, the audit file, the DEBUG log capture and 27 recorded responses.
  - Unknown, wrong-password, disabled (right and wrong password) and invalid-format logins all return 401 with one identical body.
  - Clean AU2 timing, n=25 each, median ms: unknown 113.3, wrong 112.6, disabled with right password 112.1, disabled with wrong password 110.7, invalid-format 113.1, right password (303) 124.3. The p10 to p90 spreads overlap at about 100-135 ms.
  - An earlier contended run showed about 730 ms medians with the same ratios. I discarded its absolute numbers.
- **C. Rate limit: PASS as specified, with findings 4, 6, 10 and 14.**
  - The limits are 5 failures per account, 20 per address, 10 signups per address, a 600 s window and 50,000 keys.
  - The limiter keys on `request.client.host` only; spoofed `X-Forwarded-For`, `X-Real-IP` and `Forwarded` do nothing by default.
  - Failure 21 from one address gives 429, and the right password is blocked from that address.
  - The lock expires between t+599 s and t+601 s. Hammering does not extend it, and a success does not reset the counter.
  - The 429 body is identical for existing and non-existing accounts.
- **D. Privilege: AU27 holds for grants; findings 1, 5, 7, 8, 13 and 15.**
  - Every admin route as sub, dev, tester and no-group users gives 403, or 404 for other projects, with nothing stored.
  - Mass-assignment extras are ignored.
  - IDOR and slug-traversal probes are refused.
  - XSS payloads are escaped.
  - AU9 holds in all seven probed forms, such as self-disable, self-delete and removing self from Admin.
  - The AU27 grant refusals all returned 403: joining Admin/CEO, ticking `settings.manage` or `credentials.view`, creating a group with `users.manage`, and editing Admin/CEO.
- **E. First admin: PASS on the specified paths; findings 2 and 3.**
  - Local: the first signup is admin. 10 trials of 2 concurrent first signups and one trial of 6 each gave exactly one admin.
  - Hosted with the variable set: lookalikes get no group. 6 trials of 4 concurrent signups gave exactly one admin and one owner row.
  - The startup warning appears exactly once when the variable is unset, blank or empty, and never when it is set or on loopback.
  - CLI: create, reset and promote work, and nothing leaks (no password, hash or other email). `--password X` is a usage error that does not echo the value. An unexpected error gives rc 1 with a clean traceback.
  - The AU17 matrix refuses `AUTH_DISABLED` for `HOSTED=1`, `UVICORN_HOST=0.0.0.0`, `--host 0.0.0.0` and `--host=0.0.0.0`. The gunicorn-style argv starts anyway (finding 2). `AUTH_DISABLED=true` is not honoured.
- **F. Audit: PASS on secrets and injection; findings 9 and the Info items.**
  - Ten unauthenticated state-changing requests carrying canaries wrote 0 lines.
  - Authenticated lines contain no query, body, cookie, password or hash.
  - Emails with quotes, CR/LF, U+2028, U+0085 and ESC are rejected or JSON-escaped. All 52 lines are valid JSON, with no forged keys or login lines.

## Timing and memory numbers

- **Login latency:** about 113 ms per attempt uncontended. The cheap-hash user is 16.5 ms. Raw data is in `famB4.out`.
- **Oversized bodies:**

| Body | Result | Time | Server memory |
|---|---|---|---|
| 1 MB password, login | 401 | 0.12 s | +5 MB peak working set (tracemalloc 2 MB) |
| 1 MB email, login | 401 | 0.14 s | +5 MB (tracemalloc 6 MB) |
| 50 MB password or email | 400 | 0.03-0.04 s | 0 MB delta |
| control request | | 0.01 s | |

  - Starlette bounds each form field at 1024 KB and the field count at 1000, so there is no amplification (`famB2.out`, `famB3.out`).
- **Limiter cap:** at 50,000 live keys, `record_failure` is about 30 ms each.
- **Signup cost:** 40 signups cost about 6 s of hashing.

## Not run or not measurable

- The uvicorn access log. The entrypoint uses `--no-access-log`.
- A real uvicorn socket server with real proxy headers. I emulated it with `ProxyHeadersMiddleware`.
- `--workers` and `--reload` argv propagation, and Linux file modes.
- Signup duplicate-vs-fresh timing.
- The sub-admin probes against p-dev were invalidated when the manager reset that account's password, and I did not re-run them. The dev and tester probes on p-dev were valid.
