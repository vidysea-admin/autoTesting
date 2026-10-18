# Verdict - g11-port-wiring (G11 integration: LiveRolePort)

Cycle checked: 0
Date: 2026-10-18 (checker, single, claude-sonnet-subagent; bound to D:/autoTesting/.worktrees/g11-port-wiring)
Policy-Version: proportional-verification/2026-10-18.15
Checked state: HEAD 5176c0d7 (code at 2e3c5c8e); base 5865cf92 = `git merge-base HEAD int/1017` (int/1017 has since moved to 6ddcd54f)

## Check plan
Logic + browser adapter, no UI surface of the product (local fixture only). Tier L (credentials-at-fill, masked screenshots) single checker; no changed code resolves or stores a secret itself (every secret path is a call to shipped `SecretStore`/`Redactor`/`host_of`/`sign_in`), so no dual trigger. Steps: (1) re-run the 17 unit tests; (2) one falsification per criterion in copies outside the tree; (3) diff-scope read; (4) own counterexamples: PW3 with my own planted canaries, PW4 with a never-attempted role; (5) lint/doctor/choke-point.

VERDICT: FAIL
SCOREBOARD: 3/4 criteria met (PW1, PW2, PW3 met; PW4 not met), 3/3 applicable invariants hold (MPI1, MPI3, MPI5 checked; MP15 registry untouched)
TIER: L (browser-driving adapter that fills credentials at page.fill time and takes masked screenshots; no dual trigger: no auth/tenancy/secret-handling code is changed, role_session_port.py:87,197-198 only calls shipped helpers)
FAILURES:
- [PW4] sev: medium · a role whose sign-in was NEVER ATTEMPTED does not make the oracles that read it `errored: RoleLoginFailed`: `_require_every_role` (src/autotester/stages/role_port_state.py:95) tests only `st.failed`, which only an attempted `login()` sets, so with bob never signed in the whole-run oracles api_error, request_budget, copy_lint and responsive report `ran` and yield 7 findings from alice alone (the "working half"); negative_input and state_after are errored but with `RoleNotSignedIn`, not `RoleLoginFailed` · fix direction: treat `not st.signed_in` (for a platform with a declared sign-in) as broken in `_require_every_role`, and add a test that skips `login_all` for one role · issue: AT-1335 · reproduced by `.venv/Scripts/python.exe -I qa/evidence/g11-port-wiring/probe_unattempted.py` (output in probe_unattempted.out), I read role_port_state.py:75-97 myself
CAPABILITY-COVERAGE: 4/4 floor rows reproduced (one falsification per criterion, copies outside the tree)
LIVE-BROWSER: qa/evidence/g11-port-wiring/ (headless Chromium against tests/role_port_app.py on a.localhost; no product UI surface)
ISSUES-WRITTEN: AT-1335 (medium, PW4), AT-1336 (low), AT-1337 (low)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: PW1, PW2 and PW3 hold: I re-ran the 17 tests (17 passed, 108 s), reproduced one falsification per criterion green-before/red-after on the named assertion, and re-ran the PW3 tests in a copy with my own planted passwords, email and phone (3 passed). PW4 is met for a wrong password and for a role with no sign-in declared once `login_all` ran, but not for a role whose sign-in was never attempted, which the criterion names explicitly; the repair is one line in `_require_every_role`. The diff adds files only (plus the generated docs/MAP.md), no oracle, T-207/T-209/T-211 schema or enums file is touched, ruff is clean, doctor shows only the SNAPSHOT staleness, and the choke-point test is red only on platform_links.py (T-210, outside this diff).

## Evidence (what I ran myself)
- Acceptance, Pre-check reproduced: `uv run pytest tests/test_role_session_port.py tests/test_role_session_port_login.py` -> 17 passed in 107.98 s (qa/evidence/g11-port-wiring/acceptance-run.txt). The builder's `t=109` matches.
- Falsification floor, copies at scratchpad `fal_pw1..4` (src+tests+scripts copied, PYTHONPATH confirmed to point at the copy), driver `falsify.py`, logs `falsify_pw*.log`; each named test green in the copy first:
  - PW1 `test_pw1_a_target_outside_the_roles_platform_is_refused_before_the_browser_moves`: `if not host_in_platform(platform, host_of(url)):` -> `if False:` in role_session_port.py _absolute; red: a `NavigationRefused` (the session's project-level guard) escapes instead of `PlatformScopeError` (see AT-1337).
  - PW2 `test_pw2_api_error_finds_the_failed_save_behind_the_success_screen`: `success = None` in role_probe.py page_snapshot; red on `assert {f.role ...} == {ALICE, BOB}` (found `set()`).
  - PW3 `test_pw3_observations_and_screen_text_are_scrubbed`: `text=snap.text` instead of the scrubbed text in `_after`; red on `assert all(PASSWORDS["alice"] not in t.text ...)`.
  - PW4 `test_pw4_a_failed_login_errors_every_oracle_and_yields_no_findings`: `broken = []` in `_require_every_role`; red on `assert findings == []` (3 copy_lint findings leak from the working half).
- PW3 own canaries: copy of tests with passwords `zk7canaryalicepw91`/`qx3canarybobpw44`, email `mallory.q.tester@vendor-example.net`, phone `+44 20 7946 0958` -> the 3 PW3 tests pass (canary.py).
- Secret path read: `{{SECRET:KEY}}` substitution happens only inside the shipped `session.fill` (role_session_port.py:194, `_split` line 181 admits only a `PLACEHOLDER_RE` full match for `fill`); `sign_in` checks `host_in_platform` before the browser moves (multi_role_session.py:190-193); `_absolute` uses `host_of` (fail-closed) then `host_in_platform` (role_session_port.py:166-170). The `_host_matches` suffix rule is used unchanged through `SecretStore`.
- Diff scope (4c): `git diff --name-status 5865cf92 HEAD` = 11 `A` rows + `M docs/MAP.md` (generated). Nothing deleted or renamed; no unlisted file. `git diff --name-only` lists no oracle module, `enums.py`, `multi_role_enums.py`, or T-207/T-209/T-211 schema file; `schema/role_signin.py` is new.
- `ruff check src tests scripts` -> All checks passed. `autotester doctor` -> 2 violations, both docs/SNAPSHOT.md staleness (regenerated at merge). `tests/test_actuator_chokepoint.py` -> 1 failed, only `stages/platform_links.py:120,149-156,184` (T-210, not in this diff), 1 passed; no `.page.`/playwright in any new stages file.
- Worktree shows 144 ` M` entries from LF/CRLF warnings (autocrlf); committed tree is unchanged by them; I touched none.

## Findings filed as ledger rows (non-blocking)
- AT-1336 (low): `role_port_network.py:47-54` third fallback `StepNetworkLog(..., repro_steps=[])` always raises `ValidationError` (`schema/request_budget.py:66` has `min_length=1`; reproduced with the model directly), so a step whose own action looks personal (e.g. `goto /profile/jane.doe@example.org`) escapes `perform` as a raw `ValidationError` after the browser moved. Fail-closed (errored, not clean), no test covers it.
- AT-1337 (low): the PW1 off-platform test uses a host outside the project's allowed_domains, so the project-level `NavigationRefused` guard catches it too; no test shows a host allowed for the project but outside the ROLE'S platform is refused by `_absolute` alone (two-platform case).

## Proposed contract fold-in (for the checker at PASS)
Adopt PW1-PW4 into `qa/contracts/multi-role-platform.md` under T-210 integration, with PW4 worded as: a role with a declared sign-in that is failed, never attempted, or has no sign-in declared makes every oracle that reads it, directly or through a whole-run read, `errored` and yields no findings.

Metrics: start=2026-10-18T21:40:30Z end=2026-10-18T21:53:00Z wall_min=13 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=1 mutations=4 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-18.15 lane=normal check_s=750 mutants=0 defects_unit=1 defects_6c=0
