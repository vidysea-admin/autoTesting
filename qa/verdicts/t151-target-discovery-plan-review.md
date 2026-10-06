# T-151 independent plan review

Date: 2026-10-05. Bound root: `D:/autoTesting`.
Reviewed: `qa/manifests/t151-target-discovery.md`, plan revision 1.
PLAN VERDICT: CONDITIONAL APPROVE for the bounded steps 1-3 implementation slice.
Full T-151 plan approval remains BLOCKED on explicit prompt creation approval.
This is static plan review only, not a unit PASS or implementation cycle verdict.
No runtime, source, manifest or contract edit was performed by this reviewer.

## Blocking condition

The exact new prompt path `src/autotester/prompts/ai_target_classify_v1.md`
remains explicitly authority-pending in the maker plan. D-017 and plan section
5B authorize Provider classification and name the new schema/stage modules;
C8 requires prompts in files. However the user's new-file instruction requires
explicit scope authority, and this plan does not yet settle that qualification.
Root has asked once for explicit prompt creation approval. Await that answer
before creating the prompt or implementing classification/MockProvider changes.
No inline-prompt workaround or unrelated new module is approved.

The last runtime-lane sentence is stale: root reports T-125 released the lane.
Update it before implementation; this review grants no runtime lane.

## Independently accepted design

- D-017 and plan T-151 explicitly authorize the named new schema/discovery/context
  modules and fixture tests. Scope gates run before opening contents, including
  every external context root, and resolved candidate containment is checked again.
- Actual criterion landing notes bind AI1 and AI8 to T-151, AI2 through AI5 to
  T-152, and AI6/AI7 to T-153. The header predates the criterion renumbering.
  Canonical plan names `Signal.evidence_path`; AI1's `Signal.file` is a stale
  field reference. These are interpretations, not weakened requirements; every
  signal still must resolve to a real matching file and positive line.
- `schema/project.py::Source` permits `path=None` for DOC: the field is optional
  and no validator couples kind to a mandatory path. A scrubbed label/hash with
  separate typed evidence provenance is acceptable as an unpersisted reference.
  It must not be advertised as an ingest-ready project-relative document path.
- The narrow MockProvider.act schema-specific fallback can preserve the existing
  seam. Providers already import schema models. Do not import discovery stages
  from the provider or duplicate detector logic there. Seeded response precedence,
  unrelated schema errors, usage/prompt recording and no-network behavior need
  the proposed independent tests.
- Non-AI is a distinct typed refusal, never an invented fifth dispatch kind.
  Safe bounded YAML parsing, credential exclusion, fixed detector details and
  redaction before model input are appropriate; truncation must remain visible.
- Existing contracts remain unchanged. D-017 authorized their creation; no
  inspected decision explicitly authorizes these existing-contract reference
  repairs. Record an authorizing entry before any such edit.

## Acceptance limits

Steps 1-3 may implement only the named schema/enum, deterministic scanner,
Markdown reader, tests, and necessary safe-YAML dependency/lock changes. No
MockProvider edit, classify implementation or prompt creation belongs to this
slice. Classification tests may be specified ahead of implementation but must
not create import/collection errors that prevent scanner/context checks; the
unimplemented portion must remain named and cannot count as passing evidence.
This preserves the complete T-151 goal and is not approval to close a narrower
task or silently substitute static classification.

The slice must implement the plan's pre-content gates, resolved containment,
credential exclusion, explicit size/depth/alias/time limits, redaction and
visible refusal/truncation. Independent tests must cover each context root
and symlink/junction escape. No additional concrete design gap was established
in static review; these remain acceptance obligations, not verified behavior.

Scoped fixture verification can proceed only on root's separate lane grant.
Completion still requires independent criterion evidence, attributed mutation
failures, restored byte identity, and the full adapter gates. Existing unresolved
full-suite verification is not waived. No production scan, real provider call,
endpoint probe, Source persistence, UI behavior or product completion is approved.

## Full-plan approval addendum — 2026-10-05

PLAN VERDICT: APPROVE full original T-151 implementation plan, including step 4.
This addendum supersedes the prompt-authority block above, not its acceptance
obligations. The maker manifest records Umesh's explicit prompt-file approval,
"approve krr aur aggee baddoo", for the exact explained path
`src/autotester/prompts/ai_target_classify_v1.md`. The complete goal is unchanged.
This is independent static plan approval only, not product PASS or a runtime grant.

The reviewed classification plan preserves `classify(signals, provider)` through
the existing Provider.act seam and a file-defined prompt. Signals remain produced
by deterministic scanners; the provider names a positive kind and reason only.
Check selection remains T-152's literal-table responsibility. Non-AI input has a
typed refusal before a provider call, not a fabricated conversational default.
Strict typed response validation must reject unknown kinds, malformed/extra
fields and invalid confidence values; accepted signals/provenance must remain
the scanner's original observations, never model-produced replacements. Only
sanitized signal data enters the prompt, and returned reason/output must also
pass the existing redaction/secret guard before returning or persisting.

The MockProvider fallback is approved only for the exact classification schema
when no queued response exists. Existing seeded responses retain precedence,
including malformed seeded responses that exercise real classify validation.
Unrelated roles/schemas retain their existing ProviderError behavior. Usage and
prompt recording must remain observable through the existing provider seam.
No provider-to-stage import or duplicate discovery detector is approved. The
mock may apply deterministic kind rules to sanitized signals received in the
classification request; this is model emulation, not a second signal scanner.

The maker must cover no-call non-AI behavior, exact four-kind expectations,
seeded precedence, unrelated-schema errors, malicious kind/extra-field output,
redaction in input and output, unchanged evidence, and usage/prompt receipts.
The earlier test-oracle findings remain repair obligations: pre-read and each
context gate sentinels, emission Provider spies, secret keys/tags/evidence,
nonrecursive alias/byte/time limits, supported containment escape proof and
the promised detector families. No finding was waived by this approval.

Root separately schedules fixture runtime. No real provider call, paid call,
endpoint request, production target access or contract edit is authorized.
All full adapter gates and independent implementation checking remain required
before completion. Historical manifest receipts preceding explicit approval
remain history; maker should append/update current dispatch scope clearly.

## Enum placement adjustment — 2026-10-05

PLAN ADJUSTMENT: APPROVE defining the newly introduced `AiSignalKind` and
`AiTargetKind` exactly once in the already authorized `schema/ai_target.py`.
Keep `schema/enums.py` at its original baseline and update only new consumers
to import these types directly from `schema/ai_target.py`.

BLOCK the proposed reexport from enums.py: ai_target currently imports
RunApproval (approval.py imports enums) and Source (project.py imports enums).
Adding enums -> ai_target closes a circular import; placing the reexport last
does not solve the ai_target-first import order. IssueKind's existing reexport
is not equivalent: its isolated enum module has no model dependencies.
There are no baseline consumers of these newly introduced AI enum names that
need backwards-compatible reexports. This adjustment avoids a new module,
duplicate enums and deletion of unrelated code/comments to satisfy line caps.
Static approval only; fresh-process imports and doctor checks remain the maker's
and independent checker's verification obligations under the scheduled lane.

## Classification name adjustment — 2026-10-05

PLAN ADJUSTMENT: APPROVE renaming only the newly introduced T-151 function
`stages/discover.py::classify` to `classify_target`, with its new imports/tests
and call sites updated consistently. Existing
`stages/persona_changes.py::classify` stays untouched. Independent static grep
confirmed both public definitions before the adjustment. The new function has
not shipped; its signals-plus-Provider input and classification semantics remain
the approved plan's intent. This satisfies C3 without duplicating logic, changing
contracts, adding files or deleting another feature. Required tests/design gates
remain binding; unrelated baseline findings are not waived.

## Same-cycle C5 repair and bookkeeping plan — 2026-10-05

C5 REPAIR PLAN: APPROVE the exact candidate-manifest repair scope, conditional
on the independent checker's terminal freeze and root releasing/granting the
exclusive lane. This is plan approval, not source acceptance or PASS.

Existing discover.py::scan and read_context.py::read_context must assert_clean
on the complete final Discovery JSON, including nested Source/refusal/metadata
fields. Encoded/folded secrets are refused with the existing fixed secret-gate
exception; do not alter evidence identity to mask them. Existing approved_roots
must receive the caller Redactor and reject a dirty scope.project before path
or content operations. Preserve the exact clean caller project identity.
Catch only ApprovalRequired around the existing require_approval call, retaining
its exception class and raising fixed sanitized denial text from None. The text
must still identify refusal as a read-approval denial; no target/inner traceback
may leak secrets. Exact project/kind/target, signature, expiry and budget checks
remain identical. No global Redactor, consent.py, approval identity or contract
change is approved. The four independent checker probes plus planned encoded,
raw and ordinary-identity controls remain required evidence after the repair.

BOOKKEEPING PLAN: APPROVE only the canonical append, CLI ledger recovery and
existing generators described in the candidate manifest, under the same lane
condition and fresh prewrite concurrency checks.

Independently read root .work/at113-completion-decision.md and root
.work/t125-recovery-inventory.md: the latter records the original reviewed native
pwsh append receipt. Staging SHA256 independently matched
F36BCE43A97F75E6180F50C7DF7638F43A7CC6C755A5F4DD78B1351AE89C3F84.
Candidate DECISIONS is 165025 bytes; normalized candidate history independently
equals canonical root's pre-D061 prefix, and the original staging independently
equals root's entire D061 suffix. Append through the existing append_decision.ps1
only after these identities recheck. Preserve every existing history byte and
require exactly the expected D061 suffix/24 added, zero removed lines; do not
copy wholesale history, invent another entry or change execution policy.

Existing F067 T171 event was independently reviewed earlier: cycle2 PASS,
high-value prefilled reason explicitly unconfirmed, and not new live validation.
Use only the existing ledger CLI for this candidate's missing row. Recheck no
concurrent T171/F067 event, preserve the prior ledger bytes, and verify actual
verdict/task correspondence. Fresh creation timestamp is expected; exact copied
row bytes are not required. Preserve qualification and surface the existing
reason, without treating it as confirmed.

Run only existing map/snapshot generators with the proposed candidate bindings,
offline/no-sync environment and credential-loading guard. Inspect generated
sections and SNAPSHOT output; preserve concurrent unrelated docs. No architecture
prose, contracts, goal, enforcement or source edits belong to bookkeeping. The
committed/fresh generated gate, four C5 findings and full suite remain open until
their own evidence closes them. No automatic PASS or baseline waiver is granted.

## Filesystem exception boundary repair — 2026-10-05

PLAN ADJUSTMENT: APPROVE the candidate manifest's exact filesystem exception
boundary repair. Reviewed its named existing approved_roots, scan and
read_context functions and the filesystem operations they transitively perform.
Catch OSError only around strict root resolution and filesystem traversal/reader
processing, retaining FileNotFoundError or PermissionError where applicable,
otherwise OSError. Raise fixed `filesystem access refused` text from None, with
no original filename/args/winerror or exposed exception chain.

Failure must still raise; returning empty Discovery with complete=True is not
approved. Leave ValueError/redactor refusal and ApprovalRequired semantics intact.
No new helper/module, schema, global Redactor/consent change or contract weakening
is authorized. Preserve existing oracles and numeric design caps.

Six diagnostic assertion failures are maker evidence, not independently rerun
by this static reviewer. Require exact missing/access subclasses, suppressed
formatted tracebacks, raw/base64/hex/folded fixtures, unchanged ordinary positive
behavior, and the original four C5 probes plus bounded regressions after repair.
Root schedules execution; this plan review grants no additional runtime lane.
Full adapter verification, committed generated freshness and C7 remain open.
No source acceptance or product PASS is recorded here.

## Bounded bookkeeping execution audit — 2026-10-05

STATIC AUDIT: APPROVE observed bookkeeping scope; no provenance/diff error found.
Independently hashed the candidate's first 165025 DECISIONS bytes: unchanged
9DAABAA58807601B8BAFA87D531336C1894439828546EB1A582957B23B35AB6A.
Normalized full history equals canonical root, including the previously reviewed
original D061 suffix. Actual git diff is 24 additions and zero removals.
Independently hashed the first 67418 FEATURES bytes: unchanged
251BAF59301AB26009F05BE8E674CF8B4746A36BEDBD9479E197CE6DF64E1E89.
Actual ledger diff is exactly one F067/T171 row. Its cited verdict independently
states cycle2 PASS; reason remains explicitly unconfirmed and description states
bookkeeping recovery, not new live validation. Fresh timestamp is legitimate.

MAP diff contains only 13 generated module/model rows for the authorized T151
shapes/stages; SNAPSHOT is 2 additions/2 removals: qualified F067 enters the
bounded high-value display, F055 rolls into overflow and count becomes 35.
Four current document hashes independently match the maker receipt. These are
expected generator effects; no unrelated prose/contract overwrite observed.
The reported doctor clean/native0 is maker execution evidence, not rerun by this
static audit. No committed/fresh gate, source acceptance or unit PASS is inferred.
Filesystem repair and independent/full adapter acceptance remain separate gates.

## Narrow local candidate checkpoint plan — 2026-10-05

CHECKPOINT PLAN: APPROVE one scoped local candidate-branch commit after the
active checker explicitly reaches terminal/release and root refreshes the exact
file/hash inventory. C10 requires committed source before Mode A; this checkpoint
does not require or assert release readiness, C7 completion, PASS, merge or push.

Approved scope is the existing eight product/dependency paths, four reviewed
bookkeeping documents, candidate maker manifest, exactly enumerated maker evidence,
and the two unchanged checker diagnostic reports with their enumerated evidence.
Exclude enums.py (independent content diff empty), root's dirty files, .goal,
contracts, architecture/enforcement and other units/worktrees. Named individual
pathspecs only; preserve unrelated staging and never use add-A or bare commit.

Independent current status matches that scope. Maker evidence independently
totals 14 files/119240 bytes; all 13 copied files match their original .work file
hashes (zero mismatches). The separately attributed native transcription hash
matches 038B4A8FA7C95D4DE55375FD87388FD20D775B184F7B174A4390A3EA2CF98714.
The two checker reports expressly remain diagnostic, not Mode A PASS; active
carry-guard append work means their final hashes must be refreshed after release.
Do not rewrite either checker report to make the checkpoint ready.

Run the existing sensitive-value/precommit guards on the exact refreshed scope;
synthetic fixture strings are test data, not authority to bypass a guard. Report
any hook rejection and its reason, without disabling hooks, changing policy or
silencing the finding. Preserve the previously reviewed document byte prefixes
and approved source lineage; postcommit readback must confirm exact names/SHA
and committed-generated freshness before later Mode A dispatch. Remaining C7
matrix/full suite/source acceptance stay open. This review stages/commits nothing.
