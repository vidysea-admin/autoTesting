# Manifest - consent-followups

**Status:** ready-for-check
**Fix cycle:** 2
**Security trigger:** YES - consent gate (D-018 / D-111) and the credential redactor path (C5). **Dual check recommended (A+B).**
**Issues addressed:** `.work/inbox-1028.md` lines 1-7 (hint shows `[REDACTED]:KEY`; probe estimate under-counts; first-match approval binding) and D-111 checker-B N1 / N2.
**Branch:** `fix/consent-followups` (worktree `D:/autoTesting/.claude/worktrees/consent-followups`, off `feat/d111-standing-approval` d20eb037)
**Not done by the maker (by instruction):** no merge, no push, no edit to `qa/contracts/`, no edit to `docs/DECISIONS.md`, nothing touched in the main checkout.

## Criteria (judge against these)
- **F1** The approval-refusal "Grant one with:" hint printed by `autotester run <slug>` shows the project's declared `base_url` verbatim (`--target "https://..."`), also when that URL equals a `.env` value such as a `*_LOGIN_URL`. Every other `.env` value (a real secret) is still masked in the same message, and the whole rest of the report is scrubbed exactly as before.
- **F2** The `--max-probes` in a LIVE_CASE hint is `max(probe floor, actions x PROBES_PER_ACTION)` capped at `MAX_GRANT_PROBES`, where `actions` is the planned cases' step total. The GATE is unchanged: it still demands only the floor (`execute.probe_request`), so no existing grant becomes invalid. Other kinds (adversarial, crawl) print their probes exactly as before.
- **F3** When several unexpired, intact, signed approvals cover a run, `require_approval` returns a human-granted row over an account-derived one, then the widest (wall clock, then probes, then actions); a tie keeps the earlier row; a row that does not cover the run is never chosen; with none covering, the refusal is unchanged.
- **F4** `autotester approve` stamps `granted_at` with a full UTC timestamp, so a same-day re-grant after a revoke is a new row with a new id that the gate honours (before: identical date + fields = the revoked id, CLI green, gate refusing).
- **F5** The UI `standing` form field is on only for an explicit `1` or `on` (case-insensitive, trimmed). Any other non-empty value (`0`, `false`, `yes`, `true`, `x`, a space) is NOT standing, so the grant falls to the dated path and is refused without an expiry.

## What changed (file:line on the branch head)
- `src/autotester/core/consent.py` `_grant_command` (~:141-160): `--max-probes` is `min(max(probes, actions*PROBES_PER_ACTION), MAX_GRANT_PROBES)` for `ApprovalKind.LIVE_CASE`; docstring condensed. New `_width` (~:214) and `require_approval` (~:221-): collects every covering row and returns `max(covering, key=_width)`; the `same`/`candidates`/`rejections` lists share one filter. File is exactly 300 lines, `require_approval` 50 lines.
- `src/autotester/stages/report_export.py` `_load_redactor(store, keep=frozenset())`: passes `keep` to `SecretStore.redactor(exclude=...)` (existing parameter). Default unchanged, so every other caller is identical. File stays at 300 lines.
- `src/autotester/stages/run_service.py` `_report`: after the normal full scrub, the `message` field alone is re-scrubbed with `keep={project.base_url}`. The project's base_url is already plain in `project.json`; the other secrets are still masked in the message and everything else in the report keeps the strict redactor.
- `src/autotester/cli_crawl.py:10,271`: `granted_at=datetime.now(UTC).isoformat()` (was `date.today().isoformat()`).
- `src/autotester/ui/routes_crawl_approval.py` (`crawl_approval_submit`, `_grant_expiry`): `on = standing.strip().lower() in ("1", "on")` drives both `_grant_expiry(on, ...)` and `standing=on`; `_grant_expiry` takes a bool. File stays at 300 lines.
- New `tests/test_consent_followups.py` (20 tests, one section per criterion F1-F5).

## Judgement calls (checker, please confirm)
- F1 is fixed where the redaction happens (`run_service._report`), not in `consent.py`: the hint string there already carries the real target; the mask is applied afterwards. The UI path strips the hint (`routes_crawls.py:46`) and is untouched.
- F1 keeps ONLY the project's own stored `base_url` readable, not `PUBLIC_ENV_KEYS`: `PATHLYNKS_COUNSELLOR_LOGIN_URL` is not in that list, so reusing `public_values()` would not have fixed the live case. The widening of the credential boundary is one exact string already stored in plaintext.
- F2 sizes the hint with the D-068 brake (20 probes per action) rather than a worst-case polling ceiling (~33 per step), which would hint thousands of probes; a run that polls past 20/action is failing its expectations anyway. The gate floor is deliberately NOT raised: that would refuse existing grants (e.g. the 400-probe row) at preflight.
- F3 prefers a human row over a wider account-derived row, preserving `explore_consent._credential_approval`'s human-first order.
- F4 uses the timestamp only. The CLI does not additionally probe the revocation file: with a microsecond timestamp the id collision cannot recur.
- F5: `standing` is the only field changed; `production` still uses `bool(production)` (not in scope).

## Verify (run in the worktree, one pytest at a time, `-o addopts=`)
Tests first. Before any src change:
```
uv run pytest tests/test_consent_followups.py -o addopts= -q
14 failed, 6 passed   (F1 x1, F2 x2, F3 x2, F4 x1, F5 x8 red; the 6 passes are "still masked", "still refused", "gate still checks the floor", "explicit 1/on" cases)
```
After:
```
uv run pytest tests/test_consent_followups.py -o addopts= -q
20 passed, 1 warning in 2.35s
uv run pytest tests/test_consent_followups.py tests/test_consent.py tests/test_standing_approval_grant.py tests/test_standing_approval.py tests/test_probe_floor_matches_runtime.py -o addopts= -q
105 passed, 1 warning in 10.65s
uv run pytest tests/test_consent.py tests/test_standing_approval.py tests/test_standing_approval_grant.py tests/test_approve_cli.py tests/test_approve_cli_bounds.py tests/test_approve_target_match.py tests/test_approval_revoke.py tests/test_approval_signing.py tests/test_approval_prod_gate.py tests/test_approval_prod_gate_paths.py tests/test_approval_residual_callers.py tests/test_probe_floor_matches_runtime.py tests/test_run_approval_grant_budget.py tests/test_run_launcher_approval.py tests/test_run_launcher_priorities_approval.py tests/test_ui_crawl_approval.py tests/test_ui_crawl_approval_list.py tests/test_ui_production_approval.py tests/test_ui_runs_live_case_approval.py tests/test_explore_consent.py tests/test_credential_run_approval.py tests/test_parallel_run_approval.py tests/test_team_run_approval.py tests/test_check_crawl_approval.py tests/test_report_export_secrets.py -o addopts= -q
337 passed, 1 warning in 443.89s
uv run pytest tests/test_consent_followups.py tests/test_consent.py tests/test_standing_approval_grant.py tests/test_probe_floor_matches_runtime.py tests/test_cli_mcp.py tests/test_report_export.py tests/test_approve_cli.py -o addopts= -q
138 passed, 1 warning in 25.07s
uv run ruff check src tests scripts   ->  All checks passed!
uv run autotester doctor              ->  26 violation(s), all `decision-citation-dangling` for D-110/D-111, which are not yet entries in this tree (2 are this manifest's own lines 5-6; no code rule fails; a transient `function-too-long: require_approval 51 lines` was fixed before the commit)
```
The full suite was NOT run (machine low on memory, by instruction); the checker should run its own sharded sweep.

## Fix cycle 1 (checker B FAIL cycle 0: B1; checker A PASS)
Tests first (`tests/test_consent_followups.py`, now 37 tests); before any src change:
```
uv run pytest tests/test_consent_followups.py -o addopts= -q
12 failed, 25 passed   (B1 x4, production flag x5, non-finite wall clock x3)
```
After the fixes:
```
uv run pytest tests/test_consent_followups.py -o addopts= -q
37 passed, 1 warning
uv run pytest tests/test_consent_followups.py tests/test_consent.py tests/test_ui_production_approval.py tests/test_ui_crawl_approval.py tests/test_ui_crawl_approval_list.py tests/test_approval_signing.py tests/test_approval_prod_gate.py tests/test_report_export_secrets.py tests/test_cli_mcp.py tests/test_approve_cli.py tests/test_approve_cli_bounds.py tests/test_standing_approval_grant.py tests/test_real_acceptance.py -o addopts= -q
207 passed, 1 warning in 73.47s
uv run ruff check src tests scripts  ->  All checks passed!
uv run autotester doctor  ->  only decision-citation-* findings (the added dangling ones are the two verdict files and this section citing D-111/D-110); no code rule fails
```
- **B1 (F1)** `stages/run_service.py` new `_pasteable(url)` and `_report`: the base_url is exempted from the message scrub only when it has no userinfo (`@` in netloc), no query, no fragment, and `scrub_url_credentials(url) == url`; otherwise the exemption set is empty and the `.env` match masks it (`[REDACTED]:KEY`). Tests: `?token=`, `user:pass@`, `#access_token=`, and `?next=` base_urls, each also a `.env` value, stay masked; the clean-URL test (`..._survives_the_report_scrub_...`) still passes.
- **Stale docstring** `stages/real_acceptance.py` `_newest_first` now states that `require_approval` returns the human-granted, then widest covering row and that newest-first only decides ties.
- **production flag** `ui/routes_crawl_approval.py` `crawl_approval_submit`: `production=project.production or production.strip().lower() in ("1", "on")`. Test: `1`/`on`/` ON ` true; `0`, `false`, `off`, `no`, `x`, empty false. File stays at 300 lines.
- **Non-finite bound** `schema/approval.py` `RunApproval.wall_clock_s` has `allow_inf_nan=False`: NaN/inf/-inf raise at validation. `max_actions`/`max_probes` are ints (cannot be non-finite). Ids/signatures of finite rows unchanged (`_bound_payload` untouched; test with the live 600000000.0 value). Consequence: a stored row with a non-finite wall clock now fails to load (fail closed, `read_jsonl` raises with the line number); `model_dump_json` writes NaN as null, which already failed validation, so no new on-disk breakage.

## Fix cycle 2 (both cycle-1 checkers FAIL on B2: path-embedded credential printed; malformed base_url crashes `_report`)
Design is a positive allowlist, not a denylist. `src/autotester/stages/run_service.py` `_pasteable` (+ `_PLAIN_HOST`, `_PLAIN_SEGMENT`): the base_url is exempted from the message scrub ONLY if ALL hold: `urlsplit` succeeds (ValueError -> no exemption); scheme is http or https; pure ASCII, every char in `!`..`~` (no whitespace/control); no `;`, `?` or `#` anywhere; netloc is a plain `host[:port]` (no userinfo, no `%`, no brackets); path is empty, `/`, or every segment matches `[a-z-]{1,32}` (a single trailing `/` allowed). Else the exemption is empty and the `.env` match masks it as before this unit. `scrub_url_credentials` import removed (the allowlist subsumes it).
Tests first (`tests/test_consent_followups.py`, now 78 tests; path tokens `/magic/AbC123SecretTok`, `/t/SEGsecret9XYZ/login`, `/login/bob:PATHsecret9%40x`, non-URL string, `http://[::1/login`, `http://[bad`, non-ASCII and whitespace URLs, over-long segment, empty netloc; existing query/userinfo/fragment cases kept; `https://pathlynks-like.test/signin`, bare host, `/`, `host:port/sign-in/` stay readable):
```
uv run pytest tests/test_consent_followups.py -o addopts= -q   (before src change)
34 failed, 47 passed
uv run pytest tests/test_consent_followups.py -o addopts= -q   (after)
78 passed, 1 warning
uv run pytest tests/test_cli_mcp.py tests/test_report_export_secrets.py tests/test_consent.py -o addopts= -q
67 passed, 1 warning
uv run ruff check src tests  ->  All checks passed!
uv run autotester doctor     ->  no file-too-long / function-too-long (test file 296 lines, run_service.py 153); only decision-citation-* findings
```
Full suite NOT run (machine low on memory, by instruction).
