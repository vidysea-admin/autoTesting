# Checkpoint (coordinator A) - t179a-lead-tester-core

Cycle checked: 0
Policy-Version: proportional-verification/2026-10-10.9
Result: FAIL (AL3(c) not met). Verdict: `qa/verdicts/t179a-lead-tester-core.a.md`.

## Evidence identity
- Code: branch `wave/t179-lead-tester` head 638d788a, code hash 90705dc0, merge-base with master 16aaa402 (verified with git).
- Environment: `git archive 638d788a` extracted to `C:\Users\Lenovo\AppData\Local\Temp\chkA-t179a-1175810622`, its own venv on C:, `autotester.__file__` and pytest rootdir inside the copy (`qa/evidence/t179a-lead-tester-core-A/paths.txt`). No checkout, worktree or venv on D:. No real browser, live site or model call. No `.env` value read.
- Scope and results:
  - Unit tests: `tests/test_agent_tools.py`, 14 collected, 14 passed (`unit-tests.txt`).
  - Lint and design rules: ruff and `autotester doctor` clean (`ruff-doctor.txt`).
  - Attack probes (A guards, B secret gates, C approval, D dispatcher): `probe-a.txt` .. `probe-d.txt`, sources `test_chk_attack_*.py.txt`.
  - Falsification (7 runs, one copy each): `falsify.py.txt`; AL2, AL3a, AL3b, AL3c, AL6 green-before / red-after; login-placeholder red; `get_persona` mutant survived.
  - Full suite: not run (owed only when every criterion is met). suite_runs=0.
- Reusable by a later check: the AL2, AL3a, AL3b, AL6 falsification rows and the approval and secret-gate probes, while `src/autotester/agents/*` and `schema/agent_layer.py` are unchanged. AL3(c) must be re-checked after any change to `agents/guards.py` or `agents/tools.py`.
- Attribution: coordinator A, claude-sonnet-subagent.
