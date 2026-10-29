# Manifest - hint-malformed-bounds

**Status:** ready-for-check
**Fix cycle:** 0
**Security trigger:** YES (light) - touches the consent refusal text (`core/consent.py`, `schema/approval.py`, D-018/D-112). No ceiling, signing, row shape or `approve` behaviour changes; only what a refusal prints.
**Authority:** non-blocking notes N1 and N2 in `qa/verdicts/cli-clamp-and-standing-help.b.md` (Residual notes).
**Branch:** `fix/hint-malformed-bounds` (worktree `D:/autoTesting/.claude/worktrees/hint-malformed`, off `fix/cli-clamp-and-standing-help` a8ef5392)
**Not done by the maker:** no merge, no push, nothing in the main checkout, no edit to `qa/contracts/` or `docs/DECISIONS.md`.

## Criteria (judge against these)
- **C1 (N2)** A refusal whose request has a malformed bound (negative, NaN, infinite, a bool, or absurdly large) names each bad bound by its flag, its value and why (`--max-actions is -1: negative; it must be 0 or more`), and prints NO `uv run autotester approve` command, no "Grant one with", no `--standing` line - for every `ApprovalKind`.
- **C2 (N2)** Every bad bound is named when several are bad; a good bound is not named.
- **C3 (N1)** No printed number exceeds 13 digits: above 10**12 a bound shows as `over 1000000000000` (`under -...` for negatives). A 1e308 wall clock, `10**400` and `10**5000` (whose `str()` raises) refuse cleanly with text < 700 chars and "implausibly large". `grant_clamp_warning` caps the same way (< 400 chars).
- **C4** A well-formed request still gets its `approve` command (bounds, `--standing` line for crawl) and the ceiling note when over; `approve` itself is unchanged (strict `derive_grant_bounds`).
- **C5** `explore demo --max-actions -1` exits 2, names `--max-actions is -1`, prints no approve command.
- **C6 (design rules)** `core/consent.py` 300 lines, `schema/approval.py` 299, `cli_crawl.py` 300 (untouched); functions <= 50 lines; no new module; ruff clean; helpers live in `schema/approval.py`.

## What changed (file:line on the branch head)
- `src/autotester/schema/approval.py:106-136` - new `_PRINT_CAP`, `_shown` (cap + round-up display, replaces `_whole_seconds`), `invalid_bounds_message` (replaces `hint_grant_bounds`, which no longer has a caller); `grant_clamp_warning` uses `_shown`. Docstrings of `derive_grant_bounds`, `_margined`, `_is_valid_bounds`, `grant_clamp_warning` tightened to stay under 300 lines.
- `src/autotester/core/consent.py:144-170` - `_grant_command` becomes `_grant_advice` (the whole refusal tail): returns `invalid_bounds_message` when non-empty, else the clamp note, "Grant one with" and the `--standing` line; the raise at line 266 calls it. Uses strict `derive_grant_bounds` (safe: invalid input was returned before).
- `tests/test_grant_clamp_notes.py` - cycle-1 test `test_hint_bounds_fall_back_...` removed with `hint_grant_bounds`; 8 new tests (parametrised to 109 cases in the file) for C1-C5.
- Advice-scan: the "implausibly large" reason is a plain string (an f-string naming `_PRINT_CAP` tripped `tests/test_cli_advice_resolves.py::test_the_collector_reports_what_it_could_not_resolve`).

## Judgement calls (checker, please confirm)
1. A request bound above 10**12 is treated as malformed for every kind, so a 1e308 wall clock gets the "implausibly large" note instead of the LIVE_CASE ceiling warning. Nothing real plans that; the ceiling is 86400s.
2. `hint_grant_bounds` was removed (dead after this change) rather than kept.

## Tests run (worktree, 2 files per call, `-o addopts=`, one pytest at a time)
- Red first: new tests collected with ImportError on `invalid_bounds_message`; then, with the implementation in and the new `if note := ...` branch disabled, `tests/test_grant_clamp_notes.py` -> 86 failed, 23 passed.
- `tests/test_grant_clamp_notes.py tests/test_cli_advice_resolves.py` -> 150 passed
- `tests/test_consent.py tests/test_auto_size_budget.py` -> 54 passed
- `tests/test_approve_cli.py tests/test_cli_release.py` -> 19 passed
- Before the final lint/string tweaks (re-verified for the touched files above): `tests/test_approve_cli_bounds.py tests/test_grant_bounds_caps.py` -> 17 passed; `tests/test_consent_followups.py tests/test_cli_release.py` -> 86 passed
- `uv run ruff check src tests scripts` -> All checks passed
- `uv run autotester doctor` -> 2 violations, both `docs/SNAPSHOT.md` stale-generated / stale-committed (pre-existing, same as the parent branch)
