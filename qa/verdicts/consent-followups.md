# Verdict - consent-followups (checker A: criteria + code review)

**Verdict:** PASS
**Cycle checked:** 0
**Branch / head judged:** `fix/consent-followups` 3cd33a45 (diff d20eb037..3cd33a45)
**Scope of this verdict:** criteria F1-F5, revert tests, code review. Checker B runs the sharded full suite separately; not duplicated here.

## Criteria
| # | Result | Evidence |
|---|---|---|
| F1 | PASS | `stages/run_service.py:41-48`: normal full scrub first, then `message` alone is re-scrubbed with `keep={proj.base_url}` via `report_export._load_redactor(store, keep)` (`report_export.py:76-81`) which passes the existing `SecretStore.redactor(exclude=)` (`browser/secrets.py:250-262`). Only the exact stored base_url is exempt; every other `.env` value stays masked in the message and the rest of the report keeps the strict redactor. UI path unchanged (`ui/routes_crawls.py:44` strips the hint). |
| F2 | PASS | `core/consent.py:156-160`: LIVE_CASE `--max-probes = min(max(probes, actions*PROBES_PER_ACTION), MAX_GRANT_PROBES)`; other kinds print `probes` as before. Gate untouched: `require_live_case_approval` still passes `probe_request(cases)` (`stages/run_gates.py`), `_shortfalls` unchanged. |
| F3 | PASS | `core/consent.py:214-218,243-257`: all covering rows collected, `max(covering, key=_width)`; `_width` = (human-granted, wall clock, probes, actions); Python `max` returns the first of equal keys so a tie keeps the earlier row; non-covering rows only feed `rejections`; with none covering the refusal text path is the same. Revoked rows still listed as `revoked`. Human-first matches `explore_consent` (`sorted(..., key=is_account_derived)`). |
| F4 | PASS | `cli_crawl.py:271` `datetime.now(UTC).isoformat()`; `granted_at` is a free string in the signed payload (`schema/approval.py:98,125`), the UI grant and D-068 mint already use full timestamps (`routes_crawl_approval.py:262`, `consent.py:135`); only reader that orders it is `real_acceptance.py:55` (string sort, date and timestamp forms still order correctly). |
| F5 | PASS | `ui/routes_crawl_approval.py:238` `on = standing.strip().lower() in ("1","on")` drives both `_grant_expiry(on, ...)` (`:193-197`, now bool) and `standing=on` (`:263`). The form checkbox posts `value='1'` (`:67`), so the real UI is unaffected. |

## Revert tests (each fix reverted alone to d20eb037, `tests/test_consent_followups.py -o addopts= -q`, then restored; worktree clean after)
- `core/consent.py` reverted: 4 failed (F2 x2, F3 x2), 16 passed.
- `stages/run_service.py` reverted: 1 failed (F1 hint survives scrub), 19 passed.
- `cli_crawl.py` reverted: 1 failed (F4 same-day regrant), 19 passed.
- `ui/routes_crawl_approval.py` reverted: 8 failed (F5 `0,false,off,no,yes,true,x,space`), 12 passed.
- Head: 20 passed.
- Bonus: `tests/test_consent.py test_approve_cli.py test_ui_crawl_approval.py test_report_export_secrets.py test_standing_approval_grant.py test_run_launcher_approval.py test_approval_revoke.py` = 99 passed.
- `ruff check src tests scripts`: All checks passed. `autotester doctor`: no non-advisory violation other than `decision-citation-dangling`, every one citing D-110/D-111 (expected; none are code rules).

## Design review
- Line limits: `consent.py`, `ui/routes_crawl_approval.py`, `stages/report_export.py` are each exactly 300 lines (wc -l); `run_service.py` 126. `require_approval` within 50 lines (doctor green on function-too-long).
- One concept one place: no new redactor; `exclude=` is the existing hook, `_load_redactor` just forwards it. `_width` is the single ranking key. No `_v2`/duplicate function.
- Security: F1 widens the credential boundary by exactly one string already plaintext in `project.json`; F3 never selects a row `_reject_reason` refused (signature, expiry, production, shortfall all still apply before ranking); production path (`require_project_approval`) still filters to human rows before calling `require_approval`.

## Non-blocking observations (no cycle needed)
1. `run_service._report` loads the `.env` redactor twice per report (second call only when a message exists); negligible.
2. F1 residual: if a different `.env` value is a substring of base_url (e.g. a host string key), the kept base_url is still partially masked (`https://[REDACTED]:B/login`), because only the exact value is exempted. Fails closed, so acceptable.
3. F2 hint under-sizes for runs polling past 20/action; the maker flagged this as a deliberate choice. Gate floor unchanged, no grant invalidated.
4. `production` form field still `bool(production)` (out of scope, as the manifest states).

## Not checked here
Full sharded suite (checker B), manifest flip (maker), merge/push (human gate).
