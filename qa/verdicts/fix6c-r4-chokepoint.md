# Verdict - fix6c-r4-chokepoint (Mode A, cycle 0)

Date: 2026-10-19 · Cycle checked: 0 · Checked head: fae69506 (code 4c297ce8; fae69506 adds only the manifest) · Base 58e13d6b · Policy-Version: proportional-verification/2026-10-18.15

VERDICT: PASS
SCOREBOARD: 2/2 criteria met (F1, F2); core-invariants actuator choke-point and NA6 hold
TIER: M (shared module browser/observe.py PageObserver changed; platform-scope route guard moved across files). The manifest said S; raised per the dispatch.
FAILURES: none
CAPABILITY-COVERAGE: not-applicable (no capability rows; browser-package refactor)
LIVE-BROWSER: not-applicable (no UI surface; the real-Chromium tests of the set ran, see below)
ISSUES-WRITTEN: ISS-fix6c-chokepoint-1, ISS-fix6c-chokepoint-2 (both low)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)

## Check plan
Criteria F1 (actuator choke-point), F2 (NA6). Risks: (a) guard moved verbatim, (b) PageObserver default unchanged, (c) listener leak.

## Evidence (all run by the checker)
1. Verify command: `uv run pytest` on the 7 files of the manifest -> 69 passed, 165 s (qa/evidence/fix6c-r4-chokepoint/runA-tail.txt). Includes both formerly red tests (test_actuator_chokepoint.py, NA6) and the real-Chromium files test_platform_links, test_role_session_port, test_role_session_port_login.
2. Behaviour-scoped importer set (the affected-set tool answered exit 2, integration-required: cli.py imports observe.py, so it selects 526 files; not used): test_network_assertions_serial_scope, test_browser_unreadable and every non-live tests/test_explore*.py (all construct the default PageObserver) -> 330 passed, 640 s (runB-tail.txt).
3. `ruff check` on browser/ and platform_links.py: clean. `autotester doctor`: clean. File sizes 251 / 176 / 233 lines (<= 300).
4. Falsification floor, in an isolated copy (src + the two test files under scratchpad/check-fix6c-chokepoint/m, PYTHONPATH): green 3 passed; F1 mutant (`session.page.route(...)` appended to stages/platform_links.py) -> test_no_direct_page_or_playwright_access_outside_browser_package red naming platform_links.py:235; F2 mutant (`page.on("response", h)` appended to browser/role_probe.py) -> NA6 red, hits ['observe.py:74','role_probe.py:255']; both restored, 3 passed. The bound tree was not edited.

## Step 4c diff read (full, base..head)
(a) Security read of the moved guard: I compared the removed `_HopWatch` against the added `HopWatch` and `_outside_fn` line by line. `_guard` is identical (non-navigation continue; outside first hop aborts before contact; `route.fetch(max_redirects=0)`, redirect target judged by `outside`, abort on outside, fulfill otherwise; any exception aborts). `outside` is the same expression (empty host, `bad_scheme`, no `host_in_platform`), now a closure over the same `platforms` list. `_main_navigation` only gained `bool()`. `_on_request` unchanged. The post-trace park condition `outside(now) and now != "about:blank"` is unchanged. No scope check was dropped or loosened. The probe (evidence/probe_observer_hopwatch.py) shows the guard aborting an outside first hop.
(b) Default observer unchanged: the probe shows a default `PageObserver` still registers console, requestfailed, response, dialog and the context popup hook; the non-passive `_on_response` body is the same lines in the same order, then iterates the hooks (empty by default). Passive registers only `response`. The only `session.observer` consumer outside explore, `execute._drain_network_evidence`, sees an empty passive drain as a no-op.
(c) Leak: the probe shows HopWatch.attach/detach returns the observer's hook list to its prior size (1 -> 0), removes the `request` listener and unroutes `**/*`; ResponseLog stays subscribed as before (it never removed its old listener either). The passive observer's single page listener lives as long as the page, with no hooks left.
No file outside the declared three src files changed (git diff --name-only 58e13d6b..4c297ce8).

## Findings (low, non-blocking, ledger rows)
- ISS-fix6c-chokepoint-1: `PageObserver.subscribe/unsubscribe`, `passive` and `response_observer` have no direct test (observe.py:90-97, 138-144); coverage is indirect through the role-session and platform-link tests.
- ISS-fix6c-chokepoint-2: hooks run inline in `_on_response` (observe.py:107-108); a raising hook now aborts the remaining hooks, where before each consumer had its own listener. Today's hooks do not raise on real Responses.

slow: behaviour-scoped importer run 10.7 min (two pytest processes in parallel on a real-browser-heavy set); the mandatory part (item 1 plus falsification) finished in about 4 min.

Metrics: start=2026-10-19T10:40:00Z end=2026-10-19T11:08:00Z wall_min=28 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=2 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-18.15 lane=normal check_s=1680 mutants=0 defects_unit=0 defects_6c=0
