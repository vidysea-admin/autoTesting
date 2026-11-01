# Verdict - e2e-fixes-e6 (checker B: security of the live relay)

**Unit:** e2e-fixes-e6 (E6, AT-1419). **Cycle checked:** 1. **Verdict: PASS** (4 warnings, none blocking).
**Code checked:** branch `feat/e2e-e6` head `331fc2f5`. Contract `qa/contracts/e2e-fixes.md` E6.1-E6.9; D-131 (`docs/DECISIONS.md:3106`, ACTIVE, `Approved-by` Umesh) satisfies E6.9.
**Scope of this verdict:** security of `src/autotester/ui/routes_live.py` and `routes_auth.py::live_access_refusal`, plus a code review. I did not read any other checker's verdict. Read-only toward src/tests/docker.

## Commands re-run by me (worktree, `-o addopts=`, 2 files per call, TMP under `.work/`)

| Command | Result |
|---|---|
| `pytest tests/test_live_proxy_http.py tests/test_live_default_url.py` | 39 passed |
| `pytest tests/test_live_proxy_ws.py tests/test_ui_auth_policy_table.py` | 15 passed |
| `pytest tests/test_hosting_gaps.py tests/test_ui_auth_surface.py` | 59 passed |
| `pytest tests/acceptance/test_ta02_nothing_before_access.py tests/test_ui_auth_escalation.py` | 29 passed |
| `ruff check src tests scripts` | All checks passed |
| `autotester doctor > .work/doctor-chkb.txt` | exit 0, last line `doctor: clean` |
| `git diff <merge-base of HEAD and 6eb21a54> HEAD --stat -- src docker pyproject.toml uv.lock` | 5 files only (`policy.py` +2, `routes_auth.py`, `routes_live.py`, `pyproject.toml` +1, `uv.lock` +2); `docker/` untouched (E6.8) |
| count of the `need not in ("view", "control")` decision | `routes_auth.py`: 1, `routes_live.py`: 0 (E6.3 one decision) |

## Mutation sample (my own run via `scripts/mutation_check.py`, 7 of the 26)

http spec subset: a1 upstream from request Host, a3 leading `//` allowed, a6 Cookie forwarded, a9 shared decision drops the `live.control` check, a11 `/vnc.html` look-alike unguarded: **5/5 KILLED**. ws spec subset: b1 websocket auth skipped, b3 Origin not checked: **2/2 KILLED** (b1 killed by 5 auth-matrix cases, no vacuous kill). Worktree clean afterwards (`git status` empty).

## Independent real-server probe (not the TestClient)

I started the real app (`python -m uvicorn autotester.ui.app:app`, auth ON, fresh data root under `.work/probe`), signed up and logged in as the first account (admin), put a `websockets` echo server on 127.0.0.1:6080/6081 and drove the relay with a real websocket client (script `.work/probe/probe.py`, gitignored, not committed). Observed:

| Case | Result |
|---|---|
| WS, no cookie, upstream UP | `HTTP 403` on the upgrade (refused before accept; upstream never reached) |
| WS, admin cookie, `Origin` = app origin, upstream UP | OPEN, bytes echoed unchanged |
| WS, admin cookie, `Origin: https://evil.example` | HTTP 403 |
| WS, admin cookie, `Origin: null` | HTTP 403 |
| WS, admin cookie, `Host: evil.example` | HTTP 403 |
| WS, admin cookie, no `Origin`, upstream DOWN | accepted then close 1011 (no address in the close) |
| HTTP anon `GET /novnc/vnc.html` | 401 (JSON); with `Accept: text/html` 302 to login |
| HTTP admin, upstream down | 502 |
| HTTP admin `/novnc`, `/novnc/` | 403 |
| HTTP admin `/novnc/%2e%2e/x`, `//evil.com/x`, `..%5cx`, `http://x/` | 400 x4 |
| HTTP anon `/vnc.html` | 401 |

This confirms what the TestClient cannot: uvicorn answers `close(1008)` before accept as HTTP 403, and the login gate (HTTP-only ASGI middleware, `ui/auth_middleware.py` `_AuthGate.__call__` returns early for non-http scopes) and the Origin/Host guard really do not see websocket scopes, so the in-handler checks are load-bearing and present.

## Security findings by attack class

1. **Anonymous or wrong-role access: sound.** HTTP: the gate answers anonymous 401/302 before the handler (policy rows `auth/policy.py:83`); the handler repeats `live_access_refusal(current_principal(), _NEED[prefix])` (`routes_live.py:131`) so `/novnc` needs control and `/novnc-view` needs view, matching the Caddy `forward_auth` contract. WS: `_ws_refusal` (`:166-175`) runs before `accept()` (`:211-213`): Host (`_host_allowed`), Origin, then session via the gate's own `_principal` and the same `live_access_refusal`. One decision function serves `/auth/check` and both relays (`routes_auth.py:148-164`). An unknown `need` is 400 (fail closed).
2. **WebSocket upgrade without session: refused, upstream not dialled** (probe row 1; the test matrix asserts zero stub contacts for every denied cell).
3. **Cross-site websocket hijack: closed.** Origin must be http/https, its netloc must equal the (allow-listed) Host, and a `wss` request refuses an `http` Origin (`:151-163`). A missing Origin is judged by cookie and permission only, as the contract says. `Origin: null` refused (probe).
4. **SSRF / open relay: none.** HTTP upstream is `http://{host}:{port}/` with host and port from the module constant `VNC_UPSTREAMS` (`:118`), path re-quoted with `quote(path, safe='/')` (`:140`), `_BAD_PATH` rejects NUL and control chars, backslash, `..`, a leading `/`, and a scheme (`:126`). Starlette hands over the decoded path so `%2e%2e`, `%5c`, `%2f%2f` are caught (probe: 400). The query is appended after the fixed authority and cannot change the host. `trust_env=False` (no proxy env var), websocket `proxy=None`; the target is not influenced by Host, headers, or environment. Only 127.0.0.1:6080/6081 are reachable.
5. **Header and cookie leakage: none.** The request side is an allow-list of 5 headers (`:121`), so no Cookie, Authorization, or X-Forwarded-*. The response side returns only content-type, last-modified, etag (`:122`): no Set-Cookie, Location, or Server. The auth gate stamps `Cache-Control: no-store` on signed-in responses (`ui/auth_middleware.py:151-154`). I found no app-level X-Frame-Options or CSP (grep of `ui/*.py`), so the same-origin iframe is not blocked by the app.
6. **Look-alike answers.** `/novnc`, `/novnc-view`, `/websockify`, `/websockify/*`, `/vnc.html`, `/vnc_lite.html` are never relayed; admin gets 403 (probe), anonymous gets the gate's 401/302 (probe). The contract text of E6.5 says 403 "authenticated or not"; D-131 (Result) records the anonymous 401/302 answer as approved, and a `public` row to make it literal would break AU16. Not a security weakness (the anonymous answer is the same as for every other protected path and leaks nothing), see W1.
7. **Size and idle limits.** Frames capped at 32 MiB (`_MAX_FRAME :123`, upstream `max_size` plus a client-side check; uvicorn's own default 16 MiB websocket limit applies in front of that for client frames). Connect 3 s, read 15 s. The HTTP response is buffered whole (noVNC static files only). No idle timeout, no per-account connection cap, and no re-check of the session after `accept()` (W2, W3).

## Code review notes (senior-engineer style)

- Structure is clean and small (299 lines, doctor clean, functions under the limit). One mapping is the only upstream seam (E6.8). No new module; edited in place; C3 respected via `live_access_refusal`.
- `_pump` (`:192-206`) cancels both tasks, gathers with `return_exceptions`, closes upstream, maps close codes; no leaked task on either side leaving (mutant b4 killed by a stub-saw-close assertion).
- `_client_to_upstream` (`:177-184`): `message.get("bytes") or message.get("text") or b""` silently skips empty frames; harmless for VNC. Text and binary are preserved (mutant b6 killed).
- `_relay_ws` `except Exception` (`:222`) is broad but correct here (every failure maps to 1011 without leaking the address); `CancelledError` is not swallowed.
- Cross-module import of the underscore names `_principal` and `_host_allowed` is a style smell; defensible to keep one definition (C3).
- `# type: ignore[arg-type]` at `:175` passes an `HTTPConnection` where `Request` is annotated; `_principal` only reads cookies, so it is correct today but couples to that detail.
- `_BAD_PATH` rejects any `..` substring, so a legitimate file such as `a..b.js` would 400; over-strict, safe.
- An upstream redirect (for example a directory without trailing slash) is returned without `Location` (dropped by the allow-list); safe, a latent functional quirk not hit by `vnc.html`.

## Warnings (non-blocking, none changes PASS)

- **W1 (contract wording).** E6.5 says 403 for look-alikes "authenticated or not"; delivered behaviour is 403 signed-in and 401/302 anonymous, approved in D-131. The contract owner should reword E6.5 to match (checker amendment; I did not touch `qa/contracts/`).
- **W2 (session lifetime).** Auth is evaluated at the handshake only: a socket stays open after logout, session expiry, or permission revocation until either side closes. Same as Caddy `forward_auth` today, so not a regression; worth a follow-up (a periodic `resolve_session` re-check, or a maximum socket lifetime).
- **W3 (resource caps).** No per-account or global limit on concurrent relay sockets and no idle or ping timeout (`ping_interval=None`, `:219`); an account holding `live.view` can open many sockets to the shared x11vnc. Authenticated only, low severity; same as Caddy.
- **W4 (not exercised).** No real browser against a real websockify/noVNC container, nothing behind Cloud Run's HTTP/2 front, and the upstream-to-client oversize direction relies on `websockets`'s own `max_size` (manifest note 7). The `senior-software-engineer` review agent was not dispatched by the maker (manifest note 8); this verdict is independent but does not replace the lifecycle review step. Master has advanced since the merge base (`b3663ac3`), so the integrating merge must re-run the two E6 test files.

## Criteria status (from my own evidence)

E6.1 PASS (probe, tests, a1/a3/a6 killed). E6.2 PASS (probe echo, tests). E6.3 PASS (one function; probe 403 on upgrade; a9/b1 killed). E6.4 PASS (probe; b3 killed). E6.5 PASS with W1. E6.6 PASS by tests (39 passed; not re-probed on Cloud Run). E6.7 PASS (probe: 502 and 1011, no address). E6.8 PASS (docker untouched, mapping constant). E6.9 PASS (D-131 ACTIVE).

No `.env` value was read or printed. The probe data root and script live under the gitignored `.work/`.
