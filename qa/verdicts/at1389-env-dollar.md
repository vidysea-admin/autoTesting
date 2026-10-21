# Verdict - at1389-env-dollar (coordinator A of a dual check)

**Verdict:** PASS
**Status:** PASS
**Cycle checked:** 0
**Reviewed SHA:** e7b5835de267dbdcf7c1702c4c421b7548f4f858 (base c437d3a5; code ffbe43e9; bound to D:/autoTesting/.worktrees/at1389-env-dollar)
**Policy-Version:** proportional-verification/2026-10-19.17
**TIER:** L - security: credential file handling, `src/autotester/core/env.py:98` (cited dual-trigger line verified: the new function reads the repo-root .env)

## Check plan
Logic changed (affected tests + 1 falsification per criterion), UI changed (Mode D live page), security read of changed lines, auth-gate probe. No prompt/data/portal check applies. No coordinator fan-out: one agent, steps run serially (shared port 8765 only for the live step).

## Independent checks
- Manifest verify command re-run on e7b5835d: `pytest` on the 9 manifest files -> 113 passed, 1 skipped; `ruff check src tests scripts` -> All checks passed. Only the unit's own test file was re-run per criterion in the copies; no full suite.
- C1 doctor: real command via `python -c "from autotester.cli import app; app()" doctor` against a temp root whose .env holds a `${` value: exit 0, output = one `env-dollar-literal` warning with count 1 and the KEY NAME, then "doctor: clean"; 0 hits for the value text. Zero keys -> no line (tests::no_env_line, plus `A=cost$5`, `B=$HOME`, `K5`, `K6=` give no key in my parse-shape probe).
- C2 settings page: `/settings/providers` carries `#env-dollar-warning` with count + key names; absent when clean. Auth matrix on the real gate (auth_harness, throwaway copy): unsigned -> 401/302, no key name; signed-in without settings.manage -> 403/404, no warning, no key name; settings.manage (no credentials.view) and admin -> 200 with the warning, value fragments absent. Policy row `auth/policy.py:81` is unchanged by the diff; the gate is the existing one.
- C3 temp .env only: all 7 new tests use tmp_path + AUTOTESTER_ROOT; the repo .env was never opened (the bound worktree has no .env). Value-leak assertions present on doctor, page and CLI output.
- Behaviour unchanged: `read_dotenv(...)` still returns the literal `pre${HOME}post` (probe); `load_repo_env` and `read_dotenv` are untouched by the diff (only two functions appended below them); no expansion restored.
- HTML escaping: key `A<script>x` renders escaped on the page (probe, `<script>x` absent); the message goes through `escape()` at routes_settings.py:77.

## Falsification (one per criterion, each in its own copy outside the bound root, green before / red after)
- C1: `"${" in value` -> `"$" in value` in dollar_value_keys: 7 passed -> 4 failed.
- C2: warning paragraph forced off in provider_settings_view: 7 passed -> 1 failed.
- C3: dollar_value_keys returns `KEY=value`: 7 passed -> 4 failed (the value-leak tests).
Bound tree untouched (git status clean before writing this verdict).

## Security read of the changed lines
- `core/env.py:91-109`: reads only through `read_dotenv` (no new parser, interpolate=False); returns sorted key names; None values handled (`value or ""`); no value, fragment, length or position leaves the function; `dollar_warning` formats count + keys only.
- `ledger/env_warning.py`: one Violation, message from `dollar_warning`; Violation printed to stdout only via `warning_summary` (advisory.py:25), no file or log write. `NON_BLOCKING` addition keeps doctor green (warning, not failure).
- `ui/routes_settings.py:77-85`: key names escaped; page behind central `_SETTINGS` policy. No new route, no POST, no new input.
- Residual (low, not a defect of this unit): the warning lists key names of every .env entry with `${`, including project-namespaced keys the page's own table does not list; key names are not secret in this product and are already shown to the same permission on other pages.
LIVE-BROWSER: qa/evidence/browser-at1389-env-dollar-2026-10-21-checker/report.json (own headless chromium; Playwright MCP was locked by another session and claude-in-chrome was not connected). Page loaded, warning visible, text as expected, 0 console errors/warnings, no value fragment in the rendered text. Screenshot at D:/autoTesting/.work/tmp/at1389A/ev/settings-providers.png (not committed).

## Explanation
All three criteria evidenced by commands I ran; the floor is met (3 falsifications, mutants=0 beyond the floor). Dual check: I never saw coordinator B's verdict or checkpoint.

PROPOSED-ISSUE (low, ui): `<p class='alert' id='env-dollar-warning'>` uses a CSS class `alert` that theme_style.py does not define and has no `role='alert'`, so the warning renders as plain text (visible, but not styled as a warning; other pages use `class='subtitle' role='alert'`).
PROPOSED-ISSUE (low, process): maker manifest says "Live browser evidence: SKIP"; the checker ran Mode D itself, so the SKIP line is stale. Wording only.

Metrics: start=2026-10-21T14:00:00Z end=2026-10-21T14:30:00Z wall_min=30 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=3 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-19.17 check_s=1800 mutants=0 defects_unit=0 defects_6c=0
