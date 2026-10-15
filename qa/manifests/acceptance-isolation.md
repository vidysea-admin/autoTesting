# Manifest â€” acceptance-isolation

**Status:** ready-for-check
**Fix cycle:** 2
**Unit:** T-169 acceptance driver authentication and contamination refusals (bounded repair)
**Branch:** codex/acceptance-repair
**Base commit:** abc4a0ef (runtime change); cycle-2 evidence base 14bb3782
**Candidate:** immutable commit containing this manifest; dispatch packet `.work/acceptance-checker-packet.md` records exact SHA after commit.
**Risk tier:** high-risk: authentication/permissions and baseline isolation; no auth guard changes.
**Authorization:** Umesh approved Ollama-first completion goal; parent assigned this bounded acceptance unit.

## What changed
- src/autotester/stages/real_acceptance.py: ordinary login, HTTPS loopback Origin and retained cookies; central view/edit/run/report project permission preflight before live seams. Explicit fresh-baseline refusal preserves prior user truth/cases.
- src/autotester/stages/generic_acceptance.py: reject requested mode inconsistent with stored teaching inputs before orchestration writes.
- scripts/run_real_acceptance.py: bind --root for UI paths; prompt password without echo; configured vision role; fresh-baseline refusal; real seams constructed after account authorization.
- tests/test_acceptance_isolation.py: eight named regressions (secure/plain-cookie scenarios loop inside one auth regression); local fixture accounts only.
- qa/evidence/acceptance-isolation/* and this manifest: bounded receipts, historical mutation evidence and exact environment/source fingerprint.

## Acceptance and immediate consumers
C5/C8/C9: no credential echo or hardcoded Gemini; normal account permissions retained. generic-acceptance GA1/GA3: teaching vs URL-only entry mode must match stored inputs; contaminated baselines refused without deletion. GR4: production signed-approval refusal remains intact. Core C2/C7/C10: scoped branch, structure, named mutation proof and independent checker.

## Selected checks and reasons
- tests/test_acceptance_isolation.py (eight tests): real signup/login with test auto-login disabled, HTTPS Origin/cookies, bad password refusal, missing run permission, source-mode contamination, inherited truth preservation, provider configuration and root binding.
- tests/test_generic_acceptance.py::test_both_modes_end_to_end_without_cli: immediate generic harness consumers in both modes.
- tests/test_real_acceptance.py::test_ui_run_trigger_refuses_production_without_approval: production boundary never bypassed.
- tests/test_real_acceptance.py::test_script_verifies_with_the_key_only_in_dotenv: CLI root/env/approval consumer.
- Scoped Ruff + stdlib AST structure checks: changed modules/docstrings/function limits only.

## Evidence and limits
`qa/evidence/acceptance-isolation/commands.json` records each final command/exit/duration; preflight.log binds Python 3.11.16, intended source root and writable temp parent. focused.log: 13 passed in 11.98s (parametrized cookie test then changed to a stable-node loop; final-mutation.log independently asserts green baseline over both scenarios in the final test before its named failure). lint.log clean; final scoped Ruff after stable-node edit also clean. structure.json enforces relevant caps.

Historical first focused run: 22 passed / 2 fixture setup failures in71.48s; prerequisites corrected. Historical eight-guard harness then asserted green baseline and killed 8/8 named mutations; result.txt preserves observed output, mutations.json its specification. Seven unchanged properties retain their evidence; historical receipt has no exact source fingerprint and is not advertised as exact-SHA independent evidence. The HTTPS-cookie test was subsequently strengthened; narrowed final mutation rerun killed its named defender (final-mutation.log). First narrowed attempt was INVALID due parameterized-node spelling, retained as final-mutation-invalid.log; never counted as a kill. Final stable-node loop avoids renaming historical test identifiers.

No full pytest/Ruff/doctor combined gate, independent checker, live browser/API/model, production run or deployment performed. D-100 combined integration/release gates remain mandatory centrally. Current provider factory must gain vision-role support in the provider lane before actual teaching acceptance; the selection regression stubs this external dependency.

## Remaining work
Isolated baseline preparation is a follow-on: refusing a polluted existing project alone does not create a baseline or complete T-169. Real T-169/T-206 acceptance, independent human comparison and deployment remain open. No contract/enforcement paths or project credentials changed; no push.

## Usage
Maker actual active time/tokens/cost unavailable (null), never zero. Historical mutation duration approximately six minutes, not exact telemetry. Final command durations recorded independently in commands.json. Budget helper result BOOTSTRAP_REVIEW; 10% ratios unverified. Fresh checker receives finite 180s/6000-token bootstrap scope, with high-risk boundary expansion requiring recorded allocation if necessary.

## Fix cycle 2 — provenance-only repair after checker HOLD

No runtime or test source changes after reviewed code7cda16f66dc96514edb3776efd32af64ca5e1791; cycle-1 independent12-test result and permission sabotage remain recorded in qa/verdicts/acceptance-isolation.md (cycle1 HOLD). Original unbound maker result remains unknown, never retroactively relabelled.

Fresh exact-bound evidence replaces all seven previously unbound historical claims. `qa/evidence/acceptance-isolation/cycle2/probe.py` copied complete src/tests/scripts without caches, verified the shared tests_mutation_fixtures upfront, asserted original four runtime/test files equal immutable7cda Git blobs, and ran import/temp preflight into the scratch source root. `identity.json` binds Python/version, dependency versions, lock hash, environment fingerprint and all original/scratch source hashes before tests. Each of seven named defenders received its own green baseline, exact-once applied mutation, changed-byte assertion, pytest exit1 with its exact node in plugin-produced failed list, then byte-identical restoration. `proofs.json`, `commands.json` and per-command complete logs preserve all evidence; final source hashes rechecked unchanged. No unrelated test suites repeated.

`reuse-audit.json` records that prior independent permission-probe restored hashes matched current files automatically, but lacked contemporaneous env/lock/per-run source receipts; therefore it was not used to waive the seventh rerun. Final Origin-cookie claim already has its cycle1 fresh maker proof and independently passing reviewer checks.

Results: 7/7 exact-bound named defenders killed; seven green single-defender baselines, seven attributed red runs, one preflight. Exact command time sum in cycle2/summary.json. Maker actual active seconds/tokens remain null; queue/wait time never added to maker denominators. No feature work, model calls, live browser/API or baseline creation performed. Full combined integration gates remain parent-owned.
