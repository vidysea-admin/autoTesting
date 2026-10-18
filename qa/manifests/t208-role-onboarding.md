# Manifest - t208-role-onboarding (T-208, G11-2)

**Status:** ready-for-check
**Fix cycle:** 0
**Contract:** qa/contracts/multi-role-platform.md (MP4, MP5, MP6; invariants MPI1-MPI6 held)
**Goal task:** T-208
**Authority:** D-104 (Approved-by: Umesh 2026-10-17: build G11 now)
**Dual check:** required
dual-trigger: auth src/autotester/ui/routes_role_accounts.py:115
dual-trigger: security src/autotester/stages/role_onboarding.py:104
**Persona walk:** done as `onboarder`, headed browser: qa/evidence/browser-t208-role-onboarding-2026-10-18/report.json (8 accounts across 3 platforms; 2 console errors, both the deliberate 400 refusals; 0 unexpected)
**Issues addressed:** none
**Executor:** claude-sonnet-subagent
**Base SHA:** 722bf3df (worktree .worktrees/t208-role-onboarding, branch wave/t208-role-onboarding)
**Code SHA:** 83c4c161

## Criteria (quoted verbatim from the contract)
- **MP4 — N accounts across M platforms at new-project time.** The new-project flow accepts at least 8 role accounts across 3 platforms in one submission, stores keys in the repo-root `.env` through the existing env editor, and the saved project lists every account with role, platform and tenant label. Verify: route test with 8x3 fixture; live persona walk as `onboarder` (a walk of AutoTester's own form, which needs no product credential, so it is not gated). serves: intent#O17 · closes T-208
- **MP5 — Scope refusal names the reason.** A role account whose SecretRef domain scope admits a host outside its own platform (including the subdomain suffix-match case) is refused with a message naming the account, the platform and the wider host. Verify: two fixtures, sibling subdomains with `include_subdomains` true and false. serves: intent#O17, intent#O7 · closes T-208
- **MP6 — Identity and permission (ruled by the checker, see below).** The form and its POST require a signed-in member. No new permission key is added. The permission is the one the existing route that does the same write already requires: (a) creating a new project with accounts = `project.create`, exactly as `POST /onboard` today (`ui/app.py:150-190`, `auth/policy.py:74`), the creator becomes owner; (b) adding or changing accounts on an existing project = `project.edit` on that project for the declarations in `project.json` AND `credentials.edit` on that project for any value written to the repo-root `.env` (auth.md AU21: "writing a new value needs `credentials.edit` on that project"); a submission that carries no value needs `project.edit` only. Verify: anonymous and no-group requests get the existing refusal; a fixture group holding `project.edit` without `credentials.edit` can declare keys but a POST carrying a value is refused 403 and writes nothing to `.env`; `credentials.edit` without `project.edit` is refused; a Tester is refused. Mutation: drop the `credentials.edit` check on the value write, the project-edit-only fixture goes red. serves: intent#O17 · closes T-208

## What changed
- `src/autotester/stages/role_onboarding.py` (new, 167 lines): pure validation. `check_platforms`, `check_scopes` (the MP5 refusal, :104), `validate_accounts` (returns the `SecretRef` list), `check_key_namespace` (wraps `refuse_foreign_key`), `check_values`, `write_values` (validates the whole batch, then `ui/env_editor.set_env_values`), `merge_by_id`, `safe_validation_message` (never echoes a value).
- `src/autotester/ui/routes_role_accounts.py` (new, 254): `GET/POST /onboard/roles` (new project; creator becomes owner) and `GET/POST /projects/{slug}/accounts` (existing project). `_require_credentials_edit` (:115) runs BEFORE any write, project.json included, whenever the submission carries a value.
- `src/autotester/ui/role_accounts_view.py` (new, 127): rendering only; every value input is empty and write-only; everything escaped; add-row buttons.
- `src/autotester/auth/policy.py` (edited, 200): `("GET"|"POST", "/onboard/roles")` -> `project.create` (:75); `/accounts` added to the GET view list and the POST edit list (:95, :108). No new permission key.
- `src/autotester/ui/routers.py`, `ui/project_view.py` (one button), `ui/app.py` (one link on /onboard), `tests/test_ui_auth_policy_table.py` (pins the new rows): small edits outside the OG-ONBOARD list, needed to reach the form and to keep the default-deny policy table honest.
- `tests/test_role_onboarding.py` (new, 12 tests) and `tests/test_role_accounts_routes.py` (new, 20 tests).
- No T-207 schema file edited. CORE-REQUEST: none.

## Judgement calls for the checker
1. NOTE-FOR-CHECKER, contract vs runtime: MP5 and CLAUDE.md describe `browser/secrets.py::_host_matches` as a suffix match; since AT-651 / D-087 the runtime match is EXACT. The stage implements the DECLARED-scope contract (suffix when `include_subdomains` true, exact when false), so the refusal fires for the suffix case as the contract asks. The stricter runtime is defence in depth, not relied on. The two MP5 fixtures are `test_mp5_suffix_scope_admitting_a_sibling_platform_is_refused_by_name` (include_subdomains true) and `test_mp5_exact_scope_beside_a_sibling_platform_is_accepted` (false).
2. The "wider host" is computed from the other platforms' hosts plus any typed scope domain outside the account's own platform. A scope typed narrower than the platform is accepted.
3. Atomicity: for an existing project the `credentials.edit` check precedes any save; for a new project everything is validated before `save_project` and before the `.env` write, so a refusal writes nothing anywhere.
4. A new project refuses a key already present in `.env` (collision); an existing project may re-declare its own keys. Keys outside the project's namespace are refused (`refuse_foreign_key`).
5. Edit merges by id and keeps untouched accounts' stored scope; row limits 16 platforms / 128 accounts.
6. Review agent not dispatched: the Agent tool's compact-handoff hook binds to the main-checkout cwd and the unit must stay inside its worktree; I did not work around it. The checker is the independent review.
7. Browser smoke was done inline (headed browser, no sub-agent) for the same reason; a full-page screenshot hung once and was redone with viewport screenshots.
8. `autotester doctor` reports 2 violations, both `stale-generated` (docs/MAP.md, docs/SNAPSHOT.md); left to the merge-queue regeneration.
9. No full suite was run (builder); `pytest --collect-only` collects 8043 tests with no error.

## Verification scope
Policy-Version: proportional-verification/2026-10-18.15
Tier: L (auth permission check plus a security scope refusal plus a `.env` data write)
Round: 10 files (7 src/policy, 3 test), 3 criteria (+ MPI1-MPI6 held), est 40 min, dual check (auth + security)
Owners: OG-ONBOARD
Base / checked state: 722bf3df / 83c4c161, clean tracked tree
Gate answers: qa/gates/write-policy-tier.md is untouched; no gate blocks a unit that only declares keys and writes values the member's own permission allows.
Affected tests / full-suite trigger: builder ran the behaviour-scoped affected set (policy table, env editor, credential guard, project routes, onboarding, schema): 357 passed. Whether a full suite is an integration obligation is the checker's `shard_suite.py` call; the builder ran none.
Tests[MP4]: tests/test_role_accounts_routes.py::test_mp4_n_accounts_across_three_platforms_in_one_submission, ::test_mp4_the_saved_project_lists_every_account_with_role_platform_tenant, ::test_mp4_the_form_renders_rows_for_three_platforms_and_eight_accounts, ::test_mp4_a_half_filled_row_is_refused_and_nothing_is_written - 8x3 and 24-account fixtures, keys in `.env`, listing shows role, platform, tenant label.
Tests[MP5]: tests/test_role_onboarding.py::test_mp5_suffix_scope_admitting_a_sibling_platform_is_refused_by_name, ::test_mp5_exact_scope_beside_a_sibling_platform_is_accepted, ::test_mp5_typed_scope_outside_the_platform_is_refused_naming_the_host, ::test_mp5_typed_scope_inside_the_platform_narrows_the_default; tests/test_role_accounts_routes.py::test_mp5_a_typed_scope_admitting_a_sibling_platform_is_refused_over_http, ::test_mp5_the_same_scope_with_exact_hosts_is_accepted - both include_subdomains fixtures, message names account, platform and host.
Tests[MP6]: tests/test_role_accounts_routes.py::test_mp6_anonymous_and_no_group_requests_get_the_existing_refusal, ::test_mp6_a_tester_cannot_create_or_edit, ::test_mp6_a_developer_creating_a_project_with_values_becomes_its_owner, ::test_mp6_project_edit_alone_declares_keys_but_cannot_write_a_value, ::test_mp6_credentials_edit_alone_is_refused, ::test_mp6_both_permissions_write_the_value, ::test_the_form_page_is_reachable_for_a_member_with_view_only - anonymous, no-group, Tester, project.edit alone (403, `.env` unchanged), credentials.edit alone, both.
Falsification[MP4]: copy-mutant outside the worktree (scratchpad/t208-role-onboarding, the `.env` write in the new-project path removed): red on 2 MP4 tests (2 failed); restored tree green.
Falsification[MP5]: copy-mutant (`if outside | sibling:` -> `if False:`): red on 2 MP5 tests (2 failed); restored tree green.
Falsification[MP6]: copy-mutant (drop the `_require_credentials_edit` call before the value write): red `test_mp6_project_edit_alone_declares_keys_but_cannot_write_a_value` (1 failed); restored tree green.
Pre-check[MP4]: 83c4c161 uv run --directory <worktree> pytest tests/test_role_onboarding.py tests/test_role_accounts_routes.py -k "mp4" -> 5 passed t=9 blobs=tests/test_role_onboarding.py:9b77662,tests/test_role_accounts_routes.py:a92e2c5
Pre-check[MP5]: 83c4c161 uv run --directory <worktree> pytest tests/test_role_onboarding.py tests/test_role_accounts_routes.py -k "mp5" -> 6 passed t=4 blobs=tests/test_role_onboarding.py:9b77662,tests/test_role_accounts_routes.py:a92e2c5
Pre-check[MP6]: 83c4c161 uv run --directory <worktree> pytest tests/test_role_onboarding.py tests/test_role_accounts_routes.py -k "mp6 or view_only or namespace or already_used" -> 9 passed t=8 blobs=tests/test_role_onboarding.py:9b77662,tests/test_role_accounts_routes.py:a92e2c5
Lint: 83c4c161 `uv run ruff check src tests scripts` -> All checks passed; `uv run autotester doctor` -> 2 violations, both stale-generated (docs/MAP.md, docs/SNAPSHOT.md), see judgement call 8.
Metrics: start=2026-10-18T10:00:00Z end=2026-10-18T18:15:00Z wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=1 mutations=3 cycle=0 resumes=3 tokens=unavailable policy=proportional-verification/2026-10-18.15 lane=normal check_s=unavailable mutants=3 defects_unit=0 defects_6c=0 tests=32 tests_min=1
