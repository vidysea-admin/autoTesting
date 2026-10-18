# Verdict - t217-cred-pay (T-217, MP27 + MP28)

**Verdict:** PASS
**Cycle checked:** 0
**Reviewed SHA:** d9cf9f28 (manifest commit c9190dee on top; base 95ffd971 = `git merge-base HEAD int/1017`)
Policy-Version: proportional-verification/2026-10-18.15

## Check plan
Tier M (two stage modules + two schema files; no UI, no auth/tenancy/prod-write trigger, dual not required). Lane: off (adapter) so a normal check. Plan: (1) MPI3 diff scope; (2) re-run the manifest verify command; (3) read the diff of the 4 src files; (4) one falsification per criterion in a copy outside the repo; (5) independent probe of the CORE-REQUEST workaround (missing/invalid declaration file) and of value leakage; (6) ruff + doctor.

## Independent checks
- MPI3: `git diff --name-only 95ffd971..d9cf9f28` = 4 src + 4 tests (credential_policy.py, payment_path.py, oracle_credential_policy.py, oracle_payment.py, credential_fakes.py, 3 test files). None of schema/multi_role_enums.py, schema/enums.py, schema/project.py, stages/oracle_registry.py, browser/session.py. Held.
- Verify command (manifest, 7 files): 127 passed, 1 warning (starlette deprecation), 6.3 s. `uv run ruff check src tests scripts`: All checks passed. `uv run autotester doctor`: 2 violations, both stale-generated docs/MAP.md and docs/SNAPSHOT.md (regenerated at merge, not a FAIL). File sizes <= 211 lines.
- MP27 (stages/oracle_credential_policy.py:78-90,107-121,141-155,192-206): one synthetic password per declared rule, each breaking exactly that rule; findings built at :129-138 and :167-175 carry `[probe:<rule>]` / rule name, never a value; reuse probe is a `{{SECRET:KEY}}` placeholder (:82-83). Unreached form -> `break` (:150-151), nothing decided -> `CredentialProbeError` (:204-205). Independent probe (scratchpad/probe/probe.py): app enforcing nothing -> 4 findings by rule name, 0 typed values and 0 previous-password value in the serialised findings.
- MP28 (stages/oracle_payment.py:95-110,140-147): gateway marker looked at after EVERY step in every phase, walk stops on REACHED/UNOBSERVED; sandbox steps only when `provider_test_mode` (:125-126) and the schema refuses `test_mode_steps` without it (payment_path.py:89-91). Independent probe: gateway_steps = [checkout, pay-now] -> `submit_calls` 0, report `reached`, `stopped_at_gateway` true, performed_steps 3, report file states-only.
- CORE-REQUEST workaround (registry state via run_oracles, independent probe): credential oracle missing file -> errored/PolicyNotDeclaredError; invalid JSON -> errored/PolicyNotDeclaredError; valid -> ran. Payment oracle missing -> errored/PaymentNotDeclaredError; invalid -> errored/PaymentNotDeclaredError. Never a clean ran. Reasons are type names only (oracle_registry.py:68).

## Falsification (floor: 1 per criterion; copies in scratchpad m27 / m28, outside D:/autoTesting; PYTHONPATH to the copy, autotester.__file__ confirmed in the copy)
- MP27: green before (37 passed). Edit oracle_credential_policy.py:86 `(rules.min_length or 1) - 1` -> `(rules.min_length or 1)` (min_length probe compliant): red, 15 failed, incl. `test_mp27_each_probe_breaks_exactly_the_one_rule_it_names` and `test_mp27_a_product_enforcing_every_rule_has_no_finding[create|reset]` (false weak-password finding). Not an import error.
- MP28: green before (20 passed). Edit oracle_payment.py:100 `self.gateway, self.stop = REACHED, True` -> `self.gateway = REACHED` (walk keeps going): red, 3 failed: `test_mp28_it_stops_even_when_the_declaration_names_a_step_that_would_pay`, `..._stops_when_an_earlier_step_already_lands_on_the_gateway`, `..._coupon_the_walk_never_reached_is_not_called_unapplied`.
- Worktree untouched by mutants (copies only).

## Review notes (non-blocking, no ledger rows)
- Over-flagging by design (token count over the whole read window; declared in manifest call 5). One-click-charge flows where the declared pre-gateway step itself charges cannot be prevented by any oracle; call 7 states the limit.
- Live legs (MP34 mailbox, real forms/gateway) credential-gated: not a FAIL.

## Result
SCOREBOARD: 2/2 criteria met (MP27, MP28), 1/1 invariant checked (MPI3) and MPI1/2/4/5 not contradicted by the diff.
TIER: M (stage + schema modules, no L trigger found in the changed non-test files)
FAILURES: none
ISSUES-WRITTEN: none
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
Metrics: start=2026-10-18T21:03:00Z end=2026-10-18T21:18:00Z wall_min=15 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=2 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-18.15 lane=normal check_s=unavailable mutants=0 defects_unit=0 defects_6c=0
slow: reading checker protocol and diff then three test legs, about 15 min wall because the protocol file is long
