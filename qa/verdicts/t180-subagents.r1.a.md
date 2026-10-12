# Verdict t180-subagents, round 1, checker A

Verdict: **FAIL** (one non-code blocker: the branch does not merge cleanly onto current master)
Cycle checked: 0
Sha: 7d47e3a76dfff60bd4127aa0ac0ffbf20fa6b51f (origin/wave/t180-subagents)
Master at check: 1f1a4817

## Blocking finding: merge onto master
`git merge --no-commit origin/wave/t180-subagents` on origin/master (1f1a4817) conflicts in two docs files:
`docs/SNAPSHOT.md` and `qa/checkpoints/t179a-lead-tester-core.b.md`. All code merged cleanly (guards.py, tools.py, schema).
Fix: rebase/merge master into the branch and resolve those two files (regenerate SNAPSHOT).
With both conflicts resolved to master's side, the agent tests on the merge (test_agent_subagents, _tools, _read_only,
_credential_gate, _destination_seam, _loop): 436 passed.

## Criteria (code is correct; merge is the only blocker)
- AL10 PASS. `SUBAGENTS` holds explicit allowlists: explorer {crawl,get_persona,get_catalog}; test-designer {get_persona,get_catalog};
  runner {run_case}; grader {read_result,read_rubric}; reporter {get_persona,get_catalog,read_result,read_verdict}.
  `SubagentSpec.tools` has min_length=1 and the spec is frozen, so no-list is refused. I probed every role against every tool in
  `TOOLS` through `call_tool`: each tool outside the list returns refusal not_allowed, and the dispatcher is not reached (test monkeypatches it).
  Junk names (None, 7, "RUN_CASE", the raw secret) are refused without echo.
- AL8 PASS. Grader is read_result/read_rubric only, and an import-time check requires every grader tool to be ToolEffect.READ.
  crawl, run_case and grade_case are refused for the grader, and no verdict was written. The module docstring of stages/grade.py (rubric and evidence only) matches.
- `grade_case` is on no list. The brief's AL8 asks only that the grader hold no action tools; it does not require the grader to grade via
  `grade_case`. The grader judges by reading and the lead persists the verdict. Acceptable under AL8 and the brief's own "unknown" note.
  Observation: the grader cannot itself call the grading stage, so the graded-verdict path rests on the lead.
- AL9 PASS, scoped. The brief's falsifier is "inspecting the invocation shows each subagent's context does not contain the other's raw
  transcript". The test builds two invocations and shows the ~1.5 MB combined transcripts are absent and the lead history is absent;
  only passed shared_files cross. deepagents is not installed, so this is proven on the invocation object, which is what the brief asks;
  actual framework isolation is T-179's call (`deep_agents_config` emits the plain dict). Accepted; flag for a later real-framework check.
- No live LLM: the test context uses MockProvider and an `open_session` that raises AssertionError. PASS.
- Mutation: (a) adding run_case to the grader tuple fails at import (RuntimeError, AL8 guard); (b) adding grade_case to the reporter
  fails `test_al10_the_allowlists_are_the_named_minimum`. Both reverted in the scratch worktree.

## Gate (on 7d47e3a7)
- Full suite: 5 failed, 5562 passed, 7 skipped, 14 xfailed (41 min). The 5 failures are symlink privilege (WinError 1314), known noise:
  test_discover symlink_escape, test_report_export x2, test_ui_crawls symlink, test_ui_video_route_traversal.
- ruff check src tests scripts: all checks passed.
- `autotester doctor`: clean.
