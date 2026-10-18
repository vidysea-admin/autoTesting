# Manifest - t214-network (T-214, G11-5)

**Status:** checked-PASS (qa/verdicts/t214-network.md 751bd035)
**Fix cycle:** 0
**Contract:** qa/contracts/multi-role-platform.md (MP21, MP22; invariants MPI1, MPI2, MPI3 held)
**Goal task:** T-214
**Authority:** D-104 (Approved-by: Umesh 2026-10-17: build G11 now; Umesh 2026-10-18: "build all remaining features")
**Dual check:** no (no auth, tenancy, data-write or prod trigger: the oracles read an in-memory network log and return findings; they send nothing, store nothing and hold no credential)
**Persona walk:** skip (no UI surface in this unit)
**Issues addressed:** none
**Executor:** claude-sonnet-subagent
**Base SHA:** cff3ffe6 (worktree .worktrees/t214-network, branch wave/t214-network; the T-211 cross-role runner head, stacked on T-209 36a87037 and T-207)
**Code SHA:** d756b351

## Criteria (quoted verbatim from qa/contracts/multi-role-platform.md:66-67)
- **MP21 - Hidden API error.** A first-party 4xx/5xx response during a step whose UI shows success becomes a finding citing the request (redacted URL, status) and the success screen. Verify: fixture returning 500 behind a success toast. serves: intent#O20, intent#O3 - closes T-214
- **MP22 - Request and polling budget.** Requests per screen and the minimum polling interval are measured from `network_capture`; exceeding the project's declared budget is a finding with the measured numbers. Verify: fixture polling every 200 ms against a 1 s budget. serves: intent#O20 - closes T-214
- **MPI1 - Leak evidence stores no third-party personal data.** (held: findings carry a placeholder URL template only, never the captured URL; the secret in a URL is `[REDACTED]` before an oracle sees it; neither oracle imports a provider.)
- **MPI2 - Fixtures stay blind.** (held: the fixtures are scripted response lists in a status/interval matrix; none reproduces a benchmark finding.)
- **MPI3 - One enums file, one editor.** `schema/multi_role_enums.py` is not in `git diff --name-only cff3ffe6..d756b351` (it already holds `FindingClass.HIDDEN_API_ERROR`, `FindingClass.REQUEST_BUDGET`, `OracleName.API_ERROR`, `OracleName.REQUEST_BUDGET`).

## What changed
- `src/autotester/schema/request_budget.py` (new, 103 lines): `RequestBudget` (`max_requests_per_screen`, `min_poll_interval_s`, `min_repeats_for_polling` default 3), `NetworkSample` (method, already-redacted URL, status 100-599, `t_s`), `StepNetworkLog` (step, role, platform, screen URL, replayable repro steps, `success_indicator` or None, samples; personal-shaped text refused), the optional `NetworkLogPort` Protocol (`network_log()`, `request_budget()`), `NetworkLogUnavailable` and `network_log_from(context)`.
- `src/autotester/stages/oracle_request_budget.py` (new, 155): `capture_samples` (raw `(method, url, status, t_s)` -> `NetworkSample`s by calling `network_capture.first_party_evidence`, so the one first-party filter and `Redactor.scrub` apply), `safe_template` (reuses `stages/leak_evidence.templatise_url`, falls back to `/{path}` rather than ever emitting a raw URL), `budget_findings`, `check_request_budget`, `run`.
- `src/autotester/stages/oracle_api_error.py` (new, 62): `hidden_api_errors`, `check_api_errors`, `run`.
- Test files: `tests/test_network_oracles.py` (47 cases incl. parametrised matrices) and the helper module `tests/network_oracle_fakes.py` (`log_for` runs the real `capture_samples`; `FakeNetworkPort`, `PlainPort`).
- No T-207/T-209/T-211 file, `schema/multi_role_enums.py`, `schema/enums.py`, `schema/project.py`, `browser/session.py`, `stages/oracle_registry.py` or `stages/network_capture.py` touched (`git diff --name-only cff3ffe6..d756b351` lists only the 5 files above).

## Judgement calls for the checker
1. **Where the network data comes from.** `OracleContext` (T-211, not mine to edit) carries only the `RoleSessionPort`, and that Protocol has no network method. So the oracles read an OPTIONAL second seam, `NetworkLogPort`, off `context.port`. CORE-REQUEST: when T-210's `multi_role_session` is wired to the runner, its port should implement `network_log()` / `request_budget()` (feed `network_log` from `capture_samples`); no change to `oracle_context.py` is needed.
2. **A port without the seam is `errored`, not clean.** `network_log_from` raises `NetworkLogUnavailable`; the registry records `errored` with the type name only. An oracle that silently returned `[]` would look like "looked and found nothing" (MP15 spirit).
3. **Where the "declared budget" lives.** `Project` has no budget field and `schema/project.py` is T-207's; the budget is `NetworkLogPort.request_budget()` (a project-level source is wiring for the runner). No budget declared = nothing to exceed = no MP22 finding. CORE-REQUEST: a `request_budget` field on `Project` (T-207 owner) when the declaration should live in project.json.
4. **"Polling" is defined by a declared repeat count.** The same method + endpoint template requested `min_repeats_for_polling` (default 3, minimum 2) or more times on one screen is polling; its smallest gap (rounded to ms) under `min_poll_interval_s` is the finding. A gap exactly equal to the budget passes. Two requests 100 ms apart are not polling at the default. Ids in the path are templated, so `/items/1001`, `/items/1002` are one endpoint.
5. **"Per screen" = a role's visits to one screen template.** Requests are summed per (role, platform, templated screen URL) across steps; different roles or screens never add up. Over means strictly more than `max_requests_per_screen`.
6. **What "UI shows success" means.** The log's `success_indicator` (the selector/label of the success element the port saw) being set; the oracle makes no judgement of its own. Status range is the contract's literal 400-599; 3xx and 399 are not errors. Identical failing requests (method + template + status) are one finding with `count` = repeats.
7. **The finding cites the template, not the URL.** MP21 says "redacted URL"; MPI1 (leak evidence stores no third-party data) and `MultiRoleFinding.url_template` require a placeholder template, so the finding carries `templatise_url` output (ids -> `{id}`, query values -> `{value}`) and the status, success indicator and screen template in the title. The `[REDACTED]` scrub of known secrets already happened in `capture_samples`.
8. **`run` is an alias.** `autotester doctor`'s duplicate-concept rule flags any top-level `def run` against `doctor.run`, and the oracle interface (`schema/oracle_context.py` "HOW TO WRITE AN ORACLE") requires the name `run`. Each module defines a uniquely named function (`check_api_errors`, `check_request_budget`) and sets `run = <it>`. CORE-REQUEST: exempt oracle `run` in `doctor.check_duplicate_definitions` (all 13 oracle units will hit it); until then the alias is the workaround, not a hidden second definition.
9. **More than one model per schema file.** OG-NET names one schema file; the budget, sample and log shapes are one concept (the oracles' input) and share it, as `oracle_context.py` does.
10. No local HTTP fixture app or browser: the fixtures are scripted response lists run through the real `capture_samples`/`network_capture` path. A live browser seam arrives with T-210's session; it is not merged here.
11. `autotester doctor` reports 2 violations, both stale-generated (docs/MAP.md, docs/SNAPSHOT.md); not hand-edited, the merge-queue owner regenerates.

## Verification scope
Policy-Version: proportional-verification/2026-10-18.15
Tier: M
Round: 3 src files + 2 test files, 2 criteria (+MPI1, MPI3), est 35 min
Owners: OG-NET
slow-plan: the round is the plan's own estimate (35 min): two oracles, the network_capture adapter and a status/interval/count matrix cannot be split without one half having no fixture.
mutant-cap-raise: two criteria with three and four independent rules each (status floor, success guard, template, interval boundary, count boundary, repeat gate, no-budget); one mutant per rule is the floor, each a one-line copy edit run in under 1 s.
Base / checked state: cff3ffe6 / d756b351, clean tree
Gate answers: none apply (D-104 opens the build; no gate in qa/gates touches the network oracles).
Affected tests / full-suite trigger: none outside the new files (no existing module edited); the builder ran no full suite.
Tests[MP21]: tests/test_network_oracles.py::test_mp21_a_500_behind_a_success_toast_is_one_finding_citing_url_status_and_screen, ::test_mp21_every_4xx_and_5xx_is_flagged, ::test_mp21_a_non_error_status_is_not_flagged, ::test_mp21_no_finding_when_the_ui_did_not_show_success, ::test_mp21_third_party_failures_are_not_product_errors, ::test_mp21_repeats_group_and_distinct_requests_are_distinct_findings, ::test_mp21_the_secret_in_a_url_never_reaches_the_finding, ::test_mp21_run_reads_the_port_and_names_the_oracle - the 500-behind-toast fixture, a status matrix (400..599 flagged, 200..399 not), the no-success and third-party exclusions, grouping and redaction.
Tests[MP22]: tests/test_network_oracles.py::test_mp22_polling_every_200ms_against_a_1s_budget_is_a_finding_with_the_numbers, ::test_mp22_the_polling_boundary_is_the_declared_interval, ::test_mp22_two_requests_are_not_polling_until_the_declared_repeat_count, ::test_mp22_only_the_fast_endpoint_is_flagged_when_polls_interleave, ::test_mp22_the_same_endpoint_with_different_ids_is_one_polled_endpoint, ::test_mp22_unsorted_timestamps_are_measured_in_time_order, ::test_mp22_requests_per_screen_over_the_budget_is_a_finding, ::test_mp22_requests_add_up_per_screen_across_steps_not_across_screens_or_roles, ::test_mp22_run_without_a_declared_budget_finds_nothing_and_with_one_finds_it, ::test_mp22_a_budget_exceeded_two_ways_gives_two_findings_with_distinct_ids - the 200 ms vs 1 s fixture, an interval and a count boundary matrix, endpoint and screen scoping, no-budget case.
Tests[MPI1]: tests/test_network_oracles.py::test_mpi1_findings_carry_no_personal_canary_and_no_provider_is_used, ::test_a_step_network_log_refuses_unsafe_or_unreplayable_input, ::test_capture_samples_reuses_network_capture_for_scope_and_redaction, ::test_a_port_without_a_network_log_is_reported_not_silently_clean - canary email/phone/id absent from every finding, no provider import, personal-shaped log text refused, type-only error.
Tests[MPI3]: none - diff check: `git diff --name-only cff3ffe6..d756b351` lists only the 5 files above.
Falsification[MP21]: copy-mutants in scratchpad/t214-network (control 47 passed): status floor 400 -> 500: red `test_mp21_every_4xx_and_5xx_is_flagged` (3 params); success guard `if log.success_indicator is not None` -> `if True`: red `test_mp21_no_finding_when_the_ui_did_not_show_success`; `url_template=request` -> the screen URL: red `test_mp21_a_500_behind_a_success_toast_is_one_finding_citing_url_status_and_screen`; restored 47 passed.
Falsification[MP22]: copy-mutants: `gap < budget` -> `<=`: red `test_mp22_the_polling_boundary_is_the_declared_interval[1.0-False]`; `total > max` -> `>=`: red `test_mp22_requests_per_screen_over_the_budget_is_a_finding[50-False]`; repeat-count gate dropped: red (4 tests incl. the no-budget and two-request cases); no-budget short-circuit replaced by a default budget: red `test_mp22_run_without_a_declared_budget_finds_nothing_and_with_one_finds_it`; restored 47 passed.
Pre-check[MP21]: d756b351 uv run --directory <worktree> pytest tests/test_network_oracles.py -> 47 passed t=1 blobs=tests/test_network_oracles.py:dff1f54,tests/network_oracle_fakes.py:e7806f8
Pre-check[MP22]: d756b351 uv run --directory <worktree> pytest tests/test_network_oracles.py -> 47 passed t=1 blobs=tests/test_network_oracles.py:dff1f54,tests/network_oracle_fakes.py:e7806f8
Pre-check[MPI1]: d756b351 uv run --directory <worktree> pytest tests/test_network_oracles.py tests/test_oracle_registry.py -> 59 passed t=1 blobs=tests/test_network_oracles.py:dff1f54
Lint: d756b351 `uv run ruff check src tests scripts` -> All checks passed; `uv run autotester doctor` -> 2 violations, both stale-generated (judgement call 11).
Metrics: start=2026-10-19T00:00:00Z end=2026-10-19T00:40:00Z wall_min=40 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=1 mutations=7 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-18.15 lane=normal check_s=unavailable mutants=7 defects_unit=0 defects_6c=0 tests=47 tests_min=1

## How to verify (commands + expected)
- `uv run pytest tests/test_network_oracles.py tests/test_oracle_registry.py` -> expected: 59 passed.
- `git diff --name-only cff3ffe6..d756b351` -> expected: the 5 files listed, nothing else.

## Capability coverage (each new claim -> its isolating falsification)
| Criterion | capability | the check that covers it | the falsifying edit | observed |
|---|---|---|---|---|
| MP21 | 4xx/5xx behind a success screen is a finding citing template, status, success screen | tests/test_network_oracles.py::test_mp21_a_500_behind_a_success_toast_is_one_finding_citing_url_status_and_screen, ::test_mp21_every_4xx_and_5xx_is_flagged | status floor 400 -> 500 / success guard -> `if True` / raw screen URL as template | green on tree; red on each |
| MP22 | polling interval and requests-per-screen against the declared budget, with measured numbers | tests/test_network_oracles.py::test_mp22_polling_every_200ms_against_a_1s_budget_is_a_finding_with_the_numbers, ::test_mp22_the_polling_boundary_is_the_declared_interval, ::test_mp22_requests_per_screen_over_the_budget_is_a_finding | `<` -> `<=` / `>` -> `>=` / repeat gate dropped / default budget when none | green on tree; red on each |

## Live browser evidence
Not UI-touching - no surface changed: only a schema and two stage modules plus tests; no route, template or static asset.

## Status: checked-PASS (qa/verdicts/t214-network.md 751bd035)
