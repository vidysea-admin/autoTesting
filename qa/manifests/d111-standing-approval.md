# Manifest - d111-standing-approval

**Status:** checked-PASS
**Fix cycle:** 1
**Security trigger:** YES - consent gate (D-018 / D-111). **Dual check required (A+B).**
**Issues addressed:** D-111 (Umesh 2026-10-28: "yes it should not expire, i admin will disable it").
**Branch:** `feat/d111-standing-approval` (worktree `D:/autoTesting/.claude/worktrees/d111-standing`, off master 26b2ce58)
**Not done by the maker (by instruction):** no merge, no push, no edit to `qa/contracts/` (the checker amends the CN4 expiry criterion), no edit to `docs/DECISIONS.md` (D-111 is uncommitted in the main checkout; this branch cannot cite it as an entry).

## Criteria derived from D-111 (judge against these)
- **S1** A `RunApproval` for the crawl kind (explore runs under it) may carry `standing=True` and `expires_at=None`; `require_approval` accepts it at any `now`, with no date check.
- **S2** An adversarial approval can NEVER be standing: a standing adversarial row is refused by the gate (`is_expired` is True for any no-expiry row that is not a standing crawl row), and the grant paths (`validate_grant_bounds(None, ..., kind=ADVERSARIAL)`, CLI, UI) refuse to mint one. The same holds for read, live_case, video_review.
- **S3** The signature and content id bind `standing`: flipping `standing` on a signed dated row, dropping it on a standing row, or adding/removing an expiry breaks `is_intact` and/or the HMAC, and the gate refuses. `standing` enters `_bound_payload` ONLY when true, so every existing dated row's id and signature are unchanged and still verify.
- **S4** Everything else D-018 requires is unchanged for a standing row: signed, exact target match, `production: true` for a production target (D-088 `require_project_approval` untouched), per-run `max_actions` / `max_probes` / `wall_clock_s` shortfalls refuse, account-derived rows unaffected.
- **S5** The 30-day `MAX_GRANT_DAYS` ceiling no longer applies to a standing grant but the 2000-action and 24h per-run caps do; a DATED grant is still capped at 30 days. `validate_grant_bounds(expires_at=None)` without an eligible `kind` raises (fail closed when the kind is unstated).
- **S6** A signed `ApprovalRevocation` ends a standing grant (existing mechanism, `autotester revoke`); an unsigned/forged one cannot.
- **S7** CLI: `autotester approve --standing` (crawl only) writes a signed standing row; exactly one of `--expires` / `--standing` is required; `--standing` with another kind or over a cap exits 1 and writes nothing. The consent refusal's printed grant command mentions `--standing` for crawl.
- **S8** UI (credentials page, crawl-approval card): a "Standing, until revoked" checkbox (expiry no longer a hard `required` field; JS disables it while ticked; the server refuses standing + a date, standing + live_case, and a dated grant with no date); the approvals-in-force table shows "Standing, until revoked" plainly and a **Revoke** button (with an optional reason) on every row; `POST /projects/{slug}/crawl-approval/{approval_id}/revoke` is a signed-in-human-only action (no API token, 403), 404 on an id not in force, appends a signed `ApprovalRevocation` (`revoked_by` = the signed-in account), never edits `approvals.jsonl`, and passes the reason through the secret-leak guard.
- **S9** Decline of a waiting signup = disable (unchanged; no code change, per D-111).
- **S10** Unrelated behaviour unchanged: identical standing submits stay idempotent (`_matching_grant`), the dated grant/list/idempotency/production UI tests and all consent, revoke, signing and prod-gate tests pass.

## What changed
- `schema/approval.py`: `expires_at: str | None = None`, new `standing: bool = False`, `STANDING_KINDS = {CRAWL}`, `is_standing` property, `is_expired` returns False for a standing crawl row and True for any other no-expiry row; `_bound_payload` adds `"standing": True` only when set. Module docstring documents it.
- `core/consent.py`: `validate_grant_bounds(..., expires_at: datetime | None, now, *, kind)`; `_reject_reason` gives a specific message for a no-expiry non-standing row; the refusal message (not `_grant_command`) carries a separate `--standing` hint line for crawl (fix cycle 1).
- `cli_crawl.py`: `approve --standing`, `--expires` now optional, new `_grant_expiry`, `_caps_or_refuse(..., kind)`; docstrings condensed to stay at the 300-line / 50-line caps (no behaviour change).
- `ui/routes_crawl_approval.py`: standing checkbox, `_grant_expiry`, `_bounds` (extracted from the submit handler, same checks), `_revoke_form`, table column + `crawl_approval_revoke` route; docstrings condensed for the 300-line cap.
- `auth/policy.py` + `tests/test_ui_auth_policy_table.py`: the new revoke POST needs a policy row (deny by default); it takes the SAME key as the grant, `access.approve`. **This file is not named in D-111's Changes-authorized** (it lists the "UI approval grant/list route and view"); the row is the minimum for the route to exist. Checker: confirm or ask Umesh.
- New tests: `tests/test_standing_approval.py` (17: schema + gate), `tests/test_standing_approval_grant.py` (15: CLI + UI + revoke).

## Judgement calls (checker, please confirm)
- Standing is limited to `ApprovalKind.CRAWL`. D-111 says "crawl and explore"; there is no separate explore kind (explore consent is `covering_approval(kind=CRAWL)`). `live_case` (which the UI can also grant) is NOT standing-eligible; widening is a one-line change to `STANDING_KINDS`.
- Revoke is offered on every in-force grant, dated or standing (revocation only narrows).
- A no-expiry row read from disk that is not a standing crawl row is treated as expired. Before this change a row missing `expires_at` failed model validation on load; now it loads and is refused by the gate.
- `docs/DECISIONS.md` cannot be touched; `autotester doctor` run in this worktree cannot see D-111 as an entry. No doctor rule failed because of that.

## Verify (run in the worktree)
Tests written first. Before the src change, `uv run pytest tests/test_standing_approval_grant.py` (src at master):
```
10 failed, 5 passed   (every CLI --standing / UI standing / Revoke test red; the 5 passes are the "still refused" cases)
```
(`tests/test_standing_approval.py` was authored in the same step but not run red before the schema edit; its 17 tests exercise fields that did not exist on master.)

After:
`uv run pytest tests/test_standing_approval.py tests/test_standing_approval_grant.py` + the existing consent / approval / revoke / signing / prod-gate / approve-cli / explore-consent / credential-run / run-launcher / team-run / parallel-run / ui-crawl-approval / ui-production-approval / ui-runs-live-case-approval / ui-auth-policy-table files (24 files):
```
315 passed, 1 warning in 156.27s
```
`uv run pytest` on the other 22 test files that construct a `RunApproval` or read `expires_at` (adversarial, agent_*, ai_*, authz_gate, ceo_run_evidence, core, crawl_inventory_live, discover, explore_*, grant_bounds_caps, oracle_privilege, parallel_run, real_acceptance, regression_trigger, role_port_authz, ui_crawl_login, ui_origin_guard):
```
10 failed, 510 passed, 14 warnings in 2944.49s (0:49:04)
```
The 10 reds: `test_crawl_inventory_live` (1), `test_real_acceptance` (1) and `test_regression_trigger` (7) are timeouts under CPU contention with other runs: re-run in isolation, `test_crawl_inventory_live.py` is 2 passed and `test_regression_trigger.py` + `test_real_acceptance.py` are 33 passed. The last, `tests/test_core.py::test_env_creation_is_coordinated_across_processes` (env-file lock, `'timeout' must be a non-negative number`), reproduces in isolation and is in the env-lock path, not consent; the maker did not run it against master, so the checker should confirm it is baseline (the signup-requests verdict records the suite reds as baseline/flake). The checker should run the full sharded suite.

`uv run ruff check src tests scripts`:
```
All checks passed!
```
`uv run autotester doctor` (no size, function-length, duplicate, name or root rule fires). The only violations are `decision-citation-dangling`: `qa/verdicts/6c-1028-signup.md` cites D-110 and this manifest cites D-111, and neither entry is committed to master (both sit uncommitted in the main checkout's `docs/DECISIONS.md`). They clear when D-110/D-111 are committed; the maker may not touch DECISIONS.md.

File sizes (all <= 300): `ui/routes_crawl_approval.py` 300, `cli_crawl.py` 296, `core/consent.py` 295, `schema/approval.py` 197, `auth/policy.py` 206. `approve_cmd` is exactly within the 50-line function cap.

## Checker pointers (security trigger, run both A and B)
- Hunt a path where a no-expiry row is honoured that is NOT (standing AND crawl AND expires_at None AND signed AND intact): `RunApproval.is_expired` / `is_standing`, `core/consent.py::_reject_reason`, `ui/routes_crawl_approval.py::_in_force` and `_matching_grant`, `stages/ceo_run_evidence.py::_approval_problems`.
- Try to mint a standing adversarial/live_case row via CLI, UI form tampering (`kind=adversarial`, hidden fields) and a hand-edited `approvals.jsonl`; try to flip a dated row; try to forge an unsigned revocation to hide a grant.
- Check the revoke route cannot be reached by an API token or an unauthenticated/other-project request, and that its policy row matches the grant's key.
- CN4 contract text still says consent is never open-ended: amend it (checker only).

## Fix cycle 1 (source: `.work/6c-1028-batch.md`, 6c RED on integrate/1028, two regressions from this unit)
Both found only by the integration suite; cycle 0 did not run these two files. Tests first.
1. `tests/test_crawl_real_cli.py::test_the_refusals_command_grants_the_run_once_a_human_fills_it_in` (`No such option: --standing,`). Cause: `core/consent.py::_grant_command` appended `" (or --standing, until revoked)"` to the printed pasteable line, so `shlex.split` produced the token `--standing,`. Fix in place: `_grant_command` is back to a pure command; `require_approval`'s `ApprovalRequired` message (`core/consent.py:258-264`) adds a separate line `To keep it valid until revoked, replace --expires <YYYY-MM-DD> with --standing.` only for `kind in STANDING_KINDS`. New test first (red on d20eb037): `tests/test_consent.py::test_the_standing_hint_is_its_own_line_and_the_command_line_stays_pasteable` (no prose or `(` in the command line, no token ending `,`, hint on its own line with `--expires`, no hint for adversarial).
2. `tests/test_cli_advice_resolves.py::test_no_advice_site_can_vanish_unnoticed` (`new: [('cli_crawl.py','revoke')]`). Decision: REGISTER, not reword. `cli_crawl.py:239` (`approve --standing` help, "(autotester revoke)") names a real command an operator is told to run to end a standing grant, which is exactly what the guard freezes; registering also puts it under `test_every_command_the_code_names_is_one_the_cli_exposes` (`revoke --help` resolves), so a rename of `revoke` would now fail. Rewording would only hide an advice site the D-111 feature genuinely adds. Added `("cli_crawl.py", "revoke")` to `EXPECTED_SITES`, `EXPECTED_SITE_COUNT` 31 -> 32, history comment.

Output (worktree, one pytest at a time, `-o addopts=`):
- Before the src fix: new consent test red (1 failed); the two reds from the 6c verdict reproduce by their cause.
- `tests/test_cli_advice_resolves.py tests/test_crawl_real_cli.py tests/test_consent.py`: 84 passed, 1 failed. The 1 failed is `test_the_collector_reports_what_it_could_not_resolve`, baseline AT-1024 (red on master e74664f8 per the 6c verdict, not touched here).
- `tests/test_standing_approval.py tests/test_standing_approval_grant.py tests/test_approve_cli.py tests/test_explore_consent.py tests/test_ui_crawl_approval.py tests/test_cli_release.py`: 62 passed.
- `uv run ruff check src tests scripts`: All checks passed. `core/consent.py` 297 lines.
- `uv run autotester doctor`: no `stale-generated`/`stale-committed` on this branch, so `autotester snapshot` was not run (the 6c SNAPSHOT staleness belongs to the integration branch); remaining violations are the known dangling D-110/D-111 citations.
Checker: re-run the 6c integration after merge.
