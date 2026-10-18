# Manifest - fix6c-r4-chokepoint (pre-push check 6c r4 repair, G11)

**Status:** ready-for-check
**Fix cycle:** 0
**Contract:** qa/contracts/core-invariants.md (actuator choke-point D-015); qa/contracts/network-assertions.md NA6
**Authority:** D-104 (build G11 now); repair of qa/verdicts/integration-6c-int1017-r4.md
**Dual check:** no (the route guard and the off-platform containment moved verbatim; the predicate that decides what is outside a declared platform is unchanged; no dual-trigger line)
**Persona walk:** skip (no UI surface)
**Issues addressed:** none
**Executor:** claude-sonnet-subagent
**Base SHA:** 58e13d6b (worktree .worktrees/fix6c-r4-chokepoint, branch wave/fix6c-r4-chokepoint)
**Code SHA:** 4c297ce8

## Criteria
- **F1 - tests/test_actuator_chokepoint.py goes green.** Root cause: the product was wrong. `stages/platform_links.py::_HopWatch` and `trace_link` touched `self.page.` / `session.page.` (route, on, remove_listener, unroute, goto) outside `browser/`. The test and its allowlist are unchanged.
- **F2 - tests/test_network_assertions.py::test_na6_exactly_one_response_listener_exists_in_browser goes green.** Root cause: the product was wrong. g11-port-wiring added a second `page.on("response")` in `browser/role_probe.py::ResponseLog.attach` (role_probe.py:74); NA6 allows only observe.py.

## What changed
- `browser/observe.py`: `PageObserver` gains `passive` (response listener only, keeps nothing, no dialog handling), `subscribe` / `unsubscribe` (hooks called from the one `_on_response`), and `response_observer(session)` (the session's observer, or a passive one attached to its page). Default behaviour is unchanged.
- `browser/role_probe.py`: `ResponseLog.attach` subscribes through `response_observer`; `_HopWatch` moved here as `HopWatch(session, outside)` with `park()`; it takes an `outside` predicate so `browser/` imports nothing from `stages/`. Status of the main navigation is read through the same single listener.
- `stages/platform_links.py`: `_outside_fn(platforms)` builds the predicate; `trace_link` uses `HopWatch` and `watch.park()`; no `.page` access left.

## Verification scope
Policy-Version: proportional-verification/2026-10-18.15
Tier: S
Round: 3 src files, 2 criteria, est 30 min - two existing red tests, no test file edited (protected tests unchanged, so no tier L)
Owners: fix6c-r4-chokepoint
Base / checked state: 58e13d6b / 4c297ce8, clean tree
Gate answers: none apply.
Affected tests / full-suite trigger: tests/test_observe.py, tests/test_platform_links.py, tests/test_role_session_port.py, tests/test_role_session_port_login.py (real Chromium) plus the two red files; no full suite run.
Tests[F1]: tests/test_actuator_chokepoint.py - no `.page.` or `playwright` outside browser/. tests/test_platform_links.py (real-browser trace, redirect containment) stays green.
Tests[F2]: tests/test_network_assertions.py::test_na6_exactly_one_response_listener_exists_in_browser; tests/test_role_session_port.py and tests/test_role_session_port_login.py (ResponseLog on a real Chromium) stay green; tests/test_observe.py (PageObserver default unchanged).
Falsification[F1]: copy-mutant in scratchpad/fix6c-r4-chokepoint (src copy, PYTHONPATH): appended `x = session.page.route("a", b)` to stages/platform_links.py -> test_no_direct_page_or_playwright_access_outside_browser_package red, naming platform_links.py:234.
Falsification[F2]: same copy: appended `page.on("response", h)` to browser/role_probe.py -> test_na6_exactly_one_response_listener_exists_in_browser red, hits ['observe.py:74', 'role_probe.py:252'].
Pre-check[F1]: 4c297ce8 uv run pytest tests/test_actuator_chokepoint.py tests/test_platform_links.py -> passed t=170 blobs=tests/test_actuator_chokepoint.py:621c2a4,tests/test_platform_links.py:ebacced
Pre-check[F2]: 4c297ce8 uv run pytest tests/test_network_assertions.py tests/test_observe.py tests/test_role_session_port.py tests/test_role_session_port_login.py -> passed t=170 blobs=tests/test_network_assertions.py:f1965d3,tests/test_observe.py:4d26889,tests/test_role_session_port.py:47eb8ba,tests/test_role_session_port_login.py:90ffbb6
Lint: 4c297ce8 `uv run ruff check src tests scripts` -> All checks passed; `uv run autotester doctor` -> doctor: clean.
Metrics: start=2026-10-19T10:00:00Z end=2026-10-19T10:30:00Z wall_min=30 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=1 mutations=2 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-18.15 lane=normal check_s=unavailable mutants=2 defects_unit=0 defects_6c=0 tests=69 tests_min=2

## How to verify (commands + expected)
- `uv run pytest tests/test_actuator_chokepoint.py tests/test_network_assertions.py tests/test_observe.py tests/test_platform_links.py tests/test_role_session_port.py tests/test_role_session_port_login.py tests/test_multi_role_session.py` -> 69 passed (about 170 s; real Chromium).
- `git diff --name-only 58e13d6b..4c297ce8` -> the three src files only.
