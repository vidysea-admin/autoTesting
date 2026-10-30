# Verdict B (adversarial, security) - d110-allow-all

**Cycle checked:** 0
**Verdict:** PASS (3 non-blocking WARNINGs, 1 INFO; no criterion C1-C4 failed)
**Checker:** B (fresh context, read-only toward src/ and tests/; qa/contracts/ untouched)
**Code SHA checked:** 51dbbf80 (branch head 6e6e7810 differs only by one manifest line, `Round cap`; src/tests identical)
**Base:** 19a9dd79

## Token attack on `_allow_all` / `_listed` (src/autotester/ui/helpers.py:196-205)
Probe: set both AUTOTESTER_ALLOWED_HOSTS and _ORIGINS to each token, ask `_allow_all`, `_host_allowed("evil.example")`, `_origin_allowed("https://evil.example")`.
- NOT allow-all (all three False; token stays a literal in `_listed`): `**`, `*.evil.com`, `https://*`, `'*'`, `"*"`, `*:443`, `%2A`, U+FF0A fullwidth asterisk, U+2217, `*;a.com`, U+200B+`*`.
- ARE allow-all (all three True): `*`, ` * `, `* `, `\t*\n`, `*,a.com`, `a.com *`, `a.com,*`.
- `_listed` still drops the bare `*`: `*,a.com` -> `{a.com}`; `https://a.com, *` -> `{https://a.com}`. With ORIGINS=`https://a.com` and no `*`: host a.com True, host b.com False, origin b.com False, origin a.com True (literal list is still exact).
- `*/` is parsed to the literal entry `*` by `_listed` (`rstrip("/")` runs after the `!= "*"` filter, helpers.py:198). It is not allow-all; it would only match a literal `Origin: *` / `Host: *` header. Pre-existing ordering, harmless. (INFO 4)

## ALLOWED_HOSTS=* never lets a cross-site POST through (ASGI `_OriginGuard`, helpers.py:268-283)
Driven through `_OriginGuard` directly, HOSTS=`*`, ORIGINS unset:
- GET with no Host header: 403, app not reached. Two Host headers: 403.
- GET Host `evil.example`: reached (intended, host check off).
- POST Host evil + `Origin: https://evil.example`: 403. POST with `Sec-Fetch-Site: cross-site` and no Origin: 403. (`origin_refusal` unchanged for HOSTS=`*`.)
ORIGINS=`*`: no Host: 403; duplicate Origin: 403 (AT-761 intact); POST Origin evil: reached (intended); POST `Sec-Fetch-Site: cross-site` with no Origin: still 403 (fail-closed, tighter than D-110 prose "passes every cross-site request"; a browser always sends Origin, so no practical effect).

## Startup without `*` still enforces AU20 (auth/config.py:61-80)
`check_startup()` with AUTOTESTER_HOSTED=1, argv `--host 0.0.0.0`:
- no list -> REFUSED "needs ALLOWED_HOSTS or ALLOWED_ORIGINS". HOSTS=`,` -> REFUSED (comma-only is not "set").
- HOSTS=at.example, no PUBLIC_ORIGIN -> REFUSED "PUBLIC_ORIGIN is required". PUBLIC_ORIGIN=http://localhost:8000 -> REFUSED "loopback address". PUBLIC_ORIGIN=https://at.example (admitted) -> STARTS.
- `--host 10.0.0.5`, HOSTS=at.example -> REFUSED own-origin check.
- HOSTS=`**` and `*.evil.com` on the wildcard bind -> REFUSED as "PUBLIC_ORIGIN required" (near-miss tokens do not satisfy the allow-list or skip the PUBLIC_ORIGIN gate).
- HOSTS=`*`, wildcard bind, no PUBLIC_ORIGIN -> STARTS (C3, intended).

## Load-bearing proof (scratch copies under .work/, `git archive HEAD`; each mutant reverts one half; three test files run as 2 + 1)
Baseline: 205 passed + 13 passed.
| Mutant | Result |
|---|---|
| remove `_host_allowed` short-circuit (helpers.py:229-230) | 4 failed: `test_star_in_allowed_origins_opens_both_the_origin_and_the_host_guard`, `test_star_in_allowed_hosts_opens_only_the_host_guard_not_the_origin_guard`, `test_hosts_of_the_allowed_origins_and_the_hosts_variable_are_added_exactly`, `test_au20_...[wild-star-origins-no-public]` |
| remove `_origin_allowed` short-circuit (helpers.py:210) | 3 + 1 failed: `test_the_allowed_origin_is_configurable_for_the_server_url`, `test_star_in_allowed_origins_opens_both_...`, `[wild-star-origins-no-public]`, and `test_au18_a_wildcard_in_the_allowed_origins_is_an_opt_in_allow_all` |
| remove config early return (config.py:74-76) | 6 failed: `[wild-star-origins-no-public]`, `[wild-star-hosts-no-public]`, `test_au20_a_star_allow_all_lets_any_bind_start[0.0.0.0, ::, *, ""]` |
| drop `allow_all` from the "needs" check (config.py:68) | 9 failed (`..._parsed_entry_or_an_allow_all_star[*--True], [-*-True], [ , *...]` plus the 6 above) |
Each half is independently pinned by at least 3 failing tests.

## Findings
1. WARNING - near-miss tokens are not pinned by any test. Mutant `_allow_all` = `"*" in <raw string>` (substring match, so `**`, `*.evil.com`, `https://*`, `*:443` would become allow-all) survives: 205 + 13 passed (helpers.py:201). The shipped code is correct (probe above); only the regression net is missing. Recommend a parametrized test over `**`, `*.evil.com`, `https://*`, `*:443`, `'*'` asserting not allow-all, plus ` * ` / `a.com *` asserting allow-all. Tests are the maker's to add; not a blocker.
2. WARNING - operational trap vs D-110 `Result` text. D-110 tells DevOps to set only `AUTOTESTER_ALLOWED_HOSTS=*`. Startup passes, but a browser's same-site login POST from `http://34.47.136.12:8000` (Origin = the public IP, not listed) returns 403 (probe: HOSTS=*, ORIGINS unset, `Host: 34.47.136.12:8000`, `Origin: http://34.47.136.12:8000` -> 403). The code matches D-110's `What` and the maker's own test says so (tests/test_ui_origin_guard.py, `test_star_in_allowed_hosts_...`: "the login POST needs ALLOWED_ORIGINS=*"). The deploy instruction should be `AUTOTESTER_ALLOWED_ORIGINS=*` (which also opens Host), and the contract amendment AU18-AU20 / `.env.example` should say so. Contract is the checker-A's/amender's file; I did not edit it.
3. WARNING - with `*` set, `AUTOTESTER_PUBLIC_ORIGIN` is never validated: `HOSTS=*` + `PUBLIC_ORIGIN="not an origin"` starts (config.py:74-76 returns before `_check_public_origin`). D-110 says PUBLIC_ORIGIN is no longer required and has no other consumer, so this is as designed; noted so the amendment states that a set value is ignored under `*`.
4. INFO - `*/` parses to literal `*` (see above). D-110 accepted risk (CSRF + Host spoofing under `*`) is opt-in only; default behaviour unchanged (all no-`*` cases above identical to D-066/AU18-AU20).

## Commands run
- `PYTHONPATH=src uv run python -I <scratch>/probe.py` (token matrix) and `probe2.py` (startup matrix + ASGI guard), scratch dir `C:/Users/Lenovo/AppData/Local/Temp/claude/D--autoTesting/dc6b1ba4-60cc-4209-9cdc-762cbc8dd078/scratchpad`.
- mutants: `git archive HEAD src tests scripts pyproject.toml | tar -x -C .work/d110-b-scratch`; string-replace mutation; `PYTHONPATH=src .venv/Scripts/python.exe -m pytest <files> -o addopts= -p no:cacheprovider --tb=no -rf` (no `-q`; at most 2 files per call). Scratch removed afterwards.
- No .env value read or printed; no src/, tests/ or qa/contracts/ edits; no push or merge.
