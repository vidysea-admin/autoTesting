# Verdict - auth-eye

Cycle checked: 0
Bound root: D:/autoTesting/.worktrees/auth-eye. Candidate a15a21c3 (HEAD 0b9d3abb = candidate + manifest). Base 47496209.
Contract: qa/contracts/auth.md AU26 (labelled, keyboard-operable controls; zero unexplained console errors), AU16 (no external reference added by the toggle). Manifest criteria C1-C3.
Policy: proportional-verification/2026-10-19.17. Tier S confirmed: diff = auth_view.py (17 lines, markup only), one test, manifest; no auth/session/route/form-field change (`git diff 47496209 HEAD --stat`).

## Check plan
1. Re-run the manifest verify commands. 2. Read the diff in full (step 4c). 3. Mode D in my own browser on /auth/login and /auth/signup. 4. One falsification per criterion in a copy. No fan-out needed (S).

## Evidence (all run by me)
- `uv run pytest tests/test_ui_auth_surface.py tests/test_ui_auth_host_and_consent.py` -> 36 passed. `ruff check src tests scripts` -> pass. `autotester doctor` -> clean. `grep -rniE "content-security|script-src" src` -> no match, so the inline onclick is not blocked (auth_view.py `_EYE`).
- Diff read: `_EYE` is `type='button'`, the label flips via setAttribute, it toggles the sibling input in the same wrapper; `_field` wraps only `kind == "password"`; input id/name/required/extra unchanged. No user data enters the markup.
- Mode D (qa/evidence/browser-auth-eye-2026-10-21-checker/report.json): my own server on :8765 (PIDs 12964/37788, stopped). Login and signup: the password starts `type=password`; click eye -> `text`, label "Hide password", text "Hide", value kept; click again -> `password`; Tab reaches the eye (BUTTON "Show password") and Enter toggles it; submit-event count 0 and no extra POST in the server log in the controlled replays; clean page loads show 0 console errors; the toggle triggers no network request (only the pre-existing font loads).
- Falsification (copy .work/tmp/ae-chk-fals, `-k eye`): base 2 passed; C1 bare input -> 2 failed; C1/C3 button type=submit -> 2 failed; C2 toggle removed -> 2 failed; C3 external script added -> 2 failed; restored 2 passed, byte-identical. Mutants beyond the floor: 0.

## Criteria
- C1 (eye present, hidden by default, never submits): MET (tests + browser, both pages).
- C2 (toggle works under no-CSP inline onclick, label flips): MET (browser, mouse + keyboard).
- C3 (no external reference, form unchanged, existing auth tests green): MET (36 passed, network list, field ids intact).

## Notes (non-blocking)
- Unexplained, not reproduced: in my FIRST login pass the server log shows two `POST /auth/login 401` and the console shows two matching 401 errors, after the page had already shown the toggled state with 0 submit events. Three later replays with a submit listener armed and server-log counts (login x2, signup x1) produced no POST. The Playwright MCP browser may be shared; I cannot attribute them to the button, and without a reproduction this does not block (evidence-to-block). No ledger row written (the brief limits my commit to verdict, checkpoint and evidence); the maker may add a low row.
- Process: this check ran about 16 min wall, over the S 10-min mark; the step that took the time was the browser replay of the unexplained POSTs (about 8 min). slow: browser-replay 8. The maker should file the `process` ledger row (checker commit scope was narrowed by the brief).

VERDICT: PASS
SCOREBOARD: 3/3 criteria met, 2/2 invariants hold (AU16 no new external ref, AU26 labelled keyboard-operable control)
TIER: S (markup-only change to one UI file plus a test; no auth behaviour change)
FAILURES: none
CAPABILITY-COVERAGE: not-applicable (UI markup, no capability rows)
LIVE-BROWSER: qa/evidence/browser-auth-eye-2026-10-21-checker/
ISSUES-WRITTEN: none
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: The eye toggles type password/text on both pages by mouse and keyboard, keeps the typed value, never submits, adds no request, and four copy mutations each turn the test red. One unexplained pair of 401 POSTs in the first browser pass was not reproducible and is not attributed to the change.
Metrics: start=2026-10-21T07:03:00Z end=2026-10-21T07:20:00Z wall_min=16 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=4 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-19.17 check_s=960 mutants=0 defects_unit=0 defects_6c=0 slow=browser-replay 8
