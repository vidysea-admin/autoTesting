# Common brief for read-only sub-checkers (unit t179a-lead-tester-core, repair cycle 1, coordinator A)

You are a read-only sub-checker. You report findings; you never fix anything and you do not judge the unit.
Bound to the checker's private copies on C: (NEVER read or write anything under D:/autoTesting; never open any
qa/ verdict, checkpoint, evidence or issues file; never any file ending `.b.md` or containing `-B`).

Copies (extracted with `git archive`, no .git):
- HEAD = C:/Users/Lenovo/AppData/Local/Temp/chkA_t179r1_355800/head  (code under check, commit c489e201; has its own .venv)
- BASE = C:/Users/Lenovo/AppData/Local/Temp/chkA_t179r1_355800/base  (repair base 638d788a, NO venv: run it with the HEAD venv and
  PYTHONPATH=<BASE>/src; always print `autotester.__file__` first and confirm it is inside the copy you mean)
- Scratch for your scripts: <ROOT>/scripts/<your-name>/   (<ROOT> = C:/Users/Lenovo/AppData/Local/Temp/chkA_t179r1_355800).
  Evidence output dir: <ROOT>/evidence/<your-name>/   (create it; save scripts, raw outputs, a RESULT.md summary there)
- Run python as: `unset VIRTUAL_ENV; uv --directory <HEAD> run python <script>` (or `uv --directory <HEAD> run pytest ... -o addopts=`).
  Foreground, with timeouts. Do not `uv sync`/install anywhere; the HEAD .venv is ready. Never use `-q` on pytest together with addopts
  (use `-o addopts=`). Never read or print any `.env` value. Fake canary secrets only (e.g. `CANARY-pw-7f3a9c`), a temp data root
  (tmp dir), no real browser, no real model, no network. Spies replace `execute.run_case`, the session factory and the judge.
- Do not edit anything under HEAD or BASE (copy to your own folder if you must mutate).
- Do not spawn further agents.

Code under test: HEAD/src/autotester/agents/guards.py (write_policy_refusal, AL3) and HEAD/src/autotester/agents/tools.py
(dispatch, F2-F4). Existing test helpers to reuse for building a project/store/context/spies:
HEAD/tests/test_agent_tools.py (_project, _case, _grant, _ctx, spies fixture, _go) and HEAD/tests/test_agent_read_only.py (_run).
Read them first and import or copy their patterns (the tests dir is importable by adding it to sys.path).
Enums: HEAD/src/autotester/schema/enums.py (Action, WritePolicy, ApprovalKind). Executor: HEAD/src/autotester/stages/execute.py;
browser: HEAD/src/autotester/browser/session.py (goto -> check_destination, host_of in browser/secrets.py).

Report format (your final message): a compact table of what you ran and the observed result per row, then a list of FINDINGS
(each: what input, what happened, what was expected, file:line you read yourself), then anything you could not run. State plainly
when everything behaved; do not invent findings. Mark a finding only if you reproduced it with a command you ran (give the command
and the script path under your evidence dir). Observations you did not reproduce go under QUESTIONS.
