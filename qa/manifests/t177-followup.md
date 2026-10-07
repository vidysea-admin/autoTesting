# T-177 follow-up — exact browser-use pin, telemetry off, read-only `cdp_url`, and fix cycle 1 for checker A's cycle-0 FAIL

Status: ready-for-check
Fix cycle: 1
Policy-Version: proportional-verification/2026-10-07.7
Tier: L (dependency pin, plus security changes: a DevTools endpoint, telemetry and `.env` exposure, the AF3 guards)
Authority: D-075 (Approved-by Umesh, chat 2026-10-07) · verdict `qa/verdicts/t177-agent-fallback.a.md` (cycle 0 FAIL) for items I1-I7
Source: branch `wave/t177-followup`, built on `wave/t177-agent-fallback` 1f950714. Not pushed.

## Criteria

Original follow-up criteria, verbatim:

- **F1.** `pyproject.toml` pins `browser-use==0.5.9` exactly, and `uv.lock` is regenerated with `uv lock`.
- **F2.** AutoTester sets `ANONYMIZED_TELEMETRY=false` in the process environment before browser-use is first imported. Do this inside `stages/browser_use_backend.py`, before its import. Also check browser-use 0.5.9's source in the venv for any other telemetry or network-on-import switch, and disable those too. A test asserts that the variable is set at import, and that no browser-use telemetry client is constructed with it enabled.
- **F3.** `BrowserSession` (in `src/autotester/browser/session.py`) exposes a read-only `cdp_url` property: it returns the CDP endpoint of the browser AutoTester launched, or `None` when that is not available; it is never settable; it never launches a second browser; the CDP endpoint must stay bound to localhost. Check whether the Playwright launch actually exposes one; if a `--remote-debugging-port` arg is needed, it must be bound to 127.0.0.1 on a random free port.
- **F4.** `browser_use_backend` reads `session.cdp_url`, so the real backend can be constructed when a session exists. A test uses a fake session object; no real browser runs in unit tests.

Fix cycle 1 (coordinator's list from checker A's cycle-0 FAIL), each TDD-first:

- **I1 (AF3 / X7).** After every agent action, the page's actual landing URL is re-checked against `allowed_domains` (redirects, open redirects, JS navigation, hrefless clicks). Off-scope = the step is blocked and reported (`REFUSED`, reason "landed outside allowed domains").
- **I2 (AF3 write guard).** Under read_only, `PRESS_KEY` is an allow-list of navigation keys only; modifiers are normalised, NumpadEnter, multi-character strings and text ending in a newline are refused.
- **I3 (scheme).** `check_destination` accepts only http/https.
- **I4 (backend).** `ProviderChatModel` satisfies browser-use 0.5.9's type check; a real `browser_use.Agent` builds, with no network call.
- **I5 (.env).** browser-use's import-time `load_dotenv()` does not read the repo `.env` into `os.environ`.
- **I6 (secret guard).** The guard never defaults to identity.
- **I7 (ProviderError).** A test kills the surviving mutant: `run_with_fallback` falls back on `ProviderError`.

## What changed (all edited in place; new files are tests only)

- `pyproject.toml:12` `browser-use==0.5.9`; `uv.lock` regenerated with `uv lock` (one line: the `requires-dist` specifier; no package moved).
- `src/autotester/stages/browser_use_backend.py` — `NO_NETWORK_ENV` forced (not `setdefault`) at module import by `_load()`: `ANONYMIZED_TELEMETRY=false`, `BROWSER_USE_CLOUD_SYNC=false` (found in 0.5.9 `config.py:63`, it follows the telemetry switch and sends agent events to api.browser-use.com), `PYTHON_DOTENV_DISABLED=1` (I5; the switch makes python-dotenv's `load_dotenv` a no-op, AutoTester's `core/env.py` uses `dotenv_values`, which ignores it). `PROFILE` = `enable_default_extensions=False` (the only other network switch in 0.5.9: a Chrome-store download, and only when browser-use launches its own browser). `ProviderChatModel` gains `_verified_api_keys` and `__get_pydantic_core_schema__` so it is a `BaseChatModel` (I4). `guard` is now required on `ProviderChatModel` and `BrowserUseBackend` (I6). New `BrowserUseBackend.for_session(provider, session, guard=None)` reads `session.cdp_url` (F4), raises `ActuatorError` naming `expose_cdp` when it is `None`, defaults the guard to `session.secrets.redactor().scrub`, and passes `*.<domain>` as browser-use's own `allowed_domains`. `on_step` calls `vet.landed(state.url)` before it vets the step's actions (I1).
- `src/autotester/browser/launch.py` — `CDP_HOST`, `loopback_port()`, `cdp_endpoint()`, and `launch_options(..., cdp_port=)` adding `--remote-debugging-address=127.0.0.1` and `--remote-debugging-port=N` only when asked (F3).
- `src/autotester/browser/session.py` — `BrowserSession(expose_cdp=False)`; a read-only `cdp_url` property (None unless started with `expose_cdp=True`; cleared on `close()`); `check_destination` refuses a non-http(s) scheme (I3). The file is at exactly 300 lines: `_sweep_orphan_videos` moved to `VideoMixin` (`browser/video.py`, behaviour unchanged) to make room.
- `src/autotester/browser/secrets.py` — `bad_scheme(url)` (I3).
- `src/autotester/stages/agent_actuator.py` — `only_safe_keys` plus `_SAFE_KEYS` / `_MODIFIERS` replace the "enter"/"return" deny-list (I2); `ActionGuard.landed(url)` and `_landing_url(session)` (asks the page `location.href`, falling back to `page.url`), called in `FallbackActuator.invoke` after the backend returns (I1).
- Tests (new): `tests/test_browser_session_cdp.py` (7), `tests/test_browser_use_pin_telemetry.py` (13), `tests/test_agent_fallback_hardening.py` (51).

Design decisions to confirm or veto:

- The CDP endpoint is opt-in (`expose_cdp=False` by default), because a debug port on every session would let any local process drive a browser that holds Pathlynks credentials. `routes_runs` (not touched, waits for T-203/T-204) must construct the session with `expose_cdp=True` when it wires `BrowserUseBackend.for_session`.
- `cdp_url` is `http://127.0.0.1:<port>` (no trailing slash); Playwright and browser-use both resolve the websocket from it.
- I1 is checked at two points: before every browser-use step (where the previous action landed, from browser-use's own CDP state) and once after the backend returns (from the page). It does not navigate back; the outcome is `REFUSED` and the step is reported.

## Falsification records

Each in a throwaway copy of the worktree (scratch dir, `PYTHONPATH` at the copy), tests scoped to the named file. All 16 killed. Script: scratchpad `falsify.py` (not committed). The first pass left 4 survivors that exposed a hole in my own test: `run_fresh` used `python -I`, which ignores `PYTHONPATH`, so it ran the unmutated code. The `-I` was dropped; those 4 were re-run and killed.

| Item | Falsifying edit | Result |
|---|---|---|
| F1 | pin back to `>=0.5.9` | `test_f1_pyproject_pins_browser_use_exactly` fails |
| F2 | `setdefault` instead of forced assignment | `test_f2_importing_the_backend_forces...` fails |
| F2 | `BROWSER_USE_CLOUD_SYNC` set to `true` | same test fails |
| F2 | drop the import-time `_load()` call | same test fails |
| F3 | `CDP_HOST = "0.0.0.0"` | `test_f3_launch_options_bind_the_debug_port_to_127_0_0_1` fails |
| F3 | `cdp_url` no longer a property | `test_f3_not_started_or_not_exposed_is_none` fails |
| F3 | always expose a port | `test_f3_not_started_or_not_exposed_is_none` fails |
| F4 | `for_session` ignores `session.cdp_url` | `test_f4_backend_is_built_from_the_sessions_cdp_url` fails |
| I1 | drop `guard.landed(...)` in `invoke` | `test_f1_an_off_scope_landing_page_is_a_blocked_step[...]` fails |
| I1 | backend skips per-step `landed` | `test_item1_the_backend_checks_the_landing_page...` fails |
| I2 | back to the enter/return deny-list | `test_f3_read_only_refuses_every_key...[enter ]` fails |
| I3 | `bad_scheme` returns None | `test_f1_an_off_scope_landing_page...[javascript://...]` fails |
| I4 | drop `_verified_api_keys` | `test_item4_provider_chat_model_satisfies...` fails |
| I5 | `PYTHON_DOTENV_DISABLED` set to `0` | `test_item5_a_dotenv_sentinel_never_reaches_the_environment` fails |
| I6 | `guard or str` | `test_item6_for_session_defaults_to_the_sessions_secret_scrubber` fails |
| I7 | `except ProviderError` -> `except KeyError` | `test_f10_run_with_fallback_survives_a_provider_error` fails |

TDD evidence: before the fixes, the real-`Agent` probe raised `ValueError: invalid llm, must be from browser_use.llm` (I4), and the first `test_f3_read_only_*` run failed 27 times. The remaining new tests were written before their code, but I did not run each against the unfixed tree; the falsification table is the per-item proof that each test fails without its fix.

## Outputs

- `uv run pytest tests/test_agent_fallback.py tests/test_agent_fallback_hardening.py tests/test_browser_session_cdp.py tests/test_browser_use_pin_telemetry.py tests/test_browser.py tests/test_browser_actions.py tests/test_browser_navigation_secrets.py tests/test_video_parallel_sweep.py tests/test_agent_loop.py` -> **199 passed** (single process, no xdist).
- `uv run ruff check src tests scripts` -> All checks passed!
- `uv run autotester doctor` -> doctor: clean (this includes the `undeclared-dependency` check; `pydantic_core` is not imported, `handler(Any)` is used instead).
- Not run (by instruction): the full suite. A live browser run was not made: no AF/F criterion requires one, and `routes_runs` is not wired yet.

## Known gaps and not-mine items

- The AGPL `pymupdf` closure (via `markdown-pdf`) is not addressed; the coordinator is taking it to Umesh.
- `agent_error` is still never surfaced as evidence (checker F10, second half); not on this cycle's list.
- Checker A's LOW findings (bare `<button>` in a form, deny-list homoglyphs, UPLOAD path, `build_fix_prompt` double substitution) are untouched.

Metrics: suite_runs=0 repeat_runs=0 mutations=16 cycle=1 policy=proportional-verification/2026-10-07.7
