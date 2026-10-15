# Manifest — acceptance-baselines

Status: checked-PASS
Fix cycle: 2
Unit: T-169 isolated input-only baseline preparation (does not close T-169/T-206/T-136)
Base SHA: bd2b465ff8cf2b67f6aa162068c77d3f82f2499c
Code/test SHA: 35624de61e94b6b94286b0fe679141566892304d
Production-code SHA: 35624de61e94b6b94286b0fe679141566892304d
Prior FAIL SHA: 93d9ad143937fbf4b5353441da4a2a0e930e5259
Branch: codex/acceptance-baselines
Root: C:/Users/product/Desktop/autoTesting/.work/codex-acceptance-baselines

## Cycle 2 containment repair

Cycle 1 remains FAIL, preserved at the Prior FAIL SHA and in
`qa/evidence/acceptance-baselines/cycle2/cycle1-verdict.git.md`; the working-byte verdict and
previous manifest are also retained. Its actual source-project junction reproducer and success
receipt are under `checker-cycle1/`. This is the bounded fix of that linked canonical verdict
under `qa/loop.md` Record's on-FAIL mechanism; no issue ID was invented and no contract changed.

The source project directory and its resolved config must both stay under the resolved supplied
source root, before reading config bytes or creating outputs. The validated resolved config path
is then read. Explicit approved teaching files retain their independent input-root policy.
Only this preflight/read and two appended parameterized cases changed after the reviewed source.
Actual junction variants prove legitimate in-root aliases succeed and escaping project aliases
fail before any config read or output. Original 22 test bodies remain byte-identical.

Cycle 2 `probe.py`, `identity.json`, `inventory.json`, `mutation.json`, `commands.json` and raw logs
bind the fresh complete source copy, Git bytes, retained interpreter/import/temp preflight,
unchanged dependency/lock identity and explicit environment import-root mapping. Three focused
cases passed, removing the exact guard produced the named outside-junction RED, and exact-byte
restoration returned all three to GREEN. Scoped Ruff and AST caps/docstrings passed. Commands
total 27.328s; maker total active time/tokens/cost remain unknown. The original 13 mutations were
not rerun: `reuse.json` authenticates their prior identity and checker compatibility receipt,
proves the exact two production hunks, original test preservation and all other inventory bytes,
and explains the unaffected behavior. They remain evidence at their historical SHA, not new-SHA
executions. The historical cycle 1 evidence below is retained with that qualification.

Independent cycle 2 review remains required. Prior checker allocation/debits (170s/5,300 tokens)
remain historical across retries; actual reviewer totals and cost remain unknown. A further
bounded review allocation must be explicitly assessed by the parent, not silently reset.

## What changed

- `src/autotester/schema/acceptance_baseline.py`: explicit input-only plan and local-preparation
  receipt. Target build is recorded as declared/unverified; credentials are selected key references.
- `src/autotester/stages/acceptance_baseline.py`: source `project.json` fingerprint and approved
  input-byte checks; two fresh roots/slugs; scoped reference/provider/policy preservation through
  ProjectStore; teaching-only inputs/provenance; no inherited canonical artifacts or `.env` access.
- `scripts/prepare_acceptance_baselines.py`: thin explicit-plan entrypoint, no browser/model/API.
- `tests/test_acceptance_baseline.py`: 22 fake/temp cases including the real preparation entrypoint,
  same-build/config binding, source isolation, input provenance, new-output refusal, stale plans,
  source/input path containment, credentials exclusion and unchanged reference scope.
  Two added safety tests exercise a real temporary junction/symlink and visible partial-write
  failure with preserved original bytes and refused reuse; no automatic cleanup is claimed.
- `qa/evidence/acceptance-baselines/**`, this manifest: raw proof artifacts, usage and limits.

No contracts, enforcement, existing project files, provider routing, mixed teaching dispatch,
account records, credentials, run approvals, schedule state or goal status were changed.

## Acceptance and immediate consumers

Core C1/C2/C6: all shapes in schema, existing file-store APIs, file/function/docstring caps.
C5/C8/C9: copy selected existing scoped SecretRefs and provider settings, never credential values;
refuse unsafe URLs, widened/unscoped refs, stale input/config and unsafe output/input paths.
C7/D-100: complete bound raw-byte copies, guard-specific GREEN/RED/restored evidence and independent
checker remain required. C10: commits restricted to these unit paths on an isolated branch.
D-096/consent CN1-CN3: production flag remains true; approvals are excluded and each later new-project
production run must obtain a covering human-signed grant. This code never grants or reuses one.
Generic-acceptance GA1/GA3 and GR1 are context: this unit supplies uncontaminated local inputs only,
and does not claim a real route/browser/model run or complete either acceptance mode.

Immediate consumers are the thin preparation script and its direct temp-data tests. The rich input
caller awaits the independently checked mixed-teaching handoff; no mixed-owned file was edited.

## Historical cycle 1 evidence and remaining gates

Historical initial checks: 19 passed (1.53s), ten static formatting issues; original sandbox
preflight temp-write refusal retained, escalated retry succeeded. These unbound logs are historical,
not exact-candidate proof. First bound INIT at 2e6f70b3: complete copy/preflight, 20 passed (1.69s),
one E501 on the final wording line; AST not reached. Full raw receipts and original harness are in
`qa/evidence/acceptance-baselines/initial-init/`. A one-line wording repair produced the Code SHA.

Prior successful INIT at the Production-code SHA: full raw `src`/`tests`/`scripts` inventory equality
and exact Git blobs;
Python 3.11.16 retained interpreter, own-source import and writable temp; 20 passed (3.86s);
scoped Ruff clean and AST caps/docstrings clean (maximum function 44 lines).
`identity.json`, `inventory.json`, `commands.json`, `shared-green.log`, `scoped-lint.log` and
`scoped-shape.log` bind that result. Every command records argv, source/lock/environment identity,
log hashes and durations; no environment values are published.

The final 22-case INIT at 8d793363 passed in 1.98s, including an actual resolved Windows
junction escape refusal and injected partial-write failure preserving source bytes and refusing
unchanged partial-output reuse. Exact code/test Git bytes, complete source-copy inventory,
Python/import/temp identity, scoped Ruff and AST checks passed. Final identity, commands and logs
are under `risk-proofs/`; only the two safety tests changed after the prior successful INIT.

Guard proofs: all 13 behavioral groups complete. Every group has bound GREEN/attributable RED/
exact-byte restoration/restored GREEN, with unchanged final complete copy/source inventory.
`risk-selection.md` freezes the 20-to-13 behavioral grouping and every selected/omitted draft
mutation. `probe-riskgroups.py` produced the final `risk-proofs/mutations.json` with each exact
semantic edit and defender; prior INIT/draft artifacts remain preserved in place. Two equivalent
output variants were merged into one output-ownership proof; five redundant positive-test mutants
were not executed. No named case was dropped: executed groups cover all 22 case IDs.
`risk-proofs/proofs.json` and command/report/log receipts contain every GREEN/RED/restored result.
The harness copies all fixture helpers and retains unique retry logs. `readiness.py` re-derived
each applied-byte mutation and verified all source/lock/harness/spec, log/report hashes, selected
argv/node attribution and 1,020 complete-copy source entries; it passed. `readiness.json` is a
dispatch-readiness receipt, not an independent verdict. Evidence-local `.gitattributes` disables
text conversion to preserve raw artifact bytes in Git. Coordinated serial bursts only; no full
suite/browser/target/model/production activity.

Mandatory combined pytest/Ruff/doctor integration gates remain parent-owned. Unit review cannot
certify them, rich teaching execution, deployment, or the actual T-169/T-206 acceptance runs.
T-136 independent recall remains unavailable until independent human findings arrive.

## Usage and limits

Maker host tokens/cost and total active time unavailable (null), not zero. Exact command durations
are in commands.json; initial failed attempts remain visible. Current bound candidate commands:
301.953s; historical failed-lint INIT: 11.296s; prior successful 20-case INIT: 25.891s. Earlier unbound
shell attempts retain logs but their total active duration remains unknown. These are command
durations, not a fabricated maker active-time denominator. No wait time is added to maker usage.
Independent checker dispatch must use fresh context, assess/preflight gates and a bounded
BOOTSTRAP_REVIEW allocation (ratios unverified), recording all retry/child usage and preserving
required secrets/scope/production boundary checks. No self-PASS, merge or push performed.
