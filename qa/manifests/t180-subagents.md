# Manifest - t180-subagents (T-180: the five subagents on the t179a core)

## Status: ready-for-check

Contract: qa/contracts/agent-layer.md AL8, AL9, AL10 (T-180 group). AL5/AL6/AL7 not re-owned here (see Held).
Goal task: T-180. Policy-Version: proportional-verification/2026-10-10.9
Tier: L (security: grader holds no action tools; per-subagent allowlists)
Fix cycle: 0
Branch: wave/t180-subagents, base 806f27a4 (t179a PASS f54af1ac merged with master a7e8acad; docs/MAP.md, SNAPSHOT.md and a checkpoint file took master's side in the merge, then MAP regenerated).
Dual check: no. Diff touches no core/consent.py, core/redact.py or browser/secrets.py, nor agents/guards.py. The grader allowlist is enforced at ONE site: `agents/subagents.py::SUBAGENTS` plus the import-time READ-only check there.
Persona walk: skip (agent layer, no screen).

## What was built
- `schema/subagent.py`: `SubagentName`, frozen `SubagentSpec` (`tools` min_length=1, so no list = refused), `SubagentInvocation` (no field for lead history or another transcript).
- `agents/subagents.py`: the 5 specs, `absent_tools`, `invocation` (own SKILL.md prompt + task + passed files), `call_tool` (allowlist gate, then t179a `tools.dispatch`), `deep_agents_config` (dict for T-179's `create_deep_agent(subagents=)`).
- `agents/evidence_tools.py`: read-only `read_result`, `read_rubric`, `read_verdict` (thin reads of ProjectStore), registered into the one dispatcher in `tools.py` (+3 lines, 299 total).
- `schema/agent_layer.py`: 3 tool names, `RefusalClass.NOT_ALLOWED`, `ReadCaseArgs`.
- 5 skills: `skills/agent-{explorer,test-designer,runner,grader,reporter}/SKILL.md`.
- `tests/test_agent_subagents.py` (25 tests).

## Allowlists (AL10, named)
| subagent | tools |
|---|---|
| explorer | crawl, get_persona, get_catalog |
| test-designer | get_persona, get_catalog |
| runner | run_case |
| grader | read_result, read_rubric (READ effect only, asserted at import and in test) |
| reporter | get_persona, get_catalog, read_result, read_verdict |

`grade_case` is on NO subagent list: it writes a verdict, so giving it to the grader would breach AL8; the lead persists verdicts. `capture_network` and `report` do not exist yet (T-179 rest); when they land the runner gains capture_network and the reporter gains report.

## Commands run (real output)
- uv run pytest tests/test_agent_subagents.py -p no:xdist -o addopts= : 25 passed
- test_agent_tools 14, test_agent_credential_gate 83, test_agent_destination_seam 183, test_agent_read_only 112, test_agent_loop 4, test_prompt_skills 16, test_schema 24: all passed
- uv run ruff check src tests scripts : All checks passed
- uv run autotester doctor : clean (after `autotester map`)

## Held / open (stated, not hidden)
- No `deepagents` in pyproject (T-179 owns it). AL9 is proven on the invocation object (what each subagent is handed), not on a live Deep Agents subgraph. `deep_agents_config` is the hand-off.
- AL5 (spans) and AL7 (delegation count) need the lead-agent loop, which is not built; no span or delegation counter here.
- AT-589 judge-vendor warning: no contract criterion exists; not built. Request for /checker: add a criterion (judge vendor named; warn when it equals the agent vendor).
- Falsifying edits (AL8, AL9, AL10 one hunk each) not yet reproduced; left to the checker.
- Question for the checker: is a grader without `grade_case` acceptable (its judgement is its own model output, persisted by the lead)?
