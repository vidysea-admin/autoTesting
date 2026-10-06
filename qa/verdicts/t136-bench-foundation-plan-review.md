# T136 bench foundation — independent preimplementation review

Status: corrected-plan APPROVE; not implementation PASS
Reviewer: /root/t136_foundation_plan_checker
Date: 2026-10-05
Policy: proportional-verification/2026-10-05.2
Baseline: bd2fe8f4d9a9fa87552e8a3999eb27cb52f8addf
Scope tier: L (critical scoring and new validation/refusal guards)

## Initial review: BLOCK

The original plan marked human findings independent/prompted but lacked per-truth provenance in the corpus. `BenchTrial.score(corpus)` receives no human trial and could not derive the independent-human denominator. Legacy inputs must not be inferred independent. The existing default-time test also contradicts K8 and needs checker-owned strengthening, not maker editing.

## Corrected plan: APPROVE for offline implementation

Existing-file scope:

- `src/autotester/schema/bench.py`: SeededBug at line 15 adds typed fixture_seeded/human_independent/human_prompted/unknown provenance; Finding at line 27 adds independent/prompted/unknown; BenchCorpus at line 38 adds fixture/human_confirmed/unknown mode; BenchTrial at line 48 adds typed participant kind, ordering and nullable duration. Defaults preserve unknown provenance for legacy input.
- `BenchTrial.score` at line 58 remains the sole arithmetic authority. Explicit fixture mode uses seeded truth; human-confirmed mode uses independent human truth. Human recall numerator excludes prompted findings. Missing provenance/order, empty eligible truth, absent timing and zero reported findings produce nullable measurements with adjacent unavailable reasons. FP population is every adjudicated report; unknown matched IDs consistently count unmatched. Measured zero timing remains numeric.
- Validation refuses mismatched corpus IDs, duplicate truth IDs, inconsistent mode/provenance, negative or non-finite duration and impossible participant-kind combinations.
- `src/autotester/stages/bench.py`: run_autotester_trial at line 37 accepts explicit provenance without inference; oracle_human_trial at line 51 stamps typed synthetic fixture/oracle and rejects non-fixture input, with default time None; scorecard at line 76 delegates exactly to trial.score; seeded_bug at line 85 stamps fixture provenance.
- `scripts/bench_trial.py`: corpus construction at line 149 explicitly identifies fixture mode. The native/paid runner is not executed under this plan.
- Checker-owned `tests/test_bench.py`: fixture helper stamps fixture provenance; the line 77 default-time assertion is strengthened to None under K8; named acceptance and falsification cases cover the criteria below. Maker leaves tests read-only.

## Required implementation interpretation

- Unknown ordering makes recall unavailable.
- Human-read-AI-first may score only independently marked, confirmed truth; prompted truth cannot establish machine recall completeness.
- AI-read-human-first makes machine independent-comparison recall unavailable: it saw its benchmark answers. This ordering is not independent parallel evidence.
- Finding provenance is required for the human numerator, not a fictitious human label on mechanically generated AutoTester findings.
- Known prompted rows may be excluded; unknown truth provenance prevents claiming a complete eligible denominator.
- Detection rate uses and discloses the same declared eligible truth population as recall, not silently every corpus row.
- Oracle timing never changes a synthetic oracle into a live human.
- Stable detected/seeded keys describe actual scored counts, with denominator metadata. No fabricated zero fraction replaces unavailable input.
- Scorecard returns trial.score values verbatim; no reporting-layer arithmetic duplication.

## Independent acceptance and falsification

- K1: explicit fixture provenance and real seeded IDs; reject duplicates and inconsistent truth records.
- K2: mechanical verdict-to-finding conversion is within foundation scope; real execute/grade/non-mock-judge trial remains outstanding.
- K3: spy score delegation and assert exact output equality; removing delegation must fail.
- K4/K6: saved JSON distinguishes AutoTester, live human and oracle; conflicting kinds fail validation; label alone is insufficient.
- K5: existing ProjectStore round-trip preserves every provenance field and null measurement.
- K7: unequal-severity independent/prompted mixed fixture yields independently derived fractions; deleting each provenance filter must fail its nominated assertion.
- K8: missing ordering/timing, zero reports and empty eligible truth each report unavailable; replacing null with zero must fail. Measured zero timing is distinguishable.
- K9: deferred and not satisfied by the foundation; no absent command/artifact or human verdict may be implied complete.

## Completion remains unproven

Offline build is approved while mandatory full-suite/browser execution is gated. Completion remains verification-incomplete and requires BLOCKED-ESCALATE when mandatory checks cannot run; scoped green tests do not waive requirements.

Remaining mandatory checks include L-tier full-suite builder/checker runs on the bound tree, every introduced guard's independently attributed failing-first falsification with green baseline and restoration, lint, doctor caps, independent postimplementation review and feature-boundary Mode B sweep. Modules must remain <=300 lines and functions <=50 lines; use helpers inside these existing files where needed.

No source/test edit, new production/test file, contract weakening, credential access, package install, model call or native browser execution was performed by this review. Root dirty changes must be preserved; implementation must isolate its scope.

T136 stays pending: real comparison data, K2 live pipeline evidence, K9 comparison command/artifact and Umesh's signed verdict remain outstanding. This is plan approval, never product PASS.
