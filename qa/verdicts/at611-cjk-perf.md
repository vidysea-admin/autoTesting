# Verdict — at611-cjk-perf

**Date:** 2026-09-27
**Cycle checked:** 1
**Checker:** /checker (standing checker session: orchestrator plus 2 fresh-context lenses — rows/verify, and semantic equivalence/scope/security)
**Contract:** qa/contracts/core-invariants.md (C2 caps, C3 one concept one place, C7 mutation duty); issue AT-611
**Branch / code commit:** wave/at611-cjk-perf · a51e1b7 (manifest 08888e1), base 7f08a3f

```
VERDICT: PASS
SCOREBOARD: 1/1 criteria met (AT-611: a CJK-heavy folded-secret scan no longer thrashes the ignorable-char cache), 3/3 invariants hold (C2: redact_fold.py 300→237, redact_wrap.py 218; C3: _BMP_IGNORABLE_RANGES built once at import; C7: both sabotage rows kill)
FAILURES: none
CAPABILITY-COVERAGE: 2/2 rows reproduced in own copies, green before / red after on the named assertion (row 1: restoring the old lru_cache'd category check makes test_cjk_heavy_scan_stays_within_a_generous_multiple_of_ascii fail at 8.79x vs the 2.5x bound; row 2: dropping (0xFE00, 0xFE0F) makes test_is_ignorable_char_matches_original_over_the_full_bmp fail with exactly 16 BMP mismatches)
LIVE-BROWSER: not-applicable (changed paths: src/autotester/core/redact_wrap.py, redact_fold.py, tests/ only; no UI surface)
ISSUES-WRITTEN: AT-620 (low, stale docstring at redact_encodings.py:112, outside this unit's diff)
EXECUTOR: maker builder (checker: claude-opus orchestrator + subagents)
EXPLANATION: The bisect-over-a-BMP-range-table is_ignorable_char agrees with the old _is_ignorable on all 1,114,112 code points, BMP and astral (0 mismatches, including U+E0001, U+1D173 and U+E0100). Ten FAKE secrets obfuscated with ZWSP, ZWNJ, soft hyphen, BOM, U+2060, a VS and a tag char inside CJK text are detected identically old vs new. The only moves were _is_ignorable→is_ignorable_char and _DEFAULT_IGNORABLE into redact_wrap.py, re-imported at the single call site. Nothing else was removed.
```

**Re-ran:**
- `uv run ruff check src tests scripts`: clean.
- `uv run autotester doctor`: clean.
- `tests/test_redact_ignorable_perf.py`: 11 passed.
- `-k redact`: 99 passed.
- `tests/test_redact_wrap_perf.py`: 18 passed.
- Full `uv run pytest`: 1919 passed, 1 failed (AT-518 `test_flake_probe_real_process…grandchild`, which also fails on master), 6 skipped, 32 xfailed (15m10s).

**Not independently re-verified:** the manifest's absolute wall-clock numbers. They depend on machine load, which is why the bound in the test is loose. The ratio assertion itself passed under concurrent load.
