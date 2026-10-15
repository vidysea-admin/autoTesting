# Provider physical attempt budgets and honest usage

Status: checked-PASS
Fix cycle: 1
Base SHA: 40299c04 (immutable full SHA and candidate SHA in linked packet)
Root: C:/Users/product/.codex/worktrees/provider-attempts/autoTesting
Packet: .work/provider-attempts/packet.json (written after this commit resolves candidate SHA)
Risk tier: high_risk — shared provider/schema boundaries and safe failure accounting.

## Authorized scope and behavior
D-099 / langchain-fallback OC2; providers-litellm LL5/LL6/LL7; core C1-C7, C9, C12;
run-trace RT4-RT7. LiteLLM physical requests reserve from every enclosing ContextVar
budget before transport, including JSON repair and model-chain fallback. Nested caps
are checked atomically before any receipt is appended. A typed AttemptBudgetExhausted
short-circuits fallback and differs from model unavailability's ProviderError.

`with attempt_budget(max_calls, wall_clock_s=None) as budget:` yields typed safe
attempt receipts and used count. Monotonic remaining time limits SDK timeout to at
most 120s; the chain has a finite 2*tiers request and 240*tiers second scope. This is
an SDK timeout request, not a hard cancellation guarantee. Thread callers must use
copy_context to propagate the budget; process IPC propagation is a follow-on boundary.

Failed requests count and preserve unknown token measurements as null, including
aggregation after failed tiers. Trace spans safely record failed status and unknown
cost without vendor exception/prompt payloads. The UI displays unknown cost; the video
review cost cap explicitly refuses unverifiable spend. Isolated usage merge preserves
failed call counts and null tokens. Explicit legacy transports and vision methods are
outside this bounded implementation, so this is not OC2-all-provider completion.

New modules: providers/attempts.py owns request reservations; schema/provider_attempt.py
owns the receipt shape. No duplicated meter or consent RunBudget: this cap measures
physical model requests, while existing RunBudget measures target actions/probes and
Meter measures estimated lead-agent tokens.

## Checks and source identity
qa/evidence/provider-attempts/checks.json contains exact commands/exits, complete output
hashes and contemporaneous source fingerprints. Focused tests: **86 passed**; scoped
lint: exit 0. Doctor: exit 1 solely stale-generated MAP and SNAPSHOT, with no source
rule violation; integration owner regenerates these shared artifacts. Full integration
pytest/ruff/doctor remain required on the exact combined candidate. No browser/live API.

qa/evidence/provider-attempts/environment.json pins interpreter, lock and dependency
identity. preflight.log pins cache-free proof-copy imports/temp writability. The initial
root preflight was executed before tests (tool output 2026-10-15T08:06:11Z); it was not
saved as a file, so it is not offered as a reusable persisted receipt.
candidate-source-binding.json binds every changed runtime/test file to the restored
proof copy. No runtime edits occurred after the proof baseline.

## Per-guard falsification
qa/evidence/provider-attempts/mutations.json is the exact semantic mutation spec;
receipts.json contains each asserted green baseline/red/restored command, source
hashes before/after, environment/lock identity and named pytest failure. All 14 red
phases exit 1, name their defending test, and restore green. Guards: count cap;
elapsed deadline; remaining-time timeout; enclosing cap propagation; context restoration;
integer/nonnegative max_calls; finite/nonnegative wall clock; failed request accounting;
unknown-success tokens; unknown aggregate tokens; unknown spend refusal; unknown cost
UI; isolated failed-call merge; extra-forbid receipt shape. Each added test has an
attributed mutation. Test fixtures copy includes tests/tests_mutation_fixtures.py and
excludes every __pycache__. Original setup failed on a singular filename typo before
baseline; fresh proof-copy-2 fixed it and supplies all claimed evidence.

## Usage and remaining gates
Actual total maker active seconds, tokens and cost: unknown (null), never inferred.
Command durations are measured in checks.json/receipts.json and are a lower-bound
subset, not a fabricated total. Checker ratio remains unverified; parent dispatches a
fresh independent checker under the bounded bootstrap policy. No self-PASS, push or
integration certification. No contracts, enforcement, credentials or shared generated
docs changed.
