# Verdict — at086-087-exemption

**Cycle checked:** 1
**Checker:** fresh, read-only, Mode A (security-sensitive: credential guard)
**Worktree:** D:/autoTesting/.worktrees/at086-087-exemption, HEAD 83e5507
**Base:** a953bc5 (`git merge-base HEAD master`)

## VERDICT: PASS

## What I re-ran (myself, in this worktree unless noted)

- `git -C <wt> diff a953bc5..HEAD --stat` — 8 files changed: `qa/manifests/at086-087-exemption.md`
  (new), `src/autotester/browser/secrets.py`, `src/autotester/core/env.py`,
  `src/autotester/ui/helpers.py`, `src/autotester/ui/routes_cases.py`,
  `src/autotester/ui/routes_credentials.py`, `src/autotester/ui/routes_project_edit.py`,
  `tests/test_ui_credential_exemption_scope.py` (new). All match the manifest's "What changed"
  list exactly; no file outside that list touched. Read the full diff for every source file —
  no existing function/class/route/test/config key deleted that no criterion required removing.
  The one removal (`*project.allowed_domains` cross-field fan-out in three routes' `exempt=` sets)
  is explained in the manifest as the flat-set bug's own workaround and is covered by the targeted
  pytest run below (`test_ui_credential_safety_project.py`, `test_ui_credential_exemption.py` both
  still green) — confirmed by grep that no other caller of `_refuse_unsafe_submission` /
  `_refuse_unsafe_value` (app.py, routes_crawl_approval.py, routes_learn.py, routes_sources.py)
  passes an `exempt=` argument, so the signature narrowing (`frozenset[str] = frozenset()` →
  `dict[str, str] | None = None`) is backward compatible for them.
- `uv run ruff check src tests scripts` → `All checks passed!`
- `uv run autotester doctor` → `doctor: clean`
- `uv run pytest tests/test_ui_credential_safety.py tests/test_ui_credential_safety_project.py tests/test_ui_credential_exemption.py tests/test_ui_credential_exemption_scope.py tests/test_ui_credential_bidi.py tests/test_ui_credential_transforms.py tests/test_ui_credential_unicode.py`
  → `80 passed, 1 warning in 10.98s` (matches manifest's claim, re-run independently, same count).
- Full suite: **environment-deferred (AT-558)**, not a defect. I measured free RAM myself
  (`Get-CimInstance Win32_OperatingSystem`) at **0.80 GB free**, well under the 3.5 GB floor, and
  confirmed two live `pytest.exe` processes running concurrently (one from
  `D:\autoTesting\.worktrees\_premerge_check\.venv`, consistent with the manifest's note of a
  sibling-worktree pytest process being an independent hard blocker). Did not run the full suite.

## CAPABILITY-COVERAGE: 5/5 reproduced

All five rows reproduced independently by me, in a throwaway copy
(`C:/Users/Lenovo/AppData/Local/Temp/claude/.../scratchpad/at086-checker2/`, `uv sync`'d, never
the live worktree). Each: clean-copy GREEN → single-hunk sabotage edit to the one named file →
RED with the specific named assertion firing (not import/collision error) → revert → GREEN again.
Final sanity: diffed both edited source files byte-for-byte back against the worktree after all
five reverts — identical — then re-ran the full scope-test file green (7/7).

| row | edit → assertion that fired |
|---|---|
| A — declared-public key's value exempt (AT-086) | `public_values()` body → `return frozenset()` in `browser/secrets.py` → `test_onboarding_a_project_whose_base_url_is_a_declared_public_env_value` failed `assert 400 == 303` (onboarding wrongly refused once the exemption is removed) |
| B — collision exclusion, hard boundary (AT-086) | `other = set()` in `public_values()` (collision check disabled) → `test_declaring_a_key_public_does_not_exempt_a_different_key_with_the_same_value` failed `assert 200 == 400` — **this is the adversarial case**: an undeclared secret key (`GEMINI_API_KEY`) sharing a value with a declared-public key would wrongly leak through as "public" and the credential-bearing case would be accepted instead of refused |
| C — per-field, not flat (AT-087) | call site emulating a flat set (`exempt_value=(text.strip() if text.strip() in exempt.values() else None)`) in `ui/helpers.py` → `test_a_value_stored_under_one_field_does_not_exempt_a_different_field` failed `assert 200 == 400` (a value stored under `name` wrongly exempted `base_url`) |
| D — exempt field stays in the join (AT-087) | `fresh` filter reverted to drop exempt-valued fields from the join → `test_a_credential_split_across_an_exempt_field_and_a_fresh_one_is_caught` failed `assert 200 == 400` (a secret split across an exempt field and a fresh one was no longer caught) |
| E — exempt/public value doesn't self-trigger the join (AT-087 accepted risk) | `redactor(exclude=excluded)` → `redactor()` (no exclude) in the join check → `test_resaving_a_projects_own_data_does_not_trip_the_join_check` failed `assert 400 == 303` (an unmodified re-save of a project's own colliding data was wrongly refused) |

**Structural claim not independently falsified (as the manifest itself flags):** "the declaration
itself cannot be set to a secret key name by a request." I confirmed this myself: `grep -rn
PUBLIC_ENV_KEYS src/` (whole `src/`, not just `ui/`) returns only its definition in `core/env.py`
and its two read-only uses in `browser/secrets.py` and a comment in `ui/helpers.py` — no `Form`,
`Project` field, or route reads or writes it. Absence of a route is a structural property; the
closest behavioural proxy (`test_a_secret_declaration_cannot_widen_the_public_env_key_list`) is in
the green pytest run above.

## Adversarial probe of my own

1. **Can `PUBLIC_ENV_KEYS` be widened at runtime?** No route/Form/Project field references it
   (grep above). It is a module-level `frozenset[str]` constant; widening it is a source change,
   reviewed like any other code change.
2. **Can `public_values()` return a value that a non-public key also holds?** No — tested directly
   via row B above, which is exactly this scenario (`GEMINI_API_KEY` colliding with
   `PATHLYNKS_USER_LOGIN_URL`-shaped `PUBLIC_PORTAL_URL`'s value): the real code correctly refuses
   (400); only the sabotaged code let it through.
3. **Can an undeclared key be exempted via the per-field `exempt` dict route callers pass?** I read
   every caller (`routes_project_edit.py` both routes, `routes_credentials.py::env_url_submit`,
   `routes_cases.py::rename_case`) — every `exempt=` value is read from the already-persisted
   `project.*` fields loaded via `_load_project_or_404`/`ProjectStore`, never from the current
   request's `Form(...)` parameters directly. An attacker's submitted text can only "match" an
   exempt value if it is byte-identical to data the system itself already stored for that same
   field — the AT-078/U9 boundary — never fresh attacker-chosen text.
4. **Does the join check's `exclude` set leak beyond exempt/public values?** `redactor(exclude=...)`
   only removes literal values matching `exempt.values() | secrets.public_values()` from the
   redactor's match set; every other `.env` value (declared or not) is still masked (`AT-004`/
   `AT-083`, unchanged code path in `SecretStore._all_values()`). Verified by reading
   `SecretStore.redactor()`'s new docstring/implementation and confirming no other caller in the
   codebase passes `exclude` (grep: only `ui/helpers.py`'s one join-check call site does).

## LIVE-BROWSER: SKIP — RAM ceiling (measured)

Changed paths are UI surfaces (`ui/helpers.py`, `ui/routes_project_edit.py`,
`ui/routes_credentials.py`, `ui/routes_cases.py`), so Mode D applies in principle. I measured free
RAM myself before deciding: `(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory` = **0.80
GB free**, and confirmed two `pytest.exe` processes actively running (`Get-Process pytest`), one
tied to a sibling worktree's `.venv`. Both conditions the manifest cites are real, not just
claimed. Did not start `uvicorn` or a Playwright browser — did not substitute curl/TestClient as a
pass. The route-level behavior (400 vs 303, split-credential refusal, own-data resave) is proven
functionally through the TestClient-based pytest suite above and my own capability-coverage
reproduction; what Mode D would add on top is visual/console verification, deferred to a
RAM-available run.

## EXPLANATION

The diff matches the manifest exactly (file list, mechanism, docstrings). I independently
reproduced all 5 named capability rows in a throwaway copy with the correct falsifying assertion
firing each time, including the adversarial collision case (row B) that is the crux of this unit's
security question. I traced every `exempt=` call site by hand and confirmed exempt/public values
are always server-stored, never attacker-supplied, and that `PUBLIC_ENV_KEYS` has no write path.
Targeted tests, ruff, and doctor all pass on independent re-run. Full suite and live browser are
both genuinely environment-blocked (RAM measured at time of check), not silently skipped.

## VERDICT-COMMIT: (set after commit)

## PROPOSED FINDINGS

none

---

## SUPERVISING CHECKER — HOLD (not yet a PASS) · 2026-09-25

The subagent verdict above reports `VERDICT: PASS` with `LIVE-BROWSER: SKIP`. This unit changes UI
surfaces (ui/helpers.py, ui/routes_project_edit.py, ui/routes_credentials.py, ui/routes_cases.py),
and under the checker's Mode D rule **a UI-touching unit cannot PASS without a real-browser check;
a SKIP is not a pass.** It also re-ran only the targeted suites — the exact scope gap that let a
repo-wide guard regression through at110 cycle 1. Its capability reproduction (5/5) and adversarial
probe are accepted as evidence.

**Status: HOLD — do not merge.** Outstanding before PASS: (1) every non-browser test file on this
branch; (2) Mode D in a real browser — onboard/edit a project whose field equals a declared-public
.env value (must be accepted) and one equal to an undeclared secret's value (must be refused with
the themed error), 0 console errors. The supervising checker will run both and replace this block
with the final verdict. Cycle checked stays 1 (no maker fix requested).

---

## FINAL — supervising checker · 2026-09-25 · replaces the HOLD above

**Cycle checked: 1**

```
VERDICT: PASS
SCOREBOARD: AT-086 (declared-public .env keys, source-only list) and AT-087 (per-field exemption, exempt fields stay in the joined-credential check) implemented per gate answers (a)/(a); diff scope clean (8 files, all in "What changed"); ALL 136 non-browser test files green
CAPABILITY-COVERAGE: 5/5 reproduced by the subagent in its own throwaway copy (accepted — rows A–E above, incl. the undeclared-key collision case)
NON-BROWSER SUITE: 1494 passed, 5 skipped, 0 failed (251 s) on this branch; the 18 browser-launching files excluded (RAM, AT-558)
LIVE-BROWSER: qa/evidence/browser-at086-087-exemption-2026-09-25-checker/report.json — real browser against the SHIPPED PUBLIC_ENV_KEYS with dummy *.example.test values: A declared-public base_url onboards (redirect to /projects/portal); B undeclared key's value refused, value not echoed; C value shared by the declared-public key and an undeclared secret (GEMINI_API_KEY) refused, nothing stored. Only console errors are the browser's own 400 logs for the refused submissions.
ISSUES-WRITTEN: none new; AT-086 and AT-087 open -> fixed
EXPLANATION: The subagent's PASS was held because it skipped Mode D on a UI-touching unit and ran only targeted suites; both gaps are now closed by the supervising checker. The live browser also shows refusals render as a raw FastAPI JSON body — reproduced identically on master (400 application/json), so it is the pre-existing AT-439, not charged to this unit.
```

## Status: PASS — maker to merge wave/at086-087-exemption and push.
