# HUMAN_GATE: T-151 STALLED after fix cycle 2 (dual check split: A PASS, B FAIL)

**Opened:** 2026-10-07 by /maker. **Blocks:** T-151 merge.
**Verdicts:** A PASS, `qa/verdicts/t151-target-discovery.md` (b18e4ea6). B FAIL, `qa/verdicts/t151-target-discovery.b.md` (c5000995). Both are on branch codex/t151-target-discovery.

**Diagnosis:** progress was real, so this is not a no-progress stall. All cycle-1 failures are closed: the 4 table survivors are killed, and line numbering, the non-md gate, the YAML alias and the output bound are fixed. Exactly one gap is left (B, X17). `discover.py::_emit` checks the deadline per Signal, and that code is correct, but no committed test defends it. With that check disabled, all 90 discover tests still pass. B's clock-advancing probe (500-line `import openai` file: 501 scrub calls on the mutant against fewer than 50 on the real code) is the template for the missing test. Cause: the cycle-2 brief named the reader's in-loop deadline test but not the scan path's twin.

The full suite gave the same result for both checkers: 4 failed, 2286 passed. All 4 failures are load-sensitive or also fail on the base commit, and none is attributable to T-151 (B P3, A issue 3).

**Options:**
- A: Authorize one narrow extra cycle. Add one test to tests/test_discover_hardening.py that drives `scan` with an advancing clock, plus its falsification row, and nothing else. Only repair checker B re-runs X17. A's PASS stands by evidence identity, since no product file changes.
- B: Owner-accept X17 as a known gap (an ISS row at medium) and merge on A's PASS plus B's otherwise-met criteria.
- C: Leave T-151 stalled.

**Recommendation:** A. It costs one test and one checker run, and keeps the dual check honest.

**Answer format:** "t151: A", "t151: B" or "t151: C".

Answered: 2026-10-07T06:34:21Z — A — chat (Umesh): one narrow extra cycle, add the scan-path deadline test only; repair checker B re-runs X17.
