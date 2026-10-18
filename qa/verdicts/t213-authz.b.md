# Verdict B - t213-authz (T-213), coordinator B (blind), Cycle checked: 1

Date: 2026-10-19 · Policy-Version: proportional-verification/2026-10-18.15 · Repair base b4fd754b -> head 4ebd8676 (manifest commit 30114a9a) · Cycle-0 verdict archived at qa/verdicts/t213-authz.b.r0-1.md.

## Check plan (repair scope, .9/repair-checker rule)
Re-validate by evidence identity from checkpoint B. Repair diff touches: `stages/authz_probe.py` (scope: MP20/A5), `stages/oracle_tenant.py` (list status: MP18), `stages/oracle_privilege.py` (revert record: MP19/MPI4), `schema/authz_probe.py` (StopReason). Untouched inputs keep their recorded cycle-0 result: `leak_evidence.py` reuse, `schema/multi_role_enums.py` (MPI3). Steps: git identity, repair diff read in full, whole-unit scope scan, affected tests, ruff/doctor, one falsification per changed criterion (copies outside the worktree).

## Results
- Git: `git merge-base HEAD int/1017` = cff3ffe6 (= declared base); HEAD 30114a9a; code head 4ebd8676; `git diff --name-only cff3ffe6..4ebd8676` = exactly the 9 declared files (4 src + 5 tests incl. `tests/authz_fakes.py`); no `schema/multi_role_enums.py`, no `qa/contracts/`; `src/autotester/schema/probe_budget.py` absent. Whole-unit range to 30114a9a adds only qa bookkeeping (manifest, verdicts, checkpoints, evidence).
- Repair diff read in full (`git diff b4fd754b..4ebd8676 -- src tests`): 
  - `authz_probe.py:113-138` `_platform_hosts`/`_in_scope`/`_check_scope`: scope is now the probed platform's own hosts (declared `allowed_domains` plus the base-URL host), subdomains only while `include_subdomains`; project-wide `allows_domain` no longer consulted. Gate order unchanged: scope, then `require_project_approval`, then ceiling; the refusal is still logged once before the raise. Hostname-confusion cases I read (userinfo `app.test@evil.test`, `evilapp.test`, `app.test.evil.test`) do not match `host == d` or `.endswith(".app.test")`.
  - `oracle_tenant.py:119-125` `_read_rows`: a non-2xx list reply returns None and names the rest of the view `list_status`; callers `_probe_view` already treat None as "stop this view". No finding is fabricated from a non-2xx reply and the view is no longer silently clean.
  - `oracle_privilege.py:97-120` `_assign`/`_record_revert`: the raising-assign path now writes a `RevertRecord` (reverted true/false); the record holds finding id, control id, role id, bool, timestamp only (no response, no value: MPI1 held). `_revert` swallows its own errors; `budget.extra()` still counts the reserved revert.
  - `schema/authz_probe.py:194` `StopReason.LIST_STATUS`: additive enum member.
- Affected tests: `uv run pytest tests/test_oracle_tenant.py tests/test_oracle_privilege.py tests/test_authz_gate.py tests/test_authz_probe_schema.py tests/test_oracle_registry.py tests/test_leak_evidence.py` -> 81 passed (my run, TMP=D:/autoTesting/.work/tmp). Manifest's 5-file set (72) is a subset.
- Lint: `uv run ruff check src tests scripts` -> All checks passed. `uv run autotester doctor` -> 4 violations (2 stale-generated docs, 2 `run` duplicates; known CORE-REQUEST fixed by doctor-oracle-exempt; not a FAIL here).
- Falsification, one per changed criterion, isolated copy per mutant outside the worktree (tool `qa/evidence/t213-authz.b/mutate_b_c1.py`, results `mutants-c1.json`): control 60 passed (green before). 
  - MP18: `if not reply.ok` -> `if False` -> RED `test_mp18_an_owner_list_that_returns_401_names_the_view_unprobed_never_clean` + `test_mp18_a_viewer_list_that_returns_403_names_the_view_unprobed`.
  - MP19/MPI4: raise-path `_record_revert` removed -> RED `test_mp19_an_assign_that_raises_and_whose_revert_failed_is_recorded_for_the_operator`.
  - MP20/A5: scope widened with sibling host -> RED `test_a5_an_approval_for_one_platform_cannot_be_spent_on_a_sibling_platforms_host`; `include_subdomains` ignored -> RED `test_a5_a_platform_pinned_to_exact_hosts_refuses_its_own_subdomain`. Reds are on the named assertions, not import errors.

## Criteria
MP18 met (list_status closes the clean-on-401 gap; evidence still values-free) · MP19 met · MP20 incl. A5 met (approval covers the probed platform only; refusal appends one non-secret line; zero transport calls on refusal) · MPI1 held · MPI3 held (enums file not in diff) · MPI4 held.

PROPOSED-ISSUE: {"sev":"low","title":"Raise-path RevertRecord cites a finding_id for which no finding is emitted (oracle_privilege.py:_assign)","detail":"operator trace is by control_id; a reader joining reverts.jsonl to findings by finding_id will find no match for an assign that raised","fix":"document in RevertRecord docstring or add a 'no_finding' marker"}

```
VERDICT: PASS
SCOREBOARD: 3/3 criteria met (MP18, MP19, MP20+A5), 3/3 invariants hold (MPI1, MPI3, MPI4)
TIER: L (security/auth/tenancy: dual-trigger lines oracle_tenant.py:142, oracle_privilege.py:74 confirmed present in changed code)
FAILURES: none
CAPABILITY-COVERAGE: not-applicable (no UI; 4 changed-criterion falsifications reproduced)
LIVE-BROWSER: not-applicable (src/autotester/stages and schema only, no UI surface)
ISSUES-WRITTEN: none (dual check: PROPOSED-ISSUE P1 above)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: The repair closes the sibling-platform approval-scope gap, the non-2xx-list-as-clean gap and the missing raise-path revert record; each has a test that goes red when the repaired line is mutated, and the 81-test affected set is green with no out-of-scope file in the unit diff.
Metrics: start=2026-10-19T12:20:00Z end=2026-10-19T12:35:00Z wall_min=15 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=4 cycle=1 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-18.15 lane=normal check_s=unavailable mutants=4 defects_unit=0 defects_6c=0
```
