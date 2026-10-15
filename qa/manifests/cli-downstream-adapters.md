# Manifest — CLI downstream adapters

Unit: D-099 / OR7 downstream stage adapters and caller factory seam
Fix cycle: 1
Status: checked-PASS
Branch: codex/cli-downstream
Source candidate: 030560cf033782f50fb54c5c034b4f0fb3e0bb93
Integration base: 00c9e13ded3cba6cfe57bd9d0c422f5154ed6e09
Checker reply: qa/verdicts/cli-downstream-adapters.md (not yet issued)

## Scope

EXPAND consumes the exact MODEL reference and snapshots complete case/model content under
run/pipeline. It preserves canonical APPROVED bytes and enforces current plus captured
pre-MODEL NEEDS_EDIT. The generation callback records admission after existing validation,
prompt and secret gates, immediately before the Provider call.

EXECUTE uses existing approval/declaration/provider gates, entry-profile isolation, RunBudget,
BrowserRecovery and extracted observation/replay/video helpers. Raw observations persist
independently of GRADE. An interrupted execution preserves saved observations, marks remaining
cases NOT_RUN and opens zero additional sessions; retrying possible writes requires a new run.
Approval refusal constructs zero sessions and creates no registered target Run/raw/verdict,
while exact existing offline artifacts remain intact.

GRADE preserves saved verdicts and closes uncertain remaining judgments INCONCLUSIVE on resume
without another provider call. Original safe failure evidence is retained. EXPAND similarly
refuses uncertain same-run generation. These are conservative interruption semantics, not a
claim of complete durable whole-run physical usage accounting.

REPORT uses frozen metadata, same run_id, existing bug/failure-bundle wiring and HTML/XLSX.
The entire generated set is secret-checked before its first case write; raw observations and
adapter-owned verdicts are checked before persistence through the canonical matcher.

## Owned files

- src/autotester/stages/orchestrate_downstream.py, orchestrate_execute.py, expand.py
- src/autotester/stages/run_case_pipeline.py, report_export.py
- src/autotester/browser/profiles.py; src/autotester/ui/run_execution.py
- src/autotester/schema/run_state.py; src/autotester/core/paths.py
- tests/downstream_fixture.py; tests/test_orchestrate_downstream.py
- tests/test_orchestrate_downstream_privacy.py; tests/test_run_case_pipeline.py

Shared CLI/runners/UI teaching registration is a separate caller unit. Construct
downstream_runners(project, store, ...) before MODEL; pass its exact returned artifact to
EXPAND. This unit does not claim a completed production CLI entrypoint.

## Bound maker evidence

qa/evidence/cli-downstream/cycle2/readiness.json validates 1021 copied src/tests/scripts/config
entries, candidate/base, physical argv, Python/import/dependencies/lock/environment,
harness/spec/selection, output hashes, named failures and exact byte restoration.

Shared GREEN: 21 nodes (13 downstream offline tests, eight exact existing consumers).
11 selected risks each have an attributable RED and exact-restored GREEN: 23 pytest receipts.
Full 15-entry mutation spec remains unchanged; selection.json explicitly excludes four rows
and binds their direct positive/consumer evidence and risk rationale. No claim of 15 executions.
Bound scoped Ruff and file/function caps pass. Full pytest, full Ruff and doctor are parent
combined-integration gates; they were not run or counted as passes here.

Historical 20-node source evidence and its supersession note remain intact. One exact checked-
base rubric test failure is preserved. Its fixture wrote non-PNG bytes in a different run
directory while real screenshot privacy now caps PASS. The narrow repair uses a valid PNG and
an explicit controlled grading collaborator that checks exact rubric/run/case/provider lineage.
It preserves PASS/default-rubric persistence intent without asserting a real screenshot PASS or
changing production image sanitation. That broader visual-evidence policy is a separate unit.

## Independent review boundary

Only a fresh checker may PASS. Apply effective OR7 + TF1/TF2: TF1 excludes direct CLI scripts;
TF2 ordering remains behaviorally tested. Select minimum relevant independent checks and a
contract-derived failure probe after independently validating packet provenance. No browser,
live target, key read, inference, install or download is needed for this adapter review.

Maker actual active time/tokens/cost are null. 176.952s is the sum of recorded pytest subprocess
wall durations, not maker active usage. Reviewer should initialize its measured/debit ledger
with review_budget.py; default finite bootstrap 180s/6000 tokens can protect the skill's
30s/800-token completion reserve. These are proposed allocations, never fabricated actuals.
The <=10% efficiency ratio is unavailable while maker/reviewer actual telemetry is unknown.
