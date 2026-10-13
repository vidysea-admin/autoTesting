# Contract — agent-layer (Deep Agents product agent, D-042)

**Status:** ACTIVE for the T-179 criteria (AL1-AL7, AL11, and the AL12/AL13 mechanism; T-179 first checker PASS 2026-10-13, cycle 1). AL8-AL10 stay with T-180; the live AL12 comparison and the AL13 keep/drop decision stay with T-181. AL-prefixed criteria are
grouped by the unit that makes them judgeable — a criterion in a T-180/T-181 group cannot be
checked until that unit builds; the checker judges only the groups whose unit is in flight.
**Feature:** AutoTester's lead tester agent, built with LangChain Deep Agents' `create_deep_agent`
on LangGraph 1.x — a planning agent that delegates to subagents, loads prompts as skills, and acts
only through the existing deterministic stages, wrapped as tools rather than re-implemented.
**Covers:** goal tasks T-179 (lead agent + stage tools), T-180 (subagents), T-181 (guardrails +
measured gain). **Deps:** T-170 (network capture, DRAFT — not yet merged), T-172 (run trace,
DRAFT — not yet merged), T-175 (skills, DRAFT — not yet merged). **Grounding:** D-042 (full text)
and D-041 (framework layers, partially superseded by D-042); `core-invariants.md` C3, C7, C8;
`qa/contracts/skills.md` SK1-SK4 (the skill-loading mechanism this unit's `skills=` consumes);
`qa/contracts/run-trace.md` RT2-RT6 (the span shape every agent/tool call extends);
`qa/contracts/network-assertions.md` (the capture tool, if T-170 has merged by the time T-179
builds); `qa/contracts/consent.md` CN1-CN9 (`require_approval`); the code this unit wraps —
`stages/execute.py::run_case`, `stages/grade.py::grade`, `stages/expand.py::expand`,
`stages/explore.py` (+ `explore_safety.py::deny_reason`/`policy_for`, the existing write_policy
gate), `stages/portal_persona.py::build_portal_persona`, `stages/orchestrate.py::run_or_resume`;
`core/consent.py::require_approval`/`ApprovalRequired`; `core/redact.py::assert_no_raw_secrets`,
`Redactor`; `browser/secrets.py::SecretStore` (`{{SECRET:KEY}}` fill-time substitution only);
`schema/enums.py::WritePolicy`; `providers/base.py::Provider` (the seam every model call goes
through today, unchanged by this unit — Deep Agents' own model calls go through the same seam);
brain pages `umesh/operating-brain/wiki/concepts/krishnaik/deep-agents.md` (2026 update:
`create_deep_agent`, `skills=` needs `deepagents>=1.7`, three storage backends) and
`umesh/operating-brain/wiki/patterns/agentic-architecture-standard.md` rules 2 ("multi-agent only
with a measured gain") and 3 ("deterministic guards before LLM calls").

## What it is

Today the pipeline is a fixed sequence of pure `run(input, ctx) -> artifact` stage functions,
driven by `stages/orchestrate.py::run_or_resume` (`docs/ARCHITECTURE.md` "Pipeline"). D-042 adds a
**lead tester agent** on top, built with `create_deep_agent` (Deep Agents on LangGraph 1.x): it
plans a job as a to-do list (Deep Agents planning middleware) and delegates to subagents
(explorer, test-designer, runner, grader, reporter — T-180), using `projects/<slug>/` as its
filesystem backend. The agent and its subagents act **only** by calling tools that **wrap** the
existing stage functions — `crawl` (wraps `stages/explore.py`), `run_case` (wraps
`stages/execute.py::run_case`), `get_persona`/`get_catalog` (wrap `stages/portal_persona.py` /
the FlowSpec catalog), `capture_network` (wraps T-170's capture, when merged), `grade_case` (wraps
`stages/grade.py::grade`), `report` (wraps report generation), plus a `browser-use` step for
unknown screens (T-177, later runner tool). No tool re-implements a stage's logic; a tool that
duplicates what a stage already does is the C3 violation this unit is built not to commit.

The safety policy, credential boundary, write_policy and consent/`RunApproval` checks stay in
**code, inside each acting tool** — the same functions they run in today
(`explore_safety.py::deny_reason`, `core/consent.py::require_approval`,
`browser/secrets.py::SecretStore.resolve`, `core/redact.py::assert_no_raw_secrets`). The model
can request anything; the tool decides. This is rule 3 of the Vidysea standard applied literally:
the deterministic guard runs **before** the acting tool does anything observable, not as a prompt
instruction the model is asked to obey.

## Criteria — grouped by the unit that makes them judgeable

### T-179 group (AL1-AL7) — lead agent, stage tools, safety-in-tools

- **AL1 — Built with `create_deep_agent`.** The lead tester agent is constructed via
  `create_deep_agent` (not a hand-rolled LangGraph `StateGraph` reimplementing planning/subagents),
  with `deepagents>=0.7.24,<0.8` in `pyproject.toml` (D-089 item 1, Approved-by Umesh; the earlier `>=1.7` named a version that does not exist) added only within this unit. The planning middleware is `langchain.agents.middleware.TodoListMiddleware` passed explicitly, because 0.7.24 `create_deep_agent` adds no `write_todos` by default. (Falsifiable: `grep -rn "create_deep_agent"` in the agent module; `deepagents`
  present in `pyproject.toml` with the `>=0.7.24,<0.8` pin; a `write_todos` call updates `todos` in state; the agent object exposes the Deep Agents
  to-do-list/planning middleware, not a bespoke planner.)
- **AL2 — Every stage is exposed as a tool that WRAPS the existing function, never
  re-implements it (C3).** Each of `crawl`, `run_case`, `get_persona`, `get_catalog`, `grade_case`,
  `report` (and `capture_network`) is a thin tool function whose body calls the
  named existing stage function/module and does not duplicate its logic. `capture_network(case_id)` takes a case id, re-reads that case's stored NETWORK evidence and returns it filtered through `stages/network_capture.py::first_party_evidence` (a READ-effect tool, no browser; live capture stays inside `run_case`). (Falsifiable: for each
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
  produces (`qa/contracts/skills.md` SK1) over a read-only backend (the model cannot write, edit or delete a skill); exposing the other packaged SK1 skills, not only `agent-*`, is permitted: they are inert prompt text with no tool or capability, and least privilege (AL10) governs tools, not skill text; no agent or tool in this unit embeds a prompt as a Python
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

### T-180 group (AL8-AL10) — subagents (judgeable once T-180 builds)

- **AL8 — The grader subagent has NO action tools (C7).** The grader's tool list contains only
  read/evidence tools (e.g. reading `RawResult`, evidence files, the rubric) — no tool in its list
  can perform a browser action, a write, or call another stage that mutates project state.
  (Falsifiable: assert the grader subagent's configured tool list programmatically; every tool in it
  has no side-effecting capability — cross-checked against the same executor/grader separation
  `stages/grade.py`'s module docstring already states: "this stage never sees the case's steps or
  script, only the rubric and the evidence".)
- **AL9 — Subagents run in separate contexts.** Each subagent (explorer, test-designer, runner,
  grader, reporter) is invoked in its own Deep Agents subagent context, not sharing the lead
  agent's message history directly — matching the brain page's "context isolation" property of Deep
  Agents subagents. (Falsifiable: a fixture job driving two subagents whose combined transcripts
  would overflow one context window still completes, and inspecting the invocation shows each
  subagent's context does not contain the other's raw transcript, only what the filesystem/shared
  state deliberately passes.)
- **AL10 — Each subagent's tool list is the minimum it needs (explicit allowlist).** Every
  subagent is configured with an explicit, named tool allowlist (no subagent inherits "all tools" by
  default); the allowlist for each of the five subagents is named in the unit's manifest and matches
  what that subagent's job actually requires (e.g. the reporter has no browser-acting tool, the
  explorer has no `grade_case` tool). (Falsifiable: for each of the five subagents, its configured
  tool list is read programmatically and diffed against the full tool set — every tool NOT in a
  subagent's allowlist is confirmed absent from its available calls.)

### AL11-AL13 — guardrails + measured gain (scope split, ruled 2026-10-13)

**Scope split.** AL11 (the budget meter and halt) is a property of the lead agent and is judged in T-179. For AL12/AL13 the comparison *mechanism* (`agents/comparison.py`: both paths scored by the one `stages/bench.py` scorer, a report with the four numbers per path and an always-present verdict line) is judged in T-179 on **injected verdicts**. The *live* comparison (real `run_and_grade_case` vs the real agent on a seeded product in a visible browser, `tests/test_agent_gain.py`) and the keep/drop decision are T-181's. A T-179 PASS never claims a measured gain.

- **AL11 — A per-run token/cost budget halts the run with a named reason when exceeded.** The lead
  agent's run carries a declared budget (tokens and/or cost); when a run would exceed it, the run
  halts (not silently truncates) and records a named reason in the run's state/trace, distinguishable
  from every other stop reason (completion, error, HITL block). (Falsifiable: a fixture budget set
  below what a scripted job requires → the run halts before completion with a reason string naming
  the budget breach; a fixture budget set above requirement → the same job completes normally.)
- **AL12 — A fixture comparison, agent-vs-pipeline, reports bugs found, false positives, tokens
  and wall time.** The same fixture product/job is run once through the plain pipeline
  (`stages/orchestrate.py::run_or_resume` for the learn/explore stages up to the review gate, then each approved case through
  `stages/run_case_pipeline.py:143::run_and_grade_case`, the seam the UI run and CLI use) and once through the Deep Agents lead agent, and a
  comparison report records, for each: bugs found, false-positive count, total tokens, wall-clock
  time — the same axes `docs/ARCHITECTURE.md`'s north star names (`stages/bench.py:76::scorecard`
  precedent - `schema/bench.py` holds only the data models). (Falsifiable: run the comparison script on a seeded fixture corpus twice (once per
  path) → a report artifact with all four numbers populated for both paths, not estimated or
  asserted from memory.)
- **AL13 — The layer is kept only if the comparison shows a gain; otherwise the finding is
  recorded, not hidden.** T-181's manifest/report states explicitly whether AL12's comparison shows
  a gain on bugs-found or false-positive rate without breaching AL11's budget; if it does not, the
  unit records that outcome in the report and the ledger rather than omitting or reframing it, and
  D-042's layer is NOT declared "kept" on unfavourable evidence. (Falsifiable: the AL12 report's
  verdict line — gain / no gain, with the numbers it rests on — is present regardless of which way
  the comparison went; a report that only shows favourable outcomes and drops an unfavourable metric
  fails this criterion.)

**T-181 rulings (2026-10-13, /checker t181-guardrails cycle 1).** (1) `tests/test_agent_gain.py` on caller-supplied fake runners satisfies the goal `done_check` and the guardrail/harness mechanics; AL12's *live* run (real `run_and_grade_case` vs the real agent, seeded product, visible browser) and the AL13 keep/drop declaration remain open and gate T-181 closing. (2) `schema/agent_guardrails.py::WinRule` is the one win rule for AL13 (provisional default, awaiting Umesh: agent bugs >= pipeline AND agent FP rate <= pipeline, tie = gain; budget default 200k tokens / $2.00); `comparison.compare(rule=None)` keeps T-179's stricter rule only for T-179's injected-verdict tests. (3) An FP rate of None from the scorer (nothing reported) is treated as 0.0, and the report must say so.

## Explicit no-fire list (do not raise these as findings)

- **Hosted agent runtime.** Managed Deep Agents (LangSmith-hosted) or Claude Managed Agents —
  self-hosted only, matching the student-data hard boundary the brain page and
  `agentic-architecture-standard.md` state; raising "why not the hosted runtime" is out of scope and
  contrary to D-042.
- **Replacing deterministic crawl/safety logic with model judgement.** `explore_safety.py`'s
  `deny_reason`, `core/consent.py`'s `require_approval`, and `browser/secrets.py`'s scoping stay
  code; a finding that the agent "should decide" any of these is out of scope — AL3 exists
  specifically to keep them in code.
- **A2A (agent-to-agent, cross-vendor/cross-team protocol).** Not adopted here; D-042 names no
  cross-boundary agent communication and the standard reserves A2A for crossing a team/vendor
  boundary, which this unit does not do.
- **Langfuse export (D-041 phase 2).** AL5 covers the local `trace.jsonl` span shape only; raising
  "should also export to Langfuse" against this contract is the same out-of-scope carved out by
  `run-trace.md`'s own no-fire list.
- **T-177's browser-use fallback implementation details.** This unit only requires that
  browser-use becomes *one of the runner's tools* once T-177 lands; the fallback mechanism's own
  correctness is T-177's/`agent-loop.md`'s contract, not this one's.
- **The exact LangGraph checkpointer/persistence wiring for T-167's release-regression run.** D-042
  names it as a later consumer of the lead agent on LangGraph checkpoints; it is not a criterion
  here.
- **Whether `create_deep_agent` returns a graph that can be mounted as a subgraph elsewhere** — the
  brain page marks this `[UNVERIFIED — test before relying]`; a finding that this unit didn't prove
  or use that property is out of scope unless a criterion above names it.

## How a unit is verified (adapter slot 1)

`uv run pytest tests/test_agent_layer.py` (T-179's `done_check`) / `tests/test_agent_subagents.py`
(T-180's `done_check`) / `tests/test_agent_gain.py` (T-181's `done_check`) — each bare, no CLI `-q`
(AT-503) — + `uv run ruff check src tests scripts` + `uv run autotester doctor`, all exit 0; each
AL criterion carries a capability-coverage row with a single-hunk falsifying edit reproduced
green→red-for-the-named-reason→revert→green. File/function caps (core-invariants C2) apply; if a
touched module has no headroom under its 300-line cap, the new logic lands in a new, justified
module per C3 rather than pushing the file over budget. AL3's three sub-clauses each need their own
falsifying edit — a single row covering "guards run in tools" is not sufficient evidence for three
separate refusal paths.

## Amendment log (append-only; git history is the version)

- 2026-09-24 · init · contract authored by /checker as DRAFT, from D-042 (Approved-by Umesh —
  AskUserQuestion answers "Haan, Umesh approve (Recommended)" + "Wave 1 ke baad (Recommended)",
  chat 2026-09-24, `qa/gates/d042-deep-agents.md`), grounded in D-041 (framework layers, partially
  superseded), `umesh/operating-brain/wiki/patterns/agentic-architecture-standard.md`, and
  `umesh/operating-brain/wiki/concepts/krishnaik/deep-agents.md`. No prior draft existed; nothing
  amended. T-180/T-181 groups are pre-registered ahead of their units building, per D-042's dispatch
  instruction; they become judgeable only once T-180/T-181 are in flight.
- 2026-09-28 - routine (correct) - the cited scorecard precedent updated from `schema/bench.py::scorecard`
  to `stages/bench.py:76::scorecard`. Cause: AT-691. `schema/bench.py` holds only the Pydantic models
  (SeededBug, Finding, BenchCorpus, BenchTrial); the function is in the stage. `qa/contracts/bench.md:44`
  already cited it correctly, so this was a one-file drift, not a shared error. No criterion changed -
  this contract is DRAFT and the line is a precedent citation inside a falsifiability note.
  **Changes-authorized:** qa/contracts/agent-layer.md (the T-181 comparison note) + Amendment log (this
  entry). **Links:** AT-691.
- 2026-10-11 - routine (correct; no criterion weakened) - **AL12's "plain pipeline" entry point named precisely.** AL12 named
  `stages/orchestrate.py::run_or_resume` as the plain path whose bugs-found and false-positive numbers are compared. Verified in code:
  `run_or_resume` wires only {INGEST|DISCOVER, MODEL} and halts at the review gate (`stages/orchestrate.py:53`, `:189`); it never
  executes or grades a case, so it cannot produce either number. Case execution and grading is `run_and_grade_case`
  (`stages/run_case_pipeline.py:143`; resilient wrapper `:174`, used by `ui/run_execution.py:52`). AL12 now names both: the stage walk
  up to the gate, then the per-case seam. The four axes, the seeded-fixture verify and AL13 are unchanged. AL1's `deepagents>=1.7`
  floor was **not** touched (NEEDS-OWNER). **Links:** T-181; AL12; AL13; AT-691.
- 2026-10-13 - /checker t179d-agent-layer, cycle 1 PASS - **AL1** floor amended `deepagents>=1.7` -> `>=0.7.24,<0.8` per D-089 item 1 (Approved-by Umesh); explicit `TodoListMiddleware` accepted as the planner. **AL2** `capture_network` input specified (case id, stored NETWORK evidence, `first_party_evidence`). **AL4** ruled: `skills=["/"]` exposing all packaged skills read-only does not violate AL4 (skill text is not a capability; deny-write tested). **AL11-AL13** scope split written in place. Status DRAFT -> ACTIVE for the T-179 criteria. No criterion weakened. **Links:** D-042; D-089; T-179; T-181.
