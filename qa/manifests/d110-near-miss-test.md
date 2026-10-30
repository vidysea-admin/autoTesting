# Manifest - d110-near-miss-test (pin near-miss tokens for `_allow_all`; closes checker-B finding 1 on d110-allow-all)

**Status:** ready-for-check
**Fix cycle:** 0
**Contract:** qa/contracts/auth.md (AU18, AU19; D-110 criterion C4: `*` is the only token with this meaning)
**Goal task:** none (T-204 linked by D-110)
**Authority:** D-110 (Approved-by: Umesh); finding source qa/verdicts/d110-allow-all.b.md (finding 1: no test pins near-miss tokens, so a substring `_allow_all` survives)
**Date:** 2026-10-30
**Round cap:** (a) SECURITY CLASS -- auth guard regression net: the test pins the token rule of the D-066 Host/Origin guard switch (`_allow_all`); D-014 never caps it.
**Persona walk:** skip (test-only, no screen or navigation change)
**Issues addressed:** none
**Executor:** claude-sonnet-subagent (maker)
**Executor rationale:** one small test addition in an existing file; no src change
**Base SHA:** 0f89becc (master)
**Code SHA:** be42bb8c (branch fix/d110-near-miss-test, worktree .claude/worktrees/near-miss)

## Criteria
- C1 - `_allow_all` is False for `**`, `*.evil.com`, `https://*`, `*:443`, `'*'`, `"*"`, `%2A`, fullwidth U+FF0A.
- C2 - `_allow_all` is True for ` * ` (space padded), `*,a.com`, `a.com *`, `a.com,*`.
- C3 - The test is load-bearing: a substring mutant of `_allow_all` makes it fail.

## What changed
- `tests/test_ui_origin_guard.py:256-271` - new `test_allow_all_matches_only_a_whole_star_token_never_a_near_miss` (12 parametrized cases), edited in place; file is 271 lines (cap 300).
- No `src/` change. Not touched: `qa/contracts/`, `docs/DECISIONS.md`, enforcement paths.

## Verification
- `uv run pytest tests/test_ui_origin_guard.py -o addopts=` -> `140 passed, 2 warnings in 13.86s`
- `uv run ruff check tests/test_ui_origin_guard.py` -> `All checks passed!`
- Mutant proof (scratch full-repo copy under .work/mutrepo, discarded; `scripts/regression_proof.py:24` pins `src` relative to itself, so `PYTHONPATH` alone does not substitute the module). Mutation at `src/autotester/ui/helpers.py:203`:
  `return "*" in os.environ.get(name, "").replace(",", " ").split()` -> `return "*" in os.environ.get(name, "")`
  Run result (module confirmed loaded from the mutated copy): `6 failed, 6 passed, 128 deselected`; failed ids: `[**-False]`, `[*.evil.com-False]`, `[https://*-False]`, `[*:443-False]`, `['*'-False]`, `["*"-False]`. (`%2A` and fullwidth pass under this mutant; they pin against decode/normalise mutants.) Unmutated copy: `12 passed`.
- Full suite not run (low-memory machine; test-only unit).
