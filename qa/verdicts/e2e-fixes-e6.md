# Verdict - e2e-fixes-e6 (checker A, independent; focus: functional contract E6.1-E6.9)

**Verdict:** FAIL
**Status:** FAIL (1 blocking finding F1: the new websocket tests are flaky; the relay itself behaves correctly)
**Cycle checked:** 1
**Reviewed SHA:** 331fc2f5 (code identical at 394c0c53, which only adds another checker's verdict file that I did not read). Worktree `D:/autoTesting/.claude/worktrees/e2e-e6`, branch `feat/e2e-e6`, base master `6eb21a54` (merge-base `b3663ac3`; a merge into current master conflicts only in generated `docs/SNAPSHOT.md`).
**Scope:** `qa/contracts/e2e-fixes.md` E6.1-E6.9 (AT-1419) and `docs/DECISIONS.md` D-131. No `src/`, `tests/` or `docker/` file was modified by me (mutants and probes ran in a scratch copy under the gitignored `.work/`, since removed).

## Commands re-run (TMP/TEMP and `--basetemp` under `.work`, `env -u ANTHROPIC_BASE_URL uv run pytest <2 files> -o addopts=`)

| Command | Result |
|---|---|
| `test_live_proxy_http.py test_live_default_url.py` | 39 passed |
| `test_live_proxy_ws.py test_ui_auth_policy_table.py` | 15 passed on this run |
| `test_hosting_gaps.py test_ui_healthz.py` | 42 passed |
| `test_ui_auth_surface.py test_ui_auth_escalation.py` | 44 passed |
| `test_ui_auth_host_and_consent.py test_routers_list.py` | 17 passed |
| `test_live_proxy_ws.py` alone, repeated 9 times (3 of them with the real tree, 6 more) | 6 clean, 3 FAILED (see F1) |
| same file, 8 runs in an identical scratch copy | 5 clean, 3 FAILED |
| `uv run ruff check src tests scripts` | All checks passed! |
| `uv run autotester doctor > .work/doctor-chk6a.txt` | exit 0, last line `doctor: clean` |

## Criteria

| Crit | Result | Evidence |
|---|---|---|
| E6.1 HTTP relay, prefix stripped, loopback, no SSRF, no Cookie/Authorization | PASS | `routes_live.py:118-148`: URL built only from `VNC_UPSTREAMS` and `quote(path)`; `_BAD_PATH :126`; 5-name header allow-list `:124`. Tests green; my real-uvicorn probe: admin `/novnc/vnc.html` -> stub saw `/vnc.html`; `/novnc/..%2f..%2fx` -> 400 with zero stub contact. |
| E6.2 websocket relay, bytes/text, `binary`, close propagates, 1009 cap | PASS on behaviour, see F1 for its test | Real server (uvicorn + `websockets` client, cookie from a real login): binary echo OK, `binary` subprotocol negotiated, client close reached the upstream stub in 40 of 40 trials within 2 s. Oversize close 1009 test passes. |
| E6.3 one decision, every request, handshake before accept | PASS | `grep -rn 'need not in' src` -> one hit, `routes_auth.py:157`; `auth_check` and `routes_live.py:131,173` call `live_access_refusal`. Real server: anon ws -> HTTP 403 on the upgrade, dev (view only) `/novnc` ws -> 403 with control-stub contacts 0, dev `/novnc-view` ws OK, admin both OK. |
| E6.4 cross-site Origin refused | PASS | Real server: admin cookie + `Origin: https://evil.example` -> HTTP 403; own origin and no Origin -> connect. `_own_origin :151-163`. |
| E6.5 look-alike paths never relay | PASS with W1 | Real server: signed-in admin gets 403 for `/novnc`, `/vnc.html`, `/websockify`, `/novnc/`; anonymous gets 401 (gate), zero stub contacts. Contract says 403 "authenticated or not": deviation is documented in D-131 and manifest judgement call 3. |
| E6.6 Cloud Run default same-origin path | PASS | `routes_live.py:54,67` keyed on `on_cloud_run()`; `test_live_default_url.py` (all in the 39 passed); `core/env.py` is identical to master. |
| E6.7 absent upstream legible, loop not blocked | PASS | closed-port 502 without address, hung upstream does not block `/healthz`, ws 1011: all in the passing tests; mutant a14 (blocking call) killed by `test_a_hung_upstream_does_not_block_other_routes`. |
| E6.8 seam and scope | PASS | `VNC_UPSTREAMS :118`; `git diff 6eb21a54...HEAD -- docker` empty; no env var reaches the host. |
| E6.9 D-entry | PASS | `docs/DECISIONS.md:3106` `## D-131 ... status: ACTIVE`, cites AT-1419 and E6.1-E6.9, `Approved-by: Umesh (chat 2026-11-01)`; no Supersedes row. |

Mutation sample (scratch copy, expected test named by the spec failed in each): a1 SSRF from Host, a9 shared decision drops control, a14 blocking upstream call, a18 bare `/novnc` unguarded, b1 websocket auth skipped, b3 Origin unchecked, b4 upstream not closed on client leave: 7 of 7 killed.

## Findings

**F1 (blocking). `tests/test_live_proxy_ws.py` is flaky, so the project's `uv run pytest` gate would be red about a third of the time.** Measured: 3 failures in 9 runs of the file, 3 in 8 in a clean copy. Two failure shapes: (a) `concurrent.futures.CancelledError` raised from the `with _ws(...)` exit in `test_auth_matrix_websocket[...allowed...]` (several ids over runs); (b) `test_frames_relay_both_ways_and_close_propagates` failing its `stubs["control"].closed.wait(2)` assertion (`tests/test_live_proxy_ws.py:43`). Cause, established by a control experiment: Starlette's `WebSocketTestSession.__exit__` sends the disconnect and then immediately calls `cs.cancel` (`.venv/Lib/site-packages/starlette/testclient.py`, `__enter__` callbacks), so any handler that still has async cleanup after the client leaves is cancelled mid-cleanup. A trivial 15-line Starlette echo endpoint with 50 ms of cleanup reproduced the same `CancelledError` (1 of 60). The relay's `_pump` finally block (`routes_live.py:198-206`: `gather`, `await up.close()` with `close_timeout=2`, `ws.close`) is slow enough to lose that race, and in shape (b) the upstream socket is left open until garbage collection. The product is fine under a real server (40 of 40 closes propagated), so this is a test-reliability defect and a small robustness gap under cancellation, not a security hole. The manifest did not report it (it noted load flakiness only for E5 and a17). Required for PASS: make the ws tests deterministic, for example by closing the client inside the `with` and waiting for the stub's `closed` event and for the handler to finish before leaving the block, and/or making the upstream close in `_pump` cancellation-safe (a synchronous `up.transport.abort()` that runs even when cancelled, or a shielded close); then show the file green on at least 10 consecutive runs.

**W1 (non-blocking). Anonymous look-alike answers 401, not 403.** Contract E6.5 wants 403 "authenticated or not"; D-131 (Umesh) states 401/302 for anonymous. The contract amendment is owed (checker-side, `qa/contracts/` is not touched here).

**W2 (non-blocking). No `senior-software-engineer` review ran** (manifest judgement call 8); the lifecycle review step is still owed.

**W3 (non-blocking). The stated 32 MiB frame cap is not the effective client-to-server cap behind uvicorn:** uvicorn's default `--ws-max-size` is 16 MiB and the entrypoint passes no override (`docker/entrypoint.sh:127`), so larger client frames close 1009 from uvicorn first. Harmless (noVNC client frames are tiny), but the D-131 text "capped at 32 MiB" overstates it for that direction.

**W4 (non-blocking). Not exercised:** a real browser against a real noVNC container and Cloud Run's HTTP/2 front, as the manifest says.

## Next step for the maker
Fix F1 only (tests and/or `_pump` cleanup in place, `routes_live.py` stays under 300 lines), rerun `test_live_proxy_ws.py` 10 times with the pass count recorded, bump `Fix cycle: 2`, set `ready-for-check`. Nothing else is blocking.
