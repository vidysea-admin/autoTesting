# Manifest — at086-087-exemption
**Contract:** qa/contracts/ui.md U9 (residuals AT-086, AT-087)
**Goal task:** T-123 (closes the last two items of the medium batch)
**Date:** 2026-09-25
**Fix cycle:** 1 of max 3
**Dual check:** no
**Issues addressed:** AT-086, AT-087
**Executor:** claude-sonnet-subagent
**Executor rationale:** security-boundary unit on the credential guard (schema/security), never delegated per SKILL.md 4b.

**Gate answered:** `qa/gates/at086-at087-credential-exemption-scope.md` — Umesh, "go with the
best", 2026-09-24T16:32:17+05:30 — AT-087 (a) per-field exemption kept in the join as context;
AT-086 (a) an explicit declared list of public `.env` key names, never inferred.

## What changed

- `src/autotester/core/env.py:70` — added `PUBLIC_ENV_KEYS: frozenset[str]`, a source-only,
  never-inferred declaration of `.env` keys whose value is not a credential (AT-086). No route
  or `Form` reads or writes this name.
- `src/autotester/browser/secrets.py:223` — `SecretStore.redactor()` gained an `exclude:
  frozenset[str] = frozenset()` kwarg. Every existing caller (`browser/session.py`,
  `stages/explore.py`, `stages/execute.py`, `SecretStore.scrub_optional`) is unaffected —
  `exclude` defaults empty, so `scrub`/`guard_prompt` still mask every `.env` value regardless
  of this list (C5 unchanged).
- `src/autotester/browser/secrets.py:237` — new `SecretStore.public_values()`: values of
  `core.env.PUBLIC_ENV_KEYS` that are on disk, **excluding** any value that also appears under a
  non-public key (the AT-086 hard-boundary: one declared-public key must never exempt a
  different key that happens to share its value).
- `src/autotester/ui/helpers.py:195-240` (`_refuse_unsafe_value`) — `exempt: frozenset[str]` →
  `exempt_value: str | None`, matched only against the field it was called for (AT-087 second
  symptom: a flat set let a value stored as one field exempt a different one). Added an early
  return when the submitted text is in `secrets.public_values()` (AT-086).
- `src/autotester/ui/helpers.py:243-283` (`_refuse_unsafe_submission`) — `exempt:
  frozenset[str]` → `exempt: dict[str, str] | None` (field label → that field's own already-
  stored value). The join no longer drops exempt fields (`fresh` now keeps every field); instead
  the join's redactor is built via `secrets.redactor(exclude=exempt.values() |
  secrets.public_values())`, so an exempt/public value can sit in the joined text as context
  without self-triggering, while every OTHER `.env` value — declared or not — still can
  (AT-083 unweakened).
- `src/autotester/ui/routes_project_edit.py:196-208` (`edit_project_submit`) — `exempt=` now a
  per-field dict (`the name` / `the base URL` / `allowed domains` → their own stored values); the
  old cross-field `*project.allowed_domains` fan-out removed (see Deferred/risk note below — it
  was the flat-set bug's own workaround, not an independent behaviour).
- `src/autotester/ui/routes_project_edit.py:235` (`declare_secret`) — `exempt={"the scope": ", ".join(project.allowed_domains)}`.
- `src/autotester/ui/routes_credentials.py:122-128` (`env_url_submit`) — per-field dict, same
  shape as `edit_project_submit`'s two fields.
- `src/autotester/ui/routes_cases.py:276` (case rename) — `exempt={"the title": case.title}`.
- `tests/test_ui_credential_exemption_scope.py` (new file) — 7 new tests for AT-086/AT-087,
  split out from `test_ui_credential_exemption.py` at doctor's 300-line cap (that file's own
  existing convention; `test_ui_credential_exemption.py` itself is untouched, still 128 lines).

## How to verify (commands + expected)

- `uv run ruff check src tests` → expected: `All checks passed!`
- `uv run autotester doctor` → expected: `doctor: clean`
- `uv run pytest tests/test_ui_credential_safety.py tests/test_ui_credential_safety_project.py tests/test_ui_credential_exemption.py tests/test_ui_credential_exemption_scope.py tests/test_ui_credential_bidi.py tests/test_ui_credential_transforms.py tests/test_ui_credential_unicode.py`
  → expected: all pass, 0 failed.

## Actual outputs (from maker's own run)

```
$ uv run ruff check src tests
All checks passed!

$ uv run autotester doctor
doctor: clean

$ uv run pytest tests/test_ui_credential_safety.py tests/test_ui_credential_safety_project.py tests/test_ui_credential_exemption.py tests/test_ui_credential_exemption_scope.py tests/test_ui_credential_bidi.py tests/test_ui_credential_transforms.py tests/test_ui_credential_unicode.py
........................................................................ [ 90%]
........                                                                 [100%]
80 passed, 1 warning in 6.90s
```

**FULL SUITE NOT RUN — RAM ceiling.** `Get-CimInstance Win32_OperatingSystem` free physical
memory measured three times across this build: 1.17 GB, 0.70 GB, 2.31 GB — never ≥ the 3.5 GB
floor. On the last check, a `pytest` process from a DIFFERENT worktree on this same repo
(`D:\autoTesting\.worktrees\at110-approval-signing\.venv\Scripts\pytest.exe`) was also actively
running, which the brief's rule treats as an independent hard blocker regardless of free RAM.
Both conditions were re-checked across the build rather than a single snapshot; neither cleared.
Checker to run `uv run pytest` (no CLI `-q`, `PYTHONUTF8=1`) when RAM allows.

## Capability coverage (each new claim -> its isolating falsification)

All five rows were driven in a throwaway copy of `src/autotester/` in the scratch directory
(`…/scratchpad/at086-087-falsify/autotester/`, sys.path-shadowed ahead of the worktree — see
`harness.py` in that directory), never against the live worktree, per the "never falsify by
running against the live working tree" rule. Each row: clean copy PASS → one anchored sabotage
edit applied → FAIL → sabotage reverted → PASS again (confirmed at the end, all five green).

| capability (one line) | the check that covers it | the falsifying edit | observed (pasted runner output) |
|---|---|---|---|
| A declared-public `.env` key's value is exempt from the credential guard (AT-086) | `SecretStore.public_values()`, `browser/secrets.py:237` | `public_values()` body replaced with `return frozenset()` before reaching the real logic | before: `row_a: PASS` · after: `row_a: FAIL` · reverted: `row_a: PASS` |
| A value that ALSO lives under a non-public key is NOT exempted merely because it collides with a declared-public one (AT-086 hard boundary) | `public_values()`'s `other` set, `browser/secrets.py:237` | `other = set()` (collision-exclusion disabled) in place of the real `other = {...}` comprehension | before: `row_b: PASS` · after: `row_b: FAIL` · reverted: `row_b: PASS` |
| A value stored under one field's exemption does not exempt a DIFFERENT field submitting the same text (AT-087, per-field not flat) | `_refuse_unsafe_submission`'s per-field `exempt.get(label)` call into `_refuse_unsafe_value`, `ui/helpers.py:270` | call site changed to `exempt_value=(text.strip() if text.strip() in exempt.values() else None)` — flat-set emulation | before: `row_c: PASS` · after: `row_c: FAIL` · reverted: `row_c: PASS` |
| A credential split across an exempt field and a fresh one is still caught — the exempt field stays in the join as context (AT-087 primary) | `_refuse_unsafe_submission`'s `fresh` list, `ui/helpers.py:272` | `fresh` reverted to the pre-fix filter: `if text.strip() not in (exempt or {}).values()` (drops exempt fields from the join again) | before: `row_d: PASS` · after: `row_d: FAIL` · reverted: `row_d: PASS` |
| An exempt field's OWN matching value does not self-trigger the join merely by being present (AT-087 accepted-risk mitigation) | `_refuse_unsafe_submission`'s `redactor(exclude=excluded)` call, `ui/helpers.py:275` | call changed to `secrets.redactor()` (no `exclude`) | before: `row_e: PASS` · after: `row_e: FAIL` · reverted: `row_e: PASS` |

Raw before/after console lines (from the actual runs, not summarised):
```
row_a: PASS   (clean)      row_a: FAIL   (sabotaged)      row_a: PASS   (reverted)
row_b: PASS   (clean)      row_b: FAIL   (sabotaged)      row_b: PASS   (reverted)
row_c: PASS   (clean)      row_c: FAIL   (sabotaged)      row_c: PASS   (reverted)
row_d: PASS   (clean)      row_d: FAIL   (sabotaged)      row_d: PASS   (reverted)
row_e: PASS   (clean)      row_e: FAIL   (sabotaged)      row_e: PASS   (reverted)
```
Final sanity pass (all five, clean copy, run last): `row_a: PASS`, `row_b: PASS`, `row_c: PASS`,
`row_d: PASS`, `row_e: PASS`.

These five rows are also exercised end-to-end through the real FastAPI app in
`tests/test_ui_credential_exemption_scope.py` (7 tests, all green in the pytest run above) —
the harness rows isolate the exact mechanism; the pytest tests prove the routes wire it up.

**Hard-boundary claim not independently falsified here (structural, not behavioural):** "the
declaration itself cannot be set to a secret key name by a request." `PUBLIC_ENV_KEYS` is a
module-level constant in `core/env.py`; no `Project` field, `Form` parameter, or route reads or
writes it (`grep -rn PUBLIC_ENV_KEYS src/autotester/ui` returns nothing outside `helpers.py`'s
read-only `secrets.public_values()` call). `NO ISOLATING FALSIFICATION — absence of a route is a
structural property, not a behaviour a sabotage edit can flip; the closest behavioural proxy is
`test_a_secret_declaration_cannot_widen_the_public_env_key_list` (declares a `SecretRef` with a
key name matching a real `.env` key and confirms it still refuses), which is in the green pytest
run above.

## Live browser evidence

`SKIP — RAM ceiling`. UI-touching per D-024 (`ui/helpers.py`, `ui/routes_project_edit.py`,
`ui/routes_credentials.py`, `ui/routes_cases.py` are route/helper modules under the D-024
definition). Free RAM measured 0.70–2.31 GB across the build, and a concurrent pytest process
from another worktree (`at110-approval-signing`) was active on the last check — neither a local
uvicorn server nor a real Playwright browser was launched. Would have onboarded a project whose
`base_url` equals a declared-public FAKE `.env` value (temp env, never the real `.env`) and
confirmed 303 + the project page rendering. Checker to run this live pass when RAM allows.

## Deferred — needs a decision

None new. The `*project.allowed_domains` fan-out removed from `edit_project_submit`,
`declare_secret`, and `env_url_submit`'s `exempt=` sets was the flat-set bug's own workaround
(AT-087's second symptom: it let one field's value validate a different field) — removing it is
the fix, not a new scope question, and no passing test relied on the fan-out (confirmed by
reading every test in `test_ui_credential_safety_project.py` and
`test_ui_credential_exemption.py` before removing it).

## Status: checked-PASS (qa/verdicts/at086-087-exemption.md FINAL, Cycle checked: 1, c7591ef)
