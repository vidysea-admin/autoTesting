# t200b-scheduled-test r1 seat A - coordinator evidence (head 371eb7f6, product sha 6d6bc318, repair base 0d9a3b56)

Interpreter: D:/autoTesting/.worktrees/t200b-scheduled-test/.venv/Scripts/python.exe.
`autotester.__file__` = D:\autoTesting\.worktrees\t200b-scheduled-test\src\autotester\__init__.py (inside the worktree, not D:/autoTesting/src).
Git: HEAD = 371eb7f6 (matches dispatch); 0d9a3b56 is an ancestor of HEAD; worktree clean (git status --porcelain empty).

## Affected tests (one pytest process)
`pytest -p no:xdist -o addopts= tests/test_schedule_model.py test_schedule_due.py test_schedule_marker.py test_schedule_catchup.py test_schedule_overlap.py test_schedule_failures.py test_schedule_gate.py test_schedule_tick.py test_explore_consent.py test_credential_run_approval.py test_consent.py test_approval_signing.py test_env_loading.py` -> 236 passed, 1 warning (36.65 s).
`ruff check src tests scripts` -> All checks passed. `autotester doctor` -> clean.
Only TickDeps( constructors: tests/schedule_fakes.py:69 (passes scrub) and tests/test_schedule_gate.py:162 (the required-field test).

## First key mint (manifest claim), probe in a temp root with a synthetic project (no repo .env touched)
Before: files [.env, projects/demo/project.json], env keys [DEMO_USER], os.environ key unset.
refusal_for (preview) with no key and no history -> None, and wrote nothing.
First gate call -> None. After: files + .env.lock + projects/demo/approvals.jsonl; env keys + AUTOTESTER_APPROVAL_KEY; os.environ key SET; 1 approval row, signed. Second call -> None, still 1 row.
Lost key (env var and .env key removed, signed history present): preview -> "approval_required: the approval signing key is unavailable"; real gate -> same string; nothing written, os.environ unset. Preview and gate agree.
Blank `AUTOTESTER_APPROVAL_KEY=` line, no history: preview None, gate None, key minted (parity with ensure_approval_key).
Manifest claim (key to .env, .env.lock left, signed row appended, key exported to os.environ) CONFIRMED.

## Falsifications run by me, throwaway copy (src, tests, scripts, pyproject) in scratchpad/fz, autotester.__file__ printed inside the copy, copy deleted
P5 preview parity: signing_key_available body -> `return True`: test_the_dry_run_preview_agrees_with_the_real_gate_when_the_signing_key_is_lost 1 passed -> 1 failed; restored -> pass.
P3 scrub: `TickDeps.scrub` given default `lambda t: t`: test_scrub_is_a_required_field_so_a_caller_cannot_forget_it 2 passed (scrub -k) -> 1 failed, 1 passed; restored -> pass.
F1 and F2 falsifications were run by sub-checkers in their own copies: see f1-import-shapes.md and f2-purge-attack.md (+ f2-scripts/).
