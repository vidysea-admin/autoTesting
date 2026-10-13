# Verdict - t203c-viewonly-ws (independent checker, security focus)

Cycle checked: 1 · checked code: wave/t203c-viewonly-ws a92a74a6 · contract hosting.md HO12 (CRITICAL), auth.md AU14/AU16

**HO12: PASS (local half).** Container/Caddy probes are SERVER-GATED by the row's own words.

| Probe | Result |
|---|---|
| (1) other route to 5900/5901/6080/6081 | PASS. x11vnc both `-localhost`; websockify ports published nowhere in docker/compose.prod.yml (`expose` only, app 8000 on loopback). Only reachable via Caddy on the compose network. Note (non-blocking): dev-only docker-compose.yml publishes 6080 (input, pre-existing) and now 6081 on all interfaces with no auth; its header says local dev machine only and DEPLOY.md uses compose.prod.yml. |
| (2) matcher order / normalisation | PASS by design. `/novnc-view/*` and `/novnc/*` cannot match each other (the slash after novnc). The upstream port is fixed by the matched handler, never by the forwarded path, so any traversal or encoded form that still matches `/novnc-view/*` reaches only 6081 (-viewonly); one that matches `/novnc/*` was authorised need=control. Everything else VNC-ish hits `@vnc_other` 403, or the app (no novnc routes in src). Exact Caddy path cleaning (`..`, `%2e%2e`, `//`, case) = SERVER-GATED. |
| (3) forward_auth | PASS. Subrequest is GET to the fixed `uri` (client query not forwarded, so client cannot set `need`); request headers incl. Cookie are copied; non-2xx is relayed (401/302/403), error/timeout is 502. Fail closed. Live confirmation SERVER-GATED. |
| (4) -viewonly | PASS. Only the 5901 x11vnc has `-viewonly`; both on `:99`; websockify 6081 -> 5901, 6080 -> 5900 (test asserts). Typing-in-session-changes-nothing = SERVER-GATED. |
| (5) need handling | PASS. Unknown/empty/case-variant need = 400 for signed-in users, anon 401, no live.view 403; duplicate `need=view&need=control` resolves to last (control), the stricter, and is tested. |

Also: `/live` routes users without live.control to `/novnc-view/` (view_only=1 kept as a hint only); `/auth/check` stays in the live.view policy row (AU14), not public (AU16).

SERVER-GATED (Ubuntu/Docker): websocket probes per endpoint (viewer -> /novnc/ 403, /novnc-view/ ok, anon 401); `/novnc-view/../novnc/`, `%2e%2e`, `//novnc/` against Caddy; keystrokes via 6081 change nothing; two x11vnc on one Xvfb.

Tests: test_hosting_gaps, test_hosting_config, test_ui_auth_policy_table: 45 passed. doctor clean. ruff: 1 E501 tests/test_isolated_provider.py:59 (master, not this branch).
