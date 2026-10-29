# Verdict B (adversarial) - cli-clamp-and-standing-help

**Verdict:** PASS
**Cycle checked:** 1
**Branch / head checked:** fix/cli-clamp-and-standing-help @ cdf15ea3 (off master a6e03fa4)
**Checker:** B, fresh context, read-only toward src and tests. Probes and the revert plugin are in `.work/` (gitignored). Combined seat: also re-judged every manifest criterion (C1-C10) and the cycle-0 B findings F1-F3.

## Cycle-0 findings: closed by falsification
| Finding | Result | Evidence |
|---|---|---|
| F1 refusal crash on inf / nan / -1 | CLOSED | `core/consent.py:150` now calls `schema/approval.py::hint_grant_bounds` (new, lines 108-116), which echoes invalid bounds and otherwise calls the strict `derive_grant_bounds`. Library probe `.work/probe_b1.py` (the cycle-0 one): 32 combinations, 0 crashes (cycle 0: 29). New wider probe `.work/probe_b3.py`: 4 kinds x 15 values^3 (0, -1, 1, 5, 2001, 10**30, inf, nan, -2.5, 1e308, 86400.0004, True, False, 1e-9, -inf) = 16875 `require_approval` calls, 0 crashes, all `ApprovalRequired`. CLI probe `.work/probe_b2.py`: `explore demo --wall-clock inf`, `--max-actions -1`, `--wall-clock nan` and the plain call all exit 2 with "refusing to start a crawl run" (cycle 0: exit 1, ValueError). Revert `consent.hint_grant_bounds` back to `derive_grant_bounds` in memory (`.work/revert_plugin2.py`, REVERT=C7): 34 failed (malformed-bound refusal cases across the kinds plus the 4 `explore` exit-2 cases), 38 passed; unreverted 72 passed. |
| F2 wall-clock formatting | CLOSED | `approval.py::_whole_seconds` (lines 119-122) is `math.ceil`, `inf` shown as-is. `grant_clamp_warning(LIVE,1,1,86400.0004)` prints `planned 86401s > ceiling 86400s`; 86400.0 gives `''`; 1234567.0 prints `1234567s` (probe_b3 plus the test). Revert to `:g` (REVERT=C8): `test_the_wall_clock_in_the_warning_is_whole_seconds_and_never_reads_equal` fails (1 failed, 71 passed). |
| F3 bool accepted | CLOSED | `_is_valid_bounds` (lines 82-84) excludes `bool`. Revert (REVERT=C9): `test_a_bool_is_not_a_bound[bad0]` and `[bad1]` fail (2 failed, 70 passed). `hint_grant_bounds` shares the predicate, so a bool in the refusal path is echoed and refused, not crashed (probe_b3 includes True/False). |

## Criteria
| # | Result | Evidence |
|---|---|---|
| C1 refusal hint | PASS | `core/consent.py:263` inserts `grant_clamp_warning(...)` before "Grant one with:". Unchanged since cycle 0; `test_the_refusal_hint_says_the_plan_is_over_the_ceiling` and `..._is_silent_when_the_plan_fits` pass in the 72-test run. |
| C2 `approve` note | PASS | `run_gates.py:133-134`; `test_approve_says_so_when_the_derived_plan_is_clamped` passes (still signs, exit 0, `max_actions == MAX_GRANT_ACTIONS`); fitting plan prints no ceiling text. |
| C3 one place | PASS | `grep` of `src`: wording and over-ceiling test only in `schema/approval.py`; the two callers are `consent.py:263` and `run_gates.py:134`. |
| C4 total derivation | PASS | Strict `derive_grant_bounds` unchanged except the bool rule; `approve` still strict (`run_gates.py:108`). Saturation and the valid-input cases pass. |
| C5 `--standing` help | PASS | `test_the_standing_help_says_crawl_only` passes; `tests/test_cli_advice_resolves.py` site count untouched. |
| C6 design rules | PASS | `wc -l`: cli_crawl.py 300, consent.py 300, approval.py 286, run_gates.py 134, advice_scan.py 291; `uv run ruff check src tests scripts`: All checks passed; no new module; `autotester doctor`: 2 violations, both `docs/SNAPSHOT.md` stale-generated / stale-committed (pre-existing, same as manifest). |
| C7 refusal never raises | PASS | See F1 above. |
| C8 whole seconds | PASS | See F2. |
| C9 bool rejected | PASS | See F3. |
| C10 advice-scan red | PASS | `tests/test_cli_advice_resolves.py` fully green: `tests/test_cli_advice_resolves.py tests/test_consent.py` -> 78 passed. `advice_scan.py::KNOWN_NUMERIC_IMPORTS = {"MAX_GRANT_PROBES"}` is named, not shape-based; its only other use in `src` is `ui/routes_crawl_approval.py:22,202-203` (the f-string it was added for), so no command-string hole is hidden. Revert to an empty set (REVERT=C10, patching the module the test imports as `advice_scan`): `test_the_collector_reports_what_it_could_not_resolve` fails (1 failed, 40 passed), so the exemption is load-bearing and the file is not trivially green. |

## Neighbour regression runs (worktree, 2 files per call, `-o addopts=`)
test_approve_cli + test_approve_cli_bounds 21 passed; test_grant_bounds_caps + test_consent_followups 85 passed; test_run_launcher_approval + test_ui_runs_live_case_approval 25 passed; test_explore_consent + test_ui_crawl_approval 11 passed; test_credential_run_approval + test_standing_approval_grant 40 passed; test_grant_clamp_notes + test_auto_size_budget 72 passed (34 at cycle 0; the rest are the parametrised cycle-1 cases).

## Residual notes (not blocking)
- N1 (info): with an astronomically large finite wall clock (1e308), the warning prints the full integer digits (`math.ceil` of a float gives a 309-digit int). Unreachable except by deliberate absurd input; the message is still true and the refusal still raises `ApprovalRequired`.
- N2 (info): the refusal path now echoes malformed bounds into the suggested `approve` command (e.g. `--max-actions -1`); that command is itself rejected by the strict `approve` path. Same refusal posture as master.
- N3 (info, carried from cycle 0): the UI pre-fill `derive_live_case_grant` carries no clamp note; out of scope for the criteria.

## To close
Nothing outstanding. The maker may flip the manifest to `checked-PASS`. No merge or push done by this checker (instruction from the dispatching agent).
