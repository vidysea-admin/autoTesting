# Verdict - cli-clamp-and-standing-help (checker A: contract)

**Verdict:** PASS
**Cycle checked:** 0
**Branch / head judged:** `fix/cli-clamp-and-standing-help` 09b63b36 (worktree `.claude/worktrees/cli-clamp`, base master a6e03fa4)
**Authority:** `qa/verdicts/auto-size-budget.b.md` F1 (line 36), F2 (line 37) and the `--standing` scoping ask; D-112 item 2 (2000 actions / 24h / 40000 probes ceilings kept).
**Probe (throwaway, no `.env` value read):** `.work/probe_clamp.py` in the worktree (gitignored, not committed).

## Re-runs (mine, one pytest at a time, `uv run --directory <worktree> pytest <2 files> -o addopts=`)
- `test_grant_clamp_notes.py test_auto_size_budget.py` -> 34 passed
- `test_cli_advice_resolves.py test_consent.py` -> 77 passed, 1 failed (pre-existing, classified below)
- `test_approve_cli.py test_approve_cli_bounds.py` -> 21 passed
- `test_standing_approval_grant.py test_ui_runs_serial_entry_order.py` -> 36 passed
- `test_grant_bounds_caps.py test_consent_followups.py` -> 85 passed
- `test_run_approval_grant_budget.py test_ui_runs_live_case_approval.py` -> 20 passed
- `test_run_launcher_approval.py test_ui_crawl_approval.py` -> 24 passed
- `test_explore_consent.py test_approval_signing.py` -> 21 passed
- `test_credential_run_approval.py test_standing_approval.py` -> 42 passed
- `ruff check src tests scripts` -> All checks passed
- `autotester doctor` -> 2 violations: `stale-generated` and `stale-committed`, both `docs/SNAPSHOT.md` (master moved; not this unit's). The decision-citation advisories are non-blocking and, for decisions newer than the base, not defects.
- Whole suite not run (low-memory machine, per the handoff).

## Criteria
- **C1 PASS.** `grant_clamp_warning` (`schema/approval.py:107-121`) lists each over bound as `<bound>: planned N > ceiling M` (wall clock in `s`), ends "Split the cases into smaller runs", and returns "" for a fitting plan and for every non-LIVE_CASE kind. `core/consent.py:262` inserts it before "Grant one with:". Tests `test_the_refusal_hint_says_the_plan_is_over_the_ceiling` (asserts the text precedes "Grant one with:") and `..._is_silent_when_the_plan_fits`. Probe: `(2001,1,86400.1)` names actions and wall clock; `(2000,40000,86400.0)` returns "" (boundary is strict `>`, no off-by-one).
- **C2 PASS.** `stages/run_gates.py:130-134` appends the warning to the "derived from N planned case(s)" note that `approve_cmd` prints. `test_approve_says_so_when_the_derived_plan_is_clamped` (2100-step case: exit 0, text present, signed `max_actions == 2000`) and `..._is_silent_about_ceilings_when_the_plan_fits` (exit 0, no "ceiling").
- **C3 PASS.** Wording and the over-ceiling test exist once, in `grant_clamp_warning`. Callers: `consent.py:262` passes the gate's own `actions, probes, wall_clock_s` (the same args `_grant_command` uses on the next line); `run_gates.py:134` passes `_planned_request(cases)`, which `derive_live_case_grant` (`run_gates.py:108`) also uses. No second copy of the wording or the comparison (grep of `src`).
- **C4 PASS.** `derive_grant_bounds` (`schema/approval.py:91-95`) raises `ValueError("grant bounds must be non-negative and finite ...")` for negative, NaN, +/-inf on all three inputs; the check runs before the kind pass-through, so it covers every kind (probe: all five kinds raise on `(-1,0,0.0)`). `_margined` (`:76-79`) saturates before multiplying, so `(5,5,1.7e308)` -> `GrantBounds(7,140,86400.0)` and `(10**400,10**400,5.0)` -> `(2000,40000,7.0)`, no OverflowError. Unchanged results confirmed: `(0,0,0.0)`, CRAWL `(150,25,900.0)` pass through, `(100,5,100.0)` -> `(125,2500,125.0)`; margin edges `(1599,1,1.0)` -> 1999, `(1600,1,69120.0)` -> 2000/86400 (ceiling). `test_auto_size_budget.py:115-118` inversion is in place and is the intended consequence of F2 (the old assertion encoded the defect); no other existing test needed changing.
- **C5 PASS.** `autotester approve --help` prints `--standing  crawl only; until revoked (autotester revoke)` (`cli_crawl.py:241-242`). `test_cli_advice_resolves.py` is not modified by the branch (`git diff a6e03fa4 HEAD` lists no such file) and `EXPECTED_SITE_COUNT = 32` (`:215`) stands; its site-count test is among the 77 passes.
- **C6 PASS.** Line counts: `cli_crawl.py` 300, `consent.py` 300, `approval.py` 263, `run_gates.py` 134 (rule is <= 300). No new module (`git diff --stat` shows only the manifest, 4 src files, 2 test files; the new test file is a test). New functions are all under 20 lines. ruff clean. Doctor reports no rule this change touches.

## Classification of the red test (pre-existing, not a block)
`tests/test_cli_advice_resolves.py::test_the_collector_reports_what_it_could_not_resolve` also FAILS on master a6e03fa4. I checked out a6e03fa4 detached in `.work/chk-master-a6e03fa4` (removed afterwards) and ran `pytest tests/test_cli_advice_resolves.py -o addopts=` against that tree's own `src` (`PYTHONPATH` set, module path confirmed): `1 failed, 40 passed`, same assertion `[(ui/routes_crawl_approval.py, 203)] == []`. Cause: `ui/routes_crawl_approval.py:203` is `f"max probes must be between 0 and {MAX_GRANT_PROBES}"`; `advice_scan.unresolved_in` (`tests/advice_scan.py:180-189`) flags any interpolated SCREAMING_CASE name it cannot resolve to a string, and `MAX_GRANT_PROBES` is an int imported from `schema.approval` that the scan neither resolves nor lists in `bound_elsewhere`. The test's own docstring says the fix is to resolve the name (add it to `bound_elsewhere` as a known non-string), not to widen the filter. The branch does not touch `ui/` or `advice_scan.py`. Follow-up for whoever owns the AT-675 probes cap.

## Findings (none blocking)
- **F1 (info, cosmetic):** `grant_clamp_warning` formats the wall clock with `:g` (`schema/approval.py:112-113`), which rounds at 6 significant digits: a planned 1234567 s prints `1.23457e+06s`. Harmless (only used past the 86400 ceiling, the value is advisory) but `f"{x:.0f}"` would be exact.
- **F2 (info):** the new validation accepts `bool` (`derive_grant_bounds(LIVE, True, 1, 1.0)` -> `(2, 40, 2.0)`), as before; not a regression and no caller passes one.
- **F3 (info, manifest judgement call 2 confirmed):** `approve` still signs the clamped grant and exits 0 for an over-ceiling plan; the silence is gone, the behaviour is unchanged. Refusing would change D-112 and is a human call. The ceilings, signing and row shape are untouched, so the light security trigger is satisfied.

No contract, `docs/DECISIONS.md` or main-checkout edit by this checker; the only changes are this verdict file.
