# Verdict - consent-followups (checker A: criteria + code review)

**Verdict:** FAIL
**Cycle checked:** 1
**Branch / head judged:** `fix/consent-followups` 3e4098c3 (cycle-1 diff 202d2b8c..3e4098c3; cycle-0 base d20eb037)
**Scope:** F1-F5, the cycle-1 items (B1, production flag, non-finite wall clock, stale docstring), revert tests, finite-row id/signature, file sizes. Checker B's sharded suite is separate and not duplicated.

## Blocking findings (both in `stages/run_service.py`, the B1 fix)
1. **`_report` now crashes on a malformed `base_url` (regression).** `run_service.py:42` `urlsplit(url)` raises `ValueError: Invalid IPv6 URL` for e.g. `http://[::1/login`; `Project` accepts that string (saved without error) and `_report` (`run_service.py:47-58`, call at `:57`) is the builder of EVERY refusal/usage/failed report, so the refusal path itself would raise instead of returning an exit code. Before cycle 1 (`202d2b8c`) `_report` used `frozenset({proj.base_url})`, no parsing, no crash. Probe (scratchpad `probe.py`, real `ProjectStore`): `http://[::1/login CRASH ValueError Invalid IPv6 URL`. Fix: wrap the parse (`except ValueError` -> empty exemption set, fail closed), with a test.
2. **A credential embedded in the URL PATH is still printed (F1 / C5).** `_pasteable` (`run_service.py:39-44`) only rejects userinfo, query, fragment and `scrub_url_credentials` changes (query-param names). A magic-link style base_url `https://demo.test/magic/AbC123SecretTok` that is also a `.env` value passes every test and is exempted: probe output `--target "https://demo.test/magic/AbC123SecretTok"` (should have been `[REDACTED]:DEMO_MAGIC_URL`). This is the same class as cycle-0 B1 (credential-bearing base_url unmasked), one component over. A heuristic cannot prove a path clean; the safe options are exempt only when the path has no opaque token-like segment, or exempt only when the `.env` key is a known-public/login-URL key, or keep mask and print the real target from a non-scrubbed channel. Maker to pick and test; judgement is the maker's, but the leak must close.

## Criteria (all other items PASS)
| # | Result | Evidence |
|---|---|---|
| F1 | FAIL (see blocking 1, 2) | clean URL path works: `run_service.py:56-58` re-scrubs `message` alone with the exemption; query/userinfo/fragment/`?next=` stay masked (4 cycle-1 tests pass). Gaps above. |
| F2 | PASS | `core/consent.py` `_grant_command` LIVE_CASE `min(max(probes, actions*PROBES_PER_ACTION), MAX_GRANT_PROBES)`; gate floor unchanged. Unchanged since cycle 0 (not in cycle-1 diff). |
| F3 | PASS | `core/consent.py:214` `_width`, `:257` `max(covering, key=_width)`. Unchanged since cycle 0. Stale docstring now fixed: `stages/real_acceptance.py:53-56` states human-then-widest, newest-first only breaks ties. |
| F4 | PASS | `cli_crawl.py:271` `datetime.now(UTC).isoformat()`. |
| F5 | PASS | `ui/routes_crawl_approval.py:238` `standing.strip().lower() in ("1","on")`. |
| Production flag (cycle 1) | PASS | `ui/routes_crawl_approval.py:260` `project.production or production.strip().lower() in ("1","on")`; the real form posts `value='1'` (`:44,47`). 9 cases (`1`,`on`,` ON ` true; `0,false,off,no,x,""` false). |
| Non-finite wall clock (cycle 1) | PASS | `schema/approval.py:85` `allow_inf_nan=False`; NaN/inf/-inf rejected at validation. `max_actions`/`max_probes` are ints. Existing rows: dummy-key id check, `_row(wall_clock_s=600000000.0)` id `appr_6f4ee6333a37`, `0.0` id `appr_1bb648a427c9`, signature `9025bc7d...` identical at head and with `schema/approval.py` reverted to 202d2b8c. All 15 rows in the worktree's `projects/*/approvals.jsonl` still load under the new schema. |
| Stale docstring (cycle 1) | PASS | see F3. |

## Revert tests (each cycle-1 fix reverted alone to 202d2b8c, `tests/test_consent_followups.py -o addopts= -q`, restored, worktree clean after)
- `stages/run_service.py` reverted: 4 failed (B1 x4), 33 passed.
- `ui/routes_crawl_approval.py` reverted: 5 failed (production `0,false,off,no,x`), 32 passed.
- `schema/approval.py` reverted: 3 failed (nan, inf, -inf), 34 passed.
- Head: 37 passed.
- The two blocking findings have NO covering test (neither a path-token nor a malformed base_url case exists), which is why head is green.

## Other checks
- Cycle-1 targeted set (13 files incl. `test_consent`, `test_ui_production_approval`, `test_ui_crawl_approval*`, `test_approval_signing`, `test_approval_prod_gate`, `test_report_export_secrets`, `test_approve_cli*`, `test_standing_approval_grant`, `test_real_acceptance`): 207 passed.
- `ruff check src tests scripts`: All checks passed.
- `autotester doctor`: 34 violations, all `decision-citation-dangling`, every one citing D-110/D-111 (expected); no code rule fails.
- Sizes: `core/consent.py`, `ui/routes_crawl_approval.py`, `stages/report_export.py` 300 lines each (at the limit, not over); `run_service.py` 137; `schema/approval.py` 197; `tests/test_consent_followups.py` 243.

## Not checked here
Full sharded suite (checker B), manifest flip (maker), merge/push (human gate).
