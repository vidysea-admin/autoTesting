# Manifest — at560-allowlist-note

**Contract:** qa/issues.jsonl AT-560; domain-adapter.md Security invariant (CONTRACT_MISMATCH rule)
**Fix cycle:** 1 of 3
**Dual check:** no
**Issues addressed:** AT-560
**Executor:** claude-sonnet-subagent
**Executor rationale:** small, well-scoped fix touching one governance JSON note + one script's
restore path + tests — sized for a single maker build unit, no delegation needed.

## What changed

- `qa/adapter.json:14` — `verify.read_only_allowlist._note` reworded. It previously claimed a
  blanket "nothing here may write, push, delete or reach the network," which was false for the
  `scripts/regression_proof.py` allowlist entry (that script mutates a TRACKED fixture file for
  one run, then restores it). New wording: each entry may only "operate within a self-created
  temp dir, or mutate-and-restore a local fixture under tests/fixtures... never mutate bound
  source outside tests/fixtures, push, or reach the network" — matching AT-560's suggested
  rewording — plus an inline note citing AT-560 and why the old phrasing was wrong. No allowlist
  entries were added, removed, or reordered; `verify.commands` (the three required gates) is
  untouched. JSON validity re-checked (`python -c "import json; json.load(...)"`).

- `scripts/regression_proof.py:43-59` — **new** `_swapped_fixture(good_path, broken_path)`
  context manager (`contextlib.contextmanager`): reads `good_path`'s content, copies
  `broken_path` over it, yields, and in a `finally` always writes the original content back —
  even if the body raises. This extracts the copy/restore pair that previously lived inline in
  `main()` (old lines 167, 176, 183, wrapped in a `try/finally` spanning the whole BEFORE+AFTER
  run) into its own testable unit. **Behaviour is unchanged**: same
  read-backup -> copy-broken-in -> run -> restore-good sequence, same file states over time —
  `main()` now just does `with _swapped_fixture(LOGIN_GOOD, LOGIN_BROKEN):` around the AFTER run
  (`scripts/regression_proof.py:191`) instead of the inline copy + bare `LOGIN_GOOD.write_text`
  in its own top-level `finally`. `server.shutdown()` stays in `main()`'s own `finally` as before.
  Import cleanup: added `collections.abc.Iterator` for the context manager's return type (ruff
  UP035 flagged an initial `typing.Iterator` import; fixed to `collections.abc`).

  Note: the pre-existing code (git blame: commit `6f52112`, 2026-09-03) already wrapped the copy
  and the AFTER run in a `try/finally` at the `main()` level, so the restore-on-raise guarantee
  already held structurally. AT-560's ask was to make it *robust and directly testable*; the
  refactor achieves that without changing behavior, and the mutation check below (removing the
  `finally`) confirms the guarantee is real, not accidental.

- `tests/test_regression_proof.py` — added `import pytest`, plus two new tests:
  - `test_swapped_fixture_copies_the_broken_content_in` — normal path: content is `BROKEN` inside
    the `with` block, `GOOD` again after it exits cleanly.
  - `test_swapped_fixture_restores_the_tracked_file_even_when_the_body_raises` — AT-560's actual
    concern: raises `RuntimeError("boom")` inside the `with` block after confirming the swap
    happened, then asserts the fixture is back to `GOOD` outside it. Both tests operate entirely
    on `tmp_path` copies of `login.html`/`login.broken.html` content — the real
    `tests/fixtures/regression_site/` files are never touched by either test.
  - Checked for any test asserting the old `_note` text: none found (`grep -rn "nothing here may
    write" tests/` and a repo-wide grep for the phrase turned up only `qa/adapter.json` itself and
    `qa/verdicts/t126-governance.md`, which quotes the old text as historical evidence of the bug
    being reported — not a test assertion). `tests/test_ledger_checks.py`'s `_adapter()` helper
    builds a synthetic minimal adapter fixture with its own `_note` string and does not reference
    the real `qa/adapter.json` content.

## Verify output

```
$ uv run pytest tests/test_regression_proof.py -v
...
collected 11 items
tests\test_regression_proof.py ...........                               [100%]
============================= 11 passed in 0.21s ==============================

$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester doctor
doctor: clean
```

Full suite (`uv run pytest` unrestricted): **gap, declared** — at verify time, free physical
memory was ~2.9 GB (`Get-CimInstance Win32_OperatingSystem`.FreePhysicalMemory ≈ 3,040,324 KB),
below the 3.5 GB floor, and multiple other `python`/`pytest` processes were running (other
maker/checker waves). Ran the targeted file instead per the dispatch's fallback instruction.

## Capability coverage

- Governance/config edit (JSON note reword): direct, no browser/network capability needed.
- Code fix (context-manager extraction) + new unit tests: covered by
  `uv run pytest tests/test_regression_proof.py` (11/11 pass, including the 2 new tests).
- Restore-on-failure guarantee: **falsified and confirmed** via the mutation check below, not
  just asserted by a passing test on unmodified code.
- Lint/design-rule gates: `ruff check` and `autotester doctor` both clean.

## Mutation duty (C7)

Scratch copy backed up: `.work/at560-mutation-scratch/regression_proof.py.orig` (deleted after
the check — transient, not committed).

1. Edited `scripts/regression_proof.py`'s `_swapped_fixture` in place to remove the
   `try/finally`, leaving a bare `copy -> yield -> write_text` sequence (no restore-on-raise).
2. Ran `uv run pytest tests/test_regression_proof.py -v -k restore` — **failed**, for exactly the
   named reason:
   ```
   AssertionError: the tracked fixture must be restored even after the body raised
   assert 'BROKEN' == 'GOOD'
   ```
3. Reverted the edit (restored the `try/finally`). `diff` against the pre-mutation backup
   confirmed the file is byte-identical to the post-fix version. Re-ran
   `uv run pytest tests/test_regression_proof.py -v` — 11/11 pass again.

## Live browser evidence: Not UI-touching

This unit only edits a JSON governance note and a Python script's control flow (plus tests
running against `tmp_path` fixtures) — no browser, no UI, no live product surface touched.

- `qa/adapter.json` (diff): reworded `verify.read_only_allowlist._note`
- `scripts/regression_proof.py` (diff): new `_swapped_fixture` context manager, `main()` updated
  to use it
- `tests/test_regression_proof.py` (diff): two new tests + `import pytest`

**Commit:** `91ed626934b143aff45a15ca5cd183fe5d2b14ac` — "fix(governance): AT-560 -- accurate
allowlist note + robust fixture restore" (branch `wave/at560-allowlist-note`, worktree
`D:/autoTesting/.worktrees/at560-allowlist-note`)

Status: checked-PASS (qa/verdicts/at560-allowlist-note.md, cycle 1, 898879e)
