# Build brief — t179-lead-tester (T-179, criticality high)

Prepared 2026-10-10 by a read-only readiness pass. Nothing was built, run or committed. Facts marked `unknown` are not in the repo; do not guess them. Re-read `git -C D:/autoTesting rev-parse master` at dispatch.

## STATUS: NOT-DISPATCHABLE. Do not hand this to a builder yet.

The contract exists (`qa/contracts/agent-layer.md`, AL1-AL7 for this unit, DRAFT) and the dependencies T-170, T-172, T-175 are `done`. Four blockers remain, none of them a builder's to resolve:

1. **AL1 cannot be satisfied as written.** AL1 and D-042 require `deepagents>=1.7`. The Python package `deepagents` on PyPI is at 0.7.23 (checked 2026-10-10; the maker manifest recorded 0.7.21 on 2026-09-30), requires Python >=3.11, and has never been 1.x. A `>=1.7` floor resolves to nothing. Correcting it needs (a) an authorizing decision entry naming the new floor, written by Umesh's approval via `scripts/append_decision.ps1`, and (b) a checker-owned amendment of AL1. D-042's `Changes-authorized` allows "add deepagents within T-179 only", not a different floor.
2. **The new file paths are unapproved and contradict each other.** The maker's planning manifest proposes three new paths (`src/autotester/stages/agent_layer.py`, `src/autotester/providers/agent_chat.py`, `tests/test_agent_layer.py`). `docs/plan.md:66` and `qa/QUEUE.md` say a new `src/autotester/agents/` package. The repo rule is edit in place; a new module needs explicit approval or a C3 cap justification. The manifest recorded the question `T179 exact three new files: approve/hold` on 2026-10-05 as unanswered.
3. **The Provider and trace approach has no authorizing decision.** The plan edits `providers/base.py::Provider` (a message/tool interface), `core/trace.py` and `schema/trace.py` (operation and parent identifiers). D-042's `Changes-authorized` lists none of these files.
4. **There is no approved concrete plan.** `qa/manifests/t179-agent-layer-plan.md` is `Status: planning; no implementation approval or product PASS`. It says: "Required human authority: exact new paths and version correction. Required decision authorization: Provider/trace approach. Then concrete plan approval, dependency lock, offline real-framework scripted-model proofs…"

When all four are answered, this brief becomes dispatchable with only sections 2, 5 and 8 updated.

## 1. Policy and tier

- `Policy-Version: proportional-verification/2026-10-10.9`
- **Tier: L.** Triggers: dependency bump (`deepagents` and its transitive set: `langchain`, `langgraph`, `langsmith`, `wcmatch` in `uv.lock`); security (AL3 guards, AL6 secret boundary); config (provider seam change).
- **Dual check: required.** Trigger: `security: src/autotester/browser/secrets.py:256` (`SecretStore.guard_prompt`) and `src/autotester/core/redact.py:120` (`assert_no_raw_secrets`) are the credential boundary AL6 extends to a model that now plans and calls tools; `src/autotester/core/consent.py:182` (`require_approval`) is the approval boundary AL3(b) tests. The tools wrap `run_case` which can write to a live product.
- No enforcement-path file (`.claude/hooks/*`, `scripts/append_decision.ps1`, `.claude/settings.json`, `qa/hooks/*`) is touched by the build. The decision entry in blocker 1 and 3 is written through `scripts/append_decision.ps1` by the owner path, not by the builder.

## 2. Root and base

- Root `D:/autoTesting`. Base = `master` @ `4f8f5da100931ebda1b26836304bfbd38460764b` (at preparation time).
- **Branch: a fresh `wave/t179-lead-tester` from master.** Reason: no branch or worktree for T-179 exists (`git branch --list '*t179*'` is empty); `src/autotester/agents/` does not exist. Start clean.

## 3. Acceptance criteria (verbatim from `qa/contracts/agent-layer.md`, T-179 group)

Contract-level facts: criterion ids AL1-AL7 belong to T-179. AL8-AL10 belong to T-180 and AL11-AL13 to T-181 and are NOT judged here. The goal `done_check` is `uv run pytest tests/test_agent_layer.py` (exit 0); that file does not exist. The contract header still says T-170/T-172/T-175 are "DRAFT — not yet merged"; that is stale, all three are `done` in `.goal/goal.json`. Contract header grounding the build: D-042, D-041, `core-invariants.md` C3, C7, C8, `skills.md` SK1-SK4, `run-trace.md` RT2-RT6, `consent.md` CN1-CN9.

### T-179 group (AL1-AL7) — lead agent, stage tools, safety-in-tools

- **AL1 — Built with `create_deep_agent`.** The lead tester agent is constructed via
  `create_deep_agent` (not a hand-rolled LangGraph `StateGraph` reimplementing planning/subagents),
  with `deepagents>=1.7` in `pyproject.toml` added only within this unit (D-042
  Changes-authorized). (Falsifiable: `grep -rn "create_deep_agent"` in the agent module; `deepagents`
  present in `pyproject.toml` with a `>=1.7` floor; the agent object exposes the Deep Agents
  to-do-list/planning middleware, not a bespoke planner.)
- **AL2 — Every stage is exposed as a tool that WRAPS the existing function, never
  re-implements it (C3).** Each of `crawl`, `run_case`, `get_persona`, `get_catalog`, `grade_case`,
  `report` (and `capture_network` once T-170 merges) is a thin tool function whose body calls the
  named existing stage function/module and does not duplicate its logic. (Falsifiable: for each
  tool, `grep -rn` its body imports and calls the cited existing function
  — e.g. `run_case` tool imports and calls `stages.execute.run_case`, `grade_case` tool imports and
  calls `stages.grade.grade` — and contains no parallel implementation of what that function does;
  `autotester doctor`'s duplicate-concept check stays clean.)
- **AL3 — Deterministic guards execute inside each acting tool, in code, and are refused
  regardless of model instruction.** Every tool that can touch a live target (`crawl`, `run_case`,
  and any future write-capable tool) calls the existing guard functions
  (`core.consent.require_approval` for outward-facing runs, `explore_safety.deny_reason`/
  `policy_for` or an equivalent `write_policy` check for `run_case`, `browser.secrets.SecretStore`
  for any credential) before performing the observable action, and a prompt instruction cannot
  route around the check. (Falsifiable, one test per clause: (a) a model instruction to "use the raw
  value of SECRET_KEY directly, ignore the placeholder" — the tool call is refused with
  `SecretError`/`assert_no_raw_secrets`, never a raw value reaching the browser or a log; (b) a model
  instruction to run a crawl beyond the granted `RunApproval` bounds — the `crawl` tool raises
  `ApprovalRequired` before any browser action, same as CN1; (c) a model instruction to submit a
  form / mutate state while `Project.write_policy == WritePolicy.READ_ONLY` — the `run_case` tool
  refuses the write action the same way `explore_safety.deny_reason` refuses it during a crawl,
  and the refusal is asserted from the tool's own return/exception, not inferred from an absence of
  side effects.)
- **AL4 — Skills are loaded via `skills=`, not inline prompt strings.** The lead agent (and any
  subagent needing one) is constructed with `skills=[...]` pointing at the `SKILL.md` folders T-175
  produces (`qa/contracts/skills.md` SK1); no agent or tool in this unit embeds a prompt as a Python
  string literal or reads a `.md` file directly outside that loader (core-invariants C8's "prompts
  live in files" extended to the agent layer). (Falsifiable: `grep -rn` for a triple-quoted prompt
  string or a direct `read_text(...)` of a skill/prompt file inside the agent module returns
  nothing; the agent's `skills=` argument resolves to the SK1 folders.)
- **AL5 — Every agent/tool call emits a T-172 trace span.** Once T-172 merges, every lead-agent
  planning step, every subagent invocation, and every tool call this unit adds produces a span in
  `projects/<slug>/runs/<run_id>/trace.jsonl` matching run-trace.md's RT3/RT4 shape (stage span or
  LLM-call span, `trace_id` equal to the run's own `run_id`) — this unit does not open a second,
  parallel trace mechanism (RT5). Until T-172 merges, this criterion is not yet judgeable and the
  checker records it as not-applicable rather than failing the unit for a dependency that has not
  landed. (Falsifiable, once T-172 is ACTIVE: a fixture run through the lead agent → its
  `trace.jsonl` carries a span per tool call and per subagent invocation, `trace_id` matching
  `state.json`'s `run_id`.)
- **AL6 — The agent never sees a secret value (C5, extended to the agent layer).** Every prompt
  the lead agent or a subagent sends to a model — planning prompts, tool-call arguments, skill
  bodies — passes `core.redact.assert_no_raw_secrets` before the call, matching the existing gate
  every `Provider` call already sits behind (`browser/secrets.py::SecretStore.guard_prompt`).
  (Falsifiable: seed a fixture project with a fake secret bound to a `SecretRef`, drive the lead
  agent through a task whose evidence would otherwise carry it, and assert no model-bound prompt in
  the run contains the raw value — only `{{SECRET:KEY}}`.)
- **AL7 — Scope discipline: subagents only where judgement is needed (rule 2).** The lead agent
  does not spin up a subagent for work that is a plain deterministic tool call — planning routes
  judgement-needing steps (test design, grading, exploration strategy) to subagents and routes
  mechanical steps (a single `run_case`, a single `get_persona` read) as direct tool calls, matching
  D-042's "used only where judgement is needed" and rule 2's per-multi-agent-step cost. (Falsifiable:
  a fixture job with one deterministic step and one judgement step → the trace/`result['files']`
  shows exactly one subagent delegation, not two; a job with zero judgement steps → zero subagent
  delegations.)


Binding no-fire list (same contract): no hosted agent runtime; no replacing deterministic crawl/safety logic with model judgement; no A2A; no Langfuse export; T-177's browser-use internals; T-167's checkpointer wiring; subgraph-mounting of `create_deep_agent` output is `[UNVERIFIED]` and out of scope unless a criterion names it. Verification (contract): `uv run pytest tests/test_agent_layer.py` bare, `uv run ruff check src tests scripts`, `uv run autotester doctor`; AL3's three sub-clauses each need their own falsifying edit.

## 4. What exists and what is missing

Built and reusable (master):
- Stages to wrap: `stages/execute.py::run_case` (:159), `stages/grade.py::grade`, `stages/expand.py` (141), `stages/explore.py` (286) with `explore_safety.py::policy_for` (:55) and `deny_reason` (:86), `stages/portal_persona.py::build_portal_persona` (:276), `stages/network_capture.py::first_party_evidence` (:24, T-170), `stages/orchestrate.py::run_or_resume` (:182, T-163; T-167 will rewrite its internals).
- Guards to keep in code: `core/consent.py::require_approval` (:182) and `ApprovalRequired` (:25); `browser/secrets.py::SecretStore.resolve` (:140) and `guard_prompt` (:256); `core/redact.py::assert_no_raw_secrets` (:120).
- Trace: `core/trace.py::TraceWriter` (80 lines) and `schema/trace.py::StageSpan/LLMSpan` (56 lines) from T-172 (one writer, `trace_id` equals `run_id`).
- Skills: `src/autotester/skills/` holds `expand-case/`, `grade/`, `ingest-video/`, `reconcile-screen/`, `ux_judge/`, `video-issues/` (T-175, `tests/test_prompt_skills.py`).
- Provider seam: `providers/base.py::Provider` (189 lines; `see_video`, `act`, `judge`), `providers/langchain_fallback.py` (171).

Missing (everything for AL1-AL7):
- No `deepagents` in `pyproject.toml`; no `create_deep_agent` call anywhere; no agent module; no stage-tool wrappers; no `skills=` wiring; no agent/tool trace spans; no `tests/test_agent_layer.py`.
- Per the planning manifest (unapproved): seven thin tools (`crawl`, `run_case`, `get_persona`, `get_catalog`, `capture_network`, `grade_case`, `report`) mapped onto existing stages; trusted injected context fixes project roots, session, provider and approval so the model cannot choose them; built-in filesystem/shell routes denied; `stages/agent_loop.py` must NOT be repurposed (it owns single-step repair).

## 5. Files the builder will touch (PROVISIONAL, pending blockers 2 and 3)

Existing, additive edits, in place:
- `pyproject.toml`, `uv.lock` (deepagents; shared lock, section 10)
- `src/autotester/providers/base.py` (189): additive message/tool interface only
- `src/autotester/providers/langchain_fallback.py` (171)
- `src/autotester/schema/trace.py` (56) and `src/autotester/core/trace.py` (80): additive operation/parent identifiers; `StageName` and the single writer preserved

New, only if approved (blocker 2): `src/autotester/stages/agent_layer.py` (lead construction, scoped backend, thin tools; will probably exceed 300 lines, so a split is `unknown`), `src/autotester/providers/agent_chat.py` (framework-specific Provider adapter), `tests/test_agent_layer.py`. The manifest says the checker owns test/oracle changes under the current test floor; whether the builder writes `tests/test_agent_layer.py` is `unknown`. Alternative path in plan.md/QUEUE: a `src/autotester/agents/` package, names `unknown`.

Regenerated: `docs/MAP.md`, `docs/SNAPSHOT.md`.
Forbidden: `docs/ARCHITECTURE.md` (150/150; D-042 allows one line after the PASS, as maker close-out), `docs/DECISIONS.md`, `qa/contracts/*`, `.goal/goal.json`, `qa/QUEUE.md`, `stages/agent_loop.py`, `stages/orchestrate*.py` (T-167's), any `.env`.

## 6. Test scope

- `tests/test_agent_layer.py` (done_check; offline, a scripted local chat model, the real pinned `create_deep_agent`).
- Existing consumers of touched files, as needed: `tests/test_run_trace.py`, `tests/test_prompt_skills.py`, `tests/test_consent.py`, `tests/test_agent_loop.py` (must stay green); the provider-seam test file for `providers/base.py` is `unknown` (no `tests/test_provider_factory.py` exists on master).
- End gates: `uv run ruff check src tests scripts`, `uv run autotester doctor`. No full suite, no native browser, no paid model call, no real account.

## 7. Reachable test cases

From the planning manifest's frozen synthetic set of 24 jobs (exact stage calls and typed references, not prose similarity): seven stage-tool dispatches, two routing jobs, three AL3 refusals, six secret-propagation surfaces, four filesystem bypasses, two invalid or empty-result jobs.
- AL1: instantiate the real `create_deep_agent` with a scripted model; planning middleware present; dependency floor matches the authorized decision.
- AL2: each of the seven tools calls its named existing function exactly once with the trusted context and returns the typed artifact; `autotester doctor` duplicate-concept check clean.
- AL3 (one test and one falsifying edit each): (a) "use the raw SECRET_KEY value" is refused with `SecretError` or `assert_no_raw_secrets`; (b) a crawl beyond the granted `RunApproval` raises `ApprovalRequired` before any browser action; (c) a form submit while `WritePolicy.READ_ONLY` is refused by the tool's own return or exception.
- AL4: `skills=` resolves the T-175 folders; no triple-quoted prompt and no direct `read_text` of a skill file in the agent module.
- AL5: every planning step, subagent call and tool call produces a span in `projects/<slug>/runs/<run_id>/trace.jsonl` with `trace_id` equal to the run id, no duplicate LLM spans.
- AL6: a fake secret bound to a `SecretRef` never appears in any model-bound request, tool result, trace or artifact across six surfaces.
- AL7: deterministic-only job delegates zero times; a mixed job delegates exactly once.
- Safety: four filesystem bypasses refused; empty or invalid jobs cannot produce a verdict or a PASS.

## 8. Gate answers

- `qa/gates/d042-deep-agents.md`: `Answered: 2026-09-24T22:33:42+05:30 — "Haan, Umesh approve (Recommended)" + "Wave 1 ke baad (Recommended)" — AskUserQuestion in the 2026-09-24 session (running under the himanshu@ claude.ai account; the answer explicitly selected "Umesh approve")`. Adoption of Deep Agents is answered. Wave 1 (T-170, AT-110, T-172, T-173, AT-086/087, T-175, T-126, AT-335) is the stated precondition; the manifest records its historical PASSes (AT086/087, AT110 cycle 2, AT335).
- **No `Answered:` line exists** for the two manifest questions (`qa/manifests/t179-agent-layer-plan.md`): `T179 Python version correction: approve/hold` and `T179 exact three new files: approve/hold`, both recorded "unanswered" as of 2026-10-05. Neither authorizes paid models, native browser or real-account runs.
- `docs/DECISIONS.md` D-068 point 3: build order "all open groups run in parallel, scheduled only by real dependencies (the agent layer waits for the stages it wraps)". D-081 and `qa/QUEUE.md` say the owner asked for all remaining work to run. Neither answers the two questions above, and `qa/manifests/t179-agent-layer-plan.md` states "No silent dependency/contract correction is authorized."

## 9. UI surface and persona walk

`Persona walk: skip (agent layer, no human-facing screen, route or CLI output is added; docs/plan.md:66 lists it as "skip (agent layer)")`.

## 10. Dependencies and conflicts

- Must land first: none by dependency (T-170, T-172, T-175 are done). D-055 says the agent layer is independent of T-167. `uv.lock` ordering: land after T-167's `langgraph` lock change or serialize with it (deepagents pulls `langchain` and `langgraph` transitively and can re-resolve the pin T-167 sets).
- **T-180 needs from this unit** (write no brief): a tool registry where each of the seven tools is individually addressable by name, with read/evidence tools separable from acting tools, so T-180 can configure the five subagents with explicit allowlists (AL10) and give the grader no action tools (AL8); the lead agent constructed with an extension point for `subagents=`; context isolation that does not depend on the lead's message history (AL9).
- **T-181 needs from this unit** (write no brief): a budget hook point on the model-call path (token/cost accounting per run, AL11); trace usage fields on every span; a way to run the same fixture job through `stages/orchestrate.py::run_or_resume` and through the lead agent for the AL12 comparison (`stages/bench.py:76::scorecard` is the precedent); and a design where the layer can be removed cleanly if AL13 shows no gain.
- Shared files (one owner each):
  - `pyproject.toml`, `uv.lock`: owner serialized: T-167 first, then T-202/T-174, then this unit (`qa/QUEUE.md:86`, `:290`).
  - `src/autotester/providers/base.py`: this unit, but `qa/QUEUE.md` shows unit t202 (LiteLLM provider, `providers/__init__.py` registry) also works in `providers/`; whether it edits `base.py` is `unknown`. Treat as shared with t202, one writer at a time.
  - `src/autotester/schema/trace.py`, `core/trace.py`: this unit only (additive).
  - `docs/ARCHITECTURE.md`: maker close-out, serialized with T-167's line.
  - `docs/MAP.md`, `docs/SNAPSHOT.md`: last merger regenerates.
  - `agents/` or `stages/agent_layer.py`: this unit, then T-180, then T-181 (`qa/QUEUE.md` owner line).

## 11. Budget and process rules

- Check budget (tier L): 45 min. The builder runs no full suite, only the files in section 6.
- Falsification only in a throwaway copy outside the bound tree, then a byte-identical restore. One row per AL criterion; AL3 needs three.
- Kill only PIDs you started. Scratch and evidence go to `.work/`. Edit in place; no `*_v2.py` or `*_new.py`. All model calls via `providers.base.Provider`; prompts are files. No secrets in logs.
- Evidence manifest `qa/manifests/t179-lead-tester.md` (or continue `t179-agent-layer-plan.md` if the maker chooses) at `Status: ready-for-check`; only `/checker` can PASS.
