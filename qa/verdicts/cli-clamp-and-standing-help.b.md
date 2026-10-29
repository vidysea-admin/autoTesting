# Verdict B (adversarial) - cli-clamp-and-standing-help

**Verdict:** FAIL (one regression, small fix; everything else holds)
**Cycle checked:** 0
**Branch / head checked:** fix/cli-clamp-and-standing-help @ 09b63b36 (off master a6e03fa4)
**Checker:** B, fresh context, read-only toward src and tests. Probes in `.work/` (gitignored).

## Criteria
| # | Result | Evidence |
|---|---|---|
| C1 refusal hint | PASS | `core/consent.py:262-263` inserts `grant_clamp_warning(...)` before "Grant one with:". Reverting only `consent.grant_clamp_warning` in memory turns `test_the_refusal_hint_says_the_plan_is_over_the_ceiling` red (1 failed, 16 passed). |
| C2 `approve` note | PASS | `run_gates.py:133-134`. Reverting only `run_gates.grant_clamp_warning` turns `test_approve_says_so_when_the_derived_plan_is_clamped` red (1 failed, 16 passed). Still signs the clamped grant, exit 0. |
| C3 one place | PASS | wording and test live only in `schema/approval.py:105-121`; both callers pass the gate's request (`consent.py:263`, `run_gates.py:96-100,134`). |
| C4 total derivation | PASS for the stated inputs, but see F1 | Reverting `derive_grant_bounds` to the a6e03fa4 body: 8 failed (6 reject cases, overflow-saturate, inverted auto-size test). Differential fuzz of 40000 (kind, actions, probes, wall) draws, edges 1599/1600/1601, 69119.99/69120/86400, 1.7e308/1.25, LIVE_CASE and CRAWL: 0 differences from the old function on valid input; results never above max(input, ceiling); actions stay `int`. Removing `_margined` saturation: 4 failed. |
| C5 `--standing` help | PASS | `cli_crawl.py:241-242`; `test_the_standing_help_says_crawl_only` reads real `approve --help` output. `EXPECTED_SITE_COUNT` untouched. |
| C6 design rules | PASS | `cli_crawl.py` 300, `consent.py` 300, `approval.py` 263, `run_gates.py` 134 lines; `ruff check` on the 6 changed files: All checks passed; no new module. |

## Findings
- **F1 (medium, regression, blocks PASS): a refusal that used to be a clean `ApprovalRequired` / exit 2 is now an uncaught `ValueError` / exit 1 for malformed bounds.** `core/consent.py:150` (`_grant_command`) calls `derive_grant_bounds` for EVERY kind on the refusal path, and the new validation at `schema/approval.py:92-94` raises for negative, NaN and infinite input. The manifest's judgement call 1 says "no existing caller passes such values"; that is wrong, `autotester explore` takes `--wall-clock` as a bare float and `--max-actions` as a bare int with no `min=` (`cli_crawl.py:55-56`), and `CrawlBounds` does not constrain them (`schema/crawl.py:65-67`), so they reach `explore_consent._require` -> `require_approval`. Same command on master a6e03fa4 vs the branch (probe `.work/probe_b2.py`, a project with no approval):
  - `explore demo --wall-clock inf`: master exit 2 `refusing to start a crawl run ... no approval exists for it`; branch exit 1, `ValueError`, no message.
  - `explore demo --max-actions -1`: master exit 2 refusal; branch exit 1 `ValueError`.
  - `explore demo --wall-clock nan`: master exit 2 refusal; branch exit 1 `ValueError`.
  - Library level (`.work/probe_b1.py`, 32 combinations over CRAWL, READ, LIVE_CASE, VIDEO_REVIEW x inf/nan/-1/1e308 x actions 0/-1): master 0 crashes, branch 29 `ValueError`.
  It fails closed (nothing runs), so this is not a bypass, but the gate's contract is "refuse with `ApprovalRequired`" and every caller catches only that (`cli_crawl.py` `except ApprovalRequired -> Exit(2)`, `cli_video_review.py:79`, `stages/discover.py:51-57`). Any UI route that catches `ApprovalRequired` would 500 instead. No test covers it, so the 13 green files could not show it.
  Fix (either, in place): (a) `_grant_command` must not raise, e.g. build the hint from the raw values when the bounds are not finite and non-negative (or wrap the derive call and fall back to the raw numbers), keeping `derive_grant_bounds` strict for `approve`; or (b) `require_approval` converts the `ValueError` into `ApprovalRequired("... bounds must be non-negative and finite")`. Add a test: `require_approval([], ..., wall_clock_s=float("inf"))` and `actions=-1` raise `ApprovalRequired`, plus `explore --wall-clock inf` exits 2.
- **F2 (low, UX): the wall-clock figure in the warning is formatted with `:g`** (`schema/approval.py:115`). `grant_clamp_warning(LIVE, 1, 1, 1234567.0)` prints `planned 1.23457e+06s`; `86400.0004` prints `planned 86400s > ceiling 86400s`, which reads as a false statement. Format with `.0f` or `ceil`. `inf` prints `planned infs`. Not blocking.
- **F3 (info): a bool passes the new validation** (`derive_grant_bounds(LIVE, True, 0, 1)` -> `GrantBounds(2, 0, 2.0)`); harmless, mentioned for completeness.
- **F4 (info): the UI pre-fill (`ui/routes_credentials.py:198`, `derive_live_case_grant`) carries no clamp note.** The criteria name only the refusal hint and `approve`, so out of scope; the UI refusal text does carry it via `require_approval`.

## Pre-existing red (not a block)
`tests/test_cli_advice_resolves.py::test_the_collector_reports_what_it_could_not_resolve` fails identically on master and on this branch: `1 failed, 40 passed` in `.claude/worktrees/crawl-gaps` (HEAD a6e03fa4; no ui/ or cli files modified there) and `1 failed, 40 passed` in this worktree. `tests/advice_scan.py::unresolved_in_source` returns `[(ui/routes_crawl_approval.py, 203)]`: the f-string `f"max probes must be between 0 and {MAX_GRANT_PROBES}"` at `routes_crawl_approval.py:203` that the advice collector cannot render. Line added by 1dc74b2b ("add max_probes to grant form", AT-675). Unrelated to this unit; the fix is to make the scanner resolve that imported name or reword the line, in another unit.

## Commands run (worktree, one pytest at a time)
- `pytest tests/test_grant_clamp_notes.py tests/test_auto_size_budget.py -o addopts= -p revert_plugin` with REVERT=F2 / F1 / MARGIN: 8 / 2 / 4 failed (monkeypatch plugin `.work/revert_plugin.py`); with REVERT=F1C / F1R: 1 / 1 failed. Unreverted: all 34 pass (26 + 8 in the F2 run are the same 34).
- `pytest .work/test_grant_clamp_notes_probe.py` against master source: collection ImportError on `grant_clamp_warning` (red first confirmed).
- `uv run python .work/probe_fuzz.py`: `cases 40000 diffs 0`.
- `uv run python .work/probe_b1.py` (library) and `.work/probe_b2.py` (CLI), both trees: figures in F1.
- `uv run ruff check <6 changed files>`: All checks passed.

## To close
Fix F1 (small, in place, with the test), set `Fix cycle: 1`, re-request check. F2 is optional in the same edit.
