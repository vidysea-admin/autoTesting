# Manifest — T136 bench foundation

## Resumed whole-comparison design — 2026-10-05

User asked to proceed toward the full goal; specific test/browser/new-file gates
remain binding. Read-only /root/t136_complete_comparison_plan produced concrete
unsaved text previews, not source edits or implementation approval. Production
capacity: schema/bench155->240 (60lines reserved for validators), ProjectStore
300->300, ProjectPaths287->291. Stages97 and tests298 were measured but a complete
new stage/test patch was NOT constructed. Do not delete tests to fit.

Proposed existing schema shapes: BenchMaterial, BenchBinding, BenchScore,
BenchSide, BenchBugRow, BenchDecision, BenchComparison. Optional legacy-compatible
BenchTrial.binding records project/run/app/build, build-source ID/full digest,
material Source IDs/full digests and evidence of participant receipt/use.
Complete acceptance requires populated validated bindings. Explicit autotester
and human slots, distinct trial IDs/roles/kinds and effective labels; never a
label-keyed dictionary as proof that both sides survived. Preserve all findings
and independent/prompted/unknown provenance, truth/per-bug/unmatched rows, and
exact BenchTrial.score output with unavailable reasons. Validate ordering,
source identity and re-derived scores. External Umesh decision binds the payload
digest excluding the decision and its own digest; no computed winner.

Source ownership: ProjectStore.load_run checks run/project, list_sources checks
material source IDs and available bytes/text; saved results/Verdicts plus cited
evidence establish real machine findings, not supplied objects alone. Only
BenchCorpus.build_ref currently identifies a target build, with no independent
deployed-build record found. Run.git_sha MUST NOT fill that gap. A separately
supplied existing Source(text/doc) row may record target/build/session/material
pack and supporting evidence; label a declaration as a declaration, never treat
its digest as truth or manufacture a human receipt. Actual external input is
still missing; no source row was created.

Concrete persistence preview: shorten existing ProjectStore class docstring to
three lines retaining lazy-cache/fresh-list descriptions; add existing-pattern
save_bench_comparison/load_bench_comparison/load_bench_trial. Add canonical
ProjectPaths.bench_comparison -> bench/comparison.json. All anchors matched once
in unsaved previews. Full stage validators and preservation/count proof for the
298-line test file remain engineering work. New K9 script exact consent remains
pending. Foundation pinned .2 remains unchanged; this future whole-comparison
design is not a retroactive policy switch or PASS. Reviewer verdict WARNING.

Follow-on test-capacity measurement, same reviewer: preserving unsaved preview
tests/test_bench298->291,62assertions retained with zero textual assertion
differences,longest top-level function21lines; only9lines remain. Runtime
equivalence is unverified and test-node/count changes would require evidence
mapping; no test was edited. Complete K9 checks cannot responsibly fit that
headroom. tests/test_store.py224 has76lines for persistence/lookup checks, not
scoring/provenance/CLI tests merely moved to evade a cap. Exact additional
boundary proposed: tests/test_bench_comparison.py, new-file authorization required
alongside scripts/check_acceptance_comparison.py. Preserve original bench tests;
the consolidation preview does not authorize an in-flight .2 test edit. No source
or test runtime/import/write occurred in the measurement.

Contract: qa/contracts/bench.md K3/K5/K6/K7/K8; D-052 fixture provenance and AT-653.
Goal task: T-136 (remains pending; this is not real-product acceptance).
Date: 2026-10-05. Fix cycle: 0 of max3. Status: implementation-in-progress.
Policy-Version: proportional-verification/2026-10-05.2.
Tier: L — critical scoring/schema and integrity/refusal guards.
Base: bd2fe8f4d9a9fa87552e8a3999eb27cb52f8addf.
Isolation: C:/Users/Lenovo/.codex/worktrees/t136-bench-provenance/autoTesting.
Managed creation operation a9c156b4-d959-4ebb-adb3-c0d852ad00c1 completed.
Root dirty files are not copied, reset, staged or overwritten.

## Preimplementation approval

Fresh reviewer initially BLOCKed missing per-truth provenance, then explicitly
approved corrected offline implementation. Root read complete persisted receipt:
qa/verdicts/t136-bench-foundation-plan-review.md, SHA256
07DEDE1583D6758ABE5BDD82F1156A9A1F9F521F4AC792D5FB2731421200DA6C.
Approval is not a completion verdict. Exact interpretations in receipt govern.

## Action / input / output / verify

1. Maker edits existing schema/bench.py::SeededBug/Finding/BenchCorpus/BenchTrial/score
   (original lines15/27/38/48/58): typed persisted truth/finding provenance,
   explicit fixture/live mode, human kind, ordering, nullable measurements and
   integrity refusals. Unknown legacy input remains unknown, never independent.
   All arithmetic stays in score; detection/recall disclose same eligible truth.
2. Maker edits stages/bench.py::run_autotester_trial/oracle_human_trial/scorecard/
   seeded_bug (37/51/76/85): explicit provenance only, synthetic oracle remains
   synthetic, scorecard verbatim delegation, explicit fixture bug stamping.
3. Maker edits scripts/bench_trial.py::main existing corpus/AI construction
   (corpus149): explicit fixture mode and fixture ordering; old zero-time prose
   corrected. Native/paid script is not executed.
4. Separate fresh checker authors only existing tests/test_bench.py: independent
   unequal-severity truth populations, unknown provenance/order, prompted filtering,
   nullable time/FP, integrity refusals, saved JSON and exact score delegation.
   Maker never edits tests. No new production/schema/test files are authorized.
5. After actual diffs: independent senior engineering review and source-bound
   isolated scoped checks/failing-first proof, with exact commands and receipts.
   Mandatory L full suite and feature-boundary sweep remain required; absent
   permission/containment yields verification-incomplete, never PASS.

## Gates / execution bounds

Policy check before each of both current dispatches: exit0 targets4 drift0.
Full-suite/native-browser gate qa/gates/t125-fullsuite-browser-egress.md remains
unanswered, not bypassed. Current dispatch permits edits and static offline
diagnostics only: no pytest/native browser, package installation/network, model
call, real account, .env read, release or production write.
Maker budget45min checkpoint; oracle-author budget25min. Only owned/recorded
PIDs may be terminated. No suite lock is held because no suite is started.

## Acceptance boundaries

Ground-truth rows carry fixture-seeded/independent-human/prompted-human/unknown.
Live independent recall denominator excludes prompted truth; human numerator
excludes prompted findings. Unknown relevant provenance/order and empty eligible
truth produce unavailable, not zero. AI-read-human-first cannot claim independent
machine recall. FP includes every adjudicated report; unknown matched IDs are
unmatched. Duration omission differs from measured zero. Duplicate truth, corpus
mismatch, inconsistent modes/kinds and invalid duration fail closed.

K2 real execute/grade/non-mock-judge evidence and K9 complete comparison command,
artifact, real human findings and Umesh verdict remain outstanding for T136.
No fixture foundation can close those criteria or the overall goal.

## Actual evidence

Implementation worker and independent oracle author dispatched in fresh contexts.
Managed worktree now contains actual three-file production edits and independently
authored existing test-file strengthening; no runtime check has been executed.
Oracle author retried the same scoped apply_patch after an approval-service
capacity error; retry succeeded, with no shell bypass or model override.
Senior engineering review dispatched fresh/read-only; final review waits for
the producer and oracle author to freeze exact file hashes. Transient API/oracle
alignment is prehandoff, not a completed checker cycle. Root has forbidden an
unapproved broad native-runner helper refactor for preexisting script line length.
No runtime outputs, mutation kills, implementation PASS, commit or push yet.
Maker source freeze, independently matched by root Get-FileHash:
schema/bench.py E26D7CF40913AD758843E37A8577FEED0E742CDF1C07904C5F54F21D9D825ACA;
stages/bench.py D9C61A7E29045D51E781E567FE617813850D5E3060043CC8EB645671DFF128F5;
scripts/bench_trial.py 4F938379D64C3605920D9D824DDDE686C590AFE648B1C2551690013A8DFD5DE7.
Maker reports scoped Ruff clean, compile-only three files clean, diff --check clean;
these are builder receipts, not independently rerun acceptance evidence.
Schema155/maxfunction39; stages97/max21. Scripts numeric caps exempt by C2/D-048.
Checker author reports test freeze19776FA5500EEB0A5D898780AEABC7E910ACF76294A284A442CB351925715E18,
295lines/max21,23testfunctions,32 expected expanded nodes (not measured by pytest).
Senior reviewer received all four frozen identities; runtime verification pending.
Senior static review: Warning solely on checker test's unknown-human-provenance
zero expectation; no source correctness finding exceeded80% confidence.
Checker author corrected that oracle to None plus unavailable reason; new test
SHA D30E96955DAC237FF628AF5F8E159A77C7846B37729561C489D4F2130A4300C5,
root directly matched. Syntax298lines/max21; runtime counts remain unmeasured.
Fresh bounded baseline checker dispatched: exact test_bench.py only, real
candidate package imports, no synthetic package bypass, existing Python runtime,
no conftest/plugin autoload/cache/bytecode, guards against socket/model/native
subprocess activity and .env access. One <=180s baseline invocation; no mutations
or repeats authorized yet. Full suite/browser and formal PASS remain gated.
Bounded checker first baseline terminal: PID50824, process exit1, guard receipt
elapsed0.50855s. Windows Colorama imported ctypes and kernel32.GetLastError;
overbroad ctypes.dlopen audit denial stopped setup before collection. Zero nodes,
no XML, one guard denial. INCONCLUSIVE instrument setup, not product FAIL.
Receipt: qa/verdicts/t136-bench-foundation-scoped-cycle0.md. No automatic retry,
mutation or source/test change follows; same checker now diagnoses a bounded
console-only correction proposal for fresh review before execution.
Metrics: start=unrecorded end=pending suite_runs=0 repeat_runs=0 mutations=0 cycle=0 tokens=unavailable

## Live browser evidence

### Immediate downstream acceptance gap — K9

Independent whole-feature plan review completed by
`/root/t136_complete_comparison_plan` (fresh senior-software-engineer,
read-only). Verdict WARNING, not implementation approval or feature PASS.
Reviewer independently established three blockers: label-keyed scorecard can
overwrite a participant; BenchTrial's corpus_id alone does not bind a trial to
the named target build/material/run; ProjectStore300/paths287/tests298 require
a concrete capacity-preserving edit plan before additions.

Required correction to the proposal: explicit AutoTester/human slots with
distinct trial IDs; final T136 requires autotester plus human_live, never an
oracle substitute. Recompute each slot via its source trial.score and require
exact persisted equality; verify truth/provenance/per-bug and unmatched-finding
coverage, ordering consistency and source content identities. Separate reported
attribution from earned independent recall credit. Missing order/time/zero-report
metrics remain unavailable, not flattering defaults. A human-winning complete
comparison must pass the completeness validator just as an AI-winning one does.

Unresolved evidence design: Run.git_sha is runner code, not the target app build.
Do not manufacture an app build attestation, material receipt, live non-mock
judge provenance, human record or Umesh signature. The external decision must
address the immutable comparison content identity; absent/stale decision fails
final completeness. The read-only CLI must not call ensure/save/load secrets.
These requirements refine the next implementation plan, with source/new-file
and runtime gates retained. No implementation was dispatched by this review.

Root inspected the ACTIVE bench contract and canonical T136 done_check.
Both name `scripts/check_acceptance_comparison.py <slug>`; no such script
or persisted typed comparison artifact was found in the inspected bench
schema/stage/store/path/script surfaces. Existing `bench_trial.py` runs a
fixture browser/model trial and prints an oracle scorecard. It is not the
Pathlynks human-comparison completeness validator and must not stand in for it.

Proposed next source scope (NOT authorized or implemented here): extend the
existing schema/bench.py and stages/bench.py to define/assemble one typed
comparison from persisted corpus and selected trial IDs; use ProjectStore's
existing bench persistence facade and the one ProjectPaths path owner. Scores
must be taken verbatim from each trial.score(corpus), with explicit unavailable
reasons and denominator/provenance metadata. A comparison binds app/build,
material refs, run ID and both selected trial IDs, includes per-bug found-by
rows plus unmatched findings, and records Umesh's separately supplied decision
without calculating a winner. No human evidence or signature is synthesized.

The exact missing entrypoint is a required new file, not a duplicate scorer:
`scripts/check_acceptance_comparison.py`. It should load and validate the
comparison and bound source artifacts, refuse incomplete/mismatched records,
and exit nonzero without modifying the product or making a model/browser call.
New-file authorization is still required under the user's edit-in-place rule;
the earlier classifier prompt approval does not cover this path. After that
authorization, obtain fresh independent plan approval before implementation.
Tests belong in existing tests/test_bench.py; retain all existing oracles and
resolve its 298-line headroom without creating an unapproved test module.

### Root compile-only readback — 2026-10-05

Using the existing root `.venv/Scripts/python.exe -B`, root parsed and compiled
the isolated candidate's schema/bench.py, stages/bench.py, bench_trial.py and
test_bench.py from their actual file bytes, without importing product code.
Exit 0: syntax compilation succeeded for all four. Measured line/function
sizes respectively: 155/39, 97/21, 188/77, 298/21; 23 test functions.
The script's 77-line function is not a new helper refactor and remains subject
to the existing scripts exemption, not an invented general cap waiver.
Tests executed: 0. This receipt establishes syntax/headroom only, not runtime
behavior, full-suite completion, independent acceptance or a task PASS.
The stopped baseline's collection/setup failure remains unresolved; a drafted
guard patch is not proof that collection succeeds. No browser, model, network,
credential access, mutation campaign or baseline retry was performed here.

At this safe boundary the current maker protocol was actually reread and
`tick.mjs --policy-check` returned policy2026-10-05.3, targets2, drift0.
This is a current routing check, not a retrospective policy relabel of this
in-flight .2 feature or evidence. No new intermediate checker was dispatched.
Whole T136 remains BUILDING: real parallel human findings, approved product
run/comparison and required acceptance evidence are still absent.

No UI file is in the proposed scope. Native/paid benchmark runner is edited for
explicit fixture metadata only, not run. Product acceptance browser evidence is
outstanding; no absence of UI changes waives the overall live-validation goal.
