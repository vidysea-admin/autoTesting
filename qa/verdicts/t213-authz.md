# Verdict - t213-authz (coordinator A, blind)

Cycle checked: 0
Policy-Version: proportional-verification/2026-10-18.15
Checked: code b4fd754b (manifest commit 83460c49); base cff3ffe6 = `git merge-base HEAD int/1017`; bound to D:/autoTesting/.worktrees/t213-authz

## Check plan
Tier L via security/auth/tenancy (dual-trigger lines `oracle_tenant.py:139`, `oracle_privilege.py:74` read: real). Steps: re-run verify commands; read the 4 src files in full (step 4c; diff = 9 files + manifest, nothing removed); one falsification per changed criterion in copies outside the worktree; counterexamples on the approval gate and on the error paths. No UI, no provider, no live service: persona walk and Mode D not applicable. No full suite (policy .7).

## Evidence (all run by me)
- `uv run pytest tests/test_oracle_tenant.py tests/test_oracle_privilege.py tests/test_authz_gate.py tests/test_authz_probe_schema.py tests/test_oracle_registry.py` -> 67 passed (qa/evidence/t213-authz.a/pytest-affected.txt). ruff clean. doctor 4 violations = the manifest's 2 stale generated docs + 2 known `run` duplicates (not judged).
- MPI3: `git diff --name-only cff3ffe6..b4fd754b` = 9 files, no `schema/multi_role_enums.py`. `ls src/autotester/schema/probe_budget.py` -> no such file. No authz module imports `providers` (grep empty).
- Falsification floor, each in its own copy outside the worktree (green-before from the copy, red-after on the named assertion; runner qa/evidence/t213-authz.a/mutate.py):
  - MP18 owner filter -> `and True`: red `assert (5 == 3)` on the foreign count (test_mp18_fixture_leaking_three_foreign_rows...).
  - MP19 revert call -> `reverted = True`: red `assert [] == [('teacher', 'promote')]` (test_mp19_a_successful_role_assign_is_p0_and_reverted...).
  - MP20 swap slice `owner_ids[:3]` -> `[:4]` in oracle_tenant.py: red `assert (4 == 3)` (test_mp20_at_most_three_swaps...). My first MP20 mutant (constant 3 -> 4) went red only through the gate (`probes 6 > approved 5`), so I used the slice mutant, which isolates the assertion.
  - A5 `probes=planned` -> `probes=0`: red `DID NOT RAISE ApprovalRequired` (test_a5_an_approval_for_two_probes...).
- MPI1 differential: a control run (3 foreign rows, synthetic PII markers) left 5 files; a scan for `ZZNAME`, `zz.leak`, `ZZPHONE`, `sid-b-` found none.

## Result by criterion
- MP18 met. MP19 met. MPI1, MPI3, MPI4 held (assign only at ALLOW_WRITES, `oracle_privilege.py:126`; revert reserved with `take(reserve=2)`, `authz_probe.py:172-176`).
- MP20 / A5 NOT met on one point: the approval is for the platform's exact `base_url`, but the scope check lets a plan send reads to any host of the PROJECT.

## FAIL finding
[MP20/A5] sev: high - the A5 gate does not bind the probes to the approved target.
- `stages/authz_probe.py:113-116` `_in_scope` returns `project.allows_domain(host) or <platform domains match>`. The project-wide clause admits every host of every platform, so the platform clause is dead and `include_subdomains=False` is ignored. The refusal text at :126 says "outside the platform's allowed_domains", which the code does not do. `core/consent.py::require_approval` matches the target EXACTLY so that an approval for one endpoint cannot authorise another.
- Reproduction (I ran it): `.venv/Scripts/python.exe -I qa/evidence/t213-authz.a/probe_scope.py` with `AUTOTESTER_APPROVAL_KEY` and `AUTOTESTER_LEAK_EVIDENCE_KEY` set to synthetic values. Project with platforms `primary` (app.test) and `second` (other.test), ADVERSARIAL approval for `https://app.test/` only, plan for `primary` with `read_urls=["https://other.test/admin/users"]` -> `GATE PASSED; transport saw URLs: ['https://other.test/admin/users']`, 1 finding, no refusal line. An approval granted for one platform is spent on another.
- Fix direction: `_in_scope` = base_url host plus the platform's `allowed_domains` honouring `include_subdomains`, not `project.allows_domain`; add a test with a second platform host (the existing `test_a5_a_planned_url_outside_the_allowed_domains` only covers a host outside the whole project).

## PROPOSED-ISSUE lines (dual check: no ledger writes)
PROPOSED-ISSUE: {"sev":"high","type":"security","unit":"T-213","criterion":"MP20/A5","title":"authz scope check admits any project host, so a base_url approval authorises probes on another platform","ref":"src/autotester/stages/authz_probe.py:113-116"}
PROPOSED-ISSUE: {"sev":"medium","type":"correctness","unit":"T-213","criterion":"MP18","title":"a non-2xx owner or viewer list read yields no finding and nothing named unprobed (silent clean)","ref":"src/autotester/stages/oracle_tenant.py:109-122; repro: owner list 401 while tenant A sees 3 foreign rows -> findings 0, unprobed [], sent 2 (probe_scope.py); control with owner 200 -> 1 finding, count 3"}
PROPOSED-ISSUE: {"sev":"low","type":"correctness","unit":"T-213","criterion":"MP19","title":"an assign that raises followed by a revert that returns False is recorded nowhere (no reverts.jsonl line, no finding)","ref":"src/autotester/stages/oracle_privilege.py:100-105 (read, not run)"}
PROPOSED-ISSUE: {"sev":"low","type":"correctness","unit":"T-213","criterion":"MP20","title":"prior_usage counts only the OTHER oracle, so a second run of the same oracle in one run dir restarts its own share of the cap; EscalationTransport.can_reach is not budgeted and its contract does not say it sends nothing","ref":"src/autotester/stages/authz_probe.py:193-202,239-242 (read, not run)"}

VERDICT: FAIL
SCOREBOARD: 2/3 criteria met (MP18, MP19; MP20/A5 not met), 3/3 checked invariants hold (MPI1, MPI3, MPI4)
TIER: L (tenancy and auth probes with a role-assign write: `oracle_tenant.py:139`, `oracle_privilege.py:74`)
FAILURES:
- [MP20/A5] sev: high · the scope check admits any project host, so the approval is not bound to the approved platform · `stages/authz_probe.py:113-116`, reproduced with probe_scope.py · restrict `_in_scope` to the platform's own domains and add a second-platform test · issue: P1
CAPABILITY-COVERAGE: 4/4 floor rows reproduced (MP18, MP19, MP20, A5); manifest rows beyond the floor not re-run (floor only, .10-3)
LIVE-BROWSER: not-applicable (schema, stage and test files only)
ISSUES-WRITTEN: none (dual check)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: The probes, caps, revert and evidence rules work and are well tested, but the approval gate checks the host against the whole project instead of the approved platform, so an ADVERSARIAL approval for one base URL lets reads go to another platform's host (reproduced). That is a security defect in the changed gate code, so MP20/A5 is not met. The silent-clean error path is a robustness question I do not block on (PROPOSED-ISSUE medium).
Metrics: start=2026-10-18T20:27:00Z end=2026-10-18T20:36:00Z wall_min=9 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=5 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-18.15 lane=normal check_s=540 mutants=0 defects_unit=1 defects_6c=0
