# t204-team-login persona walk (seat A, AU26)

Worktree wave/t204-team-login (aa6fec2e), uvicorn on 127.0.0.1:8791 (launcher PID 42100, listener PID 49516), AUTOTESTER_ROOT and AUTOTESTER_AUTH_DIR under the scratch dir, not hosted. Playwright headless, driven on http://localhost:8791 (the 127.0.0.1 origin had a stuck 25% browser zoom in the shared profile). Scratch accounts only; no password, hash or cookie value is in this evidence. Machine-readable results: report.json.

| # | Item | Result | Notes |
|---|------|--------|-------|
| 1 | Logged-out redirect, next= | PASS | every protected URL -> /auth/login?next=...; external next (https:// and //) refused after login, lands on / |
| 2 | Signup, short pw, duplicate, logout/back | PASS | first signup is Admin; server msg "a password needs 10 to 128 characters"; duplicate reveals existence (F1); Back never shows protected pages |
| 3 | Wrong password / lock | PASS | identical generic message for unknown email and wrong pw; 5 failures -> 429 "Too many sign-in attempts. Wait a few minutes"; per-account (F2) |
| 4 | Admin walk | PASS | Users, Groups, 4 seeded groups, `<b>x</b>` escaped, ticks persist, project grant/revoke effective for second account |
| 5 | Second account | PASS | waiting page, only Sign out; admin URLs 403; after group + share sees only its project; unshared project = same 404 as nonexistent (no leak); view-only user sees edit forms it cannot use (F4) |
| 6 | Credentials gating | PASS | viewer sees "SET" only, no value in HTML; admin sees masked value with show; add-credential by viewer 403 |
| 7 | A11y + 390px | PASS with findings | labels, tab order, Enter, focus visible, role=alert; no horizontal scroll at 390; email input unstyled (F5), weak error styling (F6) |
| 8 | Persona lens | FINDINGS | F4, F7, F8, F9 |
| 9 | Host guard | PASS | localhost 200, Host evil.example 403, Origin evil POST 403 |

## Findings (severity)
- medium F4: view-only users are shown write forms/links (Add case, Project settings, Credentials, Approve a crawl) that end in a bare 403; server-side blocks are correct.
- medium F5: email input on login/signup is unstyled and narrow next to the styled password field.
- medium F7: group permissions use raw keys (project.view, credentials.edit) with no plain-language help.
- low F1 (duplicate email reveals account), F2 (per-account lock refuses the right password too; no duration), F3 (favicon 401/403 console error), F6 (error text styled like normal text; no viewport meta), F8 (waiting page names no contact), F9 (terse 403 pages; no link to the access page from the project page; no save confirmation), F10 (Users/Groups header links unstyled; no security headers on /auth/login).

Console: 0 JavaScript errors; 86 error lines, all HTTP-status resource messages (favicon 401/403 and the deliberate 400/401/403 navigations).

Cleanup: browser closed, both server PIDs stopped, nothing listening on 8791, `git status --porcelain` in the worktree is empty.
