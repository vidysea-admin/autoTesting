# Verdict - consent-followups (checker A: criteria + code review)

**Verdict:** PASS
**Cycle checked:** 2
**Branch / head judged:** `fix/consent-followups` 4f46fc5b (cycle-2 diff 3e4098c3..4f46fc5b touches only `src/autotester/stages/run_service.py`, `tests/test_consent_followups.py`, the manifest)
**Scope:** the two cycle-1 FAILs (path-embedded credential printed; malformed base_url crashes `_report`), the removed-test coverage question, and F1-F5 / cycle-1 items for regression. Checker B's sharded suite is separate and not duplicated.

## Cycle-1 FAILs: both closed
1. **Path-embedded credential (F1 / C5): closed.** `run_service.py:38-60` `_pasteable` is now a positive allowlist: ASCII with every char in `!`..`~` and no `;?#` (`:48`); `urlsplit` guarded (`:49-52`); scheme http/https and netloc `_PLAIN_HOST` plain host[:port] (`:53-54`); path empty, `/`, or each segment `[a-z-]{1,32}` (`:55-58`). Tests: `test_consent_followups.py` `_NOT_PLAIN` (19 cases incl. `/magic/AbC123SecretTok`, `/t/SEGsecret9XYZ/login`, `/login/bob:PATHsecret9%40x`) assert `_pasteable == frozenset()`, and a parametrized end-to-end `_report` test with the URL also in `.env` asserts the URL and each token are absent from the message. The clean-URL cases (`/signin`, bare host, `/`, `:8080/sign-in/`, `/a/b-c/login`) stay readable.
2. **Malformed base_url crash: closed.** `run_service.py:49-52` `except ValueError -> frozenset()`; `http://[::1/login` and `http://[bad` are in `_NOT_PLAIN`, and the end-to-end test asserts `rep.exit_code == REFUSED` with no exception. My own probe (scratchpad `p.py`): `http://[::1/x`, `https://demo.test/login//x`, `//`, `/login/..`, `/Login`, `a\b` all exempt nothing and do not raise.

## Removed-test coverage question
No test was removed in cycle 2. `git diff 3e4098c3 4f46fc5b -- tests/test_consent_followups.py` has exactly one deleted line (the `_report` import, replaced by `_pasteable, _report`). Test count rose 15 -> 18 functions (37 -> 78 collected cases). No malformed-URL report test existed at 3e4098c3 (grep for malformed / `[::1` / IPv6 empty), so nothing dropped; the malformed case is newly covered.

## Criteria
| # | Result | Evidence |
|---|---|---|
| F1 | PASS | `run_service.py:62-76` `_report` re-scrubs `message` alone with `_pasteable(proj.base_url)`; everything else keeps the strict redactor; credential-bearing or non-plain URLs stay masked (tests above). |
| F2 | PASS | `core/consent.py` `_grant_command` unchanged since cycle 1 PASS. |
| F3 | PASS | `core/consent.py` `_width` / `max(covering, key=_width)` unchanged. |
| F4 | PASS | `cli_crawl.py:271` unchanged. |
| F5 | PASS | `ui/routes_crawl_approval.py` standing/production parsing unchanged. |
| Non-finite wall clock | PASS | `schema/approval.py` unchanged since cycle 1 PASS. |

## Commands I ran (worktree, one pytest at a time, `-o addopts=`)
- `tests/test_consent_followups.py`: 78 passed, 1 warning.
- `tests/test_consent.py tests/test_report_export_secrets.py tests/test_cli_mcp.py`: 67 passed, 1 warning.
- `ruff check src tests scripts`: All checks passed.
- `autotester doctor`: 34 violations, all 34 `decision-citation-dangling` (D-110/D-111 not yet entries in this tree); no file-too-long / function-too-long. `run_service.py` 153 lines, `tests/test_consent_followups.py` 296.

## Residual (non-blocking, WARNING)
- The allowlist cannot tell a credential from a word: a magic-link path that is entirely lowercase letters/hyphens, <=32 chars per segment (probe: `https://demo.test/magic/abcdefghijklmnop` is exempted) would still be printed in the hint. The URL is already plaintext in `project.json`, the credential-bearing shapes (digits, mixed case, `%`, `:`, `.`, query, fragment, userinfo) are all masked, and this is the maker's stated narrow widening. Recorded, not blocking.

## Not checked here
Full sharded suite (checker B), manifest flip (maker), merge/push (human gate).
