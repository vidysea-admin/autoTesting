# Verdict - t206-env-input-mask (coordinator A, blind)

Date: 2026-10-20 · Bound to D:/autoTesting/.worktrees/t206-env-input-mask · head d0e6b08b (code e6640a2f, base 15d9ca7b)
Cycle checked: 0
Policy-Version: proportional-verification/2026-10-19.17

## Check plan (step 0)
Tier L, dual-trigger security routes_credentials.py:112 (kept). Instruments: (1) diff-scope read of the 3 src files + test, (2) affected tests, (3) falsification floor (1 criterion changed: TA15) in a copy, (4) Mode D own browser on port 8231, (5) security read. SERIAL: browser run waits on the single app port; otherwise independent.

VERDICT: PASS
SCOREBOARD: 1/1 criteria met (TA15 clauses: masked, labelled, keyboard-operable, zero unexplained console errors), invariants unaffected
TIER: L (secret-input mask on the credentials surface; dual-trigger routes_credentials.py:112)
FAILURES: none
CAPABILITY-COVERAGE: not-applicable (no capability table in this unit)
LIVE-BROWSER: qa/evidence/browser-t206-env-input-mask-2026-10-20-checker-A/report.json
ISSUES-WRITTEN: none (dual coordinator: PROPOSED-ISSUE lines only)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: The Add credential Value box is `type='password' autocomplete='new-password'` (routes_credentials.py:112-115), stays masked while typed in a real browser, and every control on /projects/<slug>/env (23) and /settings/providers (19) has an accessible name. The diff only adds attributes (label for/id, aria-label with the KEY name); no masking logic changed.

## Evidence
- Diff read (step 4c) `git diff 15d9ca7b e6640a2f -- src` in full: 4 files, attribute-only edits; no masking line removed; files 243/260/101/71 lines (<=300).
- Affected tests, own run: `uv run pytest tests/test_ui_env_labels.py tests/test_ui_env_editor.py tests/test_ui_crawl_approval.py tests/test_ui_crawl_approval_list.py tests/test_ui_settings.py tests/test_ui_production_approval.py tests/test_ui_onboard_a11y.py tests/test_ui_secrets_declaration.py` -> 57 passed, 1 skipped (matches maker). `uv run ruff check src/autotester/ui tests/test_ui_env_labels.py` -> All checks passed. No full suite.
- Falsification (floor, TA15), in copy scratchpad/check-t206-env-mask-A/copy (git archive of d0e6b08b, PYTHONPATH to the copy): control 4 passed; removing `type='password' autocomplete='new-password'` from the Add Value input -> `test_the_add_credential_value_box_is_masked_not_clear_text` FAILED (1 failed, 3 passed); copy discarded, bound tree untouched.
- Mode D (app in this worktree, port 8231, synthetic AUTOTESTER_ROOT, loopback auth-off; PIDs 32144 and 33672 started by me and killed):
  - /projects/demo/env: 23 controls, 0 unnamed; 0 console errors (2 verbose DOM autocomplete hints). Add Value: type=password before and while typing 25 chars, webkitTextSecurity=disc, text absent from innerText; screenshot t206A-add-form-masked.png shows dots. Tab order reaches ac-value then ac-domains, ac-description, submit, ca-kind.
  - /settings/providers: 19 controls, 0 unnamed; key inputs named `Value for <KEY>`; 0 console errors.
  - Submitting with key `SYNTH_TOKEN_KEY` gave the app's 400 "must start with DEMO_" (my own input, expected); that is the single console error of the session. Re-submit with `DEMO_TOKEN_KEY` stored and re-rendered the row as a masked, labelled input.
- Security read: aria-labels contain only the key name. The Add form never carries a value= attribute. Observation, unchanged by this diff (context line `value='{escape(shown)}'` pre-exists at routes_credentials.py:70 and routes_settings.py:62): after a save, a credentials.view principal's row input carries the stored value in its value= attribute (type=password), the U3/AU21 owner-only prefill design. Not weakened here.

PROPOSED-ISSUE: {"sev":"low","type":"observation","title":"Saved secret values are written into value= of masked row inputs for credentials.view principals (U3/AU21 design); visible in page source and password-manager autofill. Pre-existing, not part of T-206.","files":["src/autotester/ui/routes_credentials.py:70","src/autotester/ui/routes_settings.py:62"]}
PROPOSED-ISSUE: {"sev":"low","type":"a11y-hint","title":"Chrome verbose hint: row password input on /env lacks autocomplete attribute (suggested new-password); Add form already has it.","files":["src/autotester/ui/routes_credentials.py:70"]}

Metrics: start=2026-10-20T00:10:00Z end=2026-10-20T00:20:00Z wall_min=10 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=1 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-19.17 check_s=600 mutants=0 defects_unit=0 defects_6c=0
