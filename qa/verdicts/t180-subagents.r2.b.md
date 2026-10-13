# t180-subagents r2 checker B: PASS

Cycle checked: 1
Checked sha: 5127e0ded98e1ef0525377bf974ddb001cfbe6c5 (origin/wave/t180-subagents)
Tier L, second blind check. Written before reading any other t180 verdict.

## AL8 - PASS
Grader allowlist is `read_result`, `read_rubric`, both `ToolEffect.READ`; asserted at import in
`agents/subagents.py` and in tests. Probe: grader refused `run_case`, `crawl`, `grade_case` with
NOT_ALLOWED and wrote no verdict. SKILL.md for the grader says "Use only read_result and
read_rubric ... You cannot act".

## AL10 - PASS
Own probe through `call_tool` for every role: all 8 tool names, plus junk (None, int, list, bytes,
dict, empty, whitespace, NUL, path-like, `*`), case variants (UPPER, Title), padded/newline/tab,
hyphenated and zero-width-suffixed names, and StrEnum members. 0 leaks: only exact allow-listed
names reached `dispatch`, every other call returned NOT_ALLOWED without echo. `SubagentSpec` is
frozen and `tools` has `min_length=1`. `grade_case` is on no subagent list.
SKILL.md prompts (all five) name exactly the tools on their allowlist and no others.
Non-blocking observation: `call_tool` uses `isinstance(tool, str) and tool in set`; a hostile str
subclass with overridden `__eq__`/`__hash__` passes the check (reached dispatch for explorer with
"grade_case", then failed on args). Needs an in-process object, a model emits plain JSON strings;
suggest `type(tool) is str` or `str.__str__(tool)` later.

## AL9 - PASS, with a stated limit
deepagents is not installed, so only the invocation object is proven: `SubagentInvocation` has
fields subagent/system_prompt/task/shared_files/tools and no field for lead history or another
transcript; `deep_agents_config` yields the plain dict. This meets the brief's "inspecting the
invocation shows each context does not contain the other's raw transcript" clause. It does not
meet "a fixture job driving two subagents" literally; the overflow test is partly tautological
(strings never passed to anything). The framework call is T-179's. Accepted for this unit, and
AL9 should be re-judged when the framework wiring lands.

## Temp merge onto current master (04e461f9, includes fix-baseline 18626438)
`git merge --no-commit --no-ff` clean, no conflicts. `tests/test_agent_*.py` on the merge:
462 passed. ruff clean on merge.

## Mutation
In the merge worktree, replaced the `isinstance(tool, str) or tool not in allowed` check in
`call_tool` with `if False:`. Result: 13 failed (al8 grader test, malformed-name tests, al10
absent-tools tests). Reverted: 25 passed.

## Gate
- Full `uv run pytest -o addopts=` on the branch: 5 failed, 5603 passed, 7 skipped, 14 xfailed.
  The 5 failures are the known symlink noise (test_discover symlink_escape, two test_report_export
  symlink, test_ui_crawls symlink, test_ui_video_route_traversal symlinked_escape). No flakes hit.
- ruff check src tests scripts: clean.
- `uv run autotester doctor` on the branch: clean. On the merge, only the unrelated t196 verdict
  citation violations (known, being amended).
- No file under `src/autotester/ui/`; `agents/` files all under 300 lines; pyproject/uv.lock and
  `qa/contracts/` untouched.
