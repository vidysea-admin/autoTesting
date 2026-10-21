# Manifest - auth-eye (show/hide eye on sign-in and sign-up password fields)

Status: checked-PASS
Fix cycle: 0
Risk tier: S (one UI markup file plus its test; no auth behaviour change)
Round: 1
Policy-Version: proportional-verification/2026-10-19.17
Base SHA: 47496209
Candidate SHA: a15a21c3c34d1930ec32d3b08b8e60e5002d184e
Request: Umesh 2026-10-21, sign-up screen: "password view k liye eye button tho de doo"

## What changed
- `src/autotester/ui/auth_view.py`: new module constant `_EYE` (inline-onclick toggle, same pattern as `routes_settings.py` `provider_settings_view` `_EYE`, lines 47-50 at base); `_field` wraps any `kind == "password"` input in a flex row with the button. Used by `login_page` and `signup_page` (both call `_field(..., "password", ...)`). Button is `type='button'`, `aria-label` flips Show password / Hide password, visible text Show / Hide.
- `tests/test_ui_auth_surface.py`: one parametrized test (`/auth/login`, `/auth/signup`) added at the end.
- CSP: `grep -rniE "content-security|script-src" src` returns nothing, so no CSP is sent and inline onclick is allowed. If a CSP is added later, this button and the settings-page one both need a nonce.
- Unchanged: field names, ids, autocomplete, minlength/maxlength, form actions, labels.
- Observation (out of scope, pre-existing): `PAGE_STYLE` already emits `<link rel="preconnect" href="https://...">` on signed-out pages; the new test therefore asserts only that the toggle itself adds no external reference.

## Tests
- C1: `tests/test_ui_auth_surface.py::test_password_field_has_a_show_hide_eye_that_stays_hidden_by_default[/auth/login]` and `[/auth/signup]` (input stays `type='password'`; button `type='button'` with `aria-label='Show password'`; page has exactly 2 buttons).
- C2: same test (onclick contains `i.type==='password'?'text':'password'` and the `Hide password` label; no `<script>`; no CSP exists to block inline onclick).
- C3: same test (no `http` or `//` in the button; button count unchanged) plus existing `tests/test_ui_auth_surface.py` and `tests/test_ui_auth_host_and_consent.py` still green.

Tests[C1]: tests/test_ui_auth_surface.py -k eye -> 2 passed
Tests[C2]: tests/test_ui_auth_surface.py -k eye -> 2 passed
Tests[C3]: tests/test_ui_auth_surface.py tests/test_ui_auth_host_and_consent.py -> 36 passed

## Pre-check
Pre-check[C1]: a15a21c3 `uv run pytest tests/test_ui_auth_surface.py tests/test_ui_auth_host_and_consent.py` -> 36 passed (test written first: 2 failed before the change, 36 passed after)
Pre-check[C2]: a15a21c3 `grep -rniE "content-security|script-src" src` -> no matches (no CSP); same pytest command -> 36 passed
Pre-check[C3]: a15a21c3 `uv run ruff check src tests scripts` -> All checks passed; `uv run autotester doctor` -> doctor: clean

## Falsification (throwaway copy at .work/tmp/ae-fals, venv python with PYTHONPATH pointing at the copy; worktree untouched)
- C1: `_field` returns the bare input (no eye) -> `-k eye` 2 failed. Also default visible (`login_page` password `kind="text"`) -> 1 failed (login case).
- C1/C3: button `type='submit'` instead of `'button'` -> 2 failed.
- C2: onclick `i.type=i.type==='password'?...` replaced with `i.type='password';` -> 2 failed.
- C3: `<script src='https://x.example/a.js'>` appended to the button markup -> 2 failed.
- Baseline in the same copy before mutations -> 2 passed.

## Metrics
suite_runs=0 (touched files only: test_ui_auth_surface.py, test_ui_auth_host_and_consent.py)

## Live browser evidence
SKIP - maker smoke only; checker runs Mode D.
