# Verdict - consent-followups (checker B: adversarial security)

**Verdict:** FAIL
**Cycle checked:** 0
**Branch / head judged:** `fix/consent-followups` 3cd33a45 (diff d20eb037..3cd33a45; 04d33f8d only adds checker A's verdict)
**Scope:** F1 secret exposure through the kept base_url, F3 row selection, F4 granted_at readers, F5 flag tampering, F2 cap and gate. Probes live in `.work/probe_b_f1.py`, `.work/test_probe_b.py`, `.work/test_probe_b_ui.py` (not committed; keys were test-only, no `.env` value read or printed).

## Blocking finding (1)

### B1 - F1 prints a credential when base_url carries one and is itself a `.env` value (C5)
`stages/run_service.py:44-47` re-scrubs `message` with `keep={proj.base_url}`; `browser/secrets.py:259-260` then drops every `.env` entry whose value equals that string from the redactor. Nothing checks that the kept string is credential-free. `Project.base_url` is a bare `str` (`schema/project.py:168`), no validator. So a project whose base_url is a magic-link or userinfo URL, also stored in `.env` (the exact shape the inbox case describes: `*_LOGIN_URL == base_url`), now prints the credential into the report message (CLI stdout, MCP, run log), where before this unit it printed `[REDACTED]:KEY`.

Reproduced (`uv run python .work/probe_b_f1.py`, tmp store, fake values):
- base_url `https://demo.test/login?token=abc123XYZ`, `.env` `DEMO_MAGIC_URL=<same>` -> hint shows `--target "https://demo.test/login?token=abc123XYZ"` (token in clear).
- base_url `https://bob:s3cretPW@demo.test/login`, `.env` `DEMO_URL=<same>` -> hint shows `bob:s3cretPW@` in clear.
- Contrast: when the token/password is ALSO its own `.env` key, it stays masked inside the URL (`token=[REDACTED]:DEMO_TOKEN`), so the hole is exactly "the credential lives only inside the URL value".

C5 (`qa/contracts/core-invariants.md:48-52`): "Everything in that file is masked from logs, prompts, and artifacts, declared or not." The maker's mitigation, that base_url is already plaintext in `project.json`, holds only for the project artifact; it does not make a log/report line an allowed surface, and `projects/*/` is committed to a public repo. No current project is affected (all `base_url` values in `projects/*/project.json` have no userinfo or query), so this is latent, but it is a reproducible regression of a hard boundary and the fix is small.

Suggested fix (edit in place, `run_service._report`): only add the exemption when the base_url is credential-free, e.g. `keep = {proj.base_url} if "@" not in urlsplit(proj.base_url).netloc and scrub_url_credentials(proj.base_url) == proj.base_url else frozenset()`; add a test next to `test_the_grant_hint_target_survives_the_report_scrub_when_it_is_an_env_value` for both probe shapes above (must stay masked). Alternative: mask only the credential part of the URL and keep the rest readable.

## Criteria
| # | Result | Evidence |
|---|---|---|
| F1 | FAIL | B1 above. Otherwise holds: a secret that is a superstring of base_url, another project's URL, and a real password in the same message all stay masked (probe: `[REDACTED]:DEMO_FULL`, `[REDACTED]:OTHER_URL`, `[REDACTED]:DEMO_PW`). Trailing-slash mismatch fails closed (`[REDACTED]:DEMO_LOGIN_URL/`), cosmetic only. |
| F2 | PASS | `core/consent.py:158-160` `min(max(probes, actions*20), MAX_GRANT_PROBES)`, LIVE_CASE only. Probe `test_hint_cap` over every kind and 6 (actions, probes) pairs: never above the cap; non-live kinds print `probes` unchanged. Gate untouched (`_shortfalls`, `consent.py:~163-171`); `test_the_gate_itself_still_checks_the_floor_not_the_hint` passes. Edge: a live floor above 40000 hints the cap (below the floor); unreachable in practice. |
| F3 | PASS | Ranking runs only on rows `_reject_reason` returned None for (`consent.py:249-257`). Probe `test_invalid_wide_rows_never_beat_valid_narrow` (wide rows: expired, revoked by signed revocation, unsigned, forged signature, edited-after-grant, foreign target, foreign project, other kind, no-expiry non-standing, standing on a non-standing kind, production:false for a production run) -> the valid narrow human row is always returned; an unsigned revocation does not revoke; none covering -> `ApprovalRequired`. A wide account-derived row loses to a narrow human row (`_width` first element). Production path still pre-filters to human rows (`consent.py:~280`). Note: a signed row with `wall_clock_s=NaN` covers any run (NaN comparisons are false in `_shortfalls`, pre-existing) and, once chosen among covering rows, can win ranking arbitrarily; it needs the signing key to mint, so not new or blocking. |
| F4 | PASS | Only reader that orders `granted_at` is `stages/real_acceptance.py:55` (string sort); date-only and `isoformat()` forms with and without microseconds still order newest-first (`'+'` < `'.'`). Other `granted_at` users are the video-share tables and writers. Observation: stale docstring at `real_acceptance.py:54` ("`require_approval` returns the first covering row ... newest grant wins") is no longer true when an older covering row is wider (`preflight` ids may now name the wider older row); crawl bounds there already choose widest-then-newest, so behaviour agrees. |
| F5 | PASS | `ui/routes_crawl_approval.py:238`. Probes (`.work/test_probe_b_ui.py`): `"01"`, `"1,0"`, `"True"`, `"enabled"`, `"on\x00"`, `"on\u200b"` -> 400 and nothing saved; `"1"`, `" on\n"`, `"ON"`, `"On"` -> standing with no expiry; standing plus an `expires_at` -> 400; duplicate field `standing=0&standing=1` accepted without error. `"\u00a01"` (NBSP + 1) is accepted as standing because `str.strip()` trims NBSP; harmless (it is an explicit 1). Residual out of scope: `production` still `bool(production)` (`:260`), so `"0"`/`"false"` selects production:true, the more privileged value. |

## Commands run
- `uv run python .work/probe_b_f1.py` (F1, twice, deterministic)
- `uv run pytest .work/test_probe_b.py -o addopts= -q` -> 4 passed (F3, F2)
- `uv run pytest .work/test_probe_b_ui.py -o addopts= -q` -> only the NBSP and the harness-unencodable full-width cases deviate from "400", both benign as noted
- `uv run pytest tests/test_consent_followups.py tests/test_consent.py -o addopts= -q` -> 56 passed

## Not checked here
Full sharded suite (low memory by instruction), manifest flip, merge, push.
