# Verdict - d111-standing-approval (checker A, criteria, Mode A)
Verdict: PASS
Cycle checked: 0
Head tested: 8e8c76c3 (branch feat/d111-standing-approval, off master 26b2ce58). Security trigger: consent gate; dual check (this is A; B is independent). Judged against D-111 (docs/DECISIONS.md, uncommitted on master) and manifest S1-S10.

## Criteria S1-S10
| # | Result | Evidence |
|---|---|---|
| S1 standing crawl accepted at any now | PASS | schema/approval.py `is_standing` / `is_expired` (standing -> False); test_standing_approval.py::test_standing_crawl_passes_with_no_expiry_however_late (now=2099) green |
| S2 adversarial/other kinds never standing | PASS | `is_standing` requires `run_kind in STANDING_KINDS={CRAWL}`; any other no-expiry row -> `is_expired` True (approval.py, `if self.expires_at is None: return True`); consent.py `_reject_reason` message; `validate_grant_bounds(None, kind=not CRAWL/None)` raises (consent.py:57); tests: standing_adversarial_is_refused, standing_is_for_crawl_only (live_case, read, video_review), grant_bounds_standing_refused_for_other_kinds_and_when_kind_unstated, CLI and UI refusals |
| S3 signature/id bind `standing`; dated rows unchanged | PASS | `_bound_payload` adds `"standing": True` only when true (approval.py); tests: flipping_standing_on_a_signed_dated_row (also the id-repaired variant -> "signature"), dropping_standing_or_adding_an_expiry, dated_row_payload_is_unchanged, row_written_before_standing_existed_loads_as_dated; existing test_approval_signing / test_consent green |
| S4 other D-018 requirements unchanged | PASS | test_standing_still_capped_per_run_and_by_the_production_flag, exact_target, unsigned_standing_is_refused; test_approval_prod_gate*, test_explore_consent, test_approval_residual_callers, test_run_approval_grant_budget green; `require_project_approval` not in the diff |
| S5 30-day ceiling dated only; per-run caps stay; fail closed on unstated kind | PASS | consent.py:57-66; tests grant_bounds_standing_skips_only_the_expiry_ceiling, grant_bounds_dated_still_capped_at_30_days (with and without kind), test_grant_bounds_caps green |
| S6 signed revocation ends standing; forged cannot | PASS | test_signed_revocation_ends_a_standing_grant; existing test_approval_revoke.py::test_unsigned_revocation_is_ignored / test_forged_revocation_is_ignored; `ApprovalRevocation.is_valid` verifies the HMAC; `revoked_ids` counts only valid ones |
| S7 CLI `--standing` | PASS | cli_crawl.py `_grant_expiry` (exactly one of --expires/--standing, exit 1 otherwise), `_caps_or_refuse(..., kind)` runs before the row is built or written; consent.py `_grant_command` mentions --standing for crawl; 5 CLI tests green |
| S8 UI grant, list, Revoke | PASS | routes_crawl_approval.py: `_grant_expiry` (standing+date -> 400), `_checked_kind` limits form kinds to crawl/live_case, `_capped(..., run_kind)` refuses standing live_case; revoke route: `_signer()` + `"authorization" in request.headers` -> 403, id not in `store.list_approvals()` -> 404, reason through `_refuse_unsafe_submission`, signed `ApprovalRevocation` via `add_revocation`, approvals.jsonl never edited; table shows "Standing, until revoked" + Revoke. UI tests green |
| S9 decline = disable | PASS | no code change in the diff (src files touched: approval.py, consent.py, cli_crawl.py, routes_crawl_approval.py, policy.py) |
| S10 unrelated behaviour unchanged | PASS | `_matching_grant` compares `_bound_payload()` (which includes standing and expires_at), so standing never dedups against a dated row and identical standing submits stay idempotent (test_ui_identical_standing_submit_is_still_idempotent); all listed existing files green |

## Adversarial probes (read from code and tests)
- Hand-edited approvals.jsonl, standing adversarial/live_case/read row: unsigned or id/signature mismatch -> refused; even a validly signed one reads as expired.
- standing=True with a date on a crawl row: treated as an ordinary dated row (honoured to its date only). Not an escalation.
- UI form tampering: kind=adversarial/read -> 400 "kind must be crawl or live_case"; standing + live_case -> 400.
- Revoke by API token -> 403; foreign-project id -> 404 (store is per project); an unsigned revocation cannot hide a grant.
- Other readers of `expires_at`: `stages/ceo_run_evidence.py::_approval_problems` uses `is_expired` (standing-aware). No other src/scripts reader dereferences a possibly-None `expires_at` (grep: only cli_crawl, consent, approval, routes_crawl_approval; auth/* session expiry is unrelated; scripts only construct dated rows).

## Commands run (worktree D:/autoTesting/.claude/worktrees/d111-standing, head 8e8c76c3)
- `uv run pytest` on 20 consent/approval/UI files (standing x2, consent, prod_gate x2, residual_callers, revoke, signing, approve_cli, explore_consent, grant_bounds_caps, run_approval_grant_budget, ui_crawl_approval x2, ui_production_approval, ui_runs_live_case_approval, ui_auth_policy_table, check_crawl_approval, ceo_run_evidence, parallel_run_approval): 270 passed.
- `uv run pytest` on the other RunApproval-building files in three groups. Group 1 (adversarial, agent_fallback, agent_tools, ai_capture, ai_persist, authz_gate, cli_video_review, core): 203 passed. Group 2 (discover, explore_live, explore_login_spa_live, explore_modal, explore_typing, oracle_privilege, parallel_run, role_port_authz): 135 passed. Group 3 (ui_auth_cli_and_limits, ui_auth_login, ui_crawl_login, ui_origin_guard, crawl_inventory_live, real_acceptance, regression_trigger): 197 passed, 1 failed (see baseline).
- `uv run ruff check src tests scripts`: All checks passed.
- `uv run autotester doctor`: 11 violations, ALL `decision-citation-dangling` (D-111 x10 in the manifest, D-110 in qa/verdicts/6c-1028-signup.md); expected, entries uncommitted on master. No size / function-length / duplicate / name rule fires. This verdict and the CN4 amendment also cite D-111 and so add to the same dangling class until D-111 is committed.

## Baseline reds
- tests/test_crawl_inventory_live.py::test_a_logged_in_crawl_maps_every_route_and_names_the_one_it_refused: red on the branch (isolated, 8m15s) AND on a detached checkout of master 26b2ce58 (isolated, 7m19s): `CrawlStatus.STOPPED_BOUND` vs COMPLETED (wall_clock bound hit, machine loaded). Baseline/load flake, not the diff. (The maker reported it green in isolation; here it is red on both sides.)
- tests/test_core.py::test_env_creation_is_coordinated_across_processes: red alone on master 26b2ce58 (`_queue.Empty` in the cross-process env-lock test, 25 s); passed in group 1 on the branch (203 passed). Intermittent, env-lock path, the diff touches nothing there. Baseline, not caused by this unit.
- The full sharded 6c suite was not run by this checker (task scope: touched tests + every RunApproval-building file); it remains the pre-push step.

## Scope question: auth/policy.py + tests/test_ui_auth_policy_table.py (not named in D-111 Changes-authorized)
Judged necessary, not creep. `ROUTE_POLICY` is default-deny (policy.py header: a route not in it matches nothing and is refused), so the new `POST /projects/{slug}/crawl-approval/{approval_id}/revoke` is unreachable without a row. The row reuses the existing key `access.approve` (the same as the grant at the adjacent line), adds no new key, and the test-table change pins exactly that. D-111 authorises "the UI approval grant/list route and view"; a route cannot exist without its policy row. policy.py is not a Lab enforcement path (those are `.claude/hooks/*`, `append_decision.ps1`, `.claude/settings.json`, `qa/hooks/*`). Residual: Umesh may want a one-line note on the D-111 record; not a blocker.

## Findings (non-blocking)
1. Revoke 404 is "not in `store.list_approvals()`" (unrevoked, any kind, any expiry), so an expired or live_case row can also be revoked. Harmless (revocation only narrows); the manifest already states this.
2. No test pins that the revoke route is refused for a signed-in user WITHOUT `access.approve`; that rests on the policy table test pinning the key plus the existing gate tests. Acceptable; a follow-up test would be cheap.
3. The manifest notes tests/test_standing_approval.py was not run red before the schema edit. This checker did not revert-test every criterion (C7); the schema-level tests exercise fields that did not exist on master, so they cannot pass against it.

## Contract change (checker-owned, same commit)
qa/contracts/consent.md CN4 amended: "Consent is never open-ended, except a signed STANDING crawl grant (D-111)": standing crawl only, valid until a signed revocation, all other bounds retained, adversarial and every other kind keep a required date, dated cap stays 30 days, verify list, plus a 2026-10-28 maintenance-log line (owner-authorized; weakens the old wording for crawl only, by explicit decision).

## Not done by design
Manifest status not flipped (the maker does that after both verdicts); no merge, no push.
