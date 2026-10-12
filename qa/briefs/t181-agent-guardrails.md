# Build brief - t181-agent-guardrails (T-181, readiness pass 2026-10-11, NOT YET DISPATCHABLE)

Written by a read-only readiness pass. Nothing here was built or run. Where the repo does not say, this brief says `unknown`.
Dispatch trigger: T-180 reaches a checker PASS merged to master. T-180 depends on T-179, which is blocked on two unanswered human questions.

## 1. Policy and tier

- `Policy-Version: proportional-verification/2026-10-10.9`
- Tier: **L**. Triggers: (a) concurrency/shared-seam: the natural hook for a per-run token and cost budget is `src/autotester/providers/base.py:106` `Provider.record`, the single choke point every model call passes and which is guarded by `_usage_lock` (`base.py:55-63`, AT-569); (b) a spend guard that must refuse before the model call. If the builder places the budget wholly inside the new agent module and leaves `providers/base.py` and `core/` untouched, this drops to M (shared module `schema/bench.py`, public scorecard shape).
- `Dual check: no`. Reason: no real `security|auth|tenancy|prod-write <path:line>` exists (the code does not exist, and a cost budget is not an auth boundary). Re-decide at dispatch: `required` if the diff changes `core/consent.py`, `core/redact.py` or `browser/secrets.py`.

## 2. Root and base

- Root: `D:/autoTesting`
- Base: the master commit where **T-180** (`t180-subagents`) lands with a checker PASS. Record the SHA in the manifest.
- Branch: `wave/t181-agent-gain-measured`
- `.goal/goal.json`: T-181 `deps = [T-180]`. Transitively T-179 (pending), then T-170/T-172/T-175 (done).

## 3. Acceptance criteria (verbatim from `qa/contracts/agent-layer.md`, status DRAFT, T-181 group; the contract says the checker judges only the group whose unit is in flight)

- **AL11 - A per-run token/cost budget halts the run with a named reason when exceeded.** The lead
  agent's run carries a declared budget (tokens and/or cost); when a run would exceed it, the run
  halts (not silently truncates) and records a named reason in the run's state/trace, distinguishable
  from every other stop reason (completion, error, HITL block). (Falsifiable: a fixture budget set
  below what a scripted job requires -> the run halts before completion with a reason string naming
  the budget breach; a fixture budget set above requirement -> the same job completes normally.)
- **AL12 - A fixture comparison, agent-vs-pipeline, reports bugs found, false positives, tokens
  and wall time.** The same fixture product/job is run once through the plain pipeline
  (`stages/orchestrate.py::run_or_resume`) and once through the Deep Agents lead agent, and a
  comparison report records, for each: bugs found, false-positive count, total tokens, wall-clock
  time - the same axes `docs/ARCHITECTURE.md`'s north star names (`stages/bench.py:76::scorecard`
  precedent - `schema/bench.py` holds only the data models). (Falsifiable: run the comparison script on a seeded fixture corpus twice (once per
  path) -> a report artifact with all four numbers populated for both paths, not estimated or
  asserted from memory.)
- **AL13 - The layer is kept only if the comparison shows a gain; otherwise the finding is
  recorded, not hidden.** T-181's manifest/report states explicitly whether AL12's comparison shows
  a gain on bugs-found or false-positive rate without breaching AL11's budget; if it does not, the
  unit records that outcome in the report and the ledger rather than omitting or reframing it, and
  D-042's layer is NOT declared "kept" on unfavourable evidence. (Falsifiable: the AL12 report's
  verdict line - gain / no gain, with the numbers it rests on - is present regardless of which way
  the comparison went; a report that only shows favourable outcomes and drops an unfavourable metric
  fails this criterion.)

Also inherited and binding on the measurement: `qa/contracts/bench.md` K3 (every number comes from `BenchTrial.score`, none hand-computed), K8 (a missing measurement reports unavailable, never a flattering default: not `0.0` duration, not `0.0` precision), K9 (the comparison artifact must be judgeable by someone who was not there); `core-invariants.md` C12. D-042 ("the layer stays only if it shows a measured gain over the plain pipeline on this fixture"); `docs/plan.md` risk 4 ("a negative result means it is removed, not patched").

Spec: `docs/spec.md` R26; `docs/plan.md` row 23.

## 4. What exists and what is missing

What is wired today: no agent runs in production (see `qa/briefs/t180-subagents.md` section 4: `stages/agent_loop.py:67` has no production caller, AT-253 open; `src/autotester/agents/` does not exist; `deepagents`, `langgraph`, `litellm` are not in `pyproject.toml`). So the "agent arm" does not exist and the "plain pipeline arm" is `stages/run_case_pipeline.py:143` `run_and_grade_case` (+ `:174` resilient), not `stages/orchestrate.py::run_or_resume`.

**Contract/code mismatch in AL12:** it names `run_or_resume` as the plain pipeline, but `stages/orchestrate_runners.py` registers runners only for INGEST (:69), DISCOVER (:88) and MODEL (:107). `run_or_resume` (`orchestrate.py:182`) stops at the first stage with no runner, so EXPAND/EXECUTE/GRADE/REPORT never run through it today. K2 and `scripts/bench_trial.py` already use `run_case` + `grade` directly. Either the checker amends AL12's citation, or T-167's orchestrator conversion wires those runners first. A maker cannot edit the contract; file it in `qa/feedback-inbox.md`.

Measurement building blocks that exist:
- `schema/bench.py:17` `SeededBug`, `:32` `Finding`, `:44` `BenchCorpus` (155 lines total), `:69` `BenchTrial`, `:117` `BenchTrial.score` returning `detected`, `seeded`, `detection_rate`, `false_positives`, `false_positive_rate` (population: all reported findings; `None` with a reason when no findings), `severity_weighted_recall`, `duration_s` (`None` with a reason when untimed). It has **no tokens or cost field**, and `kind` is `Literal["autotester","human_live","human_oracle","unknown"]` with `Participant` = `human|autotester` (`schema/enums.py:188`). Two AutoTester arms are distinguishable only by `participant_label` today.
- `stages/bench.py:17` `findings_from_verdicts` (FAIL -> Finding; unmapped FAIL = false positive), `:39` `run_autotester_trial`, `:80` `scorecard` (97 lines).
- Token accounting: `providers/base.py:106` `Provider.record` accumulates `ProviderUsage` per role and, when a `TraceWriter` is attached, writes an `LLMSpan` (`schema/trace.py:38`: `input_tokens`, `output_tokens`, `latency_s`, `cost`, `retries`, `fallback_hops`). Cost: `core/pricing.py:22` `estimate_cost` (28 lines) returns **`0.0` for any label not in its three-entry table**. That is a flattering default (K8): an unpriced model would read as free. Cost for the comparison must be `unavailable` when any label is unpriced.
- Existing run budget: `stages/run_budget.py:30` `RunBudget` (165 lines) is the consent budget over actions and probes (`try_consume`, `stop_reason` :122), keyed to a `RunApproval`. It has no token or cost dimension. Whether AL11 extends it or lives in the agent module is `unknown` (C3: do not duplicate a concept).
- Fixture: `tests/fixtures/regression_site/` (`index.html`, `login.html`, `login.broken.html`) is the K1 corpus, with one seeded bug. `scripts/bench_trial.py` (188 lines) is the precedent script. `tests/test_bench.py` is 298 lines (cap risk).
- Stop reasons: `schema/run_state.py` `StageStatus` (done/failed/skipped/...) and `StageSpan.error`; there is no budget-breach reason string anywhere.

Missing: the agent arm; the budget; token/cost on the bench trial; a fixture with enough seeded bugs to discriminate (one seeded bug gives a detection rate of 0 or 1, which cannot show a difference between arms; the required count is `unknown`); the comparison script and artifact; `tests/test_agent_gain.py` (the `done_check` file).

What T-180 must deliver for T-181 to start: a runnable lead agent with its five subagents driven by a scripted model (for the offline harness proof) and by a real model (for the measurement run); trace spans for agent and tool calls (AL5) so agent-arm tokens are attributable by `run_id`; stable construction API.

## 5. Files the builder will touch

Names `unknown` (`qa/QUEUE.md:303-313`: "src/autotester/agents/ plus schema/bench.py and stages/bench.py (E, exact edits unknown)"). Expected:
- E `src/autotester/schema/bench.py` (155 lines) - nullable `tokens`/`cost` (and an arm label) on `BenchTrial` and in `score()`, with the K8 "unavailable + reason" pattern. Headroom 145.
- E `src/autotester/stages/bench.py` (97) - a comparison function that calls `BenchTrial.score` and builds the verdict line. No parallel arithmetic (K3).
- E `src/autotester/core/pricing.py` (28) - only if cost-unavailable is signalled here; alternative is to handle it in the comparison layer. `unknown`.
- N `src/autotester/agents/budget.py` (or similar) - the AL11 budget. New. If the hook is `providers/base.py:106`, that is an E on a shared 189-line module (see tier note).
- N `scripts/<comparison script>.py` - the AL12 runner, `unknown` name (follow `scripts/bench_trial.py`; scripts have a line cap, AT-520).
- N `tests/fixtures/<bench_site>/...` - a seeded multi-bug fixture, `unknown` shape.
- N `tests/test_agent_gain.py` - the `done_check` file. New. (`tests/test_bench.py` at 298 lines cannot take more.)
- E the T-180 agent construction file to accept a budget - line count `unknown`.
- Not touched: `pyproject.toml`/`uv.lock`, `core/consent.py`, `core/redact.py`, `browser/secrets.py`, any contract, the T-136 bench scoring semantics (K6-K9 must stay green).

## 6. Test scope

- Product gate: `uv run pytest tests/test_agent_gain.py` (bare; AT-503).
- Regression files, run unmodified: `tests/test_bench.py`, `tests/test_score.py` (K1-K9 bench semantics), `tests/test_run_trace.py` (if the trace shape or `Provider.record` changes), `tests/test_agent_layer.py` and `tests/test_agent_subagents.py` (T-179/T-180's files).
- Plus `uv run ruff check src tests scripts` and `uv run autotester doctor`.
- The pytest file proves the **harness** offline with scripted arms (fixed token counts). The **gain number** is an evidence run with a real model, outside pytest (section 8).

## 7. Reachable test cases (happy path first) and the measurement method

Offline tests:
1. Happy: a scripted job under a budget above its need completes and the report has all four numbers for both arms.
2. AL11: budget set below the scripted need -> the run halts before completion with a reason naming the budget breach, distinct from completion, error and HITL block; state and trace both carry it. Budget just at the need -> completes.
3. Budget refuses before the call, not after: the over-budget call is never made (assert on the scripted model's call count).
4. K8: an arm with no timing -> `duration` unavailable with reason, not `0.0`; an arm whose model label is not in `core/pricing.py` -> cost unavailable, not `0.0`; an arm with no findings -> FP rate unavailable.
5. K3: every detection/FP number in the report equals `BenchTrial.score` output; sabotage by hand-computing one number in a throwaway copy and confirm the test goes red.
6. AL13 verdict line is present in all four outcomes: gain, no gain, tie, unavailable.

How "measured gain" is computed (this is a proposal assembled from AL12, AL13, K3, K8 and the bench code; the contract fixes the axes but not the thresholds, so each threshold below is `unknown` to the repo and needs the checker or owner):
- Two arms, same everything else: the plain pipeline (`run_and_grade_case` over the compiled cases) vs the Deep Agents lead agent, on the same seeded fixture build and material pack, the same judge model, the same project config, serial execution (browser lane max 1, `qa/adapter.json`), same machine. Each arm becomes a `BenchTrial` (`kind="autotester"`, distinct `participant_label`, `ordering="independent_parallel"`) scored with `BenchTrial.score(corpus)`.
- Bugs found: `detected` of `seeded`, `detection_rate` and `severity_weighted_recall`. False positives: `false_positives` and `false_positive_rate`.
- Tokens: sum of `input_tokens + output_tokens` over the LLM spans carrying that arm's `run_id` (planning, subagent, tool-result and grading calls all counted for the agent arm; expand and grade calls for the pipeline arm). Wall time: end-to-end seconds per arm into `duration_s`. Cost: `estimate_cost` summed, or unavailable.
- Repeats: model calls are non-deterministic and a single paired run on a handful of bugs cannot support a claim. Run each arm N times (N is `unknown`; a value of at least 3 is suggested) and report every run plus the aggregate; the verdict uses the aggregate, and any run with an unavailable input is reported as such.
- GAIN (proposed operationalization of AL13): the agent arm is within its AL11 budget on every run AND either (agent `detection_rate` is higher AND agent false positives are no more than the pipeline's) OR (agent `false_positive_rate` is lower AND agent `detection_rate` is no lower). Any unavailable metric on either side, or a tie, is NO GAIN DEMONSTRATED, never gain.
- Tokens and time are recorded and shown on the verdict line but do not decide it under AL13 as worded, even though D-042 lists them as comparison axes and the standard (`agentic-architecture-standard.md` rule 2) cites about 15x tokens for multi-agent. Whether a cost ratio can veto a marginal gain is an owner decision (below).
- What result means the layer is removed: a verdict of NO GAIN DEMONSTRATED (including tie or unavailable) means the agent layer is not declared kept; `docs/plan.md` risk 4 and `qa/QUEUE.md:313` say it is **removed, not patched**. Removal is a follow-up: a new `docs/DECISIONS.md` entry that supersedes D-042 with `Approved-by: Umesh`, then a unit that deletes `agents/` and the `deepagents` dependency. T-181's builder records the verdict in the report and the ledger and does not delete anything. T-181 can reach a checker PASS with a negative finding (AL13 requires the finding be recorded, not that it be favourable), so a PASS on T-181 does NOT mean the layer is kept; read the verdict line.

## 8. Gate answers

- `qa/gates/d042-deep-agents.md:7` (verbatim): "Answered: 2026-09-24T22:33:42+05:30 - "Haan, Umesh approve (Recommended)" + "Wave 1 ke baad (Recommended)" - AskUserQuestion in the 2026-09-24 session (running under the himanshu@ claude.ai account; the answer explicitly selected "Umesh approve")". It approves the layer subject to T-181's measured gain.
- **No gate covers the paid-model spend of the real measurement run.** `qa/manifests/t179-agent-layer-plan.md` says paid model calls "require their separate existing grants". No `qa/gates/` file names one for the agent layer, and `qa/gates/t136-model-credentials.md` is about T-136's vision key (its `Answered` says the credentials were already provided; it is not a grant for this run). `none` is the honest answer; an owner decision is needed before the real-model arms run (section "Readiness findings").
- Unanswered upstream, blocking T-179 and so T-181: the two T-179 questions (Python version correction; exact three new files), no `Answered:` line.
- `qa/gates/new-module-authorization.md:77` ("AT-710 only") does not cover T-181's new modules.

## 9. UI surface and persona walk

- UI surface: no (bench numbers and a report artifact; verify `git diff --stat` shows no path under `src/autotester/ui/`).
- `Persona walk: skip (measurement, no screen, route or navigation touched; docs/plan.md row 23)`.

## 10. Dependencies and conflicts

- Hard: T-180 (and through it T-179). `agents/` ownership is sequential: T-179, then T-180, then T-181 (`qa/QUEUE.md:290,301,312`).
- Shared files: `schema/bench.py` and `stages/bench.py` are also T-136's (K6-K9, pending, held on `qa/gates/t136-independent-human-list.md`); `wave/t136-bench` merged 2026-10-10 (D-080). T-181 must keep K6-K9 semantics intact and extend only. If T-136 work reopens those files, one owner at a time; order `unknown`.
- `providers/base.py` and `core/trace.py`/`schema/trace.py` are shared with T-202 (LiteLLM-backed Provider, pending) and T-172's tracing; if the budget hooks `Provider.record`, coordinate with T-202 so there is one writer.
- `stages/run_budget.py` is the consent budget (AT-570/CN10); do not fork its concept.
- `pyproject.toml`/`uv.lock`: not touched.
- The bench fixture directory `tests/fixtures/` is shared by many tests; add a new subfolder only.

## 11. Budget and process rules

- Check budget (tier L): 45 minutes. The paid-model measurement run is not part of the check budget and runs only after the owner grants it.
- The builder runs no full suite; only section 6 files.
- Falsification only in a throwaway copy outside the bound tree, then revert. AL11, AL12 and AL13 each need their own single-hunk falsifying edit.
- Kill only PIDs the builder started. At most one headed browser at a time (`qa/adapter.json` browser lane max 1); the arms run serially.
- Edit in place; new files only after the owner confirms. No `*_v2.py` / `*_new.py`. Scratch and run evidence to `.work/`, never the repo root. All model calls through `providers.base.Provider`; prompts are files.
- The builder never edits `qa/contracts/`; the AL12 citation fix goes verbatim into `qa/feedback-inbox.md`.
- "Ready for check" only; only `/checker` can PASS. Never present an unfavourable or unavailable measurement as a pass (AL13, K8).

## Readiness findings (outside the 11 sections, for the dispatcher)

- Buildable today without T-180: the measurement plumbing that does not touch agents: nullable `tokens`/`cost`/arm label on `BenchTrial` with K8 unavailable semantics, a cost-unavailable rule for `core/pricing.py`, the comparison function and verdict line over two scripted trials, and a multi-bug fixture. These are INPUT on a branch only (D-080 item 1) and are not checkable as T-181 because AL11/AL12 need the agent arm.
- Owner decisions needed: (1) money: approval to spend on real-model arms for N repeats on the fixture; (2) whether a token/time ratio can veto a marginal gain (AL13 as written ignores it); (3) N and the minimum seeded-bug count; (4) whether AL12's `run_or_resume` citation is amended or the orchestrator is wired first.
