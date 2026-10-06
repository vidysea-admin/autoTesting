# T179 preimplementation AI-engineering plan

Status: planning; no implementation approval or product PASS.
Human questions asked once on 2026-10-05: `T179 Python version correction:
approve/hold` and `T179 exact three new files: approve/hold`. Both unanswered.
Neither question authorizes paid models, native browser or real-account runs.
Policy: proportional-verification/2026-10-05.2; root policy-check exit0, targets4 drift0.
Pinned root baseline: bd2fe8f4. Separate T151 candidate remains unmerged.

## Authority and unresolved inputs

Framework adoption was already approved in qa/gates/d042-deep-agents.md.
Explicit T179 dependencies T170/T172/T175 are done. Fresh read-only AI-engineer
review inspected historical Wave1 verdicts: AT086/087 supervising PASS;
AT110 cycle2 PASS, 4c3b1b3 ancestor master exit0; AT335 PASS, eae44a3a and
f395852d ancestor master exit0. These are historical closure, not current browser proof.

AL1/D042 require Python deepagents>=1.7. Official Python PyPI currently lists
0.7.21 (September30): https://pypi.org/project/deepagents/ . Root independently
verified this. No silent dependency/contract correction is authorized.
Proposed authorizing decision must correct Python version requirement while
retaining real create_deep_agent, planning middleware, skills loading and AL1–AL7.

Proposed necessary new code/test paths require Umesh's explicit authorization:
src/autotester/stages/agent_layer.py (lead construction/scoped backend/thin tools),
src/autotester/providers/agent_chat.py (framework-specific Provider adapter),
tests/test_agent_layer.py (checker-owned acceptance). None created.

Existing targets: providers/base.py::Provider additive message/tool interface;
providers/langchain_fallback.py existing vendor integration; schema/trace.py and
core/trace.py additive operation/parent identifiers preserving StageName and one writer.
Exact diff/line-bound implementation plan and fresh independent approval remain required.
Do not repurpose stages/agent_loop.py: it owns single-step repair.

Seven thin tools wrap existing crawl, run_case, persona store, FlowSpec store,
network capture lifecycle, independent grade and report implementations.
Trusted injected context fixes project roots, session, provider and approval;
model cannot choose these. Preserve fixed pipeline entry and stage logic.
Map crawl→DISCOVER, catalog/persona→MODEL, case/network→EXECUTE,
grade→GRADE, report→REPORT; never disguise planning as a completed checkpoint.

## Guardrails — verbatim independent AI-engineering review

- Validate every tool argument and artifact against its existing schema; reject unknown tools, fields, paths and malformed model output before action.
- Run signed consent, approval bounds, write-policy and SecretStore checks inside each acting tool before browser activity; model instructions cannot widen trusted context.
- Guard every physical model request, including skills, tool results, summarization and fallback attempts; redact and validate model-visible output, traces and persisted artifacts.
- Deny built-in filesystem/shell routes around the stage tools; expose only scoped sanitized reads and ephemeral scratch, never credentials or canonical approval/verdict writes.
- Keep executor observations separate from the independent judge. Uncertainty, missing evidence and empty results stop as incomplete/HITL, never PASS.
- Bound retries and graph steps; do not retry policy refusals. Real accounts, native browser execution and paid model calls require their separate existing grants.
- Keep T180 subagent hardening and T181 cost/gain acceptance separate; T179 does not claim their completion.

## Evaluation — verbatim independent AI-engineering review

Use a frozen synthetic set of 24 jobs: seven stage-tool dispatches, two routing jobs, three AL3 refusals, six secret-propagation surfaces, four filesystem bypasses, and two invalid/empty-result jobs. Expected outcomes are exact stage calls, typed artifact references, refusal classes, model-bound sanitized messages and operation-tagged trace events—not prose similarity.

- AL1 PASS: instantiate the real pinned `create_deep_agent` with a scripted local chat model; prove planning middleware and the authorized dependency requirement.
- AL2 PASS: all seven tools call their named existing implementation exactly once with trusted context and produce the expected typed output; no duplicated stage logic.
- AL3 PASS: raw-secret, exceeded-approval and read-only-submit jobs each raise the named refusal before observable action; each clause has its own failing-first mutation.
- AL4 PASS: real `skills=` resolves T175 directories and loads through the framework loader; no inline prompt or agent-module direct Markdown reader.
- AL5 PASS: every tested planning/model/tool invocation is attributable in the existing run trace, with the same run_id and no duplicate LLM spans.
- AL6 PASS: fake secrets are absent from every physical model request, tool result, trace and artifact across all six propagation surfaces.
- AL7 PASS: deterministic-only job delegates zero times; mixed deterministic/judgement job delegates exactly once to a minimal scripted judgement context, without claiming T180’s five-agent completion.
- Safety PASS: all four filesystem bypasses are refused; invalid/empty jobs cannot complete successfully or produce a verdict.
- Overall FAIL: any unsafe action, secret exposure, missing required span, fabricated completion, incidental mutation failure, or missing AL criterion.

Independent checker owns test/oracle changes under the current test floor and reproduces criterion-specific falsifications. Run the focused done_check, lint and doctor, then the mandatory feature-boundary full suite and Mode B sweep when their environment gates permit; no selected-check-only completion.

## Remaining sequence

Required human authority: exact new paths and version correction. Required decision
authorization: Provider/trace approach. Then concrete plan approval, dependency lock,
offline real-framework scripted-model proofs, guard-first integration, checker
AL1–AL7 falsification, merged-feature checks and separately authorized live validation.
Current review ran no model, browser, package install or secret/account inspection.
