# Verdict - agent-write-guard-gaps

**Verdict:** PASS
**Status:** PASS
**Cycle checked:** 2
**Reviewed SHA:** f4c3e2fdeb622e5611951ff32628890b0bfc5026 (base c4d48ad109f1ef77f73ee9172866cc5feeca7063, branch worktree-agent-a1af8a18cb4bcb723)
**Prior cycles:** cycle 0 FAIL at 4119e0a0 (verdict commit 0d0b5b68); cycle 1 FAIL N1 at 5dbbe33c (verdict commit 2d4e426d). Earlier findings are kept in git history.
**Budget status:** NEEDS_EXTRA_REVIEW (active_s breach, recorded, not waived). See Budget below.

## Scope
ISS-t179b-hg1-1 and ISS-t179b-hg1-2, and the cycle-1 blocker N1 (U+2800 joining words that are mixed with invisible characters). The diff was verified independently with `git diff c4d48ad1 f4c3e2fd -- src/`. Changed source paths are src/autotester/agents/guards.py and src/autotester/schema/crawl.py, plus tests/test_agent_write_guard_gaps.py and the qa manifest and verdict. core/ and stages/ are unchanged from base. sha256 prefixes at the candidate: guards.py 1cb1352f52bf9111, crawl.py 8602e2db91d53bbd, test file 9d6f0ae9d31ae6ae.

## Independent checks
Evidence is in .work/check-awgg-c2/ of this worktree and is not committed.
- Preflight. The interpreter is the main .venv, Python 3.11.16. The import origin is this worktree's src (preflight.out).
- pytest. test_agent_write_guard_gaps, test_never_click_destroy, test_never_click_destroy_2, test_agent_tools, test_agent_destination_seam, test_browser_use_guard and test_explore_safety: 477 passed, exit 0 (pytest.out, pytest.exit).
- ruff on guards.py, crawl.py and the new test file: All checks passed, exit 0 (ruff.out, ruff.exit).
- doctor, via `from autotester.cli import app; app()`: clean, with advisories only, exit 0 (doctor.out, doctor.exit).
- Targeted adversarial probe, base vs candidate. targeted.py produced 108 names. t-base.json and t-cand.json hold the results and t-cmp.out the comparison.
- Own generated differential corpus, base vs candidate. gen.py used seed 20261016 to mutate 47 words, producing 6,939 names. It uses 20 hidden code points, Zs/NBSP/tab, 18 punctuation marks, Cyrillic lookalikes and case swaps. The names were run through the full `write_policy_refusal` path at all 3 tiers (c-base.json, c-cand.json, c-cmp.out).
- Performance check (perf.py, perf.out).

## Findings
- N1 is closed. These names are now refused under READ_ONLY, although base allowed them: `De<ZWSP>lete<ZWSP>i<ZWSP>tem`, `De<CGJ>lete<U+2800>item`, `Sa<CGJ>ve<U+2800>draft`, `Cancel<U+2800>subscri<CGJ>ption`, `Sub<VS16>mit<U+3164>form`, `Can<ZWSP>cel<ZWSP>sub<U+2800>scrip<CGJ>tion`, `De<ZWSP><U+2800>lete`, `De<U+2800><ZWSP>lete` and `Re<U+3164>move<U+2800>it`. Cycle-0 and cycle-1 family names stay refused, as do the fillers inside words and blank-only names (U+2800, ZWSP+U+2800, CGJ+U+0301).
- Run cap. Names with exactly 4 joints are read and refused when destructive (`P<B>a<Z>y<B>n<Z>ow`, `De<B>lete<B>my<B>old<B>item`). A name with 4 joints and benign text (`Vi<Z>ew<Z> m<Z>o<Z>r<Z>e`) stays allowed. Names with 5 joints are refused as "too many places", including the benign `H<Z>e<Z>l<Z>p<Z>m<Z>e`. That refusal is fail-closed.
- Leading and trailing hidden runs. Every probed edge placement of Delete and Save stays refused.
- Zs characters. `De<NBSP>lete`, `De<U+3000>lete`, `De<U+2007>lete`, `De<U+202F>lete` and `De<U+2009>lete` are allowed by both base and candidate. Base did not refuse them either, so this is not a regression. They render as a visible gap. `Cancel<NBSP|U+3000|U+2007>subscription` and `Delete<NBSP>item` are refused by both.
- Intervening words. With 3 words between the verb and the object, the name is refused (`Cancel my current premium subscription`). With 4 words, it is allowed at every tier (`Cancel your current premium plus subscription`, `Close my old shared family account`, `Cancel a b c d subscription`). That matches the declared bound and is documented here.
- Punctuation. Under READ_ONLY, an em dash, en dash, `:`, `,` and `(...)` between the verb and the object are now refused. Base already refused `-`, `.`, `/` and `_`. `De-lete`, `De.lete`, `De<U+00B7>lete`, `De<U+2022>lete` and `De<Z>-<Z>lete` are allowed by base and candidate alike, because they show visible punctuation.
- Lookalikes. Capital Cyrillic (`<U+0421>ancel subscription`, `D<U+0415>LETE`) is now refused.
- Monotonicity. 0 regressions across the 108 targeted names and the 6,939 corpus names at all 3 tiers. ALLOW_WRITES refusal text is byte-identical to base for every corpus name. TEST_ACCOUNT has 119 added refusals and none removed, all from the widened membership and auto-renew deny phrases. That is the intended unit change, plus the declared crawl-ordering effect. By construction, READ_ONLY matches base's two readings and adds extra readings plus fail-closed early returns. The commit-name check uses the superset.
- Performance. A 197-character name with 4 runs gives 18 readings and takes 11.1 ms per call. A 5,000-character plain name takes 22 ms. `cancel ` repeated 300 times takes 11.7 ms. The new patterns `(?:\w+ ){0,3}` and `auto ?renew\w*` are bounded and unambiguous, so there is no ReDoS shape.
- One concept, one place. Hidden characters are detected with `is_ignorable_char` from core/redact_wrap, plus a single U+2800 constant, `_BRAILLE_BLANK`. `_CONFUSABLE_TABLE` and `normalise_label` are reused. No other table defines U+2800 in src.
- Bypasses found: none.

## Residual advisories (non-blocking)
- These were already present at base, so none of them is a regression. Private-use and unassigned code points that render as nothing or as tofu are not treated as hidden. The lookalike table is small. Crawler-side `deny_reason` does not treat punctuation as a separator. 4-word gaps are allowed.

## Budget
- Approved escalation: ORCH hub, one finite extra cycle of 600 s active.
- Actual cycle-2 checker active time: about 1,100 s. That includes command waits, mostly Python import time of 1 to 2.5 minutes per process on the contended machine.
- The 600 s escalation was exceeded by about 500 s. Cumulative checker time is about 2,931 s against 1,330 s of maker time (ratio 2.20).
- Tokens: cycle-2 actual is unknown, with a debit allocation of 90k.
- The phase assess gate was run only at finalization, not at every phase. That is a process miss and is recorded here. The gate returned NEEDS_EXTRA_REVIEW, exit 2 (metrics-final.json, assess-final.out).
- This breach and the ratio miss are recorded and not waived. No required check was dropped. The PASS rests on complete evidence, not on budget.
