# Manifest - t218-ceo-bench (T-218, G11-12, fixture leg)

**Status:** ready-for-check
**Fix cycle:** 0
**Contract:** qa/contracts/multi-role-platform.md (MP29, MP30, MP31 build leg; invariants MPI1-MPI6 held; MP35 stays open)
**Goal task:** T-218
**Authority:** D-104 (Approved-by: Umesh 2026-10-17: build G11 now; Umesh 2026-10-18: "build all remaining features")
**Dual check:** no (MP29/MP30 are synthetic-fixture scoring and ordering; MP31 is a pure check over a run record. No auth, tenancy or product-data write code: nothing signs, grants or opens a browser. `RunApproval` is only read through its own `is_intact` / `is_signed_and_verified` / `is_expired`.)
**Persona walk:** skip (no UI surface in this unit)
**Issues addressed:** none
**Executor:** claude-sonnet-subagent
**Base SHA:** cff3ffe6 (worktree .worktrees/t218-ceo-bench, branch wave/t218-ceo-bench; the T-211 head, stacked on T-209 36a87037 and T-207)
**Code SHA:** d6fb0ed8

## Criteria (quoted verbatim from the contract)
- **MP29 — Scored by the existing scorer.** Recall (overall and per priority), FP rate over adjudicated findings and wall time come from `stages/bench.py`/`acceptance_comparison`; no second scorer. Unadjudicated findings are neither TP nor FP. Verify (A4): a synthetic atomic list (6 items over 3 priorities) and a synthetic AutoTester finding set (3 matches, 1 adjudicated FP, 1 unadjudicated) give recall 3/6 overall and per priority, an FP rate over adjudicated findings only, and one recall line per technique with its owning unit (an owner that did not run reads `not run`). The numbers are asserted equal to `stages/bench.py` output on the same input, and a second scorer module is absent. serves: intent#O21, intent#O6 · closes T-218 (build leg)
- **MP30 — Ordering and contamination recorded.** The atomic list's sha256 and commit time precede the run's start; scenarios derived from a specific finding are labelled and excluded from recall; without the recorded ordering recall reads `unavailable (ordering not recorded)` (T-136 gate). Only counts and the hash are committed. Verify (A4): three fixtures. In the first the list hash and commit time precede the run start, and recall is a number. In the second the list postdates the run, and recall reads `unavailable (ordering not recorded)`. In the third a scenario is labelled derived-from-finding, and its match is excluded from recall. A grep of the committed scorecard finds only counts and the list's sha256. serves: intent#O21 · closes T-218 (build leg)
- **MP31 — Eight roles, linked platforms, run evidence complete (build leg, fixture).** The acceptance run uses the onboarded 8 role accounts across the linked platforms in a real visible browser under a valid RunApproval, and reports per oracle whether it ran. Verify (A4), on synthetic run evidence: it lists 8 onboarded role accounts and every declared platform with each one's login outcome, references a valid signed RunApproval id, records headed mode, and has a per-oracle ran / not built / not run table covering every registry entry; a role or oracle missing from the table fails. The real run is **MP35 [GATED]**. serves: intent#O21, intent#O16, intent#O18 · closes T-218 (build leg)
- (held) **MPI6 — CEO-benchmark scoring rule (intent "Scoring").** The 69 findings are split into atomic findings before the G11 run; the list stays private under `.work/` and committed artifacts carry only counts and its sha256. Matching is one-to-one by the existing `acceptance_comparison`/`bench` scorer, never a second scorer. Unmatched AutoTester findings are "unadjudicated", neither TP nor 

- (NOT built here, GATED) **MP35 [GATED] — Live CEO-benchmark acceptance run.** The 8 onboarded role accounts on the linked platforms run in a real visible (headed) browser under a signed production RunApproval, with the real-money rule of MPI4 held; the scorecard of MP29-MP31 is produced from that run. Gates (all outside the build): real role accounts and per-project keys; the atomic split of the CEO list confirmed by Umesh with its sha256 pinned before the run (MP30); the signed RunApproval; FP adjudication and the CEO's active hours for the time number (until then time reads `unknown`). Verify: the A4 run-evidence check on the real run. serves: intent#O21, intent#O16, intent#O18 · closes the live leg of T-218; T-218 is not closed while this row is open, unless Umesh accepts the fixture leg in writing


## What changed
- `src/autotester/schema/ceo_inputs.py` (new, 141 lines): `Technique` (the 14 CEO detection techniques, closed vocabulary owned here because `schema/enums.py` is at its cap and `multi_role_enums.py` is T-207's), `AtomicFinding` (id, `Priority` reused, technique, `needs_seeded_data`; NO text field), `AtomicList`, `RunFinding` (one-to-one `matched_atomic_id`, else `false_positive` / `unadjudicated`, default unadjudicated), `ScenarioLabel`, `OrderingRecord`, `CeoRunInput`.
- `src/autotester/schema/ceo_scorecard.py` (new, 78): `CeoScorecard`, `RecallLine`, `TechniqueLine`; counts, ratios, the list sha256 and fixed-vocabulary strings only, so a dumped scorecard cannot carry a finding.
- `src/autotester/stages/ceo_benchmark.py` (new, 190): `build_scorecard(run, oracle_summary)`, `render_scorecard`, `print_scorecard`, `render_oracle_table`, `TECHNIQUE_OWNERS`, `technique_ran`, `ordering_detail`. Every rate comes out of `BenchTrial.score` through `stages.bench.scorecard` (the call `acceptance_comparison` makes); the module has no division.
- `src/autotester/schema/ceo_run_evidence.py` (new, 48) and `src/autotester/stages/ceo_run_evidence.py` (new, 96): the MP31 fixture-leg record (`CeoRunEvidence`, `RoleLogin`, per-oracle `OracleStatus` table) and `run_evidence_problems(...)`.
- tests: `tests/test_ceo_benchmark.py` (19), `tests/test_ceo_run_evidence.py` (24).
- No T-207, T-209, T-211 file, `schema/multi_role_enums.py`, `schema/enums.py`, `schema/project.py`, `browser/session.py`, `bench.py`, `acceptance_comparison.py` or `oracle_registry.py` touched (`git diff --name-only cff3ffe6..d6fb0ed8` lists only the 7 files above).

## Judgement calls for the checker
1. **Ownership.** OG-BENCH names only `stages/ceo_benchmark.py`. The design rule (every shape a Pydantic model in `schema/`, file <= 300) needed three new schema files and a second stage file `stages/ceo_run_evidence.py` (MP31). All five are new, `ceo_*`-named and disjoint from every other group. CORE-REQUEST: none.
2. **No second scorer, how.** bench has no per-priority, per-technique or adjudicated-only view, so the stage builds one `BenchCorpus` + `BenchTrial` per population (all, each priority, each technique, without seeded-data findings) and reads `detection_rate` / `false_positive_rate` from `BenchTrial.score`. Unadjudicated findings are left out of the FP trial, so bench's "false positives / reported" is FP over adjudicated findings (matched ones are the true positives). Priority maps to bench severity P0->S1, P1->S2, P2->S3 only to satisfy the corpus schema; severity-weighted recall is not reported.
3. **MP30 ordering is bench's own gate.** When the list's sha256 or commit time does not precede the run start, the trial's `ordering` is `unknown` and `BenchTrial.score` itself answers `ordering not recorded`; the scorecard prints `unavailable (ordering not recorded)` for overall, each priority, seeded-excluded and each ran technique. `ordering` also carries a fixed-vocabulary reason (`not recorded`, `list hash differs from the recorded one`, `list committed after run start`). Equal timestamps fail (strictly before). The commit time is an input (`OrderingRecord.committed_at`, taken by the caller from `git log` of the commit that recorded the hash); no git call here.
4. **Derived scenario = the matched atomic finding leaves recall entirely** (numerator and denominator): 6 items, 3 matches, one from a derived scenario gives 2/5, and `derived_excluded` counts it. The alternative (numerator only) would penalise the run for a contaminated match; the checker may choose it, the change is one line in `_derived_ids` / `build_scorecard`. A derived finding still counts as a matched (non-FP) finding in the FP rate.
5. **Technique state.** A technique reads `ran` only if EVERY owner ran (an oracle in `ran` state, or the framework owners T-210/T-211 with `runner_ran=True`); otherwise `not run` with no recall value, including `not built`, `not run` and `errored` owners. A ran technique with no atomic findings reads `unavailable (no eligible ground truth)`, never 0. `privilege` and `credential_policy` oracles own no CEO technique, so they appear only in the oracle table.
6. **One-to-one matching** is enforced on the input (`CeoRunInput` refuses an atomic id matched twice or unknown); who matches (the matcher) is upstream, the human-adjudicated step, not code here.
7. **MP31 scope.** `run_evidence_problems` checks: exactly 8 onboarded accounts, one login outcome each on its own platform, every declared platform covered, a RunApproval that exists, belongs to the project, is intact, signature verifies (a missing key is a problem, not acceptance) and was unexpired at run start, `headed`, and every `OracleName` in the table once. It judges completeness, not that logins succeeded (a recorded `failed` login is complete evidence).
8. `autotester doctor` reports 2 violations, both stale-generated (docs/MAP.md, docs/SNAPSHOT.md); not hand-edited, the merge-queue owner regenerates.

## Gates (MP31 live / MP35 are NOT built to pass now)
credential-gate: 8 role accounts + IMAP host (Umesh)
HUMAN_GATE: MP31 live run needs signed RunApproval
Also open for MP35 (contract text): the atomic split of the CEO list confirmed by Umesh with its sha256 pinned before the run, FP adjudication, the CEO's active hours (wall time stays `unknown` until then). MP31 stays pending (live leg = MP35); T-218 is not closed while MP35 is open.

## Verification scope
Policy-Version: proportional-verification/2026-10-18.15
Tier: L (live acceptance is a production run; the leg built here is fixture scoring only)
Round: 5 src files + 2 test files, 3 criteria (+MPI1-MPI6 held), est 60 min
Owners: OG-BENCH
Base / checked state: cff3ffe6 / d6fb0ed8, clean tree
Gate answers: none apply to the fixture leg (D-104 opens the build; the live leg is the credential and human gates above).
Affected tests / full-suite trigger: none outside the new files (no existing module edited); the builder ran no full suite.
Tests[MP29]: tests/test_ceo_benchmark.py - the 6-item / 3-priority list with 3 matches, 1 adjudicated FP and 1 unadjudicated gives recall 3/6 overall and 1/1, 1/3, 1/2 per priority (P0 first) and FP 1/4; the same numbers equal `bench.scorecard` on a hand-built corpus/trial; `bench.scorecard` monkeypatched to fixed numbers is what the scorecard reports; the stage has no division and `stages/` has no extra `ceo_*` scorer module; unadjudicated-only gives `unavailable (no adjudicated findings)`; recall excluding seeded data 3/5; 14 technique lines with owner units, owner not built / not run / errored / runner absent reads `not run` with no value, a ran technique with zero found is a real 0; wall time `unknown` until given; one-to-one and unknown-id input refused. The same file prints the per-oracle ran / not built / not run table from `oracle_registry.oracle_statuses` (13 oracles).
Tests[MP30]: tests/test_ceo_benchmark.py - fixture 1 (hash + commit time precede run start): recall is the number 0.5; fixture 2 (list committed after, or at, run start / hash differs / no record): recall `unavailable (ordering not recorded)` for every population; fixture 3 (scenario labelled derived-from-finding): 2/5 and `derived_excluded` 1, and unlabelled it stays 3/6; the committed scorecard (JSON + printed) holds the sha256 and only fixed-vocabulary strings, and none of the atomic or run finding ids.
Tests[MP31]: tests/test_ceo_run_evidence.py - complete synthetic evidence has no problems; a missing role account, fewer than 8 onboarded, a declared platform without a login outcome, a wrong or undeclared platform, a missing / unsigned / edited / expired / other-project RunApproval, a missing signing key, a non-headed run, and each of the 13 oracles missing from the table (parametrised) or listed twice all fail; evidence holds ids and outcomes only.
Tests[MPI6]: tests/test_ceo_benchmark.py (the MP29/MP30 tests above: one-to-one matching, unadjudicated neither TP nor FP, per-technique `not run`, only counts and the hash committed).
Falsification[MP29]: copy-mutants in scratchpad t218-ceo-bench/m (PYTHONPATH to the copy): FP counts unadjudicated (`if True`): red 4 (`..._fp_over_adjudicated_only`, `..._equal_bench_output...`, `..._unadjudicated_is_neither_tp_nor_fp`, `test_print_scorecard...`); per-priority ignores priority: red 3; own division instead of the scorer: red 7 (`..._read_from_the_bench_scorer`, `..._no_second_scorer_in_the_stage`, ...); technique always `ran`: red `..._owner_did_not_run_reads_not_run_never_zero`. Control copy 19 + 24 passed.
Falsification[MP30]: copy-mutants: missing ordering record read as recorded: red `...[None-not recorded]`; commit-after-start allowed: red 2 (`...[ordering0-...]`, `...[ordering1-...]`); derived exclusion removed (`derived = set()`): red `test_mp30_a_derived_from_finding_scenario_is_excluded_from_recall`.
Falsification[MP31]: copy-mutants: headed check removed: red `test_mp31_the_run_must_be_headed`; oracle-coverage check removed: red 13 (`..._oracle_missing_from_the_table_fails[*]`); signature check removed: red 2; platform-coverage check removed: red `..._declared_platform_without_a_login_outcome_fails`.
Pre-check[MP29]: d6fb0ed8 uv run --directory <worktree> pytest tests/test_ceo_benchmark.py -> 19 passed t=1 blobs=tests/test_ceo_benchmark.py:5171305
Pre-check[MP30]: d6fb0ed8 uv run --directory <worktree> pytest tests/test_ceo_benchmark.py -> 19 passed t=1 blobs=tests/test_ceo_benchmark.py:5171305
Pre-check[MP31]: d6fb0ed8 uv run --directory <worktree> pytest tests/test_ceo_run_evidence.py -> 24 passed t=1 blobs=tests/test_ceo_run_evidence.py:9388d38
Lint: d6fb0ed8 `uv run ruff check src tests scripts` -> All checks passed; `uv run autotester doctor` -> 2 violations, both stale-generated (judgement call 8).
mutant-cap-raise: 11 copy-mutants, one per behaviour clause of three criteria (each under a second, no suite run); cap is 10
Metrics: start=unavailable end=unavailable wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=1 mutations=11 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-18.15 lane=normal check_s=unavailable mutants=11 defects_unit=0 defects_6c=0 tests=43 tests_min=1

## How to verify (commands + expected)
- `uv run pytest tests/test_ceo_benchmark.py tests/test_ceo_run_evidence.py` -> expected: 43 passed.
- `git diff --name-only cff3ffe6..d6fb0ed8` -> expected: the 7 files listed, nothing else.

## Capability coverage (each new claim -> its isolating falsification)
| Criterion | capability | the check that covers it | the falsifying edit | observed |
|---|---|---|---|---|
| MP29 | recall / FP read from `BenchTrial.score`, FP over adjudicated only | tests/test_ceo_benchmark.py::test_mp29_numbers_equal_bench_output_on_the_same_input, ::test_mp29_unadjudicated_is_neither_tp_nor_fp | count unadjudicated as FP; replace scorer by own division | green; red 4 / red 7 |
| MP30 | ordering gate and derived-scenario exclusion | tests/test_ceo_benchmark.py::test_mp30_without_the_recorded_ordering_recall_is_unavailable, ::test_mp30_a_derived_from_finding_scenario_is_excluded_from_recall | treat missing ordering as recorded; drop the derived set | green; red on each |
| MP31 | 8 roles, platforms, signed approval, headed, oracle table complete | tests/test_ceo_run_evidence.py | drop the headed / signature / oracle-coverage / platform-coverage check | green; red on each |

## Live browser evidence
Not UI-touching - no surface changed: only schema and stage modules plus tests; no route, template or static asset.

## Status: ready-for-check
