# Verdict B - at1389-env-dollar (AT-1389), coordinator B (blind), Cycle checked: 0

Date: 2026-10-21 · Policy-Version: proportional-verification/2026-10-19.17 · Base c437d3a5 -> head e7b5835d (code ffbe43e9) · bound to D:/autoTesting/.worktrees/at1389-env-dollar

## Check plan
Tier L (credential file handling; dual-trigger src/autotester/core/env.py:98 present in the changed code). Diff: core/env.py (+2 functions), ledger/env_warning.py (new), ledger/advisory.py, doctor.py, ui/routes_settings.py, tests/test_env_dollar_warning.py, docs/MAP.md. Steps: git identity, diff read in full, security read, manifest verify commands, own probes on a temp `.env`, one falsification per criterion in a copy outside the bound root (`D:/autoTesting/.work/tmp/chkB`, `fc1`..`fc3`).

## Results
- Git: HEAD = e7b5835d; `git diff c437d3a5 HEAD` = the 8 declared files, no `qa/contracts/`, no `.env`. Real repo `.env` never opened (bound tree has none); all probes used a temp `.env`.
- Verify commands (my run, TMP=D:/autoTesting/.work/tmp): `uv run pytest tests/test_env_dollar_warning.py tests/test_env_loading.py tests/test_ui_settings.py tests/test_doctor.py` -> 64 passed. Wider reference-hit set (committed_fresh, citations x3, ui_auth_surface, policy_table, envkeys, env_editor, env_labels) -> 144 passed, 1 skipped. `uv run ruff check src tests scripts` -> All checks passed. `uv run autotester doctor` -> 2 violations, both baseline docs/SNAPSHOT.md stale (known, unrelated); no rule of this unit.
- Selection review: candidates tool exited 2 (integration-required, dynamic globs) and its reference hits are noise from the manifest and test text; the real sibling `auth_view.py:30` only mentions `provider_settings_view` in a comment. `routes_server_settings.py` has no `.env` read. No coverage gap for a changed behaviour.
- Own probes (copy, `tests/test_probe_b.py` + the unit's tests, 12 passed): real `autotester doctor` command on a temp `.env` prints `env-dollar-literal: .env - 2 value(s) ... GEMINI_API_KEY, ZZ_PW`, exit 0, "doctor: clean"; output and DEBUG logs contain no value fragment (`Zq9`, `SECRETHOME`, `NOPE`, `Tail`). Settings page: anonymous -> 401 with no key names; a signed-in user without `settings.manage` -> 403/404 with no warning; admin and a `settings.manage` group member see count + key names, `PLAIN` not listed, no fragment of any value in the warning paragraph. Expansion not restored: `read_dotenv` and the real `load_repo_env` (test marker removed) keep `GEMINI_API_KEY` literal even with `SECRETHOME` exported.
- Security read of changed lines: `dollar_value_keys` returns only dict keys that pass `"${" in value`; `dollar_warning` formats count + keys; `check_env_dollar` builds one `Violation(".env", warning)`; the page paragraph is `escape()`d; no value is read into any string, log or return. Route gate is the unchanged central `ROUTE_POLICY` `_SETTINGS` row for `/settings/providers`. `NON_BLOCKING` addition makes the rule a warning only. No new parser (`read_dotenv`). No fresh route added (ui_routes golden unaffected).
- Falsification, one per criterion, green before / red after, each in its own copy: C1 `check_env_dollar` dropped from `doctor.run` -> RED `test_doctor_command_output_carries_the_warning_and_no_value` (+ my doctor probe). C2 page paragraph forced off -> RED `test_settings_page_shows_count_and_key_names_and_no_value` (+ my admin probe). C3 `dollar_value_keys` returns `KEY=value` -> RED 6 tests across doctor, page and key-list leak assertions. Reds are on named assertions, not import errors. Bound tree untouched.

## Criteria
C1 met (doctor: count + key names, none when zero, no new parser) · C2 met (settings page for `settings.manage` only) · C3 met (all tests temp `.env`, value-absence asserted on doctor, CLI and page).

PROPOSED-ISSUE: {"sev":"low","title":"autotester doctor raises UnicodeDecodeError on a non-UTF-8 repo-root .env (core/env.py:dollar_value_keys via ledger/env_warning.py)","detail":"probe: .env bytes 'A=\xff\xfe${X}' -> check_env_dollar raises; a doctor advisory should not crash the run. The settings page already raises on such a file (routes_settings.py:34 read_text) and load_repo_env also raises, so the real CLI fails earlier; hence low, not a FAIL.","fix":"catch UnicodeDecodeError/OSError in dollar_value_keys and return []"}
PROPOSED-ISSUE: {"sev":"low","title":"warning_summary labels every advisory '(D-087, non-blocking)' including env-dollar-literal","detail":"advisory.py:31 wording is rule-agnostic; wording only","fix":"drop the D-087 tag or make it per rule"}

```
VERDICT: PASS
SCOREBOARD: 3/3 criteria met (C1, C2, C3)
TIER: L (security: credential file handling, dual-trigger src/autotester/core/env.py:98 confirmed in changed code)
FAILURES: none
CAPABILITY-COVERAGE: 3 changed-criterion falsifications reproduced in isolated copies
LIVE-BROWSER: not-applicable here (the page is covered by authenticated TestClient probes against the real route, gate and render; no live browser run in this coordinator)
ISSUES-WRITTEN: none (dual check: PROPOSED-ISSUE lines above)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: Doctor and /settings/providers report the count and key names of .env values containing ${ with no value or fragment printed, logged or rendered, expansion stays off, and only settings.manage users reach the page; each criterion has a test that goes red when its line is mutated, and the affected sets are green.
Metrics: start=2026-10-21T14:15:00Z end=2026-10-21T14:30:00Z wall_min=15 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=3 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-19.17 check_s=unavailable mutants=3 defects_unit=0 defects_6c=0
```
