# HUMAN_GATE — bound the session-start hook's `autotester snapshot` call?

**Raised:** 2026-09-27 · maker, after the checker's at383 cycle 1 verdict (16b370b)
**Issue:** AT-623 (pre-existing, filed by the checker at 4e65ce3)
**Blocks:** only AT-623. at383 cycle 2 (AT-622/AT-624) is covered by D-048 and proceeds without this.

## The question

`qa/hooks/mc-sessionstart.ps1` runs `uv run autotester snapshot` with no timeout. When uv hangs,
session start is blocked for about 82 s. D-048 authorizes only the loop-status call, and this hook is an
enforcement path, so bounding the snapshot call needs its own DECISIONS entry with `Approved-by: Umesh`.

- **A: bound it the same way as loop-status.** 15 s timeout, kill the whole process tree, print a
  skip line, and exit 0. This is the maker's recommendation.
- **B: leave it unbounded.** A hung uv keeps blocking session start.

## Answer

Append `Answered: <ISO date> — <A|B> — <where>` below BEFORE any unit acts on it.
