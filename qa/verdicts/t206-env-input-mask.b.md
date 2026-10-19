# Verdict (checker B, blind) - t206-env-input-mask

**Verdict:** PASS
**Cycle checked:** 0
**Bound to:** D:/autoTesting/.worktrees/t206-env-input-mask (branch wave/t206-env-input-mask), code SHA e6640a2f, head at check d0e6b08b, base 15d9ca7b
**Contract:** qa/contracts/team-loop-acceptance.md TA15 (secret inputs masked; every form control labelled and keyboard-operable; zero unexplained console errors)
**Tier:** L, dual-trigger security src/autotester/ui/routes_credentials.py:112 (verified: the changed line is the Add credential Value input)
**Policy-Version:** proportional-verification/2026-10-19.17
**LIVE-BROWSER:** qa/evidence/browser-t206-env-input-mask-2026-10-20-checker-B/report.json

## Check plan
Diff read (4 files, +114/-32), affected tests rerun, Mode D in my own Chromium, security read of rendered HTML, falsification floor in copies. Browser note: the shared Playwright MCP tab was being navigated by another session (port 8231), so I drove my own Chromium through the Playwright library (`scratchpad/check-t206-env-mask-B/drive.py`) against the worktree app on port 8241 (not 8217/8218). Synthetic root and synthetic .env only; no Pathlynks, no real values.

## Evidence
1. Diff read in full (`git diff 15d9ca7b e6640a2f -- src`). routes_credentials.py:112-118 `ac-value` is `type='password' autocomplete='new-password'`; `for`/`id` pairs on the other Add-form fields and the platform-URL form; row inputs get `aria-label='Value for <KEY>'` (routes_credentials.py:71, routes_settings.py:63); routes_crawl_approval.py labels carry `for`/`id` for kind, production (incl. the forced-on disabled box), scope, expires, offset, actions, probes, wall clock, note. No other behaviour changed.
2. Affected tests, run by me: `uv run pytest tests/test_ui_env_labels.py tests/test_ui_env_editor.py tests/test_ui_crawl_approval.py tests/test_ui_crawl_approval_list.py tests/test_ui_settings.py tests/test_ui_production_approval.py tests/test_ui_onboard_a11y.py tests/test_ui_secrets_declaration.py` -> 57 passed, 1 skipped (pytest-affected.txt). `ruff check src/autotester/ui tests/test_ui_env_labels.py` clean; `autotester doctor` clean (decision-citation advisories only); files 243/260/101/71 lines.
3. Mode D (report.json): app started from this worktree's src (import path verified), `AUTOTESTER_AUTH_DISABLED=1` on 127.0.0.1:8241.
   - /projects/demo/env: typed `SYNTH-typed-secret-abc` into `#ac-value` key by key: `type=password`, DOM value holds all 22 chars, screenshot shows dots only (env-typed.png), typed string absent from `body.innerText`. Label click focuses the Value box; Tab order key -> value -> domains -> description -> button -> Kind select. Row editor unchanged: DEMO_PASSWORD password -> show -> text -> hide -> password.
   - Control audit (every non-hidden input/select/textarea has a `<label for>`, wrapping label or aria-label): /projects/demo/env 18 controls, 0 unlabelled; /settings/providers 7 controls, 0 unlabelled; /projects/demo 12 controls, 0 unlabelled.
   - Console errors: 0 on /env, /settings/providers and /projects/demo. The only error in the run is a 405 on my own GET of the POST-only `/projects/demo/crawl-approval`; that was my probe, not a product page, and is not counted.
4. Security read: value-inputs.txt lists every `name='value'` input rendered. aria-labels carry only the key name, never a value. No raw `SYNTH-` value appears on /settings/providers; on /env the owner view prefills saved values into `value=` of password-type inputs (DEMO_PASSWORD, DEMO_API_KEY) exactly as at base (the 2026-09-21 owner-only display amendment, AU21 gate `show_values`); the diff does not touch `shown`, `is_secret` or `show_values`, so no masking is weakened. Non-secret DEMO_EMAIL stays type=text as before.
5. Falsification (copies under scratchpad/check-t206-env-mask-B/m-*, bound tree untouched, control first): fixed copy `tests/test_ui_env_labels.py` 4 passed; removing `type='password' autocomplete=...` from `ac-value` -> red `test_the_add_credential_value_box_is_masked_not_clear_text` (1 failed, 3 passed); removing the settings row aria-label -> red `test_every_control_on_provider_settings_has_a_label` (1 failed, 3 passed). Each restored by discarding the copy.

## Criteria
- TA15 secret inputs masked: PASS (items 3, 4, 5).
- TA15 every form control labelled: PASS on the pages this unit fixes (item 3).
- TA15 keyboard-operable: PASS for the Add form (Tab order, label focus); the pages' other controls are unchanged by this diff.
- TA15 zero unexplained console errors: PASS on the three pages walked (0).

## Findings
- none blocking. No PROPOSED-ISSUE lines.

Process note: manifest `Persona walk: skip` accepted for a two-finding fix; this check walked only the fixed pages, not the other spec user types (`dev`, `tester`, `subadmin`, `admin`) end to end, so TA15 as a whole stays with the Mode D persona-walk unit.

Metrics: start=2026-10-19T18:25:00Z end=2026-10-19T18:56:00Z wall_min=31 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=2 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-19.17 check_s=1860 mutants=0 defects_unit=0 defects_6c=0
