# Verdict - consent-followups (checker B: adversarial security)

**Verdict:** FAIL
**Cycle checked:** 1
**Branch / head judged:** `fix/consent-followups` 3e4098c3 (cycle-1 diff 202d2b8c..3e4098c3)
**Scope:** re-run of the cycle-0 B1 probes, new bypasses of `_pasteable`, the `production` form parse, the `allow_inf_nan=False` change (model, JSON row on disk, UI form, CLI). Probes (not committed, no `.env` value read or printed, fake values only): `.work/probe_b2_f1.py`, `.work/probe_b2_split.py`, `.work/probe_b2_nan.py`, `.work/test_probe_b2_ui.py`.

## Blocking finding (1)

### B2 - `_pasteable` still prints a credential that lives in the URL PATH (C5), and crashes the report on a malformed base_url
`stages/run_service.py:39-44` declares a base_url "credential-free" when it has no userinfo, query or fragment and `scrub_url_credentials(url) == url`. `scrub_url_credentials` (`core/redact_escaped.py:186-197`) only knows `?k=v` parameters, so a token carried in the path passes every test. Same shape as cycle-0 B1 (magic-link base_url that is also a `.env` value), same result: the report message (CLI stdout, MCP, run log) prints the credential where it printed `[REDACTED]:KEY` before this unit. Reproduced, `uv run python .work/probe_b2_f1.py`, tmp store, each base_url also written as a `.env` value:
- `https://demo.test/magic/PATHtok123456abcdef` -> hint shows `--target "https://demo.test/magic/PATHtok123456abcdef"` (LEAK)
- `https://demo.test/t/SEGsecret9XYZ/login` -> LEAK
- `https://demo.test/login/bob:PATHsecret9%40x` (encoded userinfo-like pair in the path, `@` not literal so the netloc test misses it) -> LEAK
- a base_url with no URL shape at all (`opensesame-not-a-url-9`, `Project.base_url` is a bare `str`) -> LEAK; unrealistic but the same missing positive check.

The docstring claim at `run_service.py:40-41` ("only when it is credential-free") is therefore not true for paths. Severity is low and latent (no `projects/*/project.json` base_url has such a path), the same grade cycle-0 gave B1, so the standard is the same.

Second defect in the same function, new in this cycle: `urlsplit` raises on malformed input and `_pasteable` has no guard. `base_url="http://[::1/login"` or `"http://[bad"` (project loads fine, no validator) -> `_report` raises `ValueError: Invalid IPv6 URL` (`probe_b2_split.py`); `\u2100.test` raises an NFKC `ValueError`. `_report` is also the error path of `run_regression`'s `except Exception` handler, so `autotester run` dies with a traceback instead of a coded report. Before this unit `_report` never parsed. Fails closed (no leak), but it is a new crash in the redaction path.

Suggested fix (edit in place, `_pasteable`): wrap `urlsplit` in `try/except ValueError` returning `frozenset()`; require `scheme in {"http","https"}` and a netloc; and keep the exemption only for a path that cannot carry a secret, e.g. every path segment matches a short plain pattern (`[a-z][a-z-]{0,23}`, no digits, no `%`, no `;`, no uppercase) else return `frozenset()` (the `.env` match then masks it, as before this unit). Add the path/non-URL/malformed cases next to `tests/test_consent_followups.py` B1 tests.

## Criteria
| # | Result | Evidence |
|---|---|---|
| F1 | FAIL | B2 above. Cycle-0 B1 shapes are now closed: `?token=`, `user:pass@`, `#access_token=`, percent-encoded query name (`?%74oken=`), `?next=%2Ftoken%3D..`, uppercase scheme with userinfo or `?TOKEN=`, backslash before `@`, `;jsessionid=`, `;token=`, non-credential query names (`?u=`, `?ref=`), IDN host with userinfo or token, empty-password userinfo with port, leading/trailing whitespace, tab inside the URL: all print `[REDACTED]:DEMO_URL` (`probe_b2_f1.py`, 20 of 24 rows masked; the four LEAK rows are the B2 shapes). Port-only URL and a bare trailing `?` stay readable and carry no secret. |
| F2 | PASS | unchanged since cycle 0 (not touched in 202d2b8c..3e4098c3; cycle-0 evidence stands). |
| F3 | PASS | unchanged; the only `consent.py` touch is none in this range. Docstring fix at `stages/real_acceptance.py:53-55` is accurate (human-granted, then widest, ties keep newest-first). |
| F4 | PASS | unchanged. |
| F5 | PASS | `standing` unchanged. The new `production` parse (`ui/routes_crawl_approval.py:260`) via `TestClient`, `test_probe_b2_ui.py`: `1`, `on`, ` ON `, `On` -> true; `0`, `false`, `off`, `no`, `x`, empty, `true`, `yes`, `01`, `1,0`, `on\x00` -> false. NBSP+`1` -> true (`str.strip()` trims NBSP; harmless, an explicit 1). A production-flagged project stays production when the form sends `0` (`project.production or ...`). The rendered checkbox sends `value='1'` (`routes_crawl_approval.py:47`), so the UI path is unaffected. |
| non-finite wall clock | PASS | `schema/approval.py:85` `allow_inf_nan=False`. Model: `nan`, `inf`, `-inf`, `"nan"`, `"inf"`, `"Infinity"`, `"1e999"` all `ValidationError`; `1e308` and `600000000.0` accepted, `0.0`, `-1.0` unchanged (gate `_shortfalls` treats <=0 as covering nothing). JSON row on disk: literals `NaN`, `Infinity`, `-Infinity`, `1e999`, `null`, `"nan"`, `"inf"` all rejected by `RunApproval.model_validate_json`. A poisoned line in `approvals.jsonl` makes `store.list_approvals()` raise `ValueError: ...approvals.jsonl:2: ...` (fail closed, the good row on line 1 is unusable too; `run_regression` turns it into a coded report through its `except Exception`). UI: `wall_clock_s` = `nan`, `inf`, `-inf`, `NaN`, `Infinity`, `1e999`, `0x10` -> 400 and nothing stored (pre-existing `_bounds` `isfinite`, `routes_crawl_approval.py:213`); `1_0`, ` 45 `, `4.5e1` accepted as 10.0/45.0/45.0, harmless. CLI: `cli_crawl.py:251` `math.isfinite` guard unchanged. No committed `projects/*/approvals.jsonl` contains `NaN`/`Infinity` (grep over worktree and main checkout). |

## Process note
Midway through the session a probe of `RunApproval(wall_clock_s=nan)` briefly ACCEPTED the value while `git status` later showed a clean tree at 3e4098c3: the other checker is evidently revert-testing in the same worktree. I re-ran the whole NaN probe on the clean tree and report only those results. Findings above are from the clean head.

## Commands run
- `uv run python .work/probe_b2_f1.py` (F1 matrix, twice, deterministic)
- `uv run python .work/probe_b2_split.py` (malformed base_url crash)
- `uv run python .work/probe_b2_nan.py` (model, JSON row, poisoned store)
- `uv run pytest .work/test_probe_b2_ui.py -o addopts= -q -s` (production flag, wall clock form; 27 passed, 1 harness-unencodable full-width case)
- `git -C <worktree> status --short` empty before and after

## Not checked here
Full sharded suite (low memory by instruction), manifest flip, merge, push.
