# Manifest — at712-ledger-store

**Contract:** none (issue AT-712 in qa/issues.jsonl; single criterion C1 below)
**Goal task:** none
**Date:** 2026-10-17
**Fix cycle:** 0 of max 2
**Dual check:** no
**Persona walk:** skip (backend-only CLI report, no human screen)
**Issues addressed:** AT-712
**Executor:** claude-sonnet-subagent
**Executor rationale:** tier M single-owner unit; resumed after an API outage from the earlier builder's partial work (kept, reviewed, finished)

## What changed
- src/autotester/ledger/store.py:136-229 — `changed_paths` (read-only `git diff-tree`, argv list), `backref_candidates`/`backref_report`: open `qa/issues.jsonl` rows (title/evidence) and every `qa/gates/*.md` line that name a path the fixing commit changed. Longest path-suffix match on component boundaries; basename-only hits are marked weak; the closing row and non-open rows are excluded; qa/, .goal/, .work/ bookkeeping paths are skipped. Report only: never edits a row or a gate.
- src/autotester/cli_loop.py:56-72,77 — `ledger-backref [REV] [--exclude ID]` command attached via the existing `attach_loop_commands` (cli.py is at its 300-line budget, so no cli.py hunk; same registration seam as loop-status/loop-tick).
- tests/test_ledger_backref.py (new, 9 tests; tests/test_ledger.py is already 297 lines) — AT-660/CN10 scenario: three stale open rows plus a gate are listed, quiet rows and gates are not; weak basename marking; open-only/exclude; boundary false-positives; bookkeeping flood; real temp git repo for `changed_paths`, no-edit guarantee, and the CLI.
- No code, test or config deleted or renamed.

## Verification scope
Policy-Version: proportional-verification/2026-10-15.12
Tier: M (new read-only ledger helper plus one CLI command; no security/auth/tenancy/prod-write trigger)
Base / checked state: base fcedc9f4, code head 81970378, clean tree
Gate answers: none (no gate touched)
Affected tests / full-suite trigger: tests/test_ledger_backref.py, tests/test_ledger.py; no safe-fallback trigger. Builder ran no full suite.
Pre-check[C1]: 81970378 uv run pytest tests/test_ledger_backref.py tests/test_ledger.py -> 33 passed t=10 blobs=tests/test_ledger_backref.py:bdb4e78,tests/test_ledger.py:05d0c74
Metrics: start=2026-10-17T10:50:00Z end=2026-10-17T11:12:00Z wall_min=22 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=1 cycle=0 resumes=1 tokens=unavailable policy=proportional-verification/2026-10-15.12 lane=normal check_s=10 mutants=1 defects_unit=0 defects_6c=0

## How to verify (commands + expected)
- `uv run pytest tests/test_ledger_backref.py tests/test_ledger.py` → expected: 33 passed
- `uv run ruff check src tests scripts` → expected: All checks passed!
- `uv run autotester doctor` → expected: doctor: clean (worktree has no root-clutter; citation findings are advisory D-087)
- `uv run autotester ledger-backref <sha> --exclude AT-660` → expected: lists open rows and gate lines naming files that commit changed

## Actual outputs (from maker's own run)
```
$ uv run pytest tests/test_ledger_backref.py tests/test_ledger.py
33 passed, 1 warning in 3.91s
$ uv run ruff check src tests scripts
All checks passed!
$ uv run autotester doctor
doctor: clean
```

## Capability coverage (each new claim -> its isolating falsification)
| Criterion | capability | check | falsifying edit | observed |
|---|---|---|---|---|
| C1 | At close-out, open ledger rows AND qa/gates files citing a changed path are listed (rows only is incomplete, AT-712 expected) | tests/test_ledger_backref.py::test_a_run_budget_fix_lists_the_three_stale_rows_and_the_gate_that_cites_them | store.py `backref_candidates`: `for name, text in sorted(gates.items()):` -> `for name, text in []:` (throwaway copy outside the worktree, PYTHONPATH-shadowed) | green before: `1 passed, 2 warnings in 0.85s`; red after: `AssertionError: assert 'qa/gates/at674-approval-key.md:4' in 'AT-675 [open] names src/autotester/stages/parallel_run.py (basename only) in evidence: ...'` then `1 failed, 1 warning in 0.86s` |

## Live browser evidence
Not UI-touching — no surface changed. Changed paths: src/autotester/ledger/store.py, src/autotester/cli_loop.py, tests/test_ledger_backref.py (CLI/ledger only).

## Status: checked-PASS (qa/verdicts/at712-ledger-store.md, cycle 0)
