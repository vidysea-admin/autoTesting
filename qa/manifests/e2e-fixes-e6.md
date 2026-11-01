# Manifest - e2e-fixes-e6

**Status:** ready-for-check
**Fix cycle:** 1
**Contract:** `qa/contracts/e2e-fixes.md`, unit E6 (AT-1419). **Criticality:** MEDIUM (a new network surface; the auth decision is HIGH-sensitivity, see judgement calls 1-3).
**Authority:** E6.9 is SATISFIED: D-131 is ACTIVE on master (b3663ac3, `Approved-by` Umesh; `grep -n "AT-1419" docs/DECISIONS.md` hits `## D-131`), cited here. It authorizes the relay and states that an anonymous caller of a look-alike path gets the gate's 401/302 (judgement call 3). No new `src/` module (CLAUDE.md), no `qa/contracts/` edit.
**Branch:** `feat/e2e-e6` (worktree `D:/autoTesting/.claude/worktrees/e2e-e6`), cut from master `70a7a486`. Not merged, not pushed (D-130).
**Base SHA:** `70a7a486`; cycle 1 merged master (E5 `58e8cf15`, D-131) at `0d69b1ce`. The only conflict was `core/env.py`: E5's single `on_cloud_run` and shortened docstring kept, the E6 copy dropped (file identical to master, 300 lines).
**Code SHA:** the commit that adds this file, `git log -1 feat/e2e-e6`.
**Criteria judged by E6:** E6.1 - E6.9.

## What changed

| File | Kind | One job / change |
|---|---|---|
| `src/autotester/ui/routes_live.py` (299 lines) | E in place | the relay. `VNC_UPSTREAMS :118` (the one mapping, E6.8), `_NEED :120`, `_MAX_FRAME :123`, `_BAD_PATH :126`, `_relay_http :129`, `_own_origin :151`, `_ws_refusal :166`, `_client_to_upstream :177`, `_upstream_to_client :187`, `_pump :192`, `_relay_ws :209`, `_register :228` (both prefixes: `GET {prefix}/{path:path}` + `WebSocket {prefix}/websockify`), `_forbidden :240` + look-alike loop `:247`. `novnc_url :57` default is `_CLOUD_RUN_NOVNC :54` when `on_cloud_run()` (E6.6); `view_only_url`/`viewer_url` untouched. |
| `src/autotester/ui/routes_auth.py` | E in place | `live_access_refusal :148` is the ONE decision (401 / 400 unknown need `:157` / 403 no `live.view` / 403 `need=control` without `live.control`); `auth_check :167` now calls it (same statuses and bodies as before). |
| `src/autotester/auth/policy.py` | E in place | `:83` two rows `GET /novnc/{path:path}`, `GET /novnc-view/{path:path}` -> `live.view` (the login gate then handles unauthenticated HTTP: 401/302). |
| `src/autotester/core/env.py` | E in place | `on_cloud_run :110` (`K_SERVICE` set and non-blank). **E5.4's single definition is the one kept (merge `0d69b1ce`).** After the cycle-1 merge `core/env.py` is byte-identical to master (300 lines). |
| `pyproject.toml`, `uv.lock` | E | `websockets>=15.0` declared direct: `autotester doctor` rule `undeclared-dependency` (it was only transitive via `uvicorn[standard]`). `uv.lock` edited by hand, two lines (a real `uv lock` upgraded every package, discarded); `uv lock --check --offline` passes. |
| `tests/test_ui_auth_policy_table.py` | E (additive) | `EXPECTED` gains the two relay rows (the test pins the whole table). |
| `tests/live_stub.py` | N (helper) | one websockify stand-in per port: HTTP + websocket echo on one loopback port, records every contact and frame. |
| `tests/test_live_proxy_http.py` (28 cases), `test_live_proxy_ws.py` (13), `test_live_default_url.py` (12) | N | see the criteria map. |
| `docs/MAP.md`, `docs/SNAPSHOT.md` | regenerated | `autotester map` / `snapshot` (SNAPSHOT also moves its newest-decision line D-125 -> D-130: stale on master). |
| `qa/evidence/e2e-fixes-e6/` | N | `mutations-http.json`, `mutations-ws.json`, `mutation-run-http.txt`, `mutation-run-ws.txt`. |

## Criteria map

| Crit | Code | Test (falsifier it kills) |
|---|---|---|
| E6.1 same-origin HTTP proxy, prefix stripped, loopback only, no SSRF, hop-by-hop dropped, no Cookie/Authorization | `routes_live.py:129-148` (`url` from `VNC_UPSTREAMS`, never the request; allow-list of 5 forwarded request headers `:121`, 3 returned `:122`; `trust_env=False`) | `test_live_proxy_http.py::test_relay_strips_prefix_and_drops_cookie_and_authorization` (stub saw `/vnc.html`, no `cookie`, no `authorization`), `::test_view_endpoint_reaches_only_the_view_upstream`, `::test_hostile_paths_are_refused_before_any_connection[7 ids: // , %2e%2e, ..%2f, backslash, NUL, scheme, a%2f..%2fb]` (400, zero stub contacts), `::test_request_host_never_picks_the_upstream` (`Host: evil.example` still reaches only the stub) |
| E6.2 websocket proxy, bytes and text unchanged, `binary` subprotocol, close propagates, frame cap 1009 | `routes_live.py:177-225` | `test_live_proxy_ws.py::test_frames_relay_both_ways_and_close_propagates` (bytes, text, `accepted_subprotocol == "binary"`, stub saw the close within 2 s), `::test_oversize_frame_closes_1009` (code 1009 AND the stub received no frame) |
| E6.3 one auth function, checked on every request, websocket BEFORE accept, upstream never dialled when denied | `routes_auth.py:148-164` shared by `auth_check :167` and `routes_live.py:129,166-175`; `_ws_refusal` runs before `accept()` `:211-213` (refusal -> `close(1008)`, which answers the upgrade 403) | `test_live_proxy_http.py::test_auth_matrix_http` and `test_live_proxy_ws.py::test_auth_matrix_websocket`: 8 ids each ({no session, tester (no live.view), dev (live.view only), admin (control)} x {`/novnc`, `/novnc-view`}); every denied case asserts zero stub contacts. `test_live_default_url.py::test_one_function_holds_the_need_decision` (grep-equivalent: exactly one `need not in ("view", "control")` in `routes_auth`, none in `routes_live`). The existing `/auth/check` tests (`test_hosting_gaps.py::test_auth_check_*`, `test_auth_check_decision_matrix`) pass unmodified |
| E6.4 cross-site websocket refused | `routes_live.py:151-163` (`_own_origin`), `:166-175` | `test_live_proxy_ws.py::test_foreign_origin_is_refused_even_with_a_valid_session`, `::test_own_origin_and_no_origin_are_accepted` |
| E6.5 bare / look-alike VNC paths 403, never relay | `routes_live.py:240-249` | `test_live_proxy_http.py::test_look_alike_vnc_paths_are_403_and_never_relay[7 ids]` (admin 403; anonymous 401/403; zero contacts) |
| E6.6 Cloud Run default is the same-origin path; localhost stays | `routes_live.py:54,57-68`; `core/env.py:110` | `test_live_default_url.py::test_default_is_unchanged_off_cloud_run` (byte-for-byte string), `::test_cloud_run_default_is_the_same_origin_path` (`novnc_url`, `viewer_url(True)`, `viewer_url(False)` starts `/novnc-view/`, contains `path=novnc-view/websockify`, ends `view_only=1`), `::test_blank_override_counts_as_unset`, `::test_explicit_override_still_wins_and_hostile_falls_back`, `::test_hosted_alone_does_not_switch_the_default`, `::test_live_page_on_cloud_run_never_mentions_localhost` (GET `/live` body has no `localhost`), `::test_on_cloud_run_reads_k_service_and_blank_is_unset[4]`. The existing `/live` tests pass unmodified |
| E6.7 absent upstream is legible: 502 / 1011 within 4 s, event loop not blocked | `routes_live.py:129-148` (`httpx.AsyncClient`, connect 3 s, read 15 s), `:209-225` (`websockets` async connect, `open_timeout=3`) | `test_live_proxy_http.py::test_closed_upstream_is_502_without_the_address` (no `127.0.0.1`, no port in the body, < 4 s), `::test_a_hung_upstream_does_not_block_other_routes` (a listening socket that never answers; `/healthz` answers < 1 s on the SAME event loop while the relay waits; the relay then answers 502), `test_live_proxy_ws.py::test_absent_upstream_closes_1011_quickly` |
| E6.8 one test seam, loopback only, entrypoint untouched | `routes_live.py:118-119`; `git diff 70a7a486 -- docker/` is empty | `test_live_default_url.py::test_production_upstreams_are_the_two_loopback_ports` (exact equality with the contract's mapping) |
| E6.9 D-entry | D-131 ACTIVE in `docs/DECISIONS.md` (Approved-by Umesh) | the checker's `grep -n "AT-1419" docs/DECISIONS.md` |

## Things the checker should look at (judgement calls)

1. **The login gate does not see websockets, and neither does the D-066 Origin/Host guard.** Both are `http`-only ASGI middleware (`ui/auth_middleware.py` `_AuthGate.__call__`, `ui/helpers.py` `_OriginGuard.__call__`). The handler therefore repeats session (`_principal`, the gate's own resolver), `live.view`/`live.control`, Host (`_host_allowed`, AT-758) and Origin before `accept()`. `_principal` and `_host_allowed` are underscore names imported across modules to keep one definition (C3); the alternative was a second copy.
2. **E6.4 "the app's own origin" is implemented as: the `Origin`'s host:port equals the `Host` header, scheme is http/https, and a `wss` request refuses an `http` Origin.** It is NOT the D-066 allow-list (`_origin_allowed`, which D-066's own docstring says must not trust the Host). It is safe here because the session cookie is host-bound (a rebinding page on another host carries no cookie) and `_host_allowed` still gates the Host. If the Cloud Run proxy does not give uvicorn `X-Forwarded-Proto`, the app sees `ws` while the browser's Origin is `https`: that is allowed (only a downgrade is refused), so the viewer still works. A missing `Origin` is accepted on cookie + permission (contract).
3. **Unauthenticated look-alike paths answer the gate's 401/302, not 403.** The six look-alike routes have no policy row (default deny), so the gate answers an anonymous request before the handler runs; a signed-in account gets 403 (from the gate for one without a row, and from the handler `_forbidden`). Contract E6.5 says "403 authenticated or not"; making it literal needs a `public` row, which AU16 closes. Never relayed in either case (zero contacts asserted). Flag it if you read E6.5 as requiring 403 to an anonymous caller.
4. **Websocket auth failure is `close(1008)` before accept**, which uvicorn answers as HTTP 403 on the upgrade; Starlette's `TestClient` surfaces it as `WebSocketDisconnect`. An absent upstream is closed 1011 AFTER accept (so a browser sees a close code); the cost is that a client briefly sees an accepted socket.
5. **`core/env.py::on_cloud_run` resolved in cycle 1:** E5 (`58e8cf15`) landed the same helper on master; the merge kept E5's single definition and dropped E6's copy, so `core/env.py` is identical to master (300 lines). `routes_live.py` imports it unchanged.
6. **`websockets` is now a declared dependency** (doctor `undeclared-dependency`); `uv.lock` was edited by hand (two lines), not regenerated.
7. **Mutation b8/oversize**: both the client-side guard and the upstream `max_size` close with 1009, so the test also asserts the stub never received the frame; that is what makes the client-side guard killable. The reverse direction (an oversize upstream frame) is guaranteed only by `websockets`'s own `max_size=_MAX_FRAME`, not by a test.
8. **No `senior-software-engineer` review agent was dispatched** (the brief forbids dispatching agents). The lifecycle review step is owed.
9. **Not exercised**: a real browser against a real websockify/noVNC container (no container in this worktree); behaviour behind Cloud Run's HTTP/2 front; the full suite in one invocation (low-memory rule, files run in pairs).
10. `HEAD` requests to the relay are not routed (GET only), as `/live` itself; a noVNC page does not issue them.

## Verify (run in `D:/autoTesting/.claude/worktrees/e2e-e6`, `-o addopts=`, `env -u ANTHROPIC_BASE_URL`, at most 2 files per call)

```
pytest tests/test_live_proxy_http.py tests/test_live_default_url.py      -> 39 passed
pytest tests/test_live_proxy_ws.py tests/test_ui_auth_policy_table.py    -> 15 passed
pytest tests/test_hosting_gaps.py tests/test_ui_healthz.py               -> 42 passed
pytest tests/test_routers_list.py tests/test_ui_auth_surface.py          -> 27 passed
pytest tests/acceptance/test_ta02_nothing_before_access.py tests/acceptance/test_ta03_real_server.py -> 11 passed
pytest tests/test_ui_auth_escalation.py tests/test_ui_auth_host_and_consent.py -> 34 passed
pytest tests/test_hosting_config.py tests/test_ui_sidebar.py             -> 14 passed
pytest tests/test_ui.py tests/test_ui_dashboard.py                       -> 29 passed
ruff check src tests scripts                                             -> All checks passed!
autotester map / snapshot                                                -> regenerated
autotester doctor (> .work/doctor-e6.txt)                                -> see cycle-1 results below
uv lock --check --offline                                                -> Resolved 335 packages
```

## Mutation evidence (C7)

`scripts/mutation_check.py` on two specs (`qa/evidence/e2e-fixes-e6/mutations-http.json`: 18 mutants over `tests/test_live_proxy_http.py` + `tests/test_live_default_url.py`; `mutations-ws.json`: 8 mutants over `tests/test_live_proxy_ws.py`), outputs `mutation-run-http.txt` and `mutation-run-ws.txt`: **26/26 killed**, no rerun needed. Mutants: upstream built from the request Host (SSRF); `..`, leading `//`, scheme and backslash each allowed; Cookie/Authorization forwarded; `/novnc` needing only view; `/novnc-view` needing control; the shared decision dropping the `live.control` check; production control upstream not loopback; `/vnc.html` and `/websockify` look-alikes unguarded; `/novnc` bare unguarded; 502 naming the upstream; a blocking client on the event loop; the policy rows removed; the default keyed on `AUTOTESTER_HOSTED`; the view-only URL not rewritten; websocket auth skipped; websocket control need weakened; Origin check skipped; upstream not closed when the client leaves; 1011 -> 1000; binary frames forwarded as text; `binary` subprotocol not negotiated; the oversize guard disabled.

## Cycle 1 (master merged: E5 `58e8cf15`, D-131 ACTIVE) - results

Merge `0d69b1ce` (only conflict `core/env.py`, resolved to master's version); SNAPSHOT regenerated and committed. Re-run on the merged tree, `-o addopts=`, two files per call:

```
test_live_proxy_http + test_live_default_url          -> 39 passed
test_live_proxy_ws + test_ui_auth_policy_table        -> 15 passed
test_hosting_gaps + test_ui_healthz                   -> 42 passed
test_routers_list + test_ui_auth_surface              -> 27 passed
test_ta02 + test_ta03 (acceptance)                    -> 11 passed
test_ui_auth_escalation + test_ui_auth_host_and_consent -> 34 passed
test_hosting_config + test_ui_sidebar                 -> 14 passed
test_ui + test_ui_dashboard                           -> 29 passed
test_storage_warning + test_container_entrypoint_behaviour (E5, merged in) -> 49 passed, 1 skipped (run alone, 6.5 s)
ruff check src tests scripts                          -> All checks passed!
autotester doctor (> .work/doctor-e6.txt)             -> exit 0, "doctor: clean" (HEAD ce5eb3d2)
mutations http: qa/evidence/e2e-fixes-e6/mutation-run-http-cycle1.txt -> 17/18 killed, a17 recorded SURVIVED
mutation a17 rerun alone: mutation-run-a17-rerun-cycle1.txt          -> 1/1 killed
mutations ws: mutation-run-ws-cycle1.txt                              -> 8/8 killed
```

Honest notes on the cycle-1 run: (1) the machine was heavily loaded by sibling worktrees (fork failures in bash at 16:30); the a17 pytest run hung with no child process and I killed that one process, which the tool recorded as SURVIVED (exit 4294967295). The same mutant rerun alone is KILLED by the test it claims, so the total is 26/26 with that one rerun. (2) An earlier, concurrent run of the E5 pair `test_storage_warning` + `test_container_entrypoint_behaviour` showed 3 failed, 46 passed, 1 skipped in 280 s while two other test loops were running; alone the same pair passes (49 passed, 1 skipped). Not caused by E6 (no E6 file touches the entrypoint), but it is E5-owned and timing sensitive under load.

The anonymous look-alike answer (judgement call 3) is as D-131 describes: the gate's 401/302 for an anonymous caller, 403 for a signed-in one, never relayed.
