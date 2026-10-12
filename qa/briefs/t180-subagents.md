# Build brief - t180-subagents (T-180, readiness pass 2026-10-11, NOT YET DISPATCHABLE)

Written by a read-only readiness pass. Nothing here was built or run. Where the repo does not say, this brief says `unknown`.
Dispatch trigger: T-179 reaches a checker PASS merged to master. T-179 is itself not startable yet (section 4).

## 1. Policy and tier

- `Policy-Version: proportional-verification/2026-10-10.9`
- Tier: **L**. Triggers: security (the C7 boundary: the grader holds no action tools, AL8; per-subagent minimum tool allowlists, AL10; the credential boundary must stay in code, AL6) and concurrency (subagents run in separate contexts, AL9, and `Provider.record` is shared under `_usage_lock`, `src/autotester/providers/base.py:55-63`, AT-569).
- `Dual check: no`. Reason: no real `security|auth|tenancy|prod-write <path:line>` exists to cite yet, because the `agents/` code does not exist. Re-decide at dispatch: the dual check becomes `required` if the diff touches `src/autotester/core/consent.py`, `core/redact.py` or `browser/secrets.py` (the existing guards, `consent.py` is 220 lines), or if the grader's allowlist is enforced anywhere other than a single, grep-able construction site.

## 2. Root and base

- Root: `D:/autoTesting`
- Base: the master commit where **T-179** (`t179-deep-agents-lead`) lands with a checker PASS. Record the SHA in the manifest.
- Branch: `wave/t180-subagents`
- `.goal/goal.json`: T-180 `deps = [T-179]`; T-179 `deps = [T-170, T-172, T-175]` (all three done). T-181 depends on T-180.

## 3. Acceptance criteria (verbatim from `qa/contracts/agent-layer.md`, status DRAFT, goes ACTIVE on T-179's first PASS)

The contract covers T-179, T-180 and T-181 and says "the checker judges only the groups whose unit is in flight". The T-180 group:

- **AL8 - The grader subagent has NO action tools (C7).** The grader's tool list contains only
  read/evidence tools (e.g. reading `RawResult`, evidence files, the rubric) - no tool in its list
  can perform a browser action, a write, or call another stage that mutates project state.
  (Falsifiable: assert the grader subagent's configured tool list programmatically; every tool in it
  has no side-effecting capability - cross-checked against the same executor/grader separation
  `stages/grade.py`'s module docstring already states: "this stage never sees the case's steps or
  script, only the rubric and the evidence".)
- **AL9 - Subagents run in separate contexts.** Each subagent (explorer, test-designer, runner,
  grader, reporter) is invoked in its own Deep Agents subagent context, not sharing the lead
  agent's message history directly - matching the brain page's "context isolation" property of Deep
  Agents subagents. (Falsifiable: a fixture job driving two subagents whose combined transcripts
  would overflow one context window still completes, and inspecting the invocation shows each
  subagent's context does not contain the other's raw transcript, only what the filesystem/shared
  state deliberately passes.)
- **AL10 - Each subagent's tool list is the minimum it needs (explicit allowlist).** Every
  subagent is configured with an explicit, named tool allowlist (no subagent inherits "all tools" by
  default); the allowlist for each of the five subagents is named in the unit's manifest and matches
  what that subagent's job actually requires (e.g. the reporter has no browser-acting tool, the
  explorer has no `grade_case` tool). (Falsifiable: for each of the five subagents, its configured
  tool list is read programmatically and diffed against the full tool set - every tool NOT in a
  subagent's allowlist is confirmed absent from its available calls.)

Also in force for this unit's build (T-179-group criteria whose wording mentions subagents, so the checker may re-judge them against the five real subagents; the contract does not say whether T-180 re-owns them): AL5 (every subagent invocation emits a span in `projects/<slug>/runs/<run_id>/trace.jsonl`, same `trace_id` as the run), AL6 (no model-bound prompt carries a raw secret; `core.redact.assert_no_raw_secrets`), AL7 (one deterministic step plus one judgement step -> exactly one subagent delegation; zero judgement steps -> zero).

**Task note not backed by a criterion:** `.goal/goal.json` T-180 says "EXTEND (AT-589, meeting 2026-09-26): explicit judge vendor + warning when it matches the agent's vendor". AL8-AL10 contain no such criterion and the contract's amendment log does not mention AT-589. A maker cannot edit contracts. File the request verbatim in `qa/feedback-inbox.md` for `/checker` to add a criterion before building that part; until then it is unjudgeable.

Spec: `docs/spec.md` R26 ("kept only on measured gain"); `docs/plan.md` row 19 ("the grader subagent holds no action tools (C7); judge vendor named, warned when it matches"); `core-invariants.md` C7.

## 4. What exists and what is missing

What is actually wired today (relevant to AT-253): **no agent runs in production.**
- `src/autotester/stages/agent_loop.py:67` `run_with_fallback` (85 lines) has zero production callers. `grep` of `src/` and `scripts/` finds only its definition; only `tests/test_agent_loop.py` calls it. `docs/ARCHITECTURE.md:54` says "unwired" and `:92-95` says every re-run is a fresh run. AT-253 is `open` in `qa/issues.jsonl` (Option A, "wire it in", chosen 2026-09-22, D-031; wiring not shipped). T-177 (pending) is the unit that revives it. T-179 must NOT repurpose it (`qa/manifests/t179-agent-layer-plan.md`: "it owns single-step repair").
- Model calls today are single-shot `Provider.act` / `Provider.judge` calls: `stages/discover.py:275`, `stages/expand.py:125`, `stages/grade.py:178` (the independent grader, `grade()` at :146), `stages/reconcile.py:118`, `stages/ux_advisory.py:140`, `ledger/relitigation.py:74`. The seam is `providers/base.py:33` `Provider` (189 lines); default roles in `schema/project.py:56` `ProviderConfig` (`agent`/`judge` both default `"langchain-fallback"`, :64-65), implemented by `providers/langchain_fallback.py` (171 lines, Anthropic-first chain at :35-69, which is why judge vendor == agent vendor by default, AT-589).
- The plain pipeline: `stages/orchestrate.py:182` `run_or_resume` (203 lines) only has runners for INGEST, DISCOVER, MODEL (`stages/orchestrate_runners.py:69,88,107`); EXPAND/EXECUTE/GRADE/REPORT have no registered runner, so it stops at the review gate. A case actually runs and grades through `stages/run_case_pipeline.py:143` `run_and_grade_case` / `:174` `run_and_grade_case_resilient`, driven from `ui/routes_runs.py`.
- Skills for the agent: T-175 is done; `src/autotester/skills/` holds `expand-case`, `grade`, `ingest-video`, `reconcile-screen`, `ux_judge`, `video-issues`; loader `providers/base.py:165` `load_skill_prompt`.
- Trace: `core/trace.py` (80), `schema/trace.py` (56), `StageName` (`schema/run_state.py:21`: ingest, discover, model, expand, execute, grade, report) has no stage for planning or delegation (T-179 manifest: "never disguise planning as a completed checkpoint").
- Missing entirely: `src/autotester/agents/` (does not exist; `qa/QUEUE.md:284`), `deepagents`/`langgraph` in `pyproject.toml` (only `langchain-anthropic`, `langchain-core`, `langchain-google-genai` at lines 14-16), `tests/test_agent_layer.py`, `tests/test_agent_subagents.py`.

What T-179 must deliver for T-180 to start (all `unknown` until it lands): the lead agent built with `create_deep_agent`; the seven tools `crawl`, `run_case`, `get_persona`, `get_catalog`, `capture_network`, `grade_case`, `report` as thin wrappers with guards inside; a Provider adapter so Deep Agents' model calls pass the redaction gate; trace spans for tool/planning calls; a scripted local chat model fixture T-180 can reuse; the module layout T-180 extends.

**T-179 is not startable, so T-180 is two steps from startable.** `qa/manifests/t179-agent-layer-plan.md` (status `planning`) records two unanswered human questions asked 2026-10-05: "T179 Python version correction: approve/hold" and "T179 exact three new files: approve/hold". Its finding: AL1/D-042 require `deepagents>=1.7`, but PyPI lists `0.7.21` (2026-09-30), so the contract floor appears unsatisfiable. This readiness pass did not check PyPI; it is the manifest's claim. The manifest also proposes `stages/agent_layer.py`, `providers/agent_chat.py` and `tests/test_agent_layer.py`, while `docs/plan.md` row 16 and `qa/QUEUE.md:284` say a new `agents/` package. The module layout T-180 extends is therefore `unknown`.

Spec question - does a spec name its choice for each of the 4 layers (`agentic-architecture-standard.md`)? **Partly.** D-042 plus the `agent-layer.md` preamble name: graph = LangGraph 1.x underneath Deep Agents (the explicit graph is T-167's and is independent of this layer, D-055); agents = a lead plus five subagents (explorer, test-designer, runner, grader, reporter); skills = `skills=` over T-175 `SKILL.md` folders (AL4); tools = the seven stage tools wrapped, browser-use later (T-177). There is no ARD/HLD for T-180 itself (`.claude/prds/` does not exist). Gaps a builder will hit: which tools each subagent gets is left to "named in the unit's manifest" (AL10); whether `grade_case` counts as an "action tool" for the grader is not stated; the portable-core "LiteLLM" row depends on T-202 (pending); whether a subagent is a LangGraph subgraph is marked `[UNVERIFIED]` in the contract's no-fire list.

## 5. Files the builder will touch

All module names are `unknown` (`qa/QUEUE.md:292-301`: "N and E under src/autotester/agents/ (names unknown)"). Expected, to be fixed after T-179 lands:
- N `src/autotester/agents/subagents.py` (or equivalent) - the five subagent specs with explicit allowlists. New. (If T-179 uses `stages/agent_layer.py` instead, the folder is whatever T-179 chose.)
- N `src/autotester/schema/` model for a subagent spec if the allowlist is typed (CLAUDE.md: shapes live in `schema/`, `extra="forbid"`). New, `unknown` name.
- E the T-179 lead-agent construction file (line count `unknown` until it lands) - to pass `subagents=`.
- N `tests/test_agent_subagents.py` - the `done_check` file. New.
- E `src/autotester/schema/project.py` (194 lines, headroom 106) - only if the judge-vendor field/warning (AT-589) is added there, and only after the contract gains a criterion. Alternative home: `providers/__init__.py` (48) or `providers/langchain_fallback.py` (171). `unknown`.
- Not touched: `pyproject.toml`/`uv.lock` (T-179 owns `deepagents`; no new dependency here), `stages/grade.py`, `stages/execute.py`, `stages/explore*.py`, `core/consent.py`, `core/redact.py`, `browser/secrets.py` (the guards stay where they are), `stages/agent_loop.py`, any contract.

## 6. Test scope

- Product gate: `uv run pytest tests/test_agent_subagents.py` (bare; AT-503).
- Regression nodes: `tests/test_agent_layer.py` (T-179's file; run, do not edit). If `schema/project.py` changes: `tests/test_schema.py` and `tests/test_providers.py` as whole files (neither is a directory).
- Plus `uv run ruff check src tests scripts` and `uv run autotester doctor`.
- No browser, no network, no paid model in tests: use T-179's scripted local chat model. A live model run needs its own grant (section 8).

## 7. Reachable test cases (happy path first)

1. Happy: the lead agent is built with all five subagents; the configured list names exactly explorer, test-designer, runner, grader, reporter.
2. AL10: for each subagent, programmatically read its tool list and diff against the full set; every tool outside its allowlist is absent. Proposed allowlists (the builder fixes them in the manifest): explorer = `crawl`, `get_persona`, `get_catalog`; test-designer = `get_persona`, `get_catalog` (no browser); runner = `run_case`, `capture_network`; grader = evidence/rubric reads only (`grade_case` only if the checker accepts that it mutates nothing; `unknown`); reporter = `report`, `get_persona`, `get_catalog`. Negative: a subagent built with no tool list is refused at construction rather than inheriting everything.
3. AL8: the grader's tools carry no side-effect capability. Sabotage in a throwaway copy: add `run_case` to the grader list, confirm the test goes red for that reason.
4. AL9: two scripted subagents with transcripts that together exceed one window both finish; neither context contains the other's raw transcript; only the shared file state crosses.
5. AL7 against the real subagents: one deterministic plus one judgement step -> exactly one delegation; zero judgement steps -> zero delegations.
6. AL6: a fake secret bound to a `SecretRef`, driven through a subagent whose evidence would carry it -> absent from every model-bound message and trace line.
7. AL5: each subagent invocation yields a span with the run's own `run_id` as `trace_id`; no second trace mechanism.
8. C7 end to end: the runner's `RawResult` is graded only through the grader subagent; the executor never grades itself.
9. Judge-vendor warning (only once a criterion exists): judge vendor equal to agent vendor -> a visible warning; different vendors -> none; vendor undeterminable -> reported as unknown, never silently "different".

## 8. Gate answers

- `qa/gates/d042-deep-agents.md:7` (verbatim): "Answered: 2026-09-24T22:33:42+05:30 - "Haan, Umesh approve (Recommended)" + "Wave 1 ke baad (Recommended)" - AskUserQuestion in the 2026-09-24 session (running under the himanshu@ claude.ai account; the answer explicitly selected "Umesh approve")". Effect: the Deep Agents layer, T-179..T-181, is approved after Wave 1; D-042 `Approved-by` is Umesh.
- `qa/gates/at253-agent-fallback-wiring.md:47` (verbatim start): "**Answered:** 2026-09-22 - Option A (wire it in) - recorded off-disk in `docs/DECISIONS.md` D-031". Context only; it concerns `agent_loop.py` (T-177), not T-180.
- **Unanswered, blocking T-179 and therefore T-180** (`qa/manifests/t179-agent-layer-plan.md`): "T179 Python version correction: approve/hold" and "T179 exact three new files: approve/hold". No `Answered:` line exists for either.
- No gate covers paid model calls or real-account runs for the agent layer. The T-179 manifest says each "requires its separate existing grant". For T-180's offline tests none is needed.
- `qa/gates/new-module-authorization.md:77` ("AT-710 only") does not cover T-180's new modules; the owner has not said whether `qa/QUEUE.md:293` "approved: 2026-10-10 (D-081; the owner asked for all remaining work to run)" authorizes specific new files.

## 9. UI surface and persona walk

- UI surface: no. Verify at check time: `git diff --stat` shows no path under `src/autotester/ui/`.
- `Persona walk: skip (agent layer, no screen, route or navigation touched; docs/plan.md row 19)`.

## 10. Dependencies and conflicts

- Hard: T-179 (the `agents/` package, tools, scripted-model fixture). Owner order per `qa/QUEUE.md:290,301`: `agents/` is owned by T-179, then T-180, then T-181 - strictly sequential, one owner at a time. Same file -> sequential.
- `pyproject.toml` and `uv.lock`: T-180 must not touch them; writers are T-167 (langgraph), T-174 (mcp), T-179 (deepagents), T-202 (litellm), serialized (`qa/QUEUE.md:86`).
- T-177 (browser-use) becomes one of the runner's tools later; do not implement it here. T-177 and T-180 both read `agent_loop.py`/the runner allowlist: the runner's allowlist gains a tool when T-177 lands (a one-line change owned by T-177).
- T-181 consumes T-180's subagent specs to build the agent arm of the measurement.
- Open issues touching this area: AT-589 (judge vendor, low, open), AT-253 (open), AT-666 (open, unrelated routing).

## 11. Budget and process rules

- Check budget (tier L): 45 minutes.
- The builder runs no full suite; only section 6 files.
- Falsification only in a throwaway copy outside the bound tree, then revert. AL8, AL9 and AL10 each need their own single-hunk falsifying edit (`agent-layer.md` "How a unit is verified": one row per clause).
- Kill only PIDs the builder started. No browser needed.
- Edit in place; new files only after the owner confirms the new-file list. No `*_v2.py` / `*_new.py`. Scratch to `.work/`.
- The builder never edits `qa/contracts/`; the AT-589 criterion request goes verbatim into `qa/feedback-inbox.md`.
- "Ready for check" only; only `/checker` can PASS. File <= 300 lines, function <= 50, model calls only through `providers.base.Provider`, prompts are `SKILL.md` files loaded via `skills=` (AL4), never inline strings.

## Readiness findings (outside the 11 sections, for the dispatcher)

- Buildable today without T-179: nothing in the agent code. One slice is independent of the agents package: the judge-vs-agent vendor comparison (AT-589) as a pure function over `ProviderConfig` and the langchain-fallback chain, but it has no contract criterion yet, so it should wait for the checker to add one.
- `unknown`: module layout, the exact tool allowlists, whether `grade_case` is an "action tool", and whether AL5-AL7 are re-judged at T-180.
