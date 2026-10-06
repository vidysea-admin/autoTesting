# T-190 — future-unit PLAN proposal

## Resumed physical-budget design — 2026-10-05

User asked root to continue the full goal; read-only engineering work proceeded
in parallel with T136. /root/codex_policy_parser_verify supplied a concrete
installed-provider design (WARNING, not implementation approval or task PASS).
Preserve configured vendor/model/fallback order and SDK retries. One run-owned
budget reserves immediately before an owned HTTP-client subclass delegates
_send_single_request. Failed attempts remain spent. Never claim packets/tokens/
currency are bounded by this HTTP-attempt cap. Receipts contain only vendor,
ordinal, method, status and fixed outcome codes, not request data/errors.

Existing-file plan: providers/base.py::Provider.__init__ optional physical_budget,
PhysicalBudget.reserve/finish/raise_if_stopped, typed BudgetExhausted(ProviderError)
and per-instance synchronous metered-client factory. Sticky stop is necessary:
Anthropic wraps transport exceptions, so subsequent retries and fallback must
consult stop state and refuse before send. Unbudgeted functional paths unchanged.
providers/anthropic.py::_structured injects owned metered DefaultHttpxClient;
providers/gemini.py::_structured uses supported HttpOptions.httpx_client;
providers/gemini_files.py::upload_and_wait shares budget across cache/upload/
chunks/polls, starts deadline before upload, checks stop before catches/sleeps;
providers/langchain_fallback.py::_default_chain splits same-file factory helpers
and passes the shared budget, _call checks stop before tiers and in catches,
_try_tier checks stop on error and success. Owned client cleanup in finally.

Pinned seams: httpx2/_client.py1065 and httpx/_client.py1001 single-request methods
sit below redirect handling. Direct Gemini _api_client.py1513 generation and
1941–1942 upload retries use its injected client; Vertex AuthorizedSession at
1480–1498 is separate and must refuse budgeted capability until covered.
LangChain Anthropic has no public HTTP-client field: proposed version-locked
ChatAnthropic cached _client override at1465–1478 uses resolved SDK configuration
with_options(http_client=owned_client); never close a shared cached original.
LangChain Gemini client field3160 is overwritten at3491, so proposed construction
replaces the declared field after ordinary configuration resolution and closes
the unused original, preserving endpoint/version/headers/retry/model settings.
These private/lifecycle seams require actual independently source-pinned fake
transport proof; static source reads alone DO NOT establish enforcement.

Absent OpenAI/Ollama packages do not authorize dropping configured tiers. Preserve
their normal zero-send import failure behavior; newly available unverified
transport capability must refuse before an unmetered invocation. No global SDK
monkeypatch, async coverage or vendor substitution is proposed.

Measured baselines: base189/fallback171/Anthropic99/Gemini195/files111 lines.
Unsaved control-only51-line projection base189->240 excludes imports, schema,
deadline clamping and wiring; complete multi-file count proof is still missing.
Required oracles: cap2 blocks third actual send across retry/redirect/upload/poll/
fallback; wrapped exhaustion remains sticky; failed sends spent; constructor
failure zero sends; own clients closed on every path/shared clients preserved;
unbudgeted functional behavior and configured identities unchanged. Reservation
and sticky-stop mutants must fail intended assertions. No code, SDK import,
runtime, test, network or new-file creation happened. Existing exact-path and
containment gates remain binding. This supersedes the competing single-provider
proposal as a DESIGN direction only, not an authorized architecture change.

Independent design delta (/root/codex_tick_marker_plan, WARNING): installed
LCGemini chat_models.py3492 captures original client in _client_cleanup, with
aclose/destructor ownership and auxiliary async client at genai _api_client875.
Replacing client alone is NOT implementation-ready. Explicitly rebind cleanup
ownership, dispose all owned auxiliary clients and preserve shared model copies;
never close a still-shared client. LCAnthropic _client_utils47–63 applies
anthropic_proxy at transport construction; with_options cannot transfer that
transport property by itself. Preserve proxy explicitly without closing shared
originals. Budgeted caller-supplied factories/custom transports must refuse
before invocation if unverified; absent vendors retain zero-send import errors.
Require atomic reservation and two-concurrent-reservation no-overspend proof,
sticky stop on success/error/cache catches, exact-once cleanup across construction/
refusal/parse failure, shared Anthropic sibling survival, and retained configured
endpoint/headers/model/retry/proxy. Owned HTTP seams are statically viable;
independent fake-transport execution remains required. No runtime or PASS.

## Ownership correction — 2026-10-05

Read-only engineering response /root/codex_policy_parser_verify REJECTS the
post-construction LCGemini client replacement above. Keep ordinary constructor,
model.client and shared cleanup token untouched. Proposed existing Gemini factory
uses declared client_args (_common311), forwarded to both SDK client argument sets
(chat_models3442–3443), to install request/response budget hooks. Installed HTTPX
sync request hooks run inside redirect loop976–979; async path awaits them1691–1692.
Require explicit async refusal before reservation/send for this sync-only design,
and reject unreviewed transports/mounts. Request hook reserves; response hook
finishes receipts; exception boundary records outstanding failures without data.
Keep model, structured runnable and copies inside one owned invocation scope;
dispose copies before public await model.aclose (chat_models3529), retaining its
existing cleanup owner for sync AND auxiliary async resources. A synchronous
caller requires an explicit safe lifecycle runner; a running event-loop case must
use its actual owner or refuse, never leak or rely on garbage collection.

This is a proposed public-hook seam replacing the earlier private Gemini client
swap, not source proof that hooks cover every configured adapter. Independent
fake-client redirect/retry/upload/async-refusal/failure/exact-cleanup tests and
full candidate counts still required. Anthropic owned metered DefaultHttpxClient
must mirror installed _client_utils47–63: resolved _client_params base_url or
existing ANTHROPIC_BASE_URL fallback or vendor default, resolved timeout when
present and model.anthropic_proxy when non-None. SDK with_options cannot copy
transport proxy; never close/modify shared original. Constructor/cleanup failures
need safe receipts, and no model copy may outlive the invocation scope.
WARNING remains: no implementation approval, SDK import/runtime/test, new source
file or product PASS. Earlier replacement text remains historical rejected design.

Independent direction review /root/codex_tick_marker_plan: client_args311 forwards
at3442–3443; GenAI filters HTTPX parameters1087–1149 retaining event_hooks for
sync868/async875; request hooks976–979 precede redirect sends, upload retry1942
uses sameclient.request; public aclose3529 delegates preserved cleanup213–226.
DIRECTION APPROVE only. Concrete constraint: identical hook list reaches async
HTTPX which awaits hook1692. A sync hook must refuse running-event-loop execution
BEFORE reservation; otherwise it reserves then async awaiting fails. An async
hook is not a safe substitute because syncHTTPX ignores its coroutine. Refuse
running-loop invocation before model construction for this synchronous design,
keep refusal sticky, and never infer mode from request/stream type. Existing-loop
support requires a separately specified owner, not a guessed runner. Retain
existing hooks/options and prove zero async reservations/sends, redirect/retry/
upload counting, spent failures, shared-cleanup preservation and exact-once
sync/async disposal. All bindings/copies confined to invocation lifetime.
No implementation/test execution or product PASS follows this source review.

## Unsaved provider-control count checkpoint — 2026-10-05

Maker helper /root/codex_policy_parser_verify constructed unsaved base/fallback
text previews and parsed them with AST, without source imports/execution/writes.
base256lines,longest function record41,SHA256
3952d8d77d00355186396977d67f822f15544f287704abdecb4fa76571702abc;
fallback187lines,longest _default_chain43,SHA256
5fc6c01bc7e8f3673c0fa40005be8dcd545d3b946018aebb4ddbdf2ff259a226.
Proposed existing changes: Provider.__init__42 optional control, _call131 sticky
refusal before tiers/in catches, _try_tier153 checks after invoke. Unbudgeted
factories/custom chain/trace/usage calls unchanged in preview. Added runtime
control uses atomic reserve/finish and fixed sanitized receipt fields, with
schema-owned sink still missing. Vendor budget wiring is NOT implemented:
preview refuses every budgeted factory before construction. This is containment
scaffolding only, NOT faithful usable T190 behavior and NOT authorized to apply
as a substitute for the complete feature. Complete vendor hooks/deadline/cleanup/
proxy/schema tests remain required. Long-line formatting may change counts/hashes.

Root preimplementation concerns: arbitrary upper bound100 in preview has no
recorded product basis; derive limits from the applicable approved budget rather
than introduce a new silent ceiling. Sink callbacks run under a non-reentrant
lock, so callback contract/reentry failure/deadlock must be resolved before
acceptance. Inline vendor/method outcome sets need closed-vocabulary schema
ownership, not duplicate domain shapes. AST success does not verify behavior,
concurrency, redaction, transport cap or lifecycle. No production source edits,
tests, model/browser/network calls or PASS occurred. Preview remains NOT READY.

## Pinned provider/physical transport inventory — read-only, 2026-10-05

Fresh reviewer addendum: inventory evidence/conclusion APPROVE, capability implementation
still BLOCK. Direct Gemini _contents:122-125 calls upload_and_wait for each screenshot;
local image inputs therefore do NOT establish an upload-free transport. An inline-image
seam requires its own reviewed implementation; current path is not proven supported.
Anthropic1.3 uses httpx2.Client (_client.py:150), physical transport.handle_request
at httpx2/_client.py:1065/1076; metering ordinary httpx would miss those sends.
Correct fallback function label below to _call:131 (loop141/catch146), not _structured.
No single-provider candidate authorizes narrowing configured model/vendor fidelity.

No SDK import, API call, upload, runtime, environment credential read, install,
network or implementation performed. Inspected uv.lock, provider code and installed
root .venv package source/METADATA only; no current-web behavior assumptions.
Locked: anthropic1.3.0 (uv.lock31-32; installed METADATA3), google-genai2.22.0
(592-593; installed METADATA3), httpx0.28.1 (768-769), httpx2 2.12.0(783-784),
langchain-anthropic1.7.0(934-935), langchain-core1.6.1(948-949),
langchain-google-genai4.4.0(969-970), tenacity9.1.4(1776-1777).
No pinned/installed openai/langchain-openai/langchain-ollama package directory
was found in this inventory; fallback optional imports are not proven available.

Confirmed package capability is NOT current Provider capability:
- Direct Anthropic current providers/anthropic.py::_structured:56 creates
  Anthropic(api_key=...) at65 without retry option, messages.create max_tokens2048
  at84. Installed anthropic/_constants.py:10 DEFAULT_MAX_RETRIES2;
  _base_client.py:1109-1112 loops max_retries+1, physical send:1269. SDK supports
  max_retries0 (constructor validation:414-416), i.e. one SDK attempt; current
  wrapper does not apply that option. It hardcodes2048 output tokens, so passing
  arbitrary Provider.options max_tokens/retries does not override this code.
  Provider.judge logical call can therefore send up to3 SDK attempts; redirect/
  custom transport behavior still needs a physical boundary oracle, not a claim
  exactly3 network packets or an enforceable money ceiling. Images inline base64
  read locally, no Files upload path in direct Anthropic judge.
- Direct Gemini current gemini.py::_structured:141 creates genai.Client(api_key)
  with no HttpOptions, generate_content:145 uses _config:87-90. VisionOptions
  observation.py:85/93 defaults max_output_tokens65536, passed to SDK config for
  agent/judge calls too when no explicit options. judge signature does not expose
  a per-call token/retry control; Provider.options alone is not wired into this.
  google/genai/_api_client.py::retry_args:562-576 with optionsNone explicitly
  stop_after_attempt1 (not default5); supplied HttpRetryOptions attempts1 gives
  one SDK attempt, supplied attemptsNone falls back5. types.py:2593-2600 documents
  attempts includes original; implementation normalizes0→1. _request:1519-1537
  accepts per-request options and calls _retry(_request_once); actual send:1513.
  Client HttpOptions exists client.py:335; max_output_tokens config exists
  types.py:6496. These controls are statically supported, not wired/enforced by
  current direct judge or transport attempt meter.
- Gemini Files upload is a DIFFERENT physical path: current
  gemini_files.py::upload_and_wait:70 calls files.get cached:82, upload:89,
  polls files.get:101. Its600s timer starts AFTER upload:93, so not an upload
  deadline; repeated polls are additional requests, not retry metadata.
  Installed files.py::upload:578/_create:622 then upload_file:641-647;
  _api_client.py::upload_file:1837/_upload_fd:1870 chunks8MiB constant:93,
  own MAX_RETRY_COUNT3:95 and retry_count loop:1941/direct httpx request:1942.
  This chunk retry bypasses _request/HttpRetryOptions; attempts1 does NOT
  disable all upload retries. Need physical send budget across initialization,
  every chunk/status retry/cachelookup/poll before promising a hard cap.
  Output-token controls do not cap upload bytes/requests or input-image tokens.
- LangChain Anthropic installed chat_models.py max_retries2:1121;
  _client_params:1445-1454 forwards configured max_retries to SDK Client:1480.
  max_tokens field:1098 optional; set_default_max_tokens:1390-1398 resolves model
  profile max_output_tokens or4096 fallback (_FALLBACK...:136), not current direct
  wrapper's2048. Current fallback _default_chain:43 constructs ChatAnthropic
  with model only:49, so no UX-specific retry/token limit is passed.
- LangChain Gemini _common.py:397 max_output_tokensNone and417 max_retries6;
  chat_models.py:3856-3858 uses model/call max_retries,4090-4097 builds
  HttpRetryOptions(attempts=max_retries), token generation config:3634-3635.
  Thus the value counts attempts including initial, unlike Anthropic retries;
  explicit1 is the unambiguous no-retry value. Current factory:58 uses model/key
  only, inheriting default6 and no explicit output ceiling. Exact profile/server
  cap when max_output_tokensNone is not established here, not an assumed bound.
- Current LangChainFallbackProvider::_structured:141-150 tries every configured
  vendor on ANY exception (broad catch:146). _try_tier:153-171 calls
  factory().with_structured_output at158 then model.invoke at160; no physical
  reservation, no per-attempt shared UX budget, and
  usage recorded only success. Provider.base::record:109 retries/fallback_hops
  are explicitly trace metadata only:115; they are not retry enforcement.
  Fallback success cannot justify forgetting failed physical sends/spend.

T190 safe capability implications, pending reviewed implementation:
Supported statically: Anthropic SDK zero retry + explicit max_tokens; Gemini
generate HttpRetryOptions(attempts1) + explicit max_output_tokens; LangChain
constructors/token kwargs with distinct vendor retry semantics. Current wrappers
DO NOT expose a uniform enforced physical-attempt/output-token budget.
Unsupported current claim: `max_calls20` around Provider.judge bounds requests,
tokens or spend across fallback/SDK retries/uploads. DirectGemini upload control
especially disproves a single SDK retry flag covering all transport traffic.
Pending: exact injected physical HTTP send adapter accounting and refusal before
each send, bounded deadline/payload/upload handling, redirect policy, failure
usage accounting and vendor-by-vendor fake transport proof. No live provider
probe is needed to derive this; no live-model permission is inferred.

Plan choice for fresh reviewer/root: UX advisory uses local masked screenshots
only (no video/files upload) and a capability-approved explicitly configured
single judge provider with bounded output and disabled retries/fallback, OR
refuses/skips advisory capability until full shared physical budget is enforced.
Do not silently change configured model/vendor or disable functional judge retry
behavior; any implementation must stay in existing provider constructor/call
functions and be separately scoped/approved. T190 current source authority does
not automatically authorize global Provider seam redesign. A fixture fake
transport must count physical sends at installed SDK send/request boundaries,
including failure→retry/fallback, not MockProvider logical invocation count.


Status: proposal-awaiting-independent-plan-review
Bound root: D:/autoTesting. Prepared: 2026-10-05. Implementation cycle: not started.
Owner: root maker may schedule this only after its current T-151 unit/lane is released.
This QA artifact is preparation, not competing implementation, plan approval, task PASS,
runtime authorization or authority to create source files.

## Outcome and authority

T-190 adds UserPersona and a separately persisted advisory UX finding list, rendered beside
functional results. PU1-PU9 in qa/contracts/persona-ux-advisory.md are binding. The functional
Verdict and its rubric remain byte-identical; UX never feeds functional grading or case generation.
The goal task is pending, deps=[], user_value high. This contributes R28/operator-readable
reporting to the reusable testing platform, but closes neither two-target acceptance nor T-166
persona-driven generation, T-168 unified reporting, or T-169 generic acceptance.

Authority already recorded: qa/gates/meeting-user-persona-ux-judging.md:35 answer A;
docs/DECISIONS.md:1089 D-048 approves the advisory direction and normal maker-checker source/test
changes. D-050 at1166 authorizes the ACTIVE contract. Do not re-ask A/B/C. docs/plan.md:28
explicitly names schema/user_persona.py, grade/report surfaces and mini-grill first. Here
"grade surfaces" cannot authorize editing functional grade/rubric behavior against PU2/PU4.

Exact new-path distinction: src/autotester/schema/user_persona.py is explicitly named by the
existing plan and PU1. PU5 expressly names a new skills/ux_judge/SKILL.md (package-resolved
candidate: src/autotester/skills/ux_judge/SKILL.md). This needs review of exact location under
normal maker authority, not a second product-direction question. Proposed schema/ux_report.py,
stages/ux_advisory.py and tests/test_user_persona.py are NOT explicitly named exact source/test
paths in D-048/D-050; their necessity is below, and path authority must be resolved by root and
fresh reviewer before creation. This preparation creates none of them.

## Five plan decisions — concrete recommendations, not approved defaults

1. Provider: reuse the project's configured functional judge provider through Provider.judge,
   with separate UX prompt and output schema. Preserve configured model choice; no cheap-model
   substitution. Fixture verification supplies a deterministic fake Provider. The current UI
   trigger hardcodes LangChainFallbackProvider, so resolve the actual configured provider using
   existing registry rather than claiming the route already honors ProviderConfig.judge.
2. Budget: [ASSUMPTION, proposed plan choice] opt-in per-run max_calls=20, one call per eligible
   case, with bounded prompt/image payload. A typed shared call budget reserves before dispatch,
   counting failures/retries too; do not launch parallel UX calls. When exhausted, persist each
   remaining case as advisory skipped_budget, never modify Run/RawResult/Verdict outcome.
   This is a CALL cap, not a claimed money/token ceiling. Numeric limit and evidence-byte limit
   require independent plan review; actual paid usage still requires explicit run authority.
3. UX storage: one projects/<slug>/runs/<run_id>/ux_report.json with typed per-case outcomes and
   findings. Contains case_id, persona_id/ref, cited evidence/step, Severity S1-S3, finding text,
   effective condition evidence, provider label and skip/error reason. Artifact envelope and
   extra=forbid apply. Findings and budget/error records live outside functional verdict files.
   Exports load this exact facade path; absent report means UX not requested, malformed report
   yields visible advisory-unavailable/error, never silently zero findings.
4. Persona storage/attachment: projects/<slug>/user_personas.jsonl, typed UserPersona artifacts
   with stable id and required role/TechComfort/locale/device. Optional user_persona_ref on BOTH
   Project and Case; case override wins, project ref fallback; missing ref is recorded, never
   inferred from PortalPersona. Ref identifiers cannot contain separators or escape the project.
   Case.with_fixed_step must preserve its existing persona ref when fixing a step.
5. Execution: project-level ux_enabled=False default, with explicit opt-in and per-run snapshot.
   Run the UX reader once after all functional results/verdicts are persisted, in case_ids order.
   No rerun of product actions. This keeps entry/serial/parallel execution on their existing paths
   and makes one common post-run budget deterministic. Advisory errors are persisted/disclosed;
   they do not abort functional report generation or silently report a completed UX pass.

These are contract-permitted plan choices, not settled product mandates. No new HUMAN_GATE is
opened here. Existing docs/intent.md/spec.md/plan.md and plan gate must be reconciled by the
maker against this concrete proposal and independently approved before code. Any genuinely
unresolved ownership/product choice must be identified specifically by that review.

## Existing edit-in-place targets (verified current anchors)

| Existing file/function | Proposed purpose |
|---|---|
| schema/project.py:123 Project | optional project ref, ux_enabled and bounded opt-in policy; no credential values |
| schema/case.py:13 Case; :71 with_fixed_step | optional override ref and preservation during corrected-step construction |
| schema/enums.py:96 Severity; :175 ProviderRole | add TechComfort in this vocabulary module; reuse Severity/judge, no new UX severity/role |
| core/paths.py:25 ProjectPaths; :110 run_dir | persona collection and exact UX report path methods; only path construction place |
| store/project_store.py:42 ProjectStore; :157 save_run; :163 save_result; :179 save_verdict | typed persona/report facade operations beside existing persistence pattern |
| ui/routes_runs.py:125 trigger_run; :93 _execute_with_trace | one post-functional advisory call before final redirect, opt-in only; stable case order |
| stages/report_export.py:114 export_excel; :187 _case_section; :260 export_html | distinct UX sheet and sibling ux-findings section; empty means no section |
| schema/run.py:39 RawResult | only if needed, typed observed execution-condition evidence for PU8; never infer actual locale/device from persona |
| stages/execute.py:142 run_case; :190 _result | capture condition evidence after enact and before reset, carry into result; preserve enact/reset semantics |
| providers/base.py:90 Provider.judge; :165 load_skill_prompt | reuse unchanged generic structured output/prompt seam |
| browser/secrets.py:256 guard_prompt; core/redact.py:120 assert_no_raw_secrets | reuse unchanged guard before UX call; scrub persisted/exported fields |

Before actual implementation, reviewer/maker must revalidate these current function lines
and inspect T-151/T-125 integration overlap. No edits to
schema/verdict.py or functional grade.py/run_case_pipeline rubric-building functions.

New concepts require one home: user_persona.py for persona/policy shapes;
proposed ux_report.py for finding/report/output shapes; proposed ux_advisory.py for read-only
evidence selection, alignment/guard/call/budget orchestration and small export-format helpers.
No duplicate Provider/store/path implementation. Test file covers the dedicated new concept.

## Known structural/semantic risks that review must settle

Measured by file reads: enums.py 300 lines, project_store.py 300, report_export.py 299,
paths.py 287. A casual append violates C2. Reviewer must approve concrete in-place headroom
refactoring (small existing helpers, no duplicated implementation), or explicitly authorized
single-purpose extraction path, before edits. Do not use blanket whitespace collapse or remove
useful comments merely to pass line caps. export_excel currently approaches its 50-line limit.

PU1 says attachable at both levels while a later bullet says Project "or" Case. This proposal
meets the stronger title/answer by supporting both. Do not amend the contract to pick one.

PU8 cannot be fully established from current RawResult: it has no observed locale/device.
browser/conditions.py enacts a mobile viewport only for VIEWPORT_MOBILE; LOCALE_I18N returns
NOT_RUN. browser/launch.py supplies viewport but no explicit locale. Proposal: record measured
conditions during execution, never retrofit persona claims from a default/guessed locale.
Unknown/incompatible condition -> advisory skipped_condition, zero findings; NOT_RUN always
skips. Browser locale support/device emulation beyond existing enactment are out of scope.
Exact evidence schema and minimal recording sites are mandatory independent plan-review items.

Treat screenshot paths as untrusted: resolve below run dir, reject traversal/symlink escape,
require masked evidence, guard all assembled textual evidence/persona fields, cap bytes/images.
The provider receives no action tool and cannot browse, log in, fetch remote media or mutate
the product. Advisory output must cite supplied evidence, with invalid citations refused.

## Independent acceptance and future verification

PU1: strict schema roundtrip, unknown-key refusal, both refs/override and corrected-step
preservation. PU2: verdict module diff unchanged, separate path/schema; raw-result loading
ignores auxiliary report files. PU3: same frozen RawResult and functional provider response
with/without post-run UX -> byte-identical complete Verdict JSON, including metadata.
PU4: AST/import/function-body oracle catches persona entering functional rubric/prompt.
PU5: fake Provider sees dedicated schema/prompt; missing SKILL fails visibly, no inline/vendor
fallback. PU6: synthetic secrets in persona text, evidence and model output are guarded/scrubbed;
removing guard must fail the named pre-call zero-invocation test.
PU7: HTML parsed sibling sections, escaping and no empty block; Excel distinct UX sheet and
unchanged functional cells; unknown/malformed advisory status visible. Real local headed
checker interaction/render evidence is still required for the affected UI/export surfaces.
PU8: actual mobile/desktop/locale evidence matrix, NOT_RUN/mismatch/unknown refusal and a
falsification that bypasses alignment. PU9: doctor plus current file/function counts.

Budget/integration: disabled flag -> zero advisory Provider calls and no extra artifact; enabled
post-run route -> exactly once, deterministic ordering, cap exhausted/failure/retry counted,
stored functional outcomes unchanged, no duplicate calls across serial/parallel/entry legs.
Independent checker derives fixture oracles from PU criteria, not maker expected-output text.
Every new guard needs applied-once mutation, green baseline, named assertion red (not collection
failure), raw-byte restore, green; C7 requirements remain binding.

Future checks required by contract: uv run pytest tests/ -k persona; uv run pytest;
uv run ruff check src tests scripts; uv run autotester doctor. Tighten task done_check to actual
accepted test node only when implementation exists (current waiver is deliberate).
Full-suite/browser containment remains unresolved in this project; mocked fixture proof cannot
waive that boundary for T-190 either. Any paid/live calls stay outside this preparation.

## Preparation terminal

### Independent engineering review — 2026-10-05

Advisory direction approved; implementation-plan approval BLOCKED. Required refinements before source work:
- Define typed measured viewport/locale conditions and capture after enactment but before `execute.py::run_case` resets viewport; viewport alone does not prove device emulation. Unknown, mismatch and NOT_RUN must remain finding-free.
- Define physical provider-attempt budget enforcement at the fallback attempt seam, not merely `judge()` invocation count, plus concrete numeric text/image bounds.
- Exclude exactly `ux_report.json` in `project_store.py::load_results`; preserve malformed functional-result behavior. Define stable persona IDs, missing-reference outcomes and common post-functional persistence integration seam/run snapshot.
- Establish exact new-path authority for proposed advisory schema/stage/tests. Existing answer A does not authorize these paths or replace required intent/spec/plan gates.
- Name concrete capped-module refactors, destinations, resulting counts and preserved callers before edits. Existing `core/excel.py::autosize_columns` is a possible reviewed spreadsheet responsibility destination, not authorization for an arbitrary new module. Reuse Severity and keep TechComfort vocabulary in enums.

Fresh reviewer source anchors correct earlier proposal references: `ProjectPaths::run_dir:110`, `ProjectStore::load_results:166`, `save_portal_persona:296`, `Case::with_fixed_step:71`, report `_case_section:187` and `export_excel:114`, execution `run_case:142` / `_result:190`. These are read-only review evidence; revalidate before editing. No source/runtime/contract change or feature PASS accompanies this appendix.

PLAN PREPARED, REVIEW REQUIRED. No implementation was started; no runtime/browser/network,
source/contracts/goals/decisions/gate-answer edits, mini-grill claim or acceptance PASS.

## Refinement 1 — concrete acceptance design, pending review

This addendum supersedes recommendation 2's logical-call interpretation and supplies the
previously missing designs. It is still proposal-only. No implementation permission arises
from the numerical values or projected counts below.

### Measured conditions and PU8

Define `ExecutionConditions` in existing schema/run.py (extra=forbid):
`viewport_width:int|None`, `viewport_height:int|None` (positive when present),
`navigator_language:str|None`, `mobile_emulation:bool|None`,
`measurement_error:str|None`, `captured_step_order:int|None`.
RawResult gains optional `execution_conditions`, default None for legacy artifacts.
This is observation, not persona or judgement. No extra fields on Verdict.

Add `conditions.observe(session)` in browser/conditions.py beside enact/reset: read actual
page.viewport_size and navigator.language, not DEFAULT_VIEWPORT or persona text. Record
mobile_emulation=None unless a real context option has independently established it; today's
390x844 viewport is not an emulated phone. A failed read returns typed unknown/error, scrubbed
through session.secrets, never a fabricated desktop/en-US value. No remote query is needed.

In execute.py::run_case, after successful enact and before `_run_steps`, take initial observation;
take final observation inside the try/finally BEFORE conditions.reset. Capture it for `_result`
and replace any early RawResult returned by `_run_steps` with a copy carrying those conditions.
For NOT_RUN, attach measurement_error='condition not enacted' and no viewport/locale claim.
If initial/final observations disagree, mark unknown ('condition changed during case') rather
than associating screenshots from incompatible conditions with one persona. A stronger future
per-screenshot condition record is outside this first unit; uncertainty must skip findings.

Device interpretation is explicit: UserPersona.device='desktop_viewport' or 'mobile_viewport'
describes layout only. Mobile viewport requires VIEWPORT_MOBILE, successful enact and measured
390x844 throughout; 'phone', 'tablet', touch or OS emulation claims are unsupported and skip.
Locale must match measured navigator_language; no broad default-language assumption. An
LOCALE_I18N case that never ran produces zero findings. Ordinary cases may judge desktop layout
only with measured compatible conditions. Unknown/NOT_RUN/mismatch -> typed skipped_condition,
zero Provider invocations and zero findings. Persona fields remain free strings per PU1;
unsupported claims have an explicit reason rather than coercion to a convenient supported value.

### Physical attempts, payload and fallback

Proposed UXPolicy fields in user_persona.py: enabled=False; max_attempts=20 (0..100),
max_prompt_utf8_bytes=32768, max_image_count=3, max_image_bytes=1048576,
max_total_image_bytes=2097152, max_image_pixels=2097152, max_findings_per_case=20,
max_finding_utf8_bytes=2048. Reject oversize input, with recorded skipped_payload reason;
do not silently truncate citations/text. Validate image dimensions/type using an existing
image reader before base64/upload, read no more than cap+1 bytes. Attempt payload including
base64 must also fit 3 MiB. UTF-8 byte limits are not token ceilings or currency guarantees.
Provider output-token maximum is proposed 2048 only where the adapter can enforce it;
unsupported provider -> skipped_unsupported_budget, not an unbounded call.

One sequential run-owned AttemptBudget reserves BEFORE each actual physical transport attempt,
never after successful usage reporting. Reserved attempts stay spent on timeout, parse failure,
rate limiting or exception. Separate providers/base.py typed hook carries reserve/receipt;
functional callers with no hook retain existing behavior. Exact existing fallback seam:
langchain_fallback.py::_try_tier:153, before `model.invoke` at160 (current source recheck
2026-10-05; previous164 anchor was stale). `_call:131` must re-raise the
distinct BudgetExhausted signal before its broad vendor catch can consume/fall through it.
Fallback tiers each spend one reservation. Model/factory construction failure that sends no
request spends zero; receipt must distinguish transport reached from construction failure.

This hook alone DOES NOT contain SDK internal retries. For the opted-in UX provider only,
factories must disable SDK/LangChain internal retries and tool-output retries, or instrument
their request transport so every retry reserves. Current _default_chain:35 supplies no such
retry setting, and paid Gemini media upload is another transport in _contents. Therefore the
smallest first supported live path is a separately constructed LangChainFallbackProvider whose
factories expose verified retry-disabled transport; unsupported direct Gemini/Anthropic paths
are refused for UX until their transport proof exists. Keep configured vendor/model identities,
do not silently replace a configured unsupported provider with another vendor.
SDK capability/version verification remains an engineering prerequisite; no network/docs
lookup or guessing a vendor option key is authorized in this preparation.

Future independent fake-transport oracle: cap=2, tier A fails once, tier B fails once,
tier C sentinel must remain zero; cap=0 sends zero. A factory failure sends zero. A retrying
SDK fake attempts a third request and is refused at the transport. Remove either reservation
or BudgetExhausted propagation -> named test red. This proves physical attempts rather than
20 judge calls potentially hiding 80+ requests. Report records every reserved attempt/tier and
its terminal outcome; successful-only ProviderUsage cannot substitute for this receipt.

### Snapshot, common seam and loading

At trigger_run before execution, resolve Project/Case refs and create immutable UXRunSnapshot:
policy values, configured provider identity, ordered case ids, full persona values per resolved
ref, persona content digest and report schema version. UserPersona.id is an explicit stable
slug (pattern `[a-z][a-z0-9-]{0,63}`), independent of mutable content; snapshot digest detects
edits. Missing project ref/case override -> per-case skipped_missing_persona, never fallback
from an explicitly missing case ref to a different project persona.

Persist the snapshot as a typed optional field on Run; disabled flag records disabled policy
without creating UX findings/report. In trigger_run AFTER store.save_run and all result/verdict
persistence (entry/serial/parallel share this point), call proposed
ux_advisory.complete_advisory_run(store, run, snapshot, secrets). It reloads authoritative
functional artifacts, reads no live page and processes run.case_ids once in order. No call
inside execute.py or functional pipeline grading. Future CLI/regression callers must reuse
this SAME completion function after their own persisted Run; direct standalone run_case is
not falsely claimed to have integrated run-level UX.

If ux_report.json exists for the matching snapshot digest and terminal report status, reuse it
without calls; a partial/interrupted report is explicitly incomplete, and this first unit
refuses automatic reattempt (which could reset the budget). Human-directed new run has a new
run id/budget. This proposal does not promise retry/resume functionality.
ProjectStore::load_results:166 excludes exactly `run.json`, exactly `ux_report.json`, and
existing *.verdict.json; DO NOT ignore arbitrary failed JSON loads. A malformed case result
must still fail as before. Unknown auxiliary JSON is not silently licensed.

### Capped files — concrete destinations and bounded projected results

These are source-read projections, not edited-file measurements or doctor PASS. Maker's plan
must include actual patch/count proof before any behavior work. Preserve original public
imports/callers with single imported definitions, not duplicate wrappers.

| File baseline | Concrete change/destination | Proposed maximum after change |
|---|---|---|
| report_export.py 299 | Move existing export_excel:114-159 body to existing core/excel.py as `export_run_workbook`; keep public export_excel a <=12-line facade loading typed cases/results/verdicts/redactor/UX report. Presentation helper receives data, imports no ProjectStore. Add UX sheet there; _case_section delegates UX fragment to ux_advisory renderer. | report_export <=280; core/excel <=120; each function <=50 |
| project_store.py 300 | Move run persistence block save_run:157 through load_verdicts:182-191 to proposed store/run_store.py::RunStoreMixin; import/inherit it in ProjectStore. New typed persona/UX facade methods in same mixin where run adjuncts belong; preserve save_run/load_run/save_result/load_results/save_verdict/load_verdicts API names. | project_store <=270; run_store <=150 |
| enums.py 300 | Keep all vocabularies in place. Condense Action docstring (24-30) from 7 lines to 3 preserving D-005/D-014/C3 and four names; CaseClass (54-59) 6->3 preserving per-flow applicable-class guarantee; TraversalStrategy (255-257) 3->2 preserving BFS/DFS/unchanged X4; NodeStatus skipped docstring (271-273) 3->2 preserving not-explored. Saves 9 lines; add TechComfort LOW/MEDIUM/HIGH with 7-line declaration including separation. | 298 before concurrent changes; no semantic/string-value movement |
| paths.py 287 | Add user_personas property and run_ux_report method, each 3-5 lines beside existing persona/run paths. | <=299 |
| schema/run.py 107 | measured conditions + optional RawResult field + Run UX snapshot field using dedicated schema model import. | <=150 |
| execute.py 213; conditions.py 63 | add capture/helper/condition threading, re-use existing `_result` and keep run_case <=50 through existing-module small helpers. | <=260 / <=110 |

Existing core/excel.py currently contains autosize_columns only, 21 lines; workbook presentation
is its declared responsibility. Moving persisted-run store methods to CrawlStoreMixin or
RequestStoreMixin would misstate their jobs and is rejected here. The new RunStoreMixin path
is a specific authorization prerequisite, not a path created by this document. No movement
of functional grade.py/run_case_pipeline rubric code or Verdict classes.

### Exact creation authority still unresolved

Root must resolve the following HUMAN-ONLY exact new-file authorization before creation,
because user-level edit-in-place rules require explicit new-file consent, and existing gate A
settles product direction rather than these names:
`src/autotester/schema/ux_report.py`, `src/autotester/stages/ux_advisory.py`,
`src/autotester/store/run_store.py`, `tests/test_user_persona.py`.
`src/autotester/schema/user_persona.py` and package-resolved
`src/autotester/skills/ux_judge/SKILL.md` have stronger explicit plan/contract names, but root
must still verify exact path consent in current session before writing. Do not claim D-050's
contract-write authority approves arbitrary new source modules. No human question is emitted
here; review and all reversible proposal work come first. A source path already explicitly
approved in session requires no repeated question. Requirements are not weakened to evade this.

Remaining engineering review items: actual retry-disabled physical transport feasibility,
exact patch/count demonstration, immutable snapshot schema and per-artifact persistence error
handling. Those are maker/reviewer work, not automatically human product gates. Settled A and
PU1-PU9 remain unchanged; mini-grill/status gates are not claimed completed by this addendum.

## Refinement 2 — independently raised gaps addressed in proposal

Scope remains QA preparation only; no source, SDK, browser, transport or implementation run.
This addendum supersedes conflicting condition/export/count text above. Current root source
was read at bd2fe8f4; the separate T-151 candidate/checker lane is not consumed here.

### Evidence-local conditions, not an initial/final inference

Remove the claim that two equal samples establish conditions "throughout" a case. Define
ExecutionConditions as proposed above, and add an optional `conditions: ExecutionConditions`
to existing schema/run.py::Evidence. Unknown is explicit; legacy Evidence.conditions=None
is insufficient for a persona assertion. Retain an optional RawResult summary only as an
observed summary, never the authority for a screenshot's conditions.

Exact capture seam is browser/evidence.py::EvidenceMixin.screenshot:31, not session.py.
Immediately before each physical page.screenshot (including its transient-CDP retry), sample
viewport_size and navigator.language through conditions.observe; immediately after, sample
again. Associate the successful screenshot's exact path/step_order with those samples only
when equal and both complete; mismatch or sampling error -> unknown/error conditions. The
retry discards the failed attempt's sample and samples anew. This is explicitly the capture
interval's measured condition, not proof about every instant of the whole case or device OS.
`_record:56` accepts this typed observation and persists it with that Evidence. Existing
step ordering/case evidence slicing stays intact. Capture occurs while enactment is active,
before execute.py::run_case finally resets viewport.

UX findings must name one supplied Evidence path AND step_order and are validated against
that item's conditions, not final-case conditions. DOM/URL evidence without their own measured
condition may supply functional context but cannot establish the persona locale/device claim.
Never combine incompatible screenshots into one claimed condition: eligible evidence is selected
per matching persona; unselected/unknown screenshots are recorded as omitted_condition reasons.
If no eligible measured screenshot remains -> skipped_condition, zero attempts/findings.
NOT_RUN -> zero findings irrespective of stray evidence. A phone/touch/emulation claim remains
unsupported; mobile_viewport is the only measured mobile layout claim proposed here.

Independent fixtures must include viewport changing then returning between start/end while
an intermediate screenshot has mismatched dimensions: that screenshot cannot be cited. Also
test capture retry resampling, missing step identity, unknown locale, conflicting screenshots,
legacy unmapped evidence, and a sabotage replacing per-evidence selection with summary-only
selection. Thus the plan cannot pass on a start/end equivalence test alone.

### Snapshot guard before any persistent write

Use full persona values only transiently in memory until ALL assembled snapshot strings have
passed SecretStore.guard_prompt/assert_no_raw_secrets, with the loaded root SecretStore's
known secrets including undeclared root values. This guard occurs BEFORE store.save_run or
write_json, not merely before the later Provider call. Reject any value whose scrubbed form
differs from input; do not scrub it into a different persona silently and then preserve the
old digest as if it were the original identity. Compute the content digest only on the exact
guarded canonical typed snapshot; stable persona id is also guarded and validated before use.
Case/project refs remain distinct and case override precedence stays exact.

A denied/malformed persona produces no full snapshot persistence. Persist a minimal typed
advisory-snapshot status containing safe run/case identity and stable reason code only;
persona ref is included only if itself guarded. Functional execution/reporting stays available;
the existing opt-in request does not imply a functional failure. Exception text, validation
input snippets, failed-path details and cause strings are passed through the same Redactor
before any operator/log/artifact surface. Literal scrubbing is followed by assert_clean;
if folded/encoded credentials remain, emit only a fixed safe reason code, without exception
text or causes. Apply this same scrub-plus-assert_clean boundary to observed locale and
measurement_error strings before Evidence.conditions persistence. Persistence errors are visible advisory_unavailable
with safe identity, not zero findings. If the error receipt itself cannot persist, report the
sanitized failure through the existing response/log surface and do not claim an on-disk status.
No broad filestore error swallowing or replacement of malformed functional-result semantics.

Tests independently insert synthetic secrets into each persona field/ref, provider identity,
snapshot error text and storage exception; spies assert zero snapshot writes on guard denial,
no raw value in any receipt/response/log, unchanged safe id and canonical digest for valid input.
Removing the pre-save guard must make the named zero-write test fail before any model call.

### Exact enum replacement arithmetic

Earlier 7/6-line docstring estimates were wrong. Read-only regex matching of the current file
measured Action 6 docstring lines, CaseClass 5, TraversalStrategy 3, skipped-state 2.
These exact proposed replacements preserve the criteria/decision meaning:

```text
Action (2 lines):
    """Browser actions; BACK/HOVER/PRESS_KEY/SCROLL serve the Track B explorer.
    D-005/D-014 authorize those additions; this shared vocabulary prevents C3 drift."""
CaseClass (2 lines):
    """Edge-case taxonomy, the product differentiator: expansion covers each
    applicable class per flow so the agent cannot drift to happy-path-only tests."""
TraversalStrategy (2 lines):
    """CR1 frontier order: hybrid combines BFS with bounded per-workflow DFS.
    X4 retains its existing four bounds."""
NodeStatus.SKIPPED_UNCHANGED (1 line):
    """CR3/CR5: stored PersonaScreen not revisited; never folded into EXPLORED."""
```

Savings: (6-2)+(5-2)+(3-2)+(2-1)=9. Read-only in-memory substitution of exactly
those four anchors returned `DOC-ONLY PROJECTED LINES 291`. A seven-line allocation for
TechComfort (two separators, class, one-line docstring and LOW/MEDIUM/HIGH) yields 298.
No source was changed. Each source anchor must match exactly once in the actual candidate;
concurrent T-151 AiTargetKind additions require remeasurement, not carrying 298 forward.
If the current integrated enum needs more headroom, that is a concrete new plan revision;
this calculation is not a waiver. No enum values/CaseClass mapping moved or duplicated.

### Workbook extraction without hidden stage dependencies

Existing report_export.py::_failure_rows:87, _repro_steps:95 and _needs_developer_detail:81
remain their single definitions in the exporter. Precompute the complete existing eleven-column
rows there, including redaction, failure text and repro text; pass header plus rows and separately
precomputed UX header/rows into core/excel.py::export_run_workbook. The Excel helper imports only
Workbook/presentation primitives and calls existing autosize_columns; it imports no report_export,
ProjectStore, provider, case/verdict model or UX stage. It formats/saves workbook data, never
rederives result truth. No duplicated _failure_rows/_repro_steps or circular stage import.
To stay under 50 function lines, extract the existing row computation into one local
report_export helper (new helper in an EXISTING file, replaces inline block; no duplicate).
Public export_excel remains the stable facade. The previous <=280 report budget is a projection
to re-evaluate from this exact split, not a guaranteed result; fresh reviewer must count the
concrete proposed patch before approval. Existing column text/order is byte/value compared
against the pre-unit fixture workbook, plus a separate UX sheet.

### Still unresolved and next safe step

Independent review receipt (2026-10-05, /root/codex_policy_parser_verify):
VERDICT Block for implementation-plan approval, not a task verdict. Static
review validated evidence-local conditions, pre-save guarded digests, enum
anchors and workbook dependency split. It found three remaining concrete gaps:
logical model.invoke is not physical-send enforcement; a single-provider
candidate cannot preserve configured multi-vendor fidelity; complete candidate
file/function counts are absent. Reviewer measured current enums300,
report-exporter299, evidence61, run-schema107, Excel-helper21 lines. These are
current baseline counts, not candidate counts or execution evidence.
Implementation-ready design must name installed transport injection/reservation
sites across retries, fallback, uploads, redirects and failed sends, propagate
budget exhaustion without fallback swallowing it, and refuse unsupported
capability before sending. Preserve configured vendor/model identities and
fallback order. Exact new-path consent remains unresolved; answer A is settled.
No SDK imports/calls, tests, browser, network or code edits occurred in review.

UNRESOLVED engineering: every supported provider's physical retry/output-token capability
needs exact pinned-adapter source/documentation proof. A LangChain invoke count and guessed
SDK option are insufficient; no option keys are invented here. Disable paid UX operation on
unsupported capability with a typed reason. Fake transport oracles establish the intended
contract but are not evidence that a particular vendor SDK enforces it.
UNRESOLVED authorization/process: exact new source/test paths listed above and the existing
mini-grill/intent/spec/plan prerequisites remain unfulfilled unless root finds explicit current
session authority. Answer A stays settled and must not be re-asked. This preparation does not
emit an approval request or substitute an appendix for those approvals.
UNRESOLVED count proof: new evidence mapping grows schema/run and evidence.py; complete
candidate patch, actual file/function counts and preserved callers must be reviewed together.

NEXT SAFE PLAN STEP: root dispatches a fresh read-only reviewer over this refined proposal,
asking it to validate evidence-local PU8, pre-save guard ordering, the four exact enum anchors,
workbook dependency graph and remaining provider/path gates. In parallel with that read-only
review, inventory pinned installed provider adapter retry/output settings without importing SDKs
or running them, and prepare a concrete in-memory patch/count preview. Implementation remains
held; neither task PASS nor the sole T-151 runtime lane is touched.

## UNAPPROVED concrete schema/storage/workbook preview — 2026-10-06

Attribution: /root/review_t196_writepolicy_occurrences · BUILDING maker preparation only.
Architecture and settled Refinement 2 read first. No product, test, schema, browser or new file has been edited. Exact six-path consent and independent PLAN approval remain pending. Other reviewer owns physical-provider readiness. This is a partial actual full-text candidate, not an implementation-ready feature or acceptance verdict.

Completed in-memory full-text coverage: schema/enums.py (four exact docstring replacements + TechComfort); schema/project.py (optional ref/default-off); schema/case.py (optional override/preserved with_fixed_step); schema/run.py (legacy-compatible optional Evidence.conditions); core/paths.py (central persona JSONL and nested run ux/report.json); store/project_store.py (run facade extraction); core/excel.py and stages/report_export.py (workbook extraction); proposed schema/user_persona.py, schema/ux_report.py, store/run_store.py. All candidates below are actual whole source strings, not line-count estimates. New module paths are PROPOSALS ONLY, not created.

Preservation proof by literal candidate comparison: the existing eleven-column row computation is moved unchanged except ws.append -> rows.append and loop iterable injection; original header column values/order retained exactly. Original six run facade method bodies/signatures are copied verbatim to RunStoreMixin. Existing public export_excel signature is unchanged. No Verdict/Rubric/grade function or model is touched. Workbook helper imports Workbook/presentation primitives only, never a stage, store, model or provider. Persona/UX facade saves require explicit Redactor.assert_clean before write; UX reports use nested ux/report.json so load_results' *.json scan never mistakes UX for RawResult. New advisory report run identity is checked against stored run.

NOT COMPLETE: guarded canonical run/persona snapshot + digest/status schema and before-save-run orchestration; physical budget and configured-provider wiring; browser/conditions.py observe and browser/evidence.py retry-local capture sampling/record threading; eligibility validator + UX prompt/provider reader; UX HTML fragment/section; UI post-run opt-in integration; actual proposed ux_advisory.py/test_user_persona.py/SKILL.md bodies. The observation type alone is not capture proof; the workbook scaffold is not a working UX producer. schema/run.py RawResult/Run snapshot modifications were deliberately NOT invented to fill this gap. stages/conditions.py does not exist: actual enact/reset seam is browser/conditions.py. Current browser/evidence.py is 92 lines and execute.py 231, not the historical 61/213 assumptions. Future integration must remeasure caps; this subset cannot certify whole-feature <=300/<=50.

Current root identities (before preview; unchanged product files):

```jsonl
{"path":"src/autotester/schema/enums.py","sha256":"CFEC1B7A5FAB31FBC5F20C30ADF1F81CE3E476CD3163BC5EB4A60197759C00F8","lines":300}
{"path":"src/autotester/schema/project.py","sha256":"93654FBB0B8D8A92F2B911178DF1BF099195E678F9B70755ED65E5035FF33614","lines":167}
{"path":"src/autotester/schema/case.py","sha256":"2AAC1B00E771C52B7C09C5D0303C2D98E29B13C4487B72FC26CFBCF8BF7BD544","lines":128}
{"path":"src/autotester/schema/run.py","sha256":"D6D35F6A6754375706B7C728F7E1EDB21A98EFDF95C2DFA3A4B1B44CA880C7D6","lines":107}
{"path":"src/autotester/core/paths.py","sha256":"C37A23D5E6165268AA05E5ECE60A1B73B3315A528DB172D888964BB5CCF121BA","lines":287}
{"path":"src/autotester/core/excel.py","sha256":"E8A0CFD5EC76B098E6E4C7BAE22E451F5D5A55A65365927F9EE91CA21FF57894","lines":21}
{"path":"src/autotester/store/project_store.py","sha256":"6CE43E91B0F2DB23A8E12CEE004710C3701E7577C281F09552A5F9949C15D588","lines":300}
{"path":"src/autotester/browser/evidence.py","sha256":"39A13D06A4C268AC8099E858C906D603CBC8A3460B9A37BC600E0812B15E54B8","lines":92}
{"path":"src/autotester/stages/report_export.py","sha256":"1A28EFEB639C68E6B7A8348779409A66A7CBFD12DA1AFCDC99F5D77FE591F2B8","lines":299}
{"path":"src/autotester/stages/execute.py","sha256":"7033186AB6602DE4E3023B52867FB1FF7F20ADE599CEA230B80B8A2C7648DF69","lines":231}
```

Candidate whole-text JSONL (one source string per planned path; data-only AST/count diagnostic may consume this exact block):

<!-- T190-SCHEMA-WORKBOOK-PREVIEW-BEGIN -->
```jsonl
{"path":"src/autotester/schema/enums.py","source":"\"\"\"Every closed vocabulary in the system. Nothing else defines these strings.\"\"\"\n\nfrom __future__ import annotations\n\nfrom enum import StrEnum\n\nfrom autotester.schema.issue_kind import IssueKind  # noqa: F401 -- re-exported (AT-600)\n\n\nclass SourceKind(StrEnum):\n    VIDEO = \"video\"\n    DOC = \"doc\"\n    TEXT = \"text\"\n    AUDIO = \"audio\"\n    EMAIL = \"email\"\n    DRIVE = \"drive\"\n    URL = \"url\"\n    EVAL = \"eval\"\n    CONDITION = \"condition\"\n    USE_CASE = \"use_case\"\n\n\nclass Action(StrEnum):\n    \"\"\"Browser actions; BACK/HOVER/PRESS_KEY/SCROLL serve the Track B explorer.\n    D-005/D-014 authorize those additions; this shared vocabulary prevents C3 drift.\"\"\"\n\n    NAVIGATE = \"navigate\"\n    CLICK = \"click\"\n    FILL = \"fill\"\n    SELECT = \"select\"\n    UPLOAD = \"upload\"\n    WAIT = \"wait\"\n    ASSERT = \"assert\"\n    BACK = \"back\"\n    HOVER = \"hover\"\n    PRESS_KEY = \"press_key\"\n    SCROLL = \"scroll\"\n\n\nclass CaseKind(StrEnum):\n    \"\"\"Coarse bucket a case belongs to.\"\"\"\n\n    BEST = \"best\"\n    WORST = \"worst\"\n    EDGE = \"edge\"\n    ANCHOR = \"anchor\"\n\n\nclass CaseClass(StrEnum):\n    \"\"\"Edge-case taxonomy, the product differentiator: expansion covers each\n    applicable class per flow so the agent cannot drift to happy-path-only tests.\"\"\"\n\n    HAPPY = \"happy\"\n    AUTH_WRONG_CREDS = \"auth_wrong_creds\"\n    AUTH_EXPIRED_SESSION = \"auth_expired_session\"\n    SERVER_ERROR = \"server_error\"\n    NETWORK_OFFLINE_SLOW = \"network_offline_slow\"\n    INPUT_EMPTY = \"input_empty\"\n    INPUT_BOUNDARY = \"input_boundary\"\n    INPUT_UNICODE_OVERSIZE = \"input_unicode_oversize\"\n    DOUBLE_SUBMIT = \"double_submit\"\n    BACK_REFRESH_MIDFLOW = \"back_refresh_midflow\"\n    DEEPLINK_UNAUTH = \"deeplink_unauth\"\n    CONCURRENT_TAB = \"concurrent_tab\"\n    LOCALE_I18N = \"locale_i18n\"\n    VIEWPORT_MOBILE = \"viewport_mobile\"\n    REGRESSION_ANCHOR = \"regression_anchor\"\n\n\nKIND_BY_CLASS: dict[CaseClass, CaseKind] = {\n    CaseClass.HAPPY: CaseKind.BEST,\n    CaseClass.AUTH_WRONG_CREDS: CaseKind.WORST,\n    CaseClass.AUTH_EXPIRED_SESSION: CaseKind.WORST,\n    CaseClass.SERVER_ERROR: CaseKind.WORST,\n    CaseClass.NETWORK_OFFLINE_SLOW: CaseKind.WORST,\n    CaseClass.INPUT_EMPTY: CaseKind.EDGE,\n    CaseClass.INPUT_BOUNDARY: CaseKind.EDGE,\n    CaseClass.INPUT_UNICODE_OVERSIZE: CaseKind.EDGE,\n    CaseClass.DOUBLE_SUBMIT: CaseKind.EDGE,\n    CaseClass.BACK_REFRESH_MIDFLOW: CaseKind.EDGE,\n    CaseClass.DEEPLINK_UNAUTH: CaseKind.EDGE,\n    CaseClass.CONCURRENT_TAB: CaseKind.EDGE,\n    CaseClass.LOCALE_I18N: CaseKind.EDGE,\n    CaseClass.VIEWPORT_MOBILE: CaseKind.EDGE,\n    CaseClass.REGRESSION_ANCHOR: CaseKind.ANCHOR,\n}\n\n\nclass Severity(StrEnum):\n    S1 = \"S1\"  # blocks a core flow\n    S2 = \"S2\"  # degrades a flow, workaround exists\n    S3 = \"S3\"  # cosmetic or minor\n\n\nclass TechComfort(StrEnum):\n    \"\"\"User technical comfort; distinct from issue severity.\"\"\"\n    LOW = \"low\"\n    MEDIUM = \"medium\"\n    HIGH = \"high\"\n\n\nclass CaseStatus(StrEnum):\n    PROPOSED = \"proposed\"\n    APPROVED = \"approved\"\n    RETIRED = \"retired\"\n\n\nclass ReviewStatus(StrEnum):\n    DRAFT = \"draft\"\n    APPROVED = \"approved\"\n    NEEDS_EDIT = \"needs_edit\"\n\n\nclass Outcome(StrEnum):\n    \"\"\"What the executor observed — NOT a judgement. Grading is separate.\"\"\"\n\n    COMPLETED = \"completed\"\n    ERRORED = \"errored\"\n    BLOCKED_HITL = \"blocked_hitl\"\n    ASSERTION_FAILED = \"assertion_failed\"\n    \"\"\"D-032/AT-540: a step's declared expectation (or an Action.ASSERT\n    step's expected state) deterministically did not hold at settle time.\n    An OBSERVATION, not a grade — the grader still owns the verdict.\"\"\"\n\n    NOT_RUN = \"not_run\"\n    \"\"\"D-045/AT-581/E6: condition not enacted; case did not run -- must never be judged PASS.\"\"\"\n\n\nclass Result(StrEnum):\n    \"\"\"The grader's verdict. Only the grader writes this.\"\"\"\n\n    PASS = \"PASS\"\n    FAIL = \"FAIL\"\n    BLOCKED = \"BLOCKED\"\n    INCONCLUSIVE = \"INCONCLUSIVE\"\n\n\nclass EvidenceKind(StrEnum):\n    SCREENSHOT = \"screenshot\"\n    DOM = \"dom\"\n    URL = \"url\"\n    NETWORK = \"network\"\n    TRACE = \"trace\"\n    CONSOLE = \"console\"\n    DB = \"db\"\n    VIDEO = \"video\"\n    \"\"\"T-191/AT-587: a kept run video (FAIL/INCONCLUSIVE only, masked, linked\n    in the report -- never embedded, report-export.md RE3's named exception).\"\"\"\n\n\nclass Trigger(StrEnum):\n    MANUAL = \"manual\"\n    CI = \"ci\"\n    SCHEDULE = \"schedule\"\n\n\nclass WritePolicy(StrEnum):\n    \"\"\"How much the tester is allowed to mutate in the target app.\"\"\"\n\n    READ_ONLY = \"read_only\"\n    TEST_ACCOUNT = \"test_account\"\n    ALLOW_WRITES = \"allow_writes\"\n\n\nclass ApprovalKind(StrEnum):\n    \"\"\"What a `RunApproval` authorises. D-018's two gates: READ is gate 1 (scope\n    of read access); everything else is gate 2 (an outward-facing run).\"\"\"\n\n    READ = \"read\"\n    CRAWL = \"crawl\"\n    ADVERSARIAL = \"adversarial\"\n    LIVE_CASE = \"live_case\"\n\n\nclass ProviderRole(StrEnum):\n    VISION = \"vision\"\n    AGENT = \"agent\"\n    JUDGE = \"judge\"\n\n\nclass RequestStatus(StrEnum):\n    OPEN = \"open\"\n    FULFILLED = \"fulfilled\"\n    DISMISSED = \"dismissed\"\n\n\nclass Participant(StrEnum):\n    HUMAN = \"human\"\n    AUTOTESTER = \"autotester\"\n\n\nclass FeatureEventKind(StrEnum):\n    \"\"\"What happened to a feature, as recorded in `docs/FEATURES.jsonl`.\"\"\"\n\n    PLANNED = \"planned\"\n    LIVE = \"live\"\n    UPDATED = \"updated\"\n    RETIRED = \"retired\"\n\n\nclass UserValue(StrEnum):\n    \"\"\"How much the product's user depends on a feature. Gates the reasoning ask.\"\"\"\n\n    HIGH = \"high\"\n    NORMAL = \"normal\"\n    LOW = \"low\"\n\n\nclass IssueCategory(StrEnum):\n    \"\"\"What kind of problem a video-derived `Issue` is. The first 12 come from the\n    proven external pipeline's bug taxonomy; `FEATURE_GAP`/`WRONG_MODEL`/`DATA_ERROR`\n    were added for D-014 after a real ground-truth workbook showed 10/33 rows were\n    spoken change requests with no home in the original 12 (\"this should be X\").\"\"\"\n\n    VALIDATION = \"validation\"\n    LAYOUT = \"layout\"\n    DEAD_END = \"dead_end\"\n    LATENCY = \"latency\"\n    BROKEN_LINK = \"broken_link\"\n    COPY_TEXT = \"copy_text\"\n    STATE_LOSS = \"state_loss\"\n    DATA_INCONSISTENCY = \"data_inconsistency\"\n    TRANSIENT_GLITCH = \"transient_glitch\"\n    NAVIGATION_CONFUSION = \"navigation_confusion\"\n    LOGIC_ERROR = \"logic_error\"\n    FEATURE_GAP = \"feature_gap\"\n    WRONG_MODEL = \"wrong_model\"\n    DATA_ERROR = \"data_error\"\n    OTHER = \"other\"\n\n\nclass IssueOrigin(StrEnum):\n    \"\"\"How an `Issue` was noticed — mirrors the human sheet's 'How we know'.\"\"\"\n\n    SPOKEN = \"spoken\"\n    SCREEN = \"screen\"\n    SPOKEN_AND_SCREEN = \"spoken_and_screen\"\n    MODEL_DETECTED = \"model_detected\"\n\n\nclass IssueStatus(StrEnum):\n    OPEN = \"open\"\n    CONFIRMED = \"confirmed\"\n    FIXED = \"fixed\"\n    DISMISSED = \"dismissed\"\n\n\nclass Confidence(StrEnum):\n    LOW = \"low\"\n    MEDIUM = \"medium\"\n    HIGH = \"high\"\n\n\nclass TraversalStrategy(StrEnum):\n    \"\"\"CR1 frontier order: hybrid combines BFS with bounded per-workflow DFS.\n    X4 retains its existing four bounds.\"\"\"\n\n    BFS = \"bfs\"\n    HYBRID = \"hybrid\"\n\n\nclass NodeStatus(StrEnum):\n    \"\"\"A crawled screen's state in the BFS frontier (Track B).\"\"\"\n\n    QUEUED = \"queued\"\n    EXPLORED = \"explored\"\n    ABORTED_DIALOG = \"aborted_dialog\"\n    ABORTED_ERROR = \"aborted_error\"\n    SKIPPED_UNCHANGED = \"skipped_unchanged\"\n    \"\"\"CR3/CR5: stored PersonaScreen not revisited; never folded into EXPLORED.\"\"\"\n\n\nclass EdgeOutcome(StrEnum):\n    \"\"\"What happened when the explorer tried one candidate action.\"\"\"\n\n    NAVIGATED = \"navigated\"\n    SAME_SCREEN = \"same_screen\"\n    DENIED_POLICY = \"denied_policy\"\n    SKIPPED_UNNAMED = \"skipped_unnamed\"\n    OFF_DOMAIN_REFUSED = \"off_domain_refused\"\n    DIALOG = \"dialog\"\n    ERRORED = \"errored\"\n\n\nclass CrawlStatus(StrEnum):\n    RUNNING = \"running\"\n    COMPLETED = \"completed\"\n    STOPPED_BOUND = \"stopped_bound\"\n    LOGIN_FAILED = \"login_failed\"\n    ABORTED = \"aborted\"\n    BLOCKED_NO_ACTIONS = \"blocked_no_actions\"\n    \"\"\"AT-242: the frontier emptied with every reachable action refused by policy\n    (denied > 0) and none performed (actions_used == 0). Distinct from COMPLETED\n    (nothing denied is genuinely explored) and LOGIN_FAILED (login didn't complete).\"\"\"\n    LOGIN_WALL = \"login_wall\"\n    \"\"\"X18/AT-458: no login case declared, every screen ends in a refused form\n    submit, no link led anywhere structurally different — the crawl met a\n    sign-in wall and saw nothing behind it. Never success.\"\"\"\n"}
{"path":"src/autotester/schema/project.py","source":"\"\"\"Project configuration and the secret contract. One directory per project.\"\"\"\n\nfrom __future__ import annotations\n\nfrom pydantic import BaseModel, ConfigDict, Field, field_validator\n\nfrom autotester.schema.base import Artifact\nfrom autotester.schema.crawl import PermittedControl\nfrom autotester.schema.enums import ProviderRole, SourceKind, WritePolicy\n\nDEFAULT_VISION_PROVIDER = \"gemini\"\n\"\"\"AT-550: the vision provider `vision_ensemble()` substitutes when the\nconfigured `vision` string is empty. Named explicitly so the substitution\nis a documented constant, not a bare literal buried in the fallback — and so\n`vision_ensemble_defaulted()` below can tell callers when this happened.\"\"\"\n\n\nclass SecretRef(BaseModel):\n    \"\"\"A declared credential. Holds the KEY and its scope — never the value.\n\n    The value lives only in the repo-root `.env` and is substituted at the\n    moment of typing into the browser, scoped to `domains`.\n    \"\"\"\n\n    model_config = ConfigDict(extra=\"forbid\")\n\n    key: str = Field(pattern=r\"^[A-Z][A-Z0-9_]*$\")\n    description: str | None = None\n    domains: list[str] = Field(default_factory=list, description=\"hosts this may be typed into\")\n    include_subdomains: bool = Field(default=True, strict=True)\n    mask_in_screenshot: bool = True\n\n    @field_validator(\"key\")\n    @classmethod\n    def _reject_value_like(cls, value: str) -> str:\n        if len(value) > 64:\n            raise ValueError(\"secret key looks like a value, not a name\")\n        return value\n\n    @field_validator(\"domains\")\n    @classmethod\n    def _reject_blank_domains(cls, domains: list[str]) -> list[str]:\n        \"\"\"A blank domain would match an empty host and open the gate (AT-001).\"\"\"\n        cleaned = [d.strip().lower().lstrip(\".\") for d in domains]\n        if any(not d for d in cleaned):\n            raise ValueError(\"secret domains must be non-empty hostnames\")\n        return cleaned\n\n\nclass ProviderConfig(BaseModel):\n    \"\"\"Which provider serves each role. Roles are swappable per project.\n\n    AT-542: `vision` may name SEVERAL providers, comma-separated\n    (`\"gemini,anthropic\"`), which run as the video ensemble — the one place\n    where agreement between independent readings is the signal itself\n    (qa/contracts/video-learning.md). A single name is an ensemble of one and\n    is exactly what the F-039 overstatement was: real agreement never ran.\n    `for_role` returns the whole string; the analyze callers split it.\"\"\"\n\n    model_config = ConfigDict(extra=\"forbid\")\n\n    vision: str = \"gemini\"\n    agent: str = \"langchain-fallback\"\n    judge: str = \"langchain-fallback\"\n\n    def for_role(self, role: ProviderRole) -> str:\n        return getattr(self, str(role))\n\n    def _configured_vision_providers(self) -> list[str]:\n        \"\"\"The vision provider ids explicitly named in `vision`, in order,\n        deduplicated — empty when the config is blank/whitespace/commas\n        only. No fallback here; shared by `vision_ensemble()` (which applies\n        the default) and `vision_ensemble_defaulted()` (which reports\n        whether it had to), so the parsing rule lives in exactly one place.\"\"\"\n        seen: list[str] = []\n        for name in self.vision.split(\",\"):\n            name = name.strip()\n            if name and name not in seen:\n                seen.append(name)\n        return seen\n\n    def vision_ensemble(self) -> list[str]:\n        \"\"\"The vision provider ids in order, deduplicated — the ensemble the\n        analyze callers run. One entry = ensemble of one (honest, not an\n        error: a single credential must still work).\"\"\"\n        return self._configured_vision_providers() or [DEFAULT_VISION_PROVIDER]\n\n    def vision_ensemble_defaulted(self) -> bool:\n        \"\"\"AT-550: True when `vision` was empty and `vision_ensemble()`\n        substituted `DEFAULT_VISION_PROVIDER` — distinct from an operator who\n        explicitly configured that same single provider. An empty config\n        falling back to a default must be observable, not silent; callers\n        (`ui/routes_sources.py`, `cli_video.py`) record this alongside\n        `requested_providers` on the persisted `VideoAnalysis` so a defaulted\n        run is never indistinguishable from an explicit one.\"\"\"\n        return not self._configured_vision_providers()\n\n\nclass Source(Artifact):\n    \"\"\"An immutable input the system learned from.\"\"\"\n\n    id: str = \"\"\n    project: str\n    kind: SourceKind\n    path: str | None = Field(default=None, description=\"project-relative, for video/doc\")\n    text: str | None = Field(default=None, description=\"inline body, for kind=text\")\n    url: str | None = None\n    sha256: str | None = None\n    duration_s: float | None = None\n    label: str | None = None\n    notes: str | None = None\n    recorded_on: str | None = Field(\n        default=None, description=\"ISO date, e.g. the Excel 'Date' column\"\n    )\n\n    def model_post_init(self, _context: object) -> None:\n        if not self.id:\n            from autotester.core.ids import content_id\n\n            key = self.sha256 or self.url or self.text or self.path or self.label\n            object.__setattr__(self, \"id\", content_id(\"src\", {\"k\": str(self.kind), \"v\": key}))\n\n\nclass Project(Artifact):\n    \"\"\"Everything the system needs to test one product.\"\"\"\n\n    slug: str = Field(pattern=r\"^[a-z][a-z0-9-]*$\")\n    name: str\n    base_url: str\n    allowed_domains: list[str] = Field(\n        default_factory=list,\n        description=\"the browser may only be driven here; secrets scoped within\",\n    )\n    write_policy: WritePolicy = WritePolicy.READ_ONLY\n    max_parallel: int = Field(\n        default=1, ge=1,\n        description=\"ceiling on concurrently-running cases (T-173/D-041); the run's actual N \"\n                    \"is min(this, a measured RAM/CPU budget) -- see stages/parallel_run.py\",\n    )\n    permitted_surface: list[PermittedControl] = Field(\n        default_factory=list,\n        description=\"coverage.md V9: the controls the supplied account's role PERMITS — the \"\n                    \"denominator a crawl's coverage figure is measured against. Empty means \"\n                    \"the permitted surface is UNKNOWN, and coverage reports its denominator \"\n                    \"as screens-reached instead of silently claiming permission coverage. \"\n                    \"Declaring it never narrows a run (qa/gates/write-policy-tier.md): the \"\n                    \"account's own permissions are the scope, and this only names them so a \"\n                    \"control never reached can be listed rather than vanish from the figure.\",\n    )\n    secrets: list[SecretRef] = Field(default_factory=list)\n    providers: ProviderConfig = Field(default_factory=ProviderConfig)\n    headed: bool = Field(default=True, description=\"real visible browser by default\")\n    description: str | None = None\n    user_persona_ref: str | None = Field(default=None, pattern=r\"^[A-Za-z0-9_-]{1,100}$\")\n    ux_enabled: bool = Field(default=False, strict=True)\n    login_case_id: str | None = Field(\n        default=None,\n        description=\"the case a crawl logs in with before exploring — declared once, here, \"\n                    \"and used by every entry point (X17); None means the product is crawled \"\n                    \"signed out\",\n    )\n\n    def secret(self, key: str) -> SecretRef | None:\n        return next((s for s in self.secrets if s.key == key), None)\n\n    def allows_domain(self, host: str) -> bool:\n        \"\"\"True when `host` is the base host or an allowed domain (or subdomain).\"\"\"\n        candidates = list(self.allowed_domains)\n        return any(host == d or host.endswith(f\".{d}\") for d in candidates)\n"}
{"path":"src/autotester/schema/case.py","source":"\"\"\"A test case — one falsifiable claim about the product, plus how to check it.\"\"\"\n\nfrom __future__ import annotations\n\nfrom pydantic import BaseModel, ConfigDict, Field, model_validator\n\nfrom autotester.core.ids import content_id\nfrom autotester.schema.base import Artifact\nfrom autotester.schema.enums import Action, CaseClass, CaseKind, CaseStatus, Severity\nfrom autotester.schema.flowspec import Step\n\n\nclass Case(Artifact):\n    \"\"\"One generated or hand-written test case.\n\n    Cases are content-addressed: the same flow + class + steps always produces\n    the same id, so regenerating a flowspec does not duplicate the suite.\n    \"\"\"\n\n    id: str = \"\"\n    project: str\n    flow_id: str\n    kind: CaseKind\n    case_class: CaseClass\n    title: str\n    rationale: str | None = Field(default=None, description=\"why this case is worth running\")\n    preconditions: list[str] = Field(default_factory=list)\n    steps: list[Step] = Field(default_factory=list)\n    severity: Severity = Severity.S2\n    user_persona_ref: str | None = Field(default=None, pattern=r\"^[A-Za-z0-9_-]{1,100}$\")\n    rubric_ref: str | None = None\n    script_ref: str | None = None\n    status: CaseStatus = CaseStatus.PROPOSED\n    pinned: bool = Field(\n        default=False,\n        description=\"AT-585: born from a confirmed Issue (stages/issues.py::\"\n                     \"pin_issue_as_case). A pinned case is included in every \"\n                     \"regression run (it is just another row `list_cases()` \"\n                     \"returns — no run-time filtering exists to bypass) and \"\n                     \"`ProjectStore.delete_case` refuses to remove it. This is \"\n                     \"deliberately NOT a priority system: T-178 (p0-p3 + human \"\n                     \"pruning before LLM spend) is expected to subsume `pinned` \"\n                     \"with `priority == p0` once it lands, at which point this \"\n                     \"flag becomes redundant and can be retired in that unit.\",\n    )\n    pinned_issue_id: str | None = Field(\n        default=None,\n        description=\"Traceability to the Issue this case was pinned from. \"\n                     \"Never a new CaseClass member -- D-005/D-014 keep \"\n                     \"CaseClass closed; Issue stays a separate artifact.\",\n    )\n\n    @model_validator(mode=\"after\")\n    def _pinned_issue_id_needs_the_flag(self) -> Case:\n        if self.pinned_issue_id and not self.pinned:\n            raise ValueError(\"pinned_issue_id is set but pinned is False\")\n        return self\n\n    def model_post_init(self, _context: object) -> None:\n        if not self.id:\n            object.__setattr__(self, \"id\", self.compute_id())\n\n    def compute_id(self) -> str:\n        payload = {\n            \"project\": self.project,\n            \"flow_id\": self.flow_id,\n            \"case_class\": str(self.case_class),\n            \"steps\": [s.model_dump(mode=\"json\") for s in self.steps],\n        }\n        return content_id(\"case\", payload)\n\n    def with_fixed_step(self, order: int, fix: AgentFix) -> Case:\n        \"\"\"A new `Case` with the step at `order` replaced by `fix`. Content-addressed,\n        so the same fix applied twice never produces two rows (`ProjectStore.add_case`).\"\"\"\n        new_steps = [\n            Step(order=order, action=fix.action, target=fix.target, value=fix.value,\n                 expected=s.expected, source_ref=s.source_ref, note=f\"agent fix: {fix.reasoning}\")\n            if s.order == order else s\n            for s in self.steps\n        ]\n        return Case(\n            project=self.project, flow_id=self.flow_id, kind=self.kind,\n            case_class=self.case_class, title=self.title, rationale=self.rationale,\n            preconditions=self.preconditions, steps=new_steps, severity=self.severity,\n            rubric_ref=self.rubric_ref, script_ref=self.script_ref, status=self.status,\n            user_persona_ref=self.user_persona_ref,\n        )\n\n\nclass AgentFix(BaseModel):\n    \"\"\"The agent's proposed correction for one failing step.\"\"\"\n\n    model_config = ConfigDict(extra=\"forbid\")\n\n    action: Action\n    target: str\n    value: str | None = None\n    reasoning: str = Field(min_length=1, description=\"why this should fix the observed error\")\n\n\nclass ExpandedSteps(BaseModel):\n    \"\"\"One taxonomy class's proposed steps for a flow — `stages/expand.py`'s raw\n    model answer, turned into a `Case` by the stage (never trusted verbatim as a\n    finished artifact: an empty `steps` list means \"not applicable here\").\"\"\"\n\n    model_config = ConfigDict(extra=\"forbid\")\n\n    steps: list[Step] = Field(default_factory=list)\n    rationale: str = Field(min_length=1, description=\"why these steps test this class, or why \"\n                            \"the class doesn't apply (when steps is empty)\")\n\n\nclass Script(Artifact):\n    \"\"\"A durable Playwright script produced once an agent gets a case working.\n\n    The point of the whole execution model: after the first successful agent\n    run, a case costs zero tokens to re-run.\n    \"\"\"\n\n    id: str = \"\"\n    case_id: str\n    path: str = Field(description=\"repo-relative path under projects/<slug>/scripts/\")\n    generated_by: str = Field(description=\"provider id, or 'human'\")\n    iterations: int = Field(default=1, description=\"agent attempts before it worked\")\n    stable_runs: int = Field(default=0, description=\"consecutive passes since last edit\")\n\n    def model_post_init(self, _context: object) -> None:\n        if not self.id:\n            payload = {\"case\": self.case_id, \"p\": self.path}\n            object.__setattr__(self, \"id\", content_id(\"scr\", payload))\n"}
{"path":"src/autotester/schema/user_persona.py","source":"\"\"\"Typed user identity used only by the separate advisory UX reader.\"\"\"\n\nfrom pydantic import Field\n\nfrom autotester.schema.base import Artifact\nfrom autotester.schema.enums import TechComfort\n\n\nclass UserPersona(Artifact):\n    \"\"\"Stable identity; locale/device remain assertions checked against evidence.\"\"\"\n\n    id: str = Field(pattern=r\"^[A-Za-z0-9_-]{1,100}$\")\n    role: str = Field(min_length=1, max_length=200, strict=True, pattern=r\"\\S\")\n    tech_comfort: TechComfort\n    locale: str = Field(min_length=1, max_length=100, strict=True, pattern=r\"\\S\")\n    device: str = Field(min_length=1, max_length=100, strict=True, pattern=r\"\\S\")\n"}
{"path":"src/autotester/schema/ux_report.py","source":"\"\"\"Separate advisory findings and evidence-local observed conditions; never verdicts.\"\"\"\n\nfrom typing import Literal\n\nfrom pydantic import BaseModel, ConfigDict, Field, model_validator\n\nfrom autotester.schema.base import Artifact\nfrom autotester.schema.enums import Severity\n\n\nclass ExecutionConditions(BaseModel):\n    \"\"\"Successful screenshot interval observation, not whole-case/device-OS proof.\"\"\"\n\n    model_config = ConfigDict(extra=\"forbid\")\n    width: int | None = Field(default=None, ge=1)\n    height: int | None = Field(default=None, ge=1)\n    locale: str | None = None\n    status: Literal[\"observed\", \"unknown\"] = \"unknown\"\n    measurement_error: str | None = None\n\n    @model_validator(mode=\"after\")\n    def _complete_observation(self):\n        if self.status == \"observed\" and (\n            self.width is None or self.height is None or not self.locale\n            or self.measurement_error is not None\n        ):\n            raise ValueError(\"incomplete observed conditions\")\n        return self\n\n\nclass UXFinding(BaseModel):\n    \"\"\"A finding cites exactly one eligible supplied screenshot and its step.\"\"\"\n\n    model_config = ConfigDict(extra=\"forbid\")\n    case_id: str\n    evidence_path: str\n    step_order: int = Field(ge=0)\n    severity: Severity\n    finding: str = Field(min_length=1, max_length=2000, strict=True)\n    persona_id: str = Field(pattern=r\"^[A-Za-z0-9_-]{1,100}$\")\n\n\nclass UXReport(Artifact):\n    \"\"\"Separate per-run advisory artifact; no functional-result field.\"\"\"\n\n    run_id: str = Field(pattern=r\"^[A-Za-z0-9_-]{1,100}$\")\n    project: str\n    status: Literal[\"completed\", \"skipped_condition\", \"advisory_unavailable\"]\n    findings: list[UXFinding] = Field(default_factory=list)\n    reasons: list[str] = Field(default_factory=list)\n\n    @model_validator(mode=\"after\")\n    def _noncomplete_has_no_findings(self):\n        if self.status != \"completed\" and self.findings:\n            raise ValueError(\"unavailable advisory cannot contain findings\")\n        return self\n"}
{"path":"src/autotester/schema/run.py","source":"\"\"\"What EXECUTE observed. Deliberately contains no judgement — see verdict.py.\"\"\"\n\nfrom __future__ import annotations\n\nfrom datetime import datetime\nfrom typing import Literal\n\nfrom pydantic import BaseModel, ConfigDict, Field\n\nfrom autotester.core.ids import run_id as _mint_run_id\nfrom autotester.schema.base import Artifact\nfrom autotester.schema.enums import EvidenceKind, Outcome, Trigger\nfrom autotester.schema.ux_report import ExecutionConditions\n\n\nclass Evidence(BaseModel):\n    \"\"\"A file or value the grader may cite. Already redacted and masked.\"\"\"\n\n    model_config = ConfigDict(extra=\"forbid\")\n\n    kind: EvidenceKind\n    path: str = Field(description=\"run-relative path, or the literal value for url/dom\")\n    step_order: int | None = None\n    label: str | None = None\n    masked: bool = Field(default=True, description=\"secrets removed before storage\")\n    conditions: ExecutionConditions | None = None\n\n\nclass ProviderUsage(BaseModel):\n    \"\"\"Token and call accounting per provider role — the cost story per run.\"\"\"\n\n    model_config = ConfigDict(extra=\"forbid\")\n\n    provider: str\n    role: str\n    calls: int = 0\n    input_tokens: int = 0\n    output_tokens: int = 0\n\n\nclass RawResult(Artifact):\n    \"\"\"One case's execution record.\"\"\"\n\n    case_id: str\n    outcome: Outcome\n    used_script: bool = Field(default=False, description=\"False means the agent drove it\")\n    iterations: int = 1\n    duration_s: float = 0.0\n    error: str | None = None\n    hitl_prompt: str | None = Field(default=None, description=\"what the human must supply\")\n    not_run_reason: str | None = Field(\n        default=None,\n        description=\"D-045/AT-581 (E6): set when case_class named an execution condition \"\n                    \"(VIEWPORT_MOBILE/LOCALE_I18N) the executor could not enact -- outcome is \"\n                    \"then NOT_RUN and this names why, never a silent default-condition PASS\",\n    )\n    evidence: list[Evidence] = Field(default_factory=list)\n    log_ref: str | None = None\n\n\nclass RunBounds(BaseModel):\n    \"\"\"The `RunApproval` bounds a run ACTUALLY ran under (AT-660/CN10).\n\n    Recorded rather than capped. A bound can be present, non-zero, signed and\n    still constrain nothing — `projects/pathlynks/approvals.jsonl`'s live row\n    grants 600000000.0 wall-clock seconds, which is 19 years — and what counts\n    as a defensible maximum is a gate decision, not a build's. So the run's own\n    record states what it ran under, where a human reading `run.json` sees it,\n    and no ceiling is invented here.\n    \"\"\"\n\n    model_config = ConfigDict(extra=\"forbid\")\n\n    approval_id: str\n    max_actions: int\n    max_probes: int\n    wall_clock_s: float\n\n\nclass Run(Artifact):\n    \"\"\"One regression run over a set of cases.\"\"\"\n\n    id: str = Field(default_factory=_mint_run_id)\n    project: str\n    trigger: Trigger = Trigger.MANUAL\n    git_sha: str | None = None\n    label: str | None = None\n    case_ids: list[str] = Field(default_factory=list)\n    started_at: datetime | None = None\n    finished_at: datetime | None = None\n    usage: list[ProviderUsage] = Field(default_factory=list)\n    parallel_n: int | None = Field(\n        default=None,\n        description=\"T-173/D-041: cases that ran concurrently in this run; None means the run \"\n                    \"predates parallel execution or was not eligible for it\",\n    )\n    parallel_bound_by: Literal[\"config\", \"budget\", \"write_policy\"] | None = Field(\n        default=None,\n        description=\"which term chose parallel_n -- project.max_parallel ('config'), the \"\n                    \"measured RAM/CPU budget ('budget'), or a forced serial fallback because \"\n                    \"write_policy is allow_writes ('write_policy')\",\n    )\n    bounds: RunBounds | None = Field(\n        default=None,\n        description=\"AT-570/CN10: the approval and bounds this run ran under. None means NOT \"\n                    \"RECORDED (a run from before the live-case gate, or a path that does not \"\n                    \"record it) -- never 'unbounded', and deliberately not zeros, which would \"\n                    \"be indistinguishable from a measured zero (core-invariants C12(b))\",\n    )\n"}
{"path":"src/autotester/core/paths.py","source":"\"\"\"Filesystem layout. The ONLY place project paths are constructed.\n\nEvery artifact lives under `projects/<slug>/` as a human-readable file. Nothing\nin the system may build these paths by string concatenation elsewhere.\n\"\"\"\n\nfrom __future__ import annotations\n\nimport os\nfrom pathlib import Path\n\nENV_ROOT = \"AUTOTESTER_ROOT\"\n\n\ndef repo_root() -> Path:\n    \"\"\"Repository root; overridable via `AUTOTESTER_ROOT` (used by tests).\"\"\"\n    override = os.environ.get(ENV_ROOT)\n    if override:\n        return Path(override).resolve()\n    return Path(__file__).resolve().parents[3]\n\n\nclass ProjectPaths:\n    \"\"\"Resolved paths for one project. Construct with a slug, ask for what you need.\"\"\"\n\n    def __init__(self, slug: str, root: Path | None = None) -> None:\n        self.slug = slug\n        self.root = root or repo_root()\n\n    @property\n    def dir(self) -> Path:\n        return self.root / \"projects\" / self.slug\n\n    @property\n    def config(self) -> Path:\n        return self.dir / \"project.json\"\n\n    @property\n    def approvals(self) -> Path:\n        \"\"\"Human-granted `RunApproval` rows (D-018). Append-only in practice: an\n        approval is never edited, it expires or a new one is granted.\"\"\"\n        return self.dir / \"approvals.jsonl\"\n\n    @property\n    def env_file(self) -> Path:\n        \"\"\"One credential file for the whole repo, at the root (Umesh, 2026-09-03).\n\n        Keys are namespaced per project (`PATHLYNKS_*`) and declared in each\n        project's `SecretRef[]`; a project can only resolve the keys it declares.\n        \"\"\"\n        return self.root / \".env\"\n\n    @property\n    def sources_dir(self) -> Path:\n        return self.dir / \"sources\"\n\n    @property\n    def sources_index(self) -> Path:\n        return self.dir / \"sources.jsonl\"\n\n    @property\n    def flowspec(self) -> Path:\n        return self.dir / \"flowspec.json\"\n\n    @property\n    def cases(self) -> Path:\n        return self.dir / \"cases.jsonl\"\n\n    @property\n    def rubrics_dir(self) -> Path:\n        return self.dir / \"rubrics\"\n\n    @property\n    def scripts_dir(self) -> Path:\n        return self.dir / \"scripts\"\n\n    @property\n    def runs_dir(self) -> Path:\n        return self.dir / \"runs\"\n\n    @property\n    def requests(self) -> Path:\n        return self.dir / \"requests.jsonl\"\n\n    @property\n    def knowledge(self) -> Path:\n        return self.dir / \"knowledge.md\"\n\n    @property\n    def portal_persona(self) -> Path:\n        \"\"\"The durable cross-run product model (T-164). One JSON file per\n        project; `knowledge` is its regenerated human-readable view.\"\"\"\n        return self.dir / \"portal_persona.json\"\n\n    @property\n    def bench_dir(self) -> Path:\n        return self.dir / \"bench\"\n\n    def bench_corpus(self, corpus_id: str) -> Path:\n        return self.bench_dir / f\"{corpus_id}.json\"\n\n    def bench_trial(self, trial_id: str) -> Path:\n        return self.bench_dir / f\"{trial_id}.trial.json\"\n\n    @property\n    def profile_dir(self) -> Path:\n        \"\"\"Persistent browser profile — gitignored, holds the logged-in session.\"\"\"\n        return self.root / \"profiles\" / self.slug\n\n    def run_dir(self, run_id: str) -> Path:\n        return self.runs_dir / run_id\n\n    @property\n    def user_personas(self) -> Path:\n        return self.dir / \"user_personas.jsonl\"\n\n    def run_ux_report(self, run_id: str) -> Path:\n        return self.run_dir(run_id) / \"ux\" / \"report.json\"\n\n    def run_trace(self, run_id: str) -> Path:\n        \"\"\"The redacted per-run trace (D-041 phase 1, RT1) -- `trace_id`\n        equals `run_id`, never re-minted (RT2).\"\"\"\n        return self.run_dir(run_id) / \"trace.jsonl\"\n\n    # -- Track A: video learning (D-014) ---------------------------------------\n    def source_dir(self, source_id: str) -> Path:\n        return self.dir / \"sources\" / source_id\n\n    def source_media(self, source_id: str) -> Path:\n        return self.source_dir(source_id) / \"media.json\"\n\n    def source_transcript(self, source_id: str) -> Path:\n        return self.source_dir(source_id) / \"transcript.json\"\n\n    def source_chunks_dir(self, source_id: str) -> Path:\n        return self.source_dir(source_id) / \"chunks\"\n\n    def source_frames_dir(self, source_id: str) -> Path:\n        return self.source_dir(source_id) / \"frames\"\n\n    def source_observations_dir(self, source_id: str) -> Path:\n        return self.source_dir(source_id) / \"observations\"\n\n    def source_observation(\n        self, source_id: str, provider_label: str, prompt_name: str, chunk_index: int\n    ) -> Path:\n        label = provider_label.replace(\":\", \"_\").replace(\"/\", \"_\")\n        name = f\"{label}__{prompt_name}__{chunk_index:02d}.json\"\n        return self.source_observations_dir(source_id) / name\n\n    def source_analysis(self, source_id: str) -> Path:\n        return self.source_dir(source_id) / \"analysis.json\"\n\n    @property\n    def issues(self) -> Path:\n        return self.dir / \"issues.jsonl\"\n\n    @property\n    def screen_map(self) -> Path:\n        return self.dir / \"screenmap.json\"\n\n    # -- Track B: autonomous explorer (D-015) ----------------------------------\n    @property\n    def crawls_dir(self) -> Path:\n        return self.dir / \"crawl\"\n\n    def crawl_dir(self, crawl_id: str) -> Path:\n        return self.crawls_dir / crawl_id\n\n    def crawl_shots_dir(self, crawl_id: str) -> Path:\n        return self.crawl_dir(crawl_id) / \"shots\"\n\n    def crawl_nodes(self, crawl_id: str) -> Path:\n        return self.crawl_dir(crawl_id) / \"nodes.jsonl\"\n\n    def crawl_edges(self, crawl_id: str) -> Path:\n        return self.crawl_dir(crawl_id) / \"edges.jsonl\"\n\n    def crawl_issues(self, crawl_id: str) -> Path:\n        return self.crawl_dir(crawl_id) / \"issues.jsonl\"\n\n    def crawl_network(self, crawl_id: str) -> Path:\n        \"\"\"T-170/NA1: first-party NETWORK evidence captured during the crawl.\"\"\"\n        return self.crawl_dir(crawl_id) / \"network.jsonl\"\n\n    def crawl_frontier(self, crawl_id: str) -> Path:\n        return self.crawl_dir(crawl_id) / \"frontier.json\"\n\n    def crawl_manifest(self, crawl_id: str) -> Path:\n        return self.crawl_dir(crawl_id) / \"crawl.json\"\n\n    def ensure(self) -> None:\n        \"\"\"Create the directories a project needs. Safe to call repeatedly.\"\"\"\n        for path in (\n            self.dir,\n            self.sources_dir,\n            self.rubrics_dir,\n            self.scripts_dir,\n            self.runs_dir,\n            self.profile_dir,\n            self.bench_dir,\n        ):\n            path.mkdir(parents=True, exist_ok=True)\n\n\ndef work_dir(root: Path | None = None) -> Path:\n    \"\"\"Scratch space. Nothing here is committed; nothing outside here is scratch.\"\"\"\n    path = (root or repo_root()) / \".work\"\n    path.mkdir(parents=True, exist_ok=True)\n    return path\n\n\nclass RepoDocs:\n    \"\"\"Repo-level documents: the living map, the ledger, the history, the router.\"\"\"\n\n    def __init__(self, root: Path | None = None, *, prompts_dir: Path | None = None,\n                 skills_dir: Path | None = None) -> None:\n        self.root = root or repo_root()\n        self._root_given = root is not None\n        self._prompts_dir_override = prompts_dir\n        self._skills_dir_override = skills_dir\n\n    @property\n    def docs_dir(self) -> Path:\n        return self.root / \"docs\"\n\n    @property\n    def architecture(self) -> Path:\n        return self.docs_dir / \"ARCHITECTURE.md\"\n\n    @property\n    def snapshot(self) -> Path:\n        return self.docs_dir / \"SNAPSHOT.md\"\n\n    @property\n    def map(self) -> Path:\n        \"\"\"Generated directory map + schema summary (kept out of ARCHITECTURE's 150-line budget).\"\"\"\n        return self.docs_dir / \"MAP.md\"\n\n    @property\n    def features(self) -> Path:\n        return self.docs_dir / \"FEATURES.jsonl\"\n\n    @property\n    def decisions(self) -> Path:\n        return self.docs_dir / \"DECISIONS.md\"\n\n    @property\n    def router(self) -> Path:\n        \"\"\"`CLAUDE.md` carries the \"open X when Y\" table.\"\"\"\n        return self.root / \"CLAUDE.md\"\n\n    @property\n    def goal(self) -> Path:\n        return self.root / \".goal\" / \"goal.json\"\n\n    @property\n    def prompts_dir(self) -> Path:\n        \"\"\"Prompts ship WITH THE CODE, so the DATA root must not move them.\n\n        `root` falls back to `repo_root()`, which honours `AUTOTESTER_ROOT` — a\n        switch for relocating a project's DATA. That silently moved the prompt\n        lookup too, and `autotester ingest run` under a relocated root died on\n        `FileNotFoundError: <data root>/src/autotester/prompts/...` (AT-132,\n        found by a test driving the real CLI). Every prompt-reading stage was\n        one environment variable away from the same failure.\n\n        An EXPLICIT `root` still wins: substituting a stub prompt tree is a\n        legitimate thing for a test to do, and the defect was never explicit\n        injection — it was the env var leaking into a path it does not own.\n\n        AT-137: that fallback used to be the ONLY way to substitute a prompt\n        tree — an inferred side effect of passing `root`, not a named act.\n        Pass `prompts_dir=` explicitly instead when that is what's meant;\n        `root` alone still behaves exactly as before for every caller that\n        never adopts the explicit form (no behaviour change, C2).\"\"\"\n        if self._prompts_dir_override is not None:\n            return self._prompts_dir_override\n        if self._root_given:\n            return self.root / \"src\" / \"autotester\" / \"prompts\"\n        return Path(__file__).resolve().parents[1] / \"prompts\"\n\n    @property\n    def skills_dir(self) -> Path:\n        \"\"\"Migrated-prompt `SKILL.md` folders (T-175/D-041) -- same shape as\n        `prompts_dir` above and for the same reason: ships WITH THE CODE, so an\n        explicit override lets a test substitute a stub tree (mirroring\n        AT-137's `prompts_dir=` fix) without a relocated `AUTOTESTER_ROOT`\n        leaking into a path it does not own.\"\"\"\n        if self._skills_dir_override is not None:\n            return self._skills_dir_override\n        if self._root_given:\n            return self.root / \"src\" / \"autotester\" / \"skills\"\n        return Path(__file__).resolve().parents[1] / \"skills\"\n"}
{"path":"src/autotester/store/project_store.py","source":"\"\"\"Typed convenience over `filestore` for one project's directory.\n\nA thin wrapper — the read/write logic lives once in `filestore`. A new\nartifact kind adds a method here, not a new file format (C1/C3).\n\"\"\"\n\nfrom __future__ import annotations\n\nfrom pathlib import Path\n\nfrom autotester.core.paths import ProjectPaths\nfrom autotester.schema.analysis import VideoAnalysis\nfrom autotester.schema.approval import RunApproval\nfrom autotester.schema.bench import BenchCorpus, BenchTrial\nfrom autotester.schema.case import Case\nfrom autotester.schema.flowspec import FlowSpec\nfrom autotester.schema.issue import Issue\nfrom autotester.schema.media import MediaPrep, Transcript\nfrom autotester.schema.observation import ModelObservation\nfrom autotester.schema.portal_persona import PortalPersona\nfrom autotester.schema.project import Project, Source\nfrom autotester.schema.screenmap import ScreenMap\nfrom autotester.schema.verdict import Rubric\nfrom autotester.store.crawl_store import CrawlStoreMixin\nfrom autotester.store.filestore import (\n    append_jsonl,\n    delete_jsonl_row,\n    read_json,\n    read_jsonl,\n    upsert_jsonl,\n    write_json,\n)\nfrom autotester.store.request_store import RequestStoreMixin\nfrom autotester.store.run_store import RunStoreMixin\n\n\nclass PinnedCaseError(RuntimeError):\n    \"\"\"AT-585: `delete_case` raises this for a pinned case -- unpin via\n    `update_case` first if it genuinely must go.\"\"\"\n\n\nclass ProjectStore(CrawlStoreMixin, RequestStoreMixin, RunStoreMixin):\n    \"\"\"Load and save one project's artifacts as human-editable files (C6).\n\n    AT-024: `add_source`/`add_case`/`add_request` used to re-read their whole\n    collection (a full JSONL scan) on every single call to check idempotency —\n    O(n) per add, O(n^2) for n sequential adds in one loop (e.g. `expand.py`\n    adding a dozen-plus cases per flow). Each keeps a lazily-populated\n    in-memory id cache instead: the first add in a `ProjectStore`'s lifetime\n    still reads the file once, but every subsequent add in that same instance\n    is an O(1) set check. `list_*()` always reads fresh from disk — it must\n    reflect whatever is actually there, including anything written by another\n    process — only the add-time idempotency check is cached.\n    \"\"\"\n\n    def __init__(self, slug: str, root: Path | None = None) -> None:\n        self.paths = ProjectPaths(slug, root)\n        self._source_ids: set[str] | None = None\n        self._case_ids: set[str] | None = None\n        self._request_ids: set[str] | None = None\n        self._issue_ids: set[str] | None = None\n        self._node_ids: dict[str, set[str]] | None = None  # keyed by crawl_id\n\n    # -- project --------------------------------------------------------------\n    def save_project(self, project: Project) -> None:\n        write_json(self.paths.config, project)\n\n    def load_project(self) -> Project | None:\n        return read_json(self.paths.config, Project)\n\n    # -- sources (immutable, content-addressed) --------------------------------\n    def add_source(self, source: Source) -> Source:\n        \"\"\"Idempotent: re-adding an identical source is a no-op, not a duplicate.\"\"\"\n        if self._source_ids is None:\n            self._source_ids = {s.id for s in self.list_sources()}\n        if source.id in self._source_ids:\n            return source\n        append_jsonl(self.paths.sources_index, source)\n        self._source_ids.add(source.id)\n        return source\n\n    def list_sources(self) -> list[Source]:\n        return read_jsonl(self.paths.sources_index, Source)\n\n    # -- approvals (D-018: consent is a file, not a habit) ---------------------\n    def add_approval(self, approval: RunApproval) -> RunApproval:\n        append_jsonl(self.paths.approvals, approval)\n        return approval\n\n    def list_approvals(self) -> list[RunApproval]:\n        return read_jsonl(self.paths.approvals, RunApproval)\n\n    # -- flowspec (single, human-reviewed) -------------------------------------\n    def save_flowspec(self, spec: FlowSpec) -> None:\n        write_json(self.paths.flowspec, spec)\n\n    def load_flowspec(self) -> FlowSpec | None:\n        return read_json(self.paths.flowspec, FlowSpec)\n\n    # -- cases (content-addressed; status can change) ---------------------------\n    def add_case(self, case: Case) -> Case:\n        \"\"\"Idempotent on id: regenerating a flowspec never duplicates a case.\"\"\"\n        if self._case_ids is None:\n            self._case_ids = {c.id for c in self.list_cases()}\n        if case.id in self._case_ids:\n            return case\n        append_jsonl(self.paths.cases, case)\n        self._case_ids.add(case.id)\n        return case\n\n    def list_cases(self) -> list[Case]:\n        return read_jsonl(self.paths.cases, Case)\n\n    def get_case(self, case_id: str) -> Case | None:\n        return next((c for c in self.list_cases() if c.id == case_id), None)\n\n    def has_case(self, case_id: str) -> bool:\n        \"\"\"Whether this id is already on file — the check `add_case` makes\n        silently. A caller that must tell \"created\" from \"already existed\"\n        (a create form, say) asks this first; `add_case`'s idempotence is\n        deliberate and stays.\"\"\"\n        if self._case_ids is None:\n            self._case_ids = {c.id for c in self.list_cases()}\n        return case_id in self._case_ids\n\n    def update_case(self, case: Case) -> None:\n        \"\"\"Replace a case in place, keeping its id — so its runs, verdicts and\n        rubric stay attached. Only fields outside `Case.compute_id()`'s payload\n        can change this way; anything else is a different case.\"\"\"\n        upsert_jsonl(self.paths.cases, case, Case)\n        if self._case_ids is not None:\n            self._case_ids.add(case.id)\n\n    def delete_case(self, case_id: str) -> bool:\n        \"\"\"Remove a case; True when one was removed. Past runs/verdicts stay.\n        AT-585: raises `PinnedCaseError` for a pinned case, never a silent\n        False -- a caller must not mistake \"protected\" for \"not found\".\"\"\"\n        case = self.get_case(case_id)\n        if case is not None and case.pinned:\n            raise PinnedCaseError(\n                f\"case '{case_id}' is pinned (issue {case.pinned_issue_id}) \"\n                \"and cannot be pruned\"\n            )\n        removed = delete_jsonl_row(self.paths.cases, Case, case_id)\n        if removed and self._case_ids is not None:\n            self._case_ids.discard(case_id)\n        return removed\n\n    # -- rubrics (one file per id; `rubrics_dir` existed since design-lock, unused until now) ---\n    def save_rubric(self, rubric: Rubric) -> None:\n        write_json(self.paths.rubrics_dir / f\"{rubric.id}.json\", rubric)\n\n    def load_rubric(self, rubric_id: str) -> Rubric | None:\n        return read_json(self.paths.rubrics_dir / f\"{rubric_id}.json\", Rubric)\n\n    # -- bench (seeded corpus + trial scorecards) --------------------------------\n    def save_bench_corpus(self, corpus: BenchCorpus) -> None:\n        write_json(self.paths.bench_corpus(corpus.id), corpus)\n\n    def load_bench_corpus(self, corpus_id: str) -> BenchCorpus | None:\n        return read_json(self.paths.bench_corpus(corpus_id), BenchCorpus)\n\n    def save_bench_trial(self, trial: BenchTrial) -> None:\n        write_json(self.paths.bench_trial(trial.id), trial)\n\n    def list_bench_trials(self, corpus_id: str) -> list[BenchTrial]:\n        bench_dir = self.paths.bench_dir\n        if not bench_dir.exists():\n            return []\n        trials = [\n            model\n            for path in sorted(bench_dir.glob(\"*.trial.json\"))\n            for model in [read_json(path, BenchTrial)]\n            if model is not None\n        ]\n        return [t for t in trials if t.corpus_id == corpus_id]\n\n    # -- Track A: video learning (D-014) -----------------------------------------\n    def save_media_prep(self, prep: MediaPrep) -> None:\n        write_json(self.paths.source_media(prep.source_id), prep)\n\n    def load_media_prep(self, source_id: str) -> MediaPrep | None:\n        return read_json(self.paths.source_media(source_id), MediaPrep)\n\n    def save_transcript(self, transcript: Transcript) -> None:\n        write_json(self.paths.source_transcript(transcript.source_id), transcript)\n\n    def load_transcript(self, source_id: str) -> Transcript | None:\n        return read_json(self.paths.source_transcript(source_id), Transcript)\n\n    def save_observation(self, observation: ModelObservation) -> None:\n        path = self.paths.source_observation(\n            observation.source_id, observation.provider_label,\n            observation.prompt_name, observation.chunk_index,\n        )\n        write_json(path, observation)\n\n    def list_observations(self, source_id: str,\n                          *, skip_unreadable: bool = False) -> list[ModelObservation]:\n        \"\"\"Every cached model answer for one source.\n\n        `skip_unreadable` is for the one caller that can repair the damage:\n        a half-written observation file (the crash the cache exists to survive)\n        otherwise raises out of `analyze`, and `--force` could not clear it\n        because reading came first. Skipped means re-requested and overwritten,\n        never silently treated as an answer.\"\"\"\n        obs_dir = self.paths.source_observations_dir(source_id)\n        if not obs_dir.exists():\n            return []\n        found: list[ModelObservation] = []\n        for path in sorted(obs_dir.glob(\"*.json\")):\n            try:\n                model = read_json(path, ModelObservation)\n            except Exception:\n                if not skip_unreadable:\n                    raise\n                continue\n            if model is not None:\n                found.append(model)\n        return found\n\n    def save_analysis(self, analysis: VideoAnalysis) -> None:\n        write_json(self.paths.source_analysis(analysis.source_id), analysis)\n\n    def load_analysis(self, source_id: str) -> VideoAnalysis | None:\n        return read_json(self.paths.source_analysis(source_id), VideoAnalysis)\n\n    def add_issue(self, issue: Issue) -> Issue:\n        \"\"\"Idempotent on id, same lazy-cache pattern as `add_case`/`add_source`.\"\"\"\n        if self._issue_ids is None:\n            self._issue_ids = {i.id for i in self.list_issues()}\n        if issue.id in self._issue_ids:\n            return issue\n        append_jsonl(self.paths.issues, issue)\n        self._issue_ids.add(issue.id)\n        return issue\n\n    def list_issues(self) -> list[Issue]:\n        return read_jsonl(self.paths.issues, Issue)\n\n    def update_issue(self, issue: Issue) -> None:\n        upsert_jsonl(self.paths.issues, issue, Issue)\n        if self._issue_ids is not None:\n            self._issue_ids.add(issue.id)\n\n    def delete_issue(self, issue_id: str) -> bool:\n        removed = delete_jsonl_row(self.paths.issues, Issue, issue_id)\n        if removed and self._issue_ids is not None:\n            self._issue_ids.discard(issue_id)\n        return removed\n\n    def save_screen_map(self, screen_map: ScreenMap) -> None:\n        write_json(self.paths.screen_map, screen_map)\n\n    def load_screen_map(self) -> ScreenMap | None:\n        return read_json(self.paths.screen_map, ScreenMap)\n\n    # -- portal persona (durable, single JSON store; knowledge.md is its view) --\n    def save_portal_persona(self, persona: PortalPersona) -> None:\n        write_json(self.paths.portal_persona, persona)\n\n    def load_portal_persona(self) -> PortalPersona | None:\n        return read_json(self.paths.portal_persona, PortalPersona)\n"}
{"path":"src/autotester/store/run_store.py","source":"\"\"\"Typed persisted run records and separate advisory adjuncts.\"\"\"\n\nfrom autotester.core.redact import Redactor\nfrom autotester.schema.run import RawResult, Run\nfrom autotester.schema.user_persona import UserPersona\nfrom autotester.schema.ux_report import UXReport\nfrom autotester.schema.verdict import Verdict\nfrom autotester.store.filestore import read_json, read_jsonl, upsert_jsonl, write_json\n\n\nclass RunStoreMixin:\n    \"\"\"Run facade extracted without changing existing public run signatures.\"\"\"\n\n    # -- runs (one Run envelope + one RawResult file per case) -------------------\n    def save_run(self, run: Run) -> None:\n        write_json(self.paths.run_dir(run.id) / \"run.json\", run)\n\n    def load_run(self, run_id: str) -> Run | None:\n        return read_json(self.paths.run_dir(run_id) / \"run.json\", Run)\n\n    def save_result(self, run_id: str, result: RawResult) -> None:\n        write_json(self.paths.run_dir(run_id) / f\"{result.case_id}.json\", result)\n\n    def load_results(self, run_id: str) -> list[RawResult]:\n        run_dir = self.paths.run_dir(run_id)\n        if not run_dir.exists():\n            return []\n        return [\n            model\n            for path in sorted(run_dir.glob(\"*.json\"))\n            if path.name != \"run.json\" and not path.name.endswith(\".verdict.json\")\n            for model in [read_json(path, RawResult)]\n            if model is not None\n        ]\n\n    # -- verdicts (one file per case, alongside its RawResult) -------------------\n    def save_verdict(self, run_id: str, verdict: Verdict) -> None:\n        write_json(self.paths.run_dir(run_id) / f\"{verdict.case_id}.verdict.json\", verdict)\n\n    def load_verdicts(self, run_id: str) -> list[Verdict]:\n        run_dir = self.paths.run_dir(run_id)\n        if not run_dir.exists():\n            return []\n        return [\n            model\n            for path in sorted(run_dir.glob(\"*.verdict.json\"))\n            for model in [read_json(path, Verdict)]\n            if model is not None\n        ]\n\n    def save_user_persona(self, persona: UserPersona, *, redactor: Redactor) -> None:\n        redactor.assert_clean(persona.model_dump_json())\n        upsert_jsonl(self.paths.user_personas, persona, UserPersona)\n\n    def list_user_personas(self) -> list[UserPersona]:\n        return read_jsonl(self.paths.user_personas, UserPersona)\n\n    def get_user_persona(self, persona_id: str) -> UserPersona | None:\n        return next((p for p in self.list_user_personas() if p.id == persona_id), None)\n\n    def save_ux_report(self, report: UXReport, *, redactor: Redactor) -> None:\n        redactor.assert_clean(report.model_dump_json())\n        if report.project != self.paths.slug:\n            raise ValueError(\"advisory project mismatch\")\n        run = self.load_run(report.run_id)\n        if run is None or run.id != report.run_id or run.project != report.project:\n            raise ValueError(\"advisory run unavailable\")\n        write_json(self.paths.run_ux_report(report.run_id), report)\n\n    def load_ux_report(self, run_id: str) -> UXReport | None:\n        report = read_json(self.paths.run_ux_report(run_id), UXReport)\n        if report is not None and (\n            report.run_id != run_id or report.project != self.paths.slug\n        ):\n            raise ValueError(\"advisory identity mismatch\")\n        return report\n"}
{"path":"src/autotester/stages/report_export.py","source":"\"\"\"Tester-style run reports: an Excel summary and a screen-by-screen HTML\nreport with embedded screenshots. Contract: qa/contracts/report-export.md.\n\nBoth read only what `ProjectStore` already has (cases, RawResults, Verdicts)\n— exporting is presentation over existing evidence, never a new source of\ntruth (design principle 8, same discipline as `ui/`).\n\"\"\"\n\nfrom __future__ import annotations\n\nimport base64\nfrom datetime import UTC\nfrom html import escape\nfrom pathlib import Path\n\nfrom autotester.browser.secrets import SecretStore\nfrom autotester.core.excel import export_run_workbook\nfrom autotester.core.redact import Redactor\nfrom autotester.schema.case import Case\nfrom autotester.schema.enums import EvidenceKind, Result\nfrom autotester.schema.run import Run\nfrom autotester.schema.verdict import Verdict\nfrom autotester.store import ProjectStore\n\n_BADGE_COLOR = {\n    \"PASS\": \"#16a34a\", \"FAIL\": \"#dc2626\", \"BLOCKED\": \"#b45309\", \"INCONCLUSIVE\": \"#6b7280\",\n}\n\n\ndef _run_sort_key(run: Run) -> tuple:\n    created = run.created_at\n    if created.tzinfo is None:\n        created = created.replace(tzinfo=UTC)\n    return created.astimezone(UTC), run.id\n\n\ndef valid_runs_newest_first(store: ProjectStore) -> list[Run]:\n    \"\"\"Persisted Run envelopes only; auxiliary run artifacts are not runs.\"\"\"\n    runs_dir = store.paths.runs_dir\n    if not runs_dir.exists():\n        return []\n    runs: list[Run] = []\n    for path in sorted((p for p in runs_dir.iterdir() if p.is_dir()), reverse=True):\n        try:\n            run = store.load_run(path.name)\n        except ValueError:\n            continue\n        if run is not None and run.id == path.name and run.project == store.paths.slug:\n            runs.append(run)\n    runs.sort(key=_run_sort_key, reverse=True)\n    return runs\n\n\ndef _latest_run_id(store: ProjectStore) -> str:\n    runs = valid_runs_newest_first(store)\n    if not runs:\n        raise ValueError(f\"no runs exist yet for '{store.paths.slug}'\")\n    return runs[0].id\n\n\ndef _case_lookup(store: ProjectStore) -> dict[str, Case]:\n    return {c.id: c for c in store.list_cases()}\n\n\ndef _load_redactor(store: ProjectStore) -> Redactor:\n    \"\"\"Reuse root SecretStore at the last export stop (C5/AT-594/AT-609).\n    Empty/undeclared credentials preserve the existing harmless Redactor behavior.\"\"\"\n    project = store.load_project()\n    if project is None:\n        return Redactor({})\n    return SecretStore.load(project, store.paths.env_file, strict=False).redactor()\n\n\ndef _needs_developer_detail(verdict: Verdict | None) -> bool:\n    \"\"\"RE6 (D-045): a FAIL or INCONCLUSIVE verdict is what a developer must act\n    on -- a PASS gets no failure/repro detail.\"\"\"\n    return verdict is not None and verdict.result in (Result.FAIL, Result.INCONCLUSIVE)\n\n\ndef _failure_rows(verdict: Verdict | None) -> list[tuple[str, str, str | None]]:\n    \"\"\"Each failure's (criterion_id, reason, fix_hint), verbatim off the\n    stored Verdict -- RE1: nothing recomputed.\"\"\"\n    if verdict is None:\n        return []\n    return [(f.criterion_id, f.reason, f.fix_hint) for f in verdict.failures]\n\n\ndef _repro_steps(case: Case | None, redactor: Redactor) -> list[str]:\n    \"\"\"The case's own steps, formatted as a plain-text repro recipe.\n\n    `redactor.scrub` runs over the formatted line before it reaches either\n    export (AT-594): a `{{SECRET:KEY}}` placeholder is not a known secret\n    VALUE, so it passes through untouched and exports as the placeholder,\n    never a resolved value; a step that somehow held a raw declared secret is\n    masked here, the same last-stop guarantee every other artifact gets.\"\"\"\n    if case is None:\n        return []\n    return [\n        redactor.scrub(\n            f\"{step.order}. {step.action.value} {step.target}\"\n            + (f\" = {step.value}\" if step.value else \"\")\n        )\n        for step in case.steps\n    ]\n\n\ndef _excel_run_rows(results, cases, verdicts, redactor: Redactor) -> list[list]:\n    \"\"\"Existing eleven-column values, computed once beside existing truth helpers.\"\"\"\n    rows = []\n    for result in results:\n        case = cases.get(result.case_id)\n        verdict = verdicts.get(result.case_id)\n        detail = _needs_developer_detail(verdict)\n        failures_text = \"\\n\".join(\n            f\"{criterion_id}: {reason}\" + (f\" (fix: {fix_hint})\" if fix_hint else \"\")\n            for criterion_id, reason, fix_hint in _failure_rows(verdict)\n        ) if detail else \"\"\n        steps_text = \"\\n\".join(_repro_steps(case, redactor)) if detail else \"\"\n        # AT-609: `Case.title` is operator-authored free text, not a step\n        # value -- nothing upstream guarantees it never carries a pasted raw\n        # secret, so it gets the same last-stop scrub every other exported\n        # field gets.\n        case_title = redactor.scrub(case.title) if case else result.case_id\n        rows.append([\n            case_title,\n            case.kind.value if case else \"\",\n            case.case_class.value if case else \"\",\n            result.outcome.value,\n            verdict.result.value if verdict else \"\",\n            f\"{verdict.criteria_met}/{verdict.criteria_total}\" if verdict else \"\",\n            round(result.duration_s, 2),\n            verdict.grader_provider if verdict else \"\",\n            (verdict.scoreboard if verdict else \"\") or (result.error or \"\"),\n            failures_text,\n            steps_text,\n        ])\n    return rows\n\n\ndef export_excel(\n    project_slug: str, run_id: str | None, out_path: Path, root: Path | None = None\n) -> Path:\n    \"\"\"One row per case; optional separate advisory sheet, never merged failures.\"\"\"\n    store = ProjectStore(project_slug, root)\n    run_id = run_id or _latest_run_id(store)\n    cases = _case_lookup(store)\n    verdicts = {v.case_id: v for v in store.load_verdicts(run_id)}\n    redactor = _load_redactor(store)\n    rows = _excel_run_rows(store.load_results(run_id), cases, verdicts, redactor)\n    report = store.load_ux_report(run_id)\n    ux_rows = [] if report is None else [\n        [f.case_id, f.persona_id, f.evidence_path, f.step_order, f.severity.value,\n         redactor.scrub(f.finding)] for f in report.findings\n    ]\n    redactor.assert_clean(str(ux_rows))\n    header = [\"Case\", \"Kind\", \"Class\", \"Outcome\", \"Result\", \"Criteria met\",\n              \"Duration (s)\", \"Grader\", \"Notes\", \"Failures\", \"Repro steps\"]\n    ux_header = [\"Case\", \"Persona\", \"Evidence\", \"Step\", \"Severity\", \"UX finding\"]\n    return export_run_workbook(out_path, header, rows, ux_header=ux_header, ux_rows=ux_rows)\n\n\ndef png_base64(path: Path, allowed_root: Path, trusted_root: Path) -> str | None:\n    \"\"\"Base64-encode a screenshot for inline embedding. Public — also used by\n    `ui/routes_report.py` to embed the same screenshots in the live view, so\n    the live page and the portable export show identical evidence.\"\"\"\n    trusted = trusted_root.resolve()\n    try:\n        parts = allowed_root.absolute().relative_to(trusted).parts\n    except ValueError:\n        return None\n    safe_root = trusted\n    for part in parts:\n        safe_root /= part\n        if safe_root.is_symlink():\n            return None\n    resolved_safe_root = safe_root.resolve()\n    if resolved_safe_root != safe_root:\n        return None\n    candidate = path.resolve()\n    if not candidate.is_relative_to(resolved_safe_root):\n        return None\n    if not candidate.is_file():\n        return None\n    return base64.b64encode(candidate.read_bytes()).decode(\"ascii\")\n\n\ndef _case_section(\n    store: ProjectStore, run_id: str, case: Case | None, result, verdict, redactor: Redactor\n) -> str:\n    run_dir = store.paths.run_dir(run_id)\n    # AT-609: `Case.title` (the <h2>) and `Evidence.label` (the <figcaption>)\n    # are both operator-authored free text with no upstream guarantee against\n    # a pasted raw secret -- scrubbed here, the same last-stop rule the repro\n    # steps already get, before `escape` ever sees them.\n    title = escape(redactor.scrub(case.title) if case else result.case_id)\n    color = _BADGE_COLOR.get(verdict.result.value if verdict else \"\", \"#6b7280\")\n    badge_text = escape(verdict.result.value) if verdict else escape(result.outcome.value)\n    shots = [e for e in result.evidence if e.kind is EvidenceKind.SCREENSHOT]\n    figures = \"\".join(\n        f\"<figure><img src='data:image/png;base64,{data}'>\"\n        f\"<figcaption>{escape(redactor.scrub(shot.label or shot.path))}</figcaption></figure>\"\n        for shot in shots\n        for data in [png_base64(run_dir / shot.path, run_dir, store.paths.dir)] if data is not None\n    )\n    scoreboard = escape(verdict.scoreboard) if verdict and verdict.scoreboard else \"\"\n    error = escape(result.error) if result.error else \"\"\n    no_shots = \"<p class='meta'>no screenshots captured</p>\"\n    detail = _failure_detail_html(verdict, case, redactor)\n    video_html = _video_link_html(result)\n    return (\n        f\"<section><h2>{title} \"\n        f\"<span class='badge' style='background:{color}'>{badge_text}</span></h2>\"\n        f\"<p class='meta'>{scoreboard}{error}</p>\"\n        f\"{detail}\"\n        f\"<div class='shots'>{figures or no_shots}</div>\"\n        f\"{video_html}\"\n        \"</section>\"\n    )\n\n\ndef _video_link_html(result) -> str:\n    \"\"\"RE3's named exception (D-050) + T-191 V8: a kept video is LINKED, never\n    embedded like a screenshot -- a 15-20 minute recording base64'd into the\n    page would defeat the whole point of the exception. Path is run-relative,\n    same as `Evidence.path` everywhere else; `report-export.md`'s \"relative\n    to the run directory\" phrasing (not to the exported file).\"\"\"\n    videos = [e for e in result.evidence if e.kind is EvidenceKind.VIDEO]\n    if not videos:\n        return \"\"\n    links = \"\".join(\n        f\"<p class='meta'><a href='{escape(v.path)}'>video ({escape(v.path)})</a></p>\"\n        for v in videos\n    )\n    return links\n\n\ndef _failure_detail_html(verdict: Verdict | None, case: Case | None, redactor: Redactor) -> str:\n    \"\"\"RE6 (D-045): for a FAIL/INCONCLUSIVE verdict, each failure's criterion,\n    reason and fix_hint, plus the case's own steps as the repro -- read\n    straight off the stored Verdict/Case (RE1: nothing recomputed).\"\"\"\n    if not _needs_developer_detail(verdict):\n        return \"\"\n    items = \"\".join(\n        f\"<li><code>{escape(criterion_id)}</code> — {escape(reason)}\"\n        + (f\" <em>fix: {escape(fix_hint)}</em>\" if fix_hint else \"\") + \"</li>\"\n        for criterion_id, reason, fix_hint in _failure_rows(verdict)\n    )\n    failures_html = f\"<h3>Failures</h3><ul>{items}</ul>\" if items else \"\"\n    steps = _repro_steps(case, redactor)\n    steps_html = (\n        \"<h3>Repro steps</h3><ol>\"\n        + \"\".join(f\"<li>{escape(step)}</li>\" for step in steps)\n        + \"</ol>\"\n    ) if steps else \"\"\n    if not failures_html and not steps_html:\n        return \"\"\n    return f\"<div class='detail'>{failures_html}{steps_html}</div>\"\n\n\ndef export_html(\n    project_slug: str, run_id: str | None, out_path: Path, root: Path | None = None\n) -> Path:\n    \"\"\"One section per case, in run order, each with its own screenshots\n    embedded inline (base64) so the file is a single portable artifact.\"\"\"\n    store = ProjectStore(project_slug, root)\n    run_id = run_id or _latest_run_id(store)\n    cases = _case_lookup(store)\n    verdicts = {v.case_id: v for v in store.load_verdicts(run_id)}\n    results = store.load_results(run_id)\n    redactor = _load_redactor(store)\n\n    sections = \"\".join(\n        _case_section(store, run_id, cases.get(r.case_id), r, verdicts.get(r.case_id), redactor)\n        for r in results\n    )\n    style = (\n        \"body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:900px;\"\n        \"margin:2rem auto;padding:0 1rem;color:#16181d}\"\n        \"h1{margin-bottom:.2rem}.meta{color:#667085;font-size:.85rem}\"\n        \"section{border:1px solid #e2e5ea;border-radius:10px;padding:1.2rem 1.4rem;\"\n        \"margin-bottom:1.2rem}\"\n        \".badge{color:#fff;padding:.15rem .6rem;border-radius:999px;font-size:.75rem}\"\n        \".detail{margin-top:.6rem}.detail h3{font-size:.85rem;margin:.6rem 0 .2rem}\"\n        \".detail li{font-size:.85rem;margin-bottom:.2rem}\"\n        \".shots{display:flex;flex-wrap:wrap;gap:1rem;margin-top:.8rem}\"\n        \"figure{margin:0;max-width:320px}img{max-width:100%;border:1px solid #e2e5ea;\"\n        \"border-radius:6px}figcaption{font-size:.75rem;color:#667085;margin-top:.3rem}\"\n    )\n    html = (\n        \"<!doctype html><meta charset='utf-8'>\"\n        f\"<title>{escape(project_slug)} — {escape(run_id)} report</title>\"\n        f\"<style>{style}</style>\"\n        f\"<h1>{escape(project_slug)} — run report</h1>\"\n        f\"<p class='meta'>Run <code>{escape(run_id)}</code> · {len(results)} case(s)</p>\"\n        f\"{sections}\"\n    )\n    out_path.parent.mkdir(parents=True, exist_ok=True)\n    out_path.write_text(html, encoding=\"utf-8\")\n    return out_path\n"}
{"path":"src/autotester/core/excel.py","source":"\"\"\"Workbook presentation helpers shared by every Excel exporter.\n\nExtracted from `stages/report_export.py` when `stages/crawl_report.py` needed\nthe same column sizing: two exporters computing column widths two slightly\ndifferent ways is exactly the \"one concept, two places\" drift C3 forbids.\n\"\"\"\n\nfrom __future__ import annotations\n\nfrom pathlib import Path\nfrom typing import Any\n\nfrom openpyxl import Workbook\n\n\ndef autosize_columns(ws: Any, *, max_width: int = 60) -> None:\n    \"\"\"Widen every column to fit its longest cell, capped so one long error\n    string cannot push a column off the screen.\"\"\"\n    for column in ws.columns:\n        values = [cell.value for cell in column if cell.value is not None]\n        if not values:\n            continue\n        width = max(len(str(value)) for value in values)\n        ws.column_dimensions[column[0].column_letter].width = min(width + 2, max_width)\n\n\ndef export_run_workbook(\n    out_path: Path, header: list[str], rows: list[list], *,\n    ux_header: list[str], ux_rows: list[list],\n) -> Path:\n    \"\"\"Present precomputed data; no stage/store/model/provider dependencies.\"\"\"\n    wb = Workbook()\n    ws = wb.active\n    ws.title = \"Run report\"\n    ws.append(header)\n    for row in rows:\n        ws.append(row)\n    autosize_columns(ws)\n    if ux_rows:\n        ux = wb.create_sheet(\"UX findings\")\n        ux.append(ux_header)\n        for row in ux_rows:\n            ux.append(row)\n        autosize_columns(ux)\n    out_path.parent.mkdir(parents=True, exist_ok=True)\n    wb.save(out_path)\n    return out_path\n"}
```
<!-- T190-SCHEMA-WORKBOOK-PREVIEW-END -->

Count diagnostic is pending below until its actual output is appended. These bytes are unapproved proposals. No product imports, SDKs, tests, browser/network, .env, Docker, source writes or PASS were executed.

Actual data-only diagnostic receipt: PowerShell read the existing manifest's
T190-SCHEMA-WORKBOOK-PREVIEW JSONL block and the two original source texts,
serialized JSON to stdin of `D:/autoTesting/.venv/Scripts/python.exe -I -S -c`
(stdlib `ast,json,sys,hashlib` only). Native exit 0; no product/SDK import or
test execution. `ast.parse` succeeded for every whole candidate. Function
lengths below use end_lineno-lineno+1; these are AST measurements, not doctor.

```json
{"counts":[{"path":"src/autotester/schema/enums.py","lines":298,"max_function":0,"longest":[],"sha256_lf":"a5fc3d892fc3320b9c74ed6645f9a1efa6f82719b0f103deb1246a18a19ec258"},{"path":"src/autotester/schema/project.py","lines":169,"max_function":12,"longest":[["_configured_vision_providers",12],["vision_ensemble_defaulted",9]],"sha256_lf":"9f3a4e60d402517f0a3b96740e893b544c4bcaa3518029c8eb7a0efa52a7b326"},{"path":"src/autotester/schema/case.py","lines":130,"max_function":16,"longest":[["with_fixed_step",16],["compute_id",8]],"sha256_lf":"83cc00b87a9e6d19b691f675b059a1ea32de18600c4aa5fb0e043e24de186238"},{"path":"src/autotester/schema/user_persona.py","lines":16,"max_function":0,"longest":[],"sha256_lf":"adff603ee7edfd916d939a6e195e2c9b7571c8a5e0981f078fee9456d1086e4e"},{"path":"src/autotester/schema/ux_report.py","lines":56,"max_function":7,"longest":[["_complete_observation",7],["_noncomplete_has_no_findings",4]],"sha256_lf":"2ec76bfb632d03fbaa6e7dac87a0e130aac3314ec300737617a5d3cc5042f2ba"},{"path":"src/autotester/schema/run.py","lines":109,"max_function":0,"longest":[],"sha256_lf":"f8fa8ce322bd4a44f0a63364152c029c258d0d2963002deb4733ca4e50a68588"},{"path":"src/autotester/core/paths.py","lines":294,"max_function":24,"longest":[["prompts_dir",24],["ensure",12]],"sha256_lf":"66ae04a11496810b32fbea247de24f2930096a9297085844bd24aff24c49ce59"},{"path":"src/autotester/store/project_store.py","lines":263,"max_function":23,"longest":[["list_observations",23],["delete_case",14]],"sha256_lf":"386956d93cf64ea5d9a1bb985a2710ef27fddc7525233a43d8526f7422dfcba5"},{"path":"src/autotester/store/run_store.py","lines":76,"max_function":11,"longest":[["load_results",11],["load_verdicts",10]],"sha256_lf":"a0d327aa15397fe1cf92d90fa0e2b29dd9bf0231c992cda4b5a54c174908f03d"},{"path":"src/autotester/stages/report_export.py","lines":299,"max_function":40,"longest":[["export_html",40],["_case_section",32]],"sha256_lf":"a995052e29753af0a0ab97ce09bb4989d997a2d843ff5e6e59d18a9425e02821"},{"path":"src/autotester/core/excel.py","lines":47,"max_function":21,"longest":[["export_run_workbook",21],["autosize_columns",9]],"sha256_lf":"9d170c7f306e79c17ba10680965cf42bd7679e4e8214b427d68b248822509381"}],"six_moved_signatures":{"save_run":true,"load_run":true,"save_result":true,"load_results":true,"save_verdict":true,"load_verdicts":true},"export_signature_equal":true,"header_exact_equal":true,"all_caps":true}
```

Current-subset maximum is 299 file lines and 40 function lines. All 11 actual
full-text candidates satisfy <=300/<=50 by that diagnostic. Six moved public
run signatures and public export_excel signature compare equal by AST; the
eleven literal workbook headers compare equal by ast.literal_eval. Unchanged
row computation preservation was separately exact text compared in memory.
These facts do not establish runtime imports, behavioral equivalence, whole
T190 caps, import/doctor/lint cleanliness, product readiness or PASS.

Separate provider BLOCKER retained (root /root/t190_budget_readiness handoff):
installed google/genai/_api_client.py:870–875 then :877–880 constructs and
overwrites the first default AsyncHttpxClient when HttpOptions.httpx_async_client
is absent; LangChain client_args hooks become async-client kwargs, not an
explicit owned client, and public aclose closes the surviving client only.
This schema/workbook subset neither proves provider lifecycle readiness nor
patches an SDK. Physical-provider design remains its separate owner's work.

Finite preview checkpoint released. Root may obtain independent plan review
and exact path authorization; product implementation remains held. No further
schema/storage/export/evidence bodies are represented as complete by this receipt.

## Source-pinned AI Engineering Plan receipt — 2026-10-06

Reviewer:/root/t190_budget_readiness, fresh read-only ai-engineer role.
This is design evidence, not implementation-plan approval or acceptance. No
SDK/product imports, tests, provider/browser/network calls or SDK edits occurred.
Installed source pins:google/genai/_api_client.py SHA256
7ccb06e2ade9feea574ce858767824d749d6d7e2c50ccc8ef36b051bf3b5a341;
langchain_google_genai/chat_models.py SHA256
0f249f2e247b73ad0746a12d570b5222c6e508219634017b5e2c4329e7265cba;
uv.lock188681b3a300c36fb485c3979ccb735236e3073443d73015bbb3bace34c86ba1.
The unresolved construction seam must supply one owned explicit async client
before SDK construction, preserving resolved configuration; post-construction
model.client replacement or accepting the abandoned client is not a solution.
This technical gap is engineering work, not a new product-direction question.

The following Guardrails and Evaluation sections are quoted verbatim from
that review; their PASS lines are required future oracles, not measured results.

### Guardrails

- Reserve atomically before every metered send; keep failed reservations spent. Invoke receipt callbacks outside the accounting lock.
- Once stopped, retain that state across SDK wrappers, fallback catches, upload/cache catches and successful returns. Anthropic wraps transport exceptions into `APIConnectionError` at installed `_base_client.py:1277–1283` and retries those at 856–878.
- Preserve configured vendor/model/fallback identities and retry counts. Unsupported installed capabilities refuse before an unmetered invocation.
- Refuse running-event-loop invocation before construction for the proposed synchronous hook design; async HTTPX awaits the same hook list. Never reserve and then discover async incompatibility.
- Refuse Vertex/google-auth budgeting until its separate `AuthorizedSession` path, installed `_api_client.py:1477–1504`, is covered.
- Validate every model output against the schema and evidence citations. Empty findings require successful completed assessment; exhaustion, truncation, parsing failure and unsupported capability require distinct safe status.
- Bound application retries with the same run control; no budget reset through retries or report resume.
- Keep functional grading outside this pass. High-impact advisory findings receive human review before being used for product decisions.

### Evaluation (sample set · expected outputs · error categories · pass/fail rubric lines)

Freeze 18 synthetic transport/lifecycle scenarios across direct Anthropic, direct Gemini and both installed fallback adapters. Include cap zero/two, wrapped SDK retry, redirect, upload/chunk retry, cache/poll, constructor failure, malformed output, concurrency, configured proxy/headers/endpoint, fallback transition, async refusal and ownership failures.

Use actual installed adapter code against independent fake HTTP transports. Expected outputs are send counters, bounded request configuration, terminal receipt states, unchanged configured identity/order and close counters—not prose similarity. Error categories: cap escape, sticky-stop escape, identity drift, output-cap omission, unsafe receipt, lifecycle leak and false completion.

Verbatim-ready rubric lines:

- `PASS physical-cap: cap=2 permits at most two transport sends across retries, redirects, uploads, polling and fallback; cap=0 permits zero.`
- `PASS sticky-stop: SDK-wrapped exhaustion prevents every later send and fallback construction/invocation.`
- `PASS failure-accounting: failed sends remain spent; a constructor that sends nothing spends zero.`
- `PASS concurrency: two concurrent reservations cannot overspend the shared run limit.`
- `PASS provider-fidelity: vendor/model/order/retry/proxy/endpoint/header settings match the configured baseline except the explicitly approved UX output ceiling.`
- `PASS output-limit: every generation payload carries the approved adapter-specific ceiling; unsupported capability sends zero and records its reason.`
- `PASS lifecycle: all owned constructed clients close exactly once on success, failure, refusal and parsing failure; shared siblings remain usable.`
- `PASS secret-safety: synthetic credentials appear in no prompt, receipt, exception surface or persisted advisory artifact.`
- `PASS functional-isolation: complete serialized functional Verdict bytes are identical with the UX pass enabled and disabled.`
- `FAIL mutation-proof: removing transport reservation or sticky-stop propagation must make its named independent assertion fail.`

No evaluation was executed in this review.
