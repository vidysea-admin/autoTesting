# Checkpoint: t179a-lead-tester-core, repair check r2, coordinator B

Cycle checked: 2 | Verdict: PASS | Resumes: 0 | Policy-Version: proportional-verification/2026-10-10.9

Common: code tree 86d240a9 (code cc7f29ed), repair base c489e201, unit base 16aaa402. `git archive` copies under C:/Users/Lenovo/AppData/Local/Temp/claude/chk-t179r2b-2791923252/{head,base,f1,f2,f3}, each with its own `uv sync --frozen` venv, `autotester.__file__` printed from the copy, uv.lock from the archive. Agent: claude-sonnet-subagent. Scripts: qa/evidence/t179a-lead-tester-core-r2-B/.

| Check | Command and scope | Result |
|---|---|---|
| AL6 split matrix | p_split.py, 9 locations x 37 separators x 6 cuts, oracle guard_prompt | 1,998 rows, 0 leak, 0 over-withhold |
| AL6 decoded forms and Verdict fields | same harness, in-session run | all withheld, nothing stored |
| AL6 availability | p_size.py at head vs c489e201 | head withholds 6 of 9 secret-free sizes; base stores 9 of 9 (P1) |
| AL3 guard table | p_guard.py head vs c489e201, 14,358 rows | above READ_ONLY equals the seam (210 rows, 0 mismatch); READ_ONLY differs only in 32 blank-fill rows |
| Tests | pytest the 4 agent test files (392 passed); test_explore_safety, test_execute, test_schema, test_doctor (140); test_goal_contract_registration (1, full archive) | green |
| Static | ruff (src, scripts, 4 agent tests), autotester doctor | clean |
| Falsify AL6 / AL3 / AL6 unicode | mutate.py in f1, f2, f3; red 40 / 12 / 10 failed; restored (cmp identical); green again | 3 of 3 |

Not reusable without a re-run: the size and split probes depend on tools.py:87-130 and 257-267; the guard table depends on guards.py:86-135.
Copies under C:/.../chk-t179r2b-2791923252 are deleted after the check.
