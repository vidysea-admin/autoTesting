# Verdict - ledger-tick-integrity

**Verdict:** FAIL
**Status:** FAIL
**Cycle checked:** 0
**Reviewed SHA:** ce4e124a5ffefef83f881d07aa538860b5b515b8
**Base SHA:** c4d48ad109f1ef77f73ee9172866cc5feeca7063
**Checker:** independent (Sonnet 5.5), BOOTSTRAP_REVIEW scope (maker usage unknown; ratio unverified)

## Blocking finding (proven acceptance violation)
`autotester doctor` is a mandatory gate (`qa/adapter.json` verify.commands, expect exit 0).
- Base c4d48ad1 (archive copy, own import root): `doctor: clean`, exit 0.
- Candidate ce4e124a: exit 1, **2 violations**, both introduced by this unit:
  1. `file-too-long: src/autotester/cli.py 301 lines > 300` (base 300; candidate added the `loop-tick` registration line).
  2. `stale-generated: docs/MAP.md generated sections differ; run autotester map` (new module `core/atomic_tick.py` not in the map).
- The maker's "0 file-size violations" claim is false for cli.py; the maker did not run doctor to exit code.

## Doctor discrepancy explained
The 3301 "decision-citation-*" items (2929 coverage + 370 declaration + 2 known-disputed) are ADVISORY, non-blocking warnings (D-087) and are identical at base and candidate (base also 3301, exit 0). They are not violations and are not caused by this unit. The main checkout "clean" is the same: warnings plus 0 violations. The real delta is the 2 blocking violations above.

## Checks run (worktree, main .venv, PYTHONPATH=worktree src; import origin verified)
- pytest tests/test_ledger_tick_integrity.py tests/test_issue_ids.py tests/test_loop_status.py: 27 passed, exit 0 (.work/chk/pytest.txt).
- ruff check src tests scripts: clean, exit 0.
- doctor candidate: exit 1 (.work/chk/doctor_cand.txt); base: exit 0 (.work/chk/doctor_base.txt).
- Adversarial probe (.work/chk/probe.py), Windows:
  - append_tick when target is held open by a reader: os.replace raises PermissionError WinError 5; original intact, tmp cleaned (fail-safe, but the tick is lost).
  - append_tick is NOT locked and tmp name is pid-only: 8 threads in one process gave 3 of 9 lines with 4 PermissionErrors (lost updates, shared tmp). 8 subprocesses gave 9 of 9 in this run (timing luck; read-modify-replace has a lost-update window across processes). The "atomic" claim holds for partial-write safety only, not for concurrent appenders.
  - append_issue / append_new_issue: lock held once per call, no nested file_lock in callers (only tests call append_issue; renumber script uses next_issue_id only), so no re-entrancy deadlock. Lock sidecar `qa/issues.jsonl.lock` is created and is not gitignored (git check-ignore rc=1): untracked-file pollution.
- Claims verified true: temp+fsync+os.replace, refuses empty/shrink; `loop-tick` exists; append_issue under file_lock; append_new_issue single locked step; no glue onto unterminated row; duplicate violation names id and lines; base ledger had 0 duplicates (1025 lines).

## Required to reach PASS (cycle 1)
1. Bring cli.py to <=300 lines (e.g. register loop-tick elsewhere/compress) and run `autotester map` so doctor exits 0.
2. Make append_tick safe for concurrent writers (take file_lock on a sidecar and use a unique tmp name per call), and add a concurrent-append test.
3. Gitignore `qa/*.lock` (or equivalent) for the new sidecar.
4. Re-run doctor to exit 0 and report the exit code.

## Remaining gates / limits
Full suite not run (scoped, shared CPU). Not PASS; no ledger/push actions.
