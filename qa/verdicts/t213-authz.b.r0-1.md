# Verdict B (blind coordinator) - t213-authz (T-213, G11-7)

Cycle checked: 0
Date: 2026-10-18 (UTC)
Policy-Version: proportional-verification/2026-10-18.15
Base / Head: cff3ffe6 (= `git merge-base HEAD int/1017`, verified) / b4fd754b code, 83460c49 manifest-only

## Check plan (step 0)
Diff = 4 new src files + 5 new test files (827 src lines), tier L by the cited triggers
(`oracle_tenant.py:139` cross-tenant read, `oracle_privilege.py:74`/`:131` replay + role-assign write).
Checks: (1) re-run the verify commands; (2) read gate, budget, both oracles in full; (3) one
falsification per criterion in isolated copies OUTSIDE the repo; (4) step 4c diff scope; (5) security
read: gate-before-send, bound overrun, unreverted escalation, value leakage. No UI surface (no walks, no
Mode D). No full suite (L unit with no prod write; rule .13). Own evidence only: `qa/evidence/t213-authz.b/`.

VERDICT: PASS
SCOREBOARD: 3/3 criteria met (MP18, MP19, MP20 incl. A5), 3/3 invariants hold (MPI1, MPI3, MPI4)
TIER: L (tenancy: oracle_tenant.py:139 reads another tenant's rows; auth: oracle_privilege.py:74 replays a higher role, :131 role-assign write)
FAILURES: none
CAPABILITY-COVERAGE: every manifest row's criterion covered by my own mutants (not the maker's edits re-applied); 9 of my 14 went red on the named assertion, 5 survived (test gaps, low, below)
LIVE-BROWSER: not-applicable (changed paths: schema/ and stages/ modules plus tests; no route, template or asset)
ISSUES-WRITTEN: none (dual coordinator: PROPOSED-ISSUE lines only)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)

## Evidence
- Verify (my run, worktree venv): `uv run pytest tests/test_oracle_tenant.py tests/test_oracle_privilege.py tests/test_authz_gate.py tests/test_authz_probe_schema.py tests/test_oracle_registry.py tests/test_leak_evidence.py` -> 76 passed (manifest: 67 for the first five files + the 9 leak-evidence tests). Control copy: 55 passed.
- `ls src/autotester/schema/probe_budget.py` -> no such file. `git diff --name-only cff3ffe6..b4fd754b` -> exactly the 9 listed files; `multi_role_enums.py` absent (MPI3). `git diff --name-status b4fd754b..HEAD` -> only the manifest.
- `ruff check src tests scripts` -> All checks passed. `autotester doctor` -> 4 violations: 2 stale-generated docs + 2 `run` duplicate-concept (the known CORE-REQUEST doctor-oracle-exempt; not a FAIL here).
- Step 4c: numstat is 100% additions (0 deletions), no existing function/test/config removed, no file outside "What changed". No `providers` import in any of the 4 src files (grep rc=1).

## Criterion judgement (read at file:line in this check)
- MP18: `oracle_tenant.py:62-71` owner mode counts viewer rows whose id is in the owner's list; count mode counts the surplus and drops the id field; `:137-139` dedupes list+swap by id; `:143-152` evidence only via `collect_leak_evidence`; P0 by class (`finding_priority.py:15`). Swaps use `abs_url` + `quote(raw, safe="")` (`:84`), same host. Met.
- MP19: `oracle_privilege.py:64-80` replays each read once as the lower role, 2xx = P0 finding, response not kept; `:121-138` one attempt per reachable control, only at `ALLOW_WRITES` (`:126`), `take(reserve=2)` reserves the undo (`:131`); `:108-114` revert immediately, `RevertRecord` appended, finding titled reverted / NOT reverted. P0 by class (`finding_priority.py:16`). Met.
- MP20 + A5: `authz_probe.py:137-155` gate: scope, then `require_project_approval(kind=ADVERSARIAL, target=base_url, probes=planned, wall_clock_s=...)`, then `PROBE_CEILING=60`; any refusal appends one `ProbeRefusal` (`:129-134`) and re-raises BEFORE any transport call (the transport is only touched after `open_session` returns). Swap limit 3 (`:54`), one list page structural, cap + wall clock + pacing in `Budget.take` (`:172-186`), shared across oracles via `prior_usage` (`:193`), unprobed named (`UnprobedItem`). `planned` is a true upper bound of counted requests (tenant 1+owner+3; privilege reads + 2 per control; the assign-raises path also costs 2). Reuses T-154 `ProbeRefusal`/`ProbeCeilingExceeded`; no `probe_budget.py`. Met.
- MPI1: finding text carries probe ids, role ids and a templatised URL only; `ProbeReply.rows` is `exclude=True` (`schema/authz_probe.py:156`); a transport error is category-only (`authz_probe.py:105-110`); refusal reason is `Redactor.scrub`bed. Held. MPI3 held. MPI4 held.

## Falsification (isolated copies under the scratchpad, outside D:/autoTesting; green control first: 55 passed; tool `qa/evidence/t213-authz.b/mutate_b.py`, results `mutants-run1.json`, `mutants-run2.json`)
| Criterion | Mutant (one hunk) | Result |
|---|---|---|
| MP18 | owner filter inverted (`oracle_tenant.py:68`) | red 5: `test_mp18_fixture_leaking_three_foreign_rows_is_one_p0_data_leak` and 4 more |
| MP18 | count-mode surplus offset +1 (`:70`) | red 1: `test_mp18_declared_own_count_mode_counts_the_surplus_and_keeps_no_id` |
| MP19 | 4xx counts as success (`oracle_privilege.py:74`) | red 3: `test_mp19_one_escalatable_endpoint_is_p0_and_the_refused_one_is_not` +2 |
| MP19 | revert result recorded as True (`:112`) | red 2: `test_mp19_a_revert_that_did_not_hold_is_recorded_and_called_out[*]` |
| MP20 | swap limit 3->4 (`authz_probe.py:54`) | red 6: `test_mp20_at_most_three_swaps_and_the_rest_is_named_unprobed` +5 |
| MP20 | cap boundary `>` -> `>=` (`:176`) | red 4: `test_mp20_the_request_cap_stops_the_pass...` +3 |
| MP20 | revert reserve 2->1 (`oracle_privilege.py:131`) | red 1: `test_mp20_the_cap_reserves_room_for_the_revert_so_it_is_never_exceeded` |
| A5 | approval probes checked at planned-1 (`authz_probe.py:145`) | red 2: `test_a5_an_approval_for_two_probes_against_a_plan_of_three_is_refused_with_nothing_sent` +1 |
| MPI1 | `ProbeReply.rows` stops being excluded (`schema/authz_probe.py:156`) | red 1: `test_reply_rows_are_kept_in_memory_and_never_dumped` |
Floor (1 per criterion) met with green-before / red-after on the named assertion; 14 mutants run in total (9 red + 5 survivors, one batched runner, own copy each); the count exceeds the L cap of 10 and rests on the manifest's cited `mutant-cap-raise: src/autotester/stages/authz_probe.py:172` (4 criteria + 3 invariants, one distinct conditional/constant each).
Survived (not floor; each a test gap, no defect in the code): swap status ignored (`:89`), list status ignored (`:122`), write guard `is READ_ONLY` instead of `is not ALLOW_WRITES` (`oracle_privilege.py:126`, TEST_ACCOUNT untested; the shipped code is the stricter, correct form), ceiling `>=` (`authz_probe.py:147`, exactly-60 boundary untested), wall-clock dropped from the approval check (`:145`), cap clamp `min(...)` removed (`:240`, equivalent: planned <= 60 already bounds sends).

## Questions in EXPLANATION (non-blocking, <80% as FAIL)
Replay reads are author-declared (`PrivilegeProbe.read_urls`), not captured or baselined: the oracle never confirms the higher role gets a different answer, so a public URL listed there is reported P0.

## PROPOSED-ISSUE lines (dual check: no ledger writes)
PROPOSED-ISSUE: {"id":"P1","sev":"medium","type":"oracle-false-negative","where":"src/autotester/stages/oracle_tenant.py:109-122,131-135","what":"A non-2xx OWNER list read yields owner_ids=[] (reply.ok false returns []), so no foreign row can be found and the view reports clean with no UnprobedItem; MP20 says a probe that did not run is named","fix":"treat a non-2xx owner list as unprobed (reason transport_error/new StopReason) and add a test"}
PROPOSED-ISSUE: {"id":"P2","sev":"low","type":"bound-bypass-risk","where":"src/autotester/schema/authz_probe.py:174, src/autotester/stages/oracle_privilege.py:90-95,130","what":"EscalationTransport.can_reach is called outside Budget.take and is not counted or capped; if T-210's implementation issues a request, the per-platform cap and the gate's planned count are exceeded","fix":"document can_reach as request-free or count it in Budget and plan_size"}
PROPOSED-ISSUE: {"id":"P3","sev":"low","type":"test-gap","where":"tests/test_authz_gate.py","what":"surviving mutants: approval wall-clock shortfall not tested; exactly-60 ceiling boundary not tested; swap/list status not isolated; TEST_ACCOUNT write policy not tested","fix":"four small asserts"}
PROPOSED-ISSUE: {"id":"P4","sev":"low","type":"oracle-false-positive","where":"src/autotester/stages/oracle_privilege.py:60-80","what":"read_urls are not baselined as higher role; a public or shared endpoint listed there is a P0 finding; also an assign that raises (:100-105) leaves no record if its best-effort revert fails","fix":"baseline read as higher role in the plan author or oracle; record an unknown-state RevertRecord"}
PROPOSED-ISSUE: {"id":"P5","sev":"low","type":"process","where":"qa/manifests/t213-authz.md judgement call 11","what":"no senior-software-engineer review was dispatched by the maker (handoff refused in the worktree); this blind verdict is the first independent read","fix":"orchestrator note only"}

EXPLANATION: Both oracles send nothing until `gate` passes a signed ADVERSARIAL approval for the exact base URL covering the derived planned count, then the 60-probe code ceiling, and every refusal appends one scrubbed `ProbeRefusal` line; the budget (3 swaps, one page, shared cap with the revert reserved, wall clock, pacing) is enforced in `Budget.take`, and a role-assign is write-policy gated, reverted in-run and recorded. All three criteria and MPI1/MPI3/MPI4 were evidenced by my own runs and by 9 mutants that went red on the named assertions; the survivors are test gaps only. The slow step was none (check under 10 min).

Metrics: start=2026-10-18T20:27:00Z end=2026-10-18T20:40:00Z wall_min=13 agent_min=13 blocked_min=0 suite_runs=0 repeat_runs=0 mutations=14 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-18.15 lane=normal check_s=780 mutants=14 defects_unit=0 defects_6c=0
