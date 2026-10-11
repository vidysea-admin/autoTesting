# Manifest - t179a-lead-tester-core (T-179 slice a: the guarded stage-tool core)

## Status: ready-for-check

**Contract:** qa/contracts/agent-layer.md AL2, AL3, AL6 (the T-179 group); AL2 and AL6 in part, AL3 in full for the tools built; AL1, AL4, AL5, AL7 held (below)
**Goal task:** T-179, slice a only. T-180 (subagents) and T-181 (gain, budget) are not in this unit.
**Authority:** D-042 (Deep Agents adopted, `qa/gates/d042-deep-agents.md` answered 2026-09-24), D-018 (consent), D-053 (the supplied account is the scope). No new decision is needed for this slice: it adds no dependency and edits no file D-042 does not already allow.
Policy-Version: proportional-verification/2026-10-10.9
Tier: L (security class: the AL3 guards and the AL6 secret boundary decide what a model-driven tool may do to a live product; no dependency change, so not L for that reason)
Fix cycle: 0
Branch: wave/t179-lead-tester, based on master 16aaa402. Master was not merged. Nothing pushed.
Code commit under check: 90705dc0 (9c000f1c is the first code commit; 90705dc0 adds one test and regenerates `docs/MAP.md`/`docs/SNAPSHOT.md`; the manifest commit changes no product file)
Executor: claude-sonnet-subagent (maker build subagent)
Dual check: required
dual-trigger: security src/autotester/agents/guards.py:64 (`write_policy_refusal`, the one new guard: `execute.run_case` has no write-policy check of its own)
dual-trigger: security src/autotester/agents/tools.py:168 (`dispatch`, the secret gate on the raw call and the only path a model reaches an acting tool)
Persona walk: skip (agent layer, no human-facing screen, route or CLI output is added; docs/plan.md:66)

## Slice chosen, and why

The dependency question is open (no `deepagents` in `pyproject.toml` or `uv.lock`; the brief records that the PyPI package is 0.7.x and AL1's `>=1.7` resolves to nothing). So this slice contains **nothing that needs the framework**: the tool surface the framework will later be handed, with the safety checks already inside the tools. The planner, subagents, to-do middleware and `skills=` loading ARE the framework (AL1/AL4/AL7), and a hand-rolled planner behind `Provider` would be exactly what AL1 forbids, so none is built here.

What is in the slice: five stage tools (`crawl`, `run_case`, `get_persona`, `get_catalog`, `grade_case`), each a thin call into the existing stage function; one dispatcher a model reaches; the guards running inside the tools before any browser opens; secret gating of the call and of the result. No live model call, no browser, no network, no new dependency. `grade_case` reaches the judge only through `stages.grade.grade` and `providers.base.Provider` (tests use `MockProvider`).

Design choices a checker should know (none contradicts the contract):
- The model passes ids and requested bounds only. Project, store, secrets, judge, run id and the session factory are `AgentContext` (trusted); no args model has a field for any of them, and every args model is `extra="forbid"`.
- `crawl` calls `guards.crawl_approval` (`core.consent.require_approval`, reading existing signed rows only, so an agent can never mint one) BEFORE `ctx.open_session`. `run_crawl` checks again at its own seam; this is additional.
- `run_case` runs the write-policy check, then `require_approval(kind=LIVE_CASE)`, then opens the session. Note `trigger_run` (UI) checks no approval today (AT-570, open); this tool is stricter than that path by design, per AL3.
- Write-policy rule (new logic, `guards.py::write_policy_refusal`): a CLICK step goes through the crawler's own `explore_safety.deny_reason` (never-click and destructive names); under `READ_ONLY` a FILL/SELECT/UPLOAD step with a literal value is refused, while a value made only of `{{SECRET:KEY}}` placeholders (a login) is allowed.
- The stage result is scrubbed (`Redactor.scrub_obj`) before it is persisted or described; the outcome is scrubbed again and re-gated by `SecretStore.guard_prompt` before it returns to the model.

## Acceptance criteria claimed

| id | claim | where proved |
|---|---|---|
| AL2 | IN PART: 5 of the 7 named tools (`crawl`, `run_case`, `get_persona`, `get_catalog`, `grade_case`). Each body calls the existing function named by `ToolSpec.wraps`. `report` and `capture_network` are HELD | `test_every_tool_names_a_real_existing_function`, `test_run_case_wraps_*`, `test_crawl_wraps_*`, `test_read_tools_and_grade_wrap_*` |
| AL3 | IN FULL for the acting tools built (`crawl`, `run_case`): (a) raw secret in a call refused with `RefusalClass.SECRET` before any action, (b) crawl beyond the approval refused with the `ApprovalRequired` text before any browser opens, (c) a READ_ONLY project's mutating step refused from the tool's own result. Each asserts the session factory and the stage spy were never called | `test_al3a_*`, `test_al3b_*`, `test_al3c_*`, plus `test_read_only_still_allows_login_placeholder_*` and `test_run_case_without_a_live_case_approval_is_refused` |
| AL6 | IN PART: the tool boundary only (call arguments, stage results, stored result, the grade prompt gate). Planning prompts and skill bodies are the framework's and HELD | `test_al6_*` (three tests) |

## Criteria held (verbatim ids) and why

- **AL1** (built with `create_deep_agent`, `deepagents>=1.7`): HELD. Needs the dependency, and the `>=1.7` floor resolves to nothing (brief section 1, blocker 1).
- **AL4** (skills loaded via `skills=`): HELD. A framework argument; the slice builds no agent.
- **AL5** (a T-172 trace span per agent/tool call): HELD. Needs operation/parent identifiers in `schema/trace.py` and `core/trace.py`, which D-042's `Changes-authorized` does not list (brief blocker 3). `provider.record()` already emits the LLM span for the one judge call a tool makes.
- **AL7** (subagents only where judgement is needed): HELD. Delegation is the framework's.
- AL2 remainder (`report`, `capture_network`) and AL6 remainder (framework planning prompts, skill bodies): HELD with AL1.
- AL8-AL13 belong to T-180/T-181.

## What changed (all new files; no existing source file edited)

Existing files edited: none in `src/`. `docs/MAP.md` and `docs/SNAPSHOT.md` regenerated (`autotester map`, `autotester snapshot`).

## New-module table (D-082 item 1)

| module | lines | one job | named by |
|---|---|---|---|
| `src/autotester/schema/agent_layer.py` | 94 | the tool names, effects, refusal classes, per-tool args and the outcome a model sees | brief section 4 ("typed schemas"); contract AL2/AL3 (refusal is a result) |
| `src/autotester/agents/__init__.py` | 7 | package docstring | `docs/plan.md` row 16 and `qa/QUEUE.md:296` ("new `agents/` package wrapping existing stages as tools") |
| `src/autotester/agents/context.py` | 39 | the trusted context a model can never choose | brief section 4 ("trusted injected context fixes project roots, session, provider and approval") |
| `src/autotester/agents/guards.py` | 73 | the checks that run in code inside an acting tool | contract AL3 |
| `src/autotester/agents/tools.py` | 184 | the five stage tools and their one dispatcher | contract AL2 |
| `tests/test_agent_tools.py` | 280 | offline proof of AL2/AL3/AL6 for this slice | brief section 6; deliberately NOT named `test_agent_layer.py`, the goal's `done_check` file |

The package location follows `docs/plan.md:66` and `qa/QUEUE.md:296` (`agents/`), not the planning manifest's three proposed paths (`stages/agent_layer.py`, `providers/agent_chat.py`, `tests/test_agent_layer.py`). The contradiction is brief blocker 2 and is still an owner question; this slice is the smallest that makes either answer cheap to follow (a move, not a rewrite). `providers/agent_chat.py` is not created because no framework adapter is built.

## Verification scope
Policy-Version: proportional-verification/2026-10-10.9
Tier: L. No builder full suite; touched/affected test files only; no CLI `-q`. `autotester.__file__` confirmed under `D:\autoTesting\.worktrees\t179-lead-tester\src`.
Pre-check: 90705dc0 uv run ruff check src tests scripts -> All checks passed!
Pre-check: 90705dc0 uv run autotester doctor -> doctor: clean; `uv run autotester map` and `autotester snapshot` regenerated, committed
Pre-check: 90705dc0 uv run pytest tests/test_agent_tools.py -> 14 passed (AL2 x4, AL3 x5, AL6 x3, validation x1, guard-function x1; criteria AL2, AL3, AL6 each have named tests above)
Pre-check: 90705dc0 uv run pytest tests/test_schema.py tests/test_doctor.py -> 64 passed (C1 schema rules and the doctor rules over the new files)
Metrics: start=2026-10-12 end=2026-10-12 wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=8 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9

TDD note, stated plainly: the test file was written before `tools.py`/`guards.py`, but I did not run it red first (it went green on its first run, 13 passed). The red evidence is the falsification table, not a failing-first run.

## Falsification (throwaway copy of src, tests, scripts, docs under the scratchpad on C:, outside the worktree; run with the worktree venv and `PYTHONPATH=<copy>/src`, `autotester.__file__` printed from the copy; the worktree was never edited; the copy is discarded)

Each row: the named test green on the copy before the edit, red after it.

| Row | edit in the copy | test | before | after |
|---|---|---|---|---|
| AL2 | `run_case` tool returns a hand-built `RawResult` instead of calling `execute.run_case` | `test_run_case_wraps_execute_run_case_once_with_the_context_session` | 1 passed | 1 failed |
| AL3a | secret gate on the raw call replaced by `pass` | `test_al3a_raw_secret_in_arguments_is_refused_before_any_action` | 1 passed | 1 failed |
| AL3b | `guards.crawl_approval(...)` call removed from `_crawl` | `test_al3b_crawl_beyond_the_approval_is_refused_before_a_browser_opens` | 1 passed | 1 failed |
| AL3c | `write_policy_refusal` returns `None` first | `test_al3c_a_read_only_project_refuses_a_mutating_step_from_the_tool_itself` | 1 passed | 1 failed |
| AL6 | stored/returned result not scrubbed (`_scrubbed` returns the input) | `test_al6_a_secret_in_a_stage_result_never_reaches_the_model` | 1 passed | 1 failed |
| AL6 | `grade` called without `secrets=`/`redactor=` | `test_al6_a_real_grade_withholds_a_prompt_carrying_a_secret` | 1 passed | 1 failed |
| AL6 | release step stops scrubbing the summary | `test_al6_a_stage_summary_is_scrubbed_and_a_folded_secret_withholds_the_result` | 1 passed | 1 failed |
| AL6 | release step stops gating the outcome | same test | 1 passed | 1 failed |

One mutation first SURVIVED and was fixed by a new test, not hidden: removing the release scrub and gate together left `test_al6_a_secret_in_a_stage_result_*` green, because `_scrubbed` already cleaned the text upstream. `test_al6_a_stage_summary_is_scrubbed_*` now pins the release step separately (exact value scrubbed to a placeholder; a reversed spelling withholds the whole result).

## Contract gaps and residuals (for the checker, not for the maker to close)

1. **A CLICK that submits a form but carries no tell in its name is not caught by the write-policy guard.** A `Case` step holds a semantic target string, not an `ElementRef`, so `is_form_submit` is unknown at tool level; only names (`deny_reason`) and literal-value typing are checked. AL3(c) says "submit a form / mutate state"; the contract does not say how a step that is a submit is recognised. Proposed contract wording is the checker's. Until then this is a stated limit, not a pass claim for that sub-case.
2. **`run_case` requires a `LIVE_CASE` approval; the UI path does not (AT-570).** Contract AL3 names `require_approval` for outward-facing runs, so the tool follows it. If the owner decides a read-only fixture needs none, that is a decision to record.
3. `docs/ARCHITECTURE.md` (150/150) is not edited (forbidden to this unit); its concept to file table does not yet name `agents/`. D-042 allows one line after PASS, as maker close-out.
4. `ToolOutcome.summary` of `run_case` carries `result.error` (scrubbed). It is bounded by what the executor wrote; no length cap is applied here.
5. The `HUMAN_GATE` items below were not needed for this slice but gate the rest.

## Open owner questions (gate the REST of T-179, not this slice)

1. Which `deepagents` version floor, and is adding that dependency (with its transitive `langchain`/`langgraph`/`langsmith` set) accepted? PyPI shows 0.7.x; AL1 and D-042 say `>=1.7`. Needs a decision entry via `scripts/append_decision.ps1` and a checker amendment of AL1. Serialize the lock-file writer with T-167/T-202/T-174 (`qa/QUEUE.md:91`).
2. Package location: `src/autotester/agents/` (plan.md, QUEUE; used here) or the planning manifest's `stages/agent_layer.py` + `providers/agent_chat.py`. Answer either way and this slice moves with one rename.
3. Provider and trace approach (message/tool interface in `providers/base.py`; operation/parent ids in `schema/trace.py`, `core/trace.py`): no authorizing decision names those files (AL5 depends on it).
4. Should `tests/test_agent_layer.py` (the goal `done_check`) be checker-owned, as the planning manifest says? This unit's tests live in `tests/test_agent_tools.py`.
