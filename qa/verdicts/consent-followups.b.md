# Verdict - consent-followups (checker B: adversarial security)

**Verdict:** PASS
**Cycle checked:** 2
**Branch / head judged:** `fix/consent-followups` 4f46fc5b (cycle-2 diff 3e4098c3..4f46fc5b: `stages/run_service.py`, `tests/test_consent_followups.py`, manifest)
**Scope:** both cycle-1 B2 defects, the new allowlist `_pasteable` (`stages/run_service.py:38-60`) and its call site (`:70-74`), plus adversarial URL shapes and a crash fuzz. Probe (throwaway, fake values only, no `.env` value read or printed): `.work/probe_b3_f1.py`.

## Cycle-1 FAILs: both closed
- **Path-embedded token printed:** closed. `_PLAIN_SEGMENT = [a-z-]{1,32}` (`run_service.py:39`) is applied to every path segment (`:57-59`). Reproduced with each base_url also written as a `.env` value: `/magic/AbC123SecretTok`, `/t/SEGsecret9XYZ/login`, `/login/bob:PATHsecret9%40x` all print `--target "[REDACTED]:DEMO_URL"`, no leak.
- **Malformed base_url crashes `_report`:** closed. `urlsplit` is inside `try/except ValueError` (`:51-54`), and the ASCII / printable pre-filter (`:49`) runs first. `http://[::1/login`, `http://[bad`, `http://\u2100.test/` (NFKC bomb), lone `[`, NUL, 10k-char URL, empty and whitespace-only base_url: no exception, report returned, masked. Fuzz: 4000 random strings over `[A-Za-z0-9/:.@-_%?#;[]\ \t and unicode lookalikes]` with http/https/HTTP/no prefix, `_pasteable` raised 0 times; every non-empty exemption fully matched `https?://host(/[a-z-]{1,32})*/?` (0 odd exemptions).

## Adversarial matrix (all `ok` = hint masked, unless noted)
Masked: uppercase path, digits in segment, `%6d` encoded letter, `%40`, `..`/`.` segments, `_`, `:` or `.` in a segment, userinfo (plain, token-only, `host:80@evil`), backslash (host and path), IPv6 (valid, unclosed, bad, with userinfo), Cyrillic `\u0435` lookalike host, fullwidth `\uff4c` path, NBSP, `;param`, trailing `?` or `#`, `//` and `login//`, trailing-dot host, empty / non-digit / empty-after-colon port, 6-digit port token, mailto / javascript / file schemes, NUL. Readable (correct, no secret): `xn--` punycode host, `HTTPS://` plain, `host:99999/login` (digits-only port, nothing secret), `/`, bare host, `http://a`.

## Non-blocking residual (WARN, not a regression)
`_pasteable` is a shape test, so a credential that LOOKS like a plain host label or a lowercase word is still printed when it is also a `.env` value (`.work/probe_b3_f1.py`, rows marked LEAK):
- a lowercase-letters-only path segment of up to 32 chars: `https://demo.test/t/qwertyuiopasdfghjklzxcvbnmqwert` (`run_service.py:39`). 33 chars is masked.
- a secret in a host label: `https://opensesameopen.demo.test/`, `https://s3cr3tTOKEN9.demo.test/login` (`_PLAIN_HOST`, `run_service.py:38`, allows any alnum/dot/hyphen label).
No shape rule can tell these from a real word path or hostname; the F1 criterion itself requires the base_url be printed verbatim, and a pure-letter 32-char magic-link path or tokenised host is not a form any committed `projects/*/project.json` base_url has (all are `https://host[/word]`). Cycle-1 suggested `{0,23}`; 32 is slightly wider, same class. Documented here, not a block. Possible later hardening if a tenant-token host or lowercase invite path ever appears: a shorter segment cap or a dictionary / known-host check.

## Criteria
| # | Result | Evidence |
|---|---|---|
| F1 | PASS | both B2 defects closed (above); clean URLs (`https://pathlynks-like.test/signin`, bare host, `/`, `host:port/sign-in/`) readable (`tests/test_consent_followups.py`, `test_pasteable_keeps_a_plain_host_and_word_path_readable`); every other `.env` value still masked (existing test `test_a_secret_that_is_not_the_target_stays_masked_everywhere_else`). |
| F2 | PASS | `consent.py` untouched since cycle 0/1 (diff 3e4098c3..4f46fc5b touches no `consent.py`). |
| F3 | PASS | unchanged. |
| F4 | PASS | unchanged. |
| F5 | PASS | unchanged (UI form parse not touched this cycle). |
| non-finite wall clock, production flag | PASS | not touched this cycle; cycle-1 evidence stands. |

## Coverage of the removed code/test
`git diff 3e4098c3 4f46fc5b` removes no test: only the `_report` import line (now `_pasteable, _report`) and the old `_pasteable` body/import (`scrub_url_credentials`). No malformed-URL report test existed to drop; the cycle-2 additions cover it: `test_pasteable_exempts_nothing_unless_the_url_is_plain` (19 shapes including `[::1/login`, `[bad`, non-URL, non-ASCII, whitespace, 33-char segment, empty netloc) and `test_a_path_or_malformed_base_url_stays_masked_and_never_crashes_the_report` (end-to-end through `_report`, asserts exit code kept, base_url and tokens absent). Whitespace/newline shapes are excluded from the end-to-end case only, and are still asserted at `_pasteable` level.

## Commands run
- `uv run pytest tests/test_consent_followups.py -o addopts=` -> 78 passed, 1 warning
- `uv run pytest tests/test_consent.py tests/test_report_export_secrets.py tests/test_cli_mcp.py -o addopts=` -> 67 passed, 1 warning
- `uv run ruff check src tests scripts` -> All checks passed!
- `uv run autotester doctor` -> 34 violation(s); no file-too-long / function-too-long / duplicate findings (grep); the findings are `decision-citation-*` for D-110/D-111 not yet in this tree (same as the manifest states)
- `uv run python .work/probe_b3_f1.py` (matrix + 4000-string fuzz)
- `git -C <worktree> status --short` empty before writing this file

## Not checked here
Full sharded suite (low memory by instruction), manifest flip, merge, push.
