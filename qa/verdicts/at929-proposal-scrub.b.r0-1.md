# Verdict (coordinator B, blind) - at929-proposal-scrub
Cycle checked: 0
Date: 2026-10-17
Bound root: D:/autoTesting/.worktrees/at929-proposal-scrub · base 69ebfae7 (= git merge-base HEAD master) · head 01797fdb (code b5d83803)
Policy-Version: proportional-verification/2026-10-15.12 · Dual check: coordinator B · Tier L (security, dual-trigger expand.py:181)

## Check plan
Logic + security change in one stage file. Instruments: re-run the 4 manifest verify commands; read the diff (step 4c); read every writer of case_proposals.jsonl (grep `stage_case_proposals|review_case_proposal`) against the issue text; one falsification of C1 in a copy outside the worktree; one probe of the other writer. No UI walk (no screen changed by the diff). Lane: normal (dual check never uses the quick lane).

## Evidence
- `uv run pytest tests/test_expand_redaction.py` -> 27 passed (25.9 s). `uv run pytest tests/test_expand.py tests/test_expand_cli.py` -> 25 passed. `uv run ruff check src tests scripts` -> All checks passed. `uv run autotester doctor` -> doctor: clean. (run by me in the worktree)
- Falsification (copy outside the worktree, scratchpad): the 3 named AT-929 nodes green in the copy (3 passed), then `_scrub_proposals` made to `return rows` -> red on the named assertions: `assert 'Hunter2-Zebra-4411' not in ...` and `DID NOT RAISE ValueError` x2. Floor met.
- Diff scope (4c): 3 files (expand.py +18/-1, test +57, manifest). Nothing removed or renamed; every file is in "What changed". Error texts are static strings and never echo the secret.
- Builder's own claim holds: `stage_and_review` (the CLI `expand --by` path and `ui/routes_proposals.py:108,143`) scrubs title/rationale and refuses `--by` / flow id equal to a secret. Refusal rather than masking is acceptable per the issue's fix_direction.

## FAIL finding (reproduced by me)
[C1] sev: medium (security) - the expected text of AT-929 is "Every field of case_proposals.jsonl that carries operator or target text passes Redactor.scrub before it is stored", and the issue's title names the store layer. The unit scrubs only inside `stages/expand.py::stage_and_review`. A second writer stages the same file unscrubbed: `src/autotester/ui/routes_learn.py:233` (`store.stage_case_proposals(propose_cases(spec))`, the Generate-cases button, I read the line). `ProjectStore.stage_case_proposals` (store/project_store.py:131-147) still never scrubs.
Reproduction (copy outside the worktree, project with `ST_PASS=Hunter2-Zebra-4411`, approved flowspec whose flow is named `Sign in <secret>`): `POST /projects/demo/cases/generate` via TestClient -> `case_proposals.jsonl` contains the raw secret in every title (2 of 2 probe tests red: fresh project, and after a CLI `stage_and_review` had staged scrubbed rows). In the second case the button's raw rows replace the scrubbed ones (upsert by slot_id), so the CLI fix is undone by one click. Probe: `tests/test_probe_at929b.py` in the scratch copy, command `python -m pytest tests/test_probe_at929b.py` with PYTHONPATH=<copy>/src -> 2 failed on `assert SECRET not in ...case_proposals.read_text()`.
Fix direction: scrub (and refuse a secret in flow_id) inside `ProjectStore.stage_case_proposals`, or call `_scrub_proposals` from `routes_learn.py::generate_cases` too; add a test through the UI route. Note store/project_store.py is at the 300-line cap, so the scrub helper may need to live in a shared module the store imports.

PROPOSED-ISSUE: {"id":"P1","feature":"failure-bundle","severity":"medium","type":"security","title":"routes_learn.py:233 stages propose_cases(spec) into case_proposals.jsonl unscrubbed; AT-929 scrub covers only stages.expand.stage_and_review, and the button overwrites the scrubbed rows","expected":"Every writer of case_proposals.jsonl scrubs title/rationale and refuses a secret in flow_id","fix_direction":"Scrub in ProjectStore.stage_case_proposals or call the scrub from generate_cases"}

VERDICT: FAIL
SCOREBOARD: 0/1 criteria met (C1 = AT-929 partly: CLI path met, UI path not), invariants: core-invariants C5 not held on the UI writer
TIER: L (security: secret redaction of stored proposals; dual-trigger src/autotester/stages/expand.py:181)
FAILURES:
- [C1] sev: medium - routes_learn.py:233 writes proposals unscrubbed and overwrites scrubbed rows; reproduced by TestClient probe · scrub at the store write (or in generate_cases) · issue: P1
CAPABILITY-COVERAGE: 1/1 rows reproduced (green before, red after, restored in copy)
LIVE-BROWSER: not-applicable (changed paths: src/autotester/stages/expand.py, tests/test_expand_redaction.py)
ISSUES-WRITTEN: none (dual coordinator; PROPOSED-ISSUE P1 above)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: The CLI path is correctly scrubbed and the builder's tests, lint and doctor are green, but the criterion text covers every stored field of case_proposals.jsonl and the UI Generate button still writes it raw, and undoes the CLI scrub. A security defect in the file the unit claims to close, reproduced by a command I ran.
Metrics: start=2026-10-17T13:55:00Z end=2026-10-17T14:14:00Z wall_min=19 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=1 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-15.12 lane=normal check_s=1140 mutants=0 defects_unit=1 defects_6c=0
