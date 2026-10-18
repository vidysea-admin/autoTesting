# Verdict t213-authz (coordinator A) - repair check
Cycle checked: 1
Date: 2026-10-18 · Policy-Version: proportional-verification/2026-10-18.15 · Dual check: coordinator A (blind)
Code checked: 4ebd8676 (repair base b4fd754b, manifest 30114a9a, unit base cff3ffe6 = `git merge-base HEAD int/1017`)

## Check plan (repair scope)
Failed criterion MP20/A5 (scope gate) re-run; repair also touches `oracle_tenant._read_rows` (MP18) and
`oracle_privilege._assign` (MP19), so those two are re-run; MP20 caps/clock, MPI1, MPI3 inputs untouched except as below.
Repair diff `b4fd754b..4ebd8676` read in full (4 src + 3 test files). Whole-unit `cff3ffe6..30114a9a` non-qa files =
exactly the 9 declared files; `schema/multi_role_enums.py` and `schema/probe_budget.py` absent from the diff / tree.

## Evidence (all run by me)
- `uv run pytest tests/test_oracle_tenant.py tests/test_oracle_privilege.py tests/test_authz_gate.py tests/test_authz_probe_schema.py tests/test_oracle_registry.py` -> 72 passed (matches manifest). `uv run ruff check src tests scripts` -> clean.
- A5 scope (`stages/authz_probe.py:113-138`): `_in_scope` now tests the probed platform's own hosts only (`allowed_domains` else base host; subdomains only while `include_subdomains`). Counterexamples `qa/evidence/t213-authz.a/probe_scope_c1.py` (+ `.out`): the cycle-0 escape (read URL on the sibling platform's host under an approval for the primary base URL) is now REFUSED with zero transport URLs; also refused: sibling with include_subdomains=False, `//other.test/...`, lookalike `evilapp.test`, trailing-dot host; `user@host` forms are rejected by the schema (`_plain_url`, "@" banned) before the gate; own path / own subdomain / upper-case own host still pass (controls). No over-refusal of legitimate plans seen.
- MP18 (`oracle_tenant.py:122-124`): a 401 owner list or 403 viewer list is now `list_status` unprobed with `return None` for the rest of the view, not a clean empty result; the cycle-0 silent-clean counterexample no longer reproduces.
- MP19 (`oracle_privilege.py:97-119`): a raising assign now leaves a `RevertRecord` (reverted true/false) in `reverts.jsonl`; no value or response text is stored (MPI1 holds: record carries ids/role/bool/timestamp only).
- Falsification floor, one per repaired criterion, each in its own copy outside D:/autoTesting (runner `qa/evidence/t213-authz.a/mutate_c1.py`, output `mutate_c1.out`; green-before in the copy using the copy's package, red-after on the named assertion):
  A5 sibling host widened (`... base, 'other.test'`) -> `test_a5_an_approval_for_one_platform_cannot_be_spent_on_a_sibling_platforms_host` red; A5 `include_subdomains` ignored -> `test_a5_a_platform_pinned_to_exact_hosts_refuses_its_own_subdomain` red; MP18 cycle-0 form `list(reply.rows) if reply.ok else []` -> both `list_status` tests red; MP19 revert record removed on the raise path -> `test_mp19_an_assign_that_raises_and_whose_revert_failed_is_recorded_for_the_operator` red.
- MP18/MP19/MP20 (caps, clock, 3 swaps, no provider import) and MPI3/MPI4: input files unchanged by the repair apart from the lines above; covered by the 72-pass run.

## Criteria
MP18 met · MP19 met · MP20 (incl. A5 scope) met · MPI1 holds · MPI3 holds · MPI4 holds. Scoreboard 3/3 criteria, 3/3 invariants.

PROPOSED-ISSUE: {"sev":"low","criterion":"A5","title":"Default include_subdomains=True lets one platform's approval span a sibling platform whose host is a subdomain of the first platform's declared domain; the operator must set include_subdomains=false to pin (Platform field docstring says so). Consider a gate-side note or default for adversarial approvals.","type":"design-note","blocking":false}

VERDICT: PASS
SCOREBOARD: 3/3 criteria met, 3/3 invariants hold
TIER: L (tenancy/auth probes with a role-assign write and revert; dual check, coordinator A)
FAILURES: none
CAPABILITY-COVERAGE: not-applicable (no UI surface; repaired rows reproduced by falsification above)
LIVE-BROWSER: not-applicable (src/ and tests/ only, fake transports)
ISSUES-WRITTEN: none (dual check; qa/issues.jsonl untouched)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: The cycle-0 scope escape is closed: the gate now scopes to the probed platform's own hosts and the reproduced sibling-host read is refused with zero requests sent. The non-2xx list and raising-assign repairs behave as claimed and each falsifies red on its named test; the whole-unit diff has no out-of-scope files.
Metrics: start=2026-10-18T20:48:00Z end=2026-10-18T21:03:00Z wall_min=15 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=4 cycle=1 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-18.15 lane=normal check_s=900 mutants=0 defects_unit=0 defects_6c=0
