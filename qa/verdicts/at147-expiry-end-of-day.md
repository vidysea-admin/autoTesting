# Verdict — at147-expiry-end-of-day

**Date:** 2026-09-27
**Cycle checked:** 1
**Checker:** /checker (standing checker session: orchestrator plus 2 fresh-context lenses — rows/verify/scope, and CN4 boundary probes)
**Contract:** qa/contracts/consent.md CN4 (folded d8da333 under D-048); gate qa/gates/at147-expiry-end-of-day.md answered C by Umesh; T-188
**Branch / code commit:** wave/at147-expiry-end-of-day · e318fa6 (manifest 6af3208), base cfb905a

```
VERDICT: PASS
SCOREBOARD: 1/1 criteria met (CN4 as amended: a NEW grant's --expires D is honoured through 23:59:59 local on D, today is grantable, and pre-existing bare-date rows keep their old 00:00 lapse), 3/3 invariants hold (C2: cli_crawl.py exactly 300, approve_cmd 50 by doctor's measure; C3: one _local_now/_end_of_day seam shared by _validate_grant and approve_cmd; C7: 3/3 rows kill)
FAILURES: none
CAPABILITY-COVERAGE: 3/3 rows reproduced in own copies (a: dropping tzinfo= from _end_of_day gives a naive stamp; b: storing the bare `expires` string again; c: bare dates made inclusive in is_expired gives `assert False is True` on the pre-existing-row test), each red on the named assertion
LIVE-BROWSER: not-applicable (changed paths: src/autotester/cli_crawl.py, tests/; the web grant form already takes a datetime-local instant and is untouched)
ISSUES-WRITTEN: none
EXECUTOR: maker builder (checker: claude-opus orchestrator + subagents)
EXPLANATION: 16 boundary probes with a frozen clock all hold:
- D 23:59:59 local is honoured and D+1 00:00:00 is refused.
- --expires today is accepted and --expires yesterday is refused.
- An old bare-date row still lapses at 00:00, and schema/approval.py is unchanged vs base, which is gate C's "new only".
- The stored stamp carries the local offset and round-trips through the extra=forbid model.
- A malformed or empty expiry is refused at the CLI and treated as expired in is_expired, never permanent.
The AT-151 two-arm collapse removes only the "today" refusal branch, which gate C made unreachable. The "already in the past" arm and its named date remain.
```

**Re-ran:**
- `uv run ruff check src tests scripts`: clean.
- `uv run autotester doctor`: clean.
- `tests/test_approve_cli.py tests/test_consent.py`: 34 passed.
- Full `uv run pytest`: 1914 passed, 0 failed, 6 skipped, 32 xfailed (12m33s).
- Diff scope `cfb905a..HEAD`: the manifest, cli_crawl.py and the two test files, matching What changed.
