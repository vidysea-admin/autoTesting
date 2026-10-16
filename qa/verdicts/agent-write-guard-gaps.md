# Verdict - agent-write-guard-gaps

**Verdict:** FAIL
**Status:** FAIL
**Cycle checked:** 1
**Reviewed SHA:** 5dbbe33cfebac0b8f0cf48388128184a45244416 (base c4d48ad109f1ef77f73ee9172866cc5feeca7063, branch worktree-agent-a1af8a18cb4bcb723)
**Prior cycle:** cycle 0 FAIL at 4119e0a0c153f86ff06ab7dd2eb5f2ffec224640 (verdict commit 0d0b5b68; findings F1-F4 kept in git history)

## Scope
ISS-t179b-hg1-1 (invisible blank click names under READ_ONLY) and ISS-t179b-hg1-2 ("Close account"-style phrases under READ_ONLY). The diff was verified independently with `git diff c4d48ad1 5dbbe33c`. Changed paths: src/autotester/agents/guards.py, src/autotester/schema/crawl.py, tests/test_agent_write_guard_gaps.py and the qa manifest and verdict. sha256 at the candidate: guards.py dac593ba..f9e2, crawl.py ace41f6a..a522, test file b2aa711c..faa.

## Independent checks (evidence in .work/check-awgg-c1/ of this worktree, not committed)
- preflight: PREFLIGHT_OK. The venv is Python 3.11.16 and the import origin is this worktree's src (preflight.out).
- pytest on 7 files: test_agent_write_guard_gaps, test_never_click_destroy, test_never_click_destroy_2, test_agent_tools, test_browser_use_guard, test_explore_safety and test_agent_destination_seam. Result: 430 passed, exit 0 (pytest.out, pytest.exit).
- ruff on the 3 changed source and test paths: All checks passed, exit 0 (ruff.out).
- doctor: clean (advisories only) and exit 0 on both the candidate and the base tree. The base tree came from `git archive` at c4d48ad1, and the import origin was checked for each run (doctor-cand.out, doctor-base.out). `python -m autotester` has no `__main__`, so doctor was run through `autotester.main()` with argv `doctor`.
- Adversarial probe: probe.py, run on the candidate (probe.out) and on a base src copy (probe-base.out). The per-name comparison is in cmp-base.txt, cmp-cand.txt and cmp.diff. A targeted regression probe, regress.py, was also run on base and candidate (regress-base.out, regress-cand.out).

## Cycle-0 findings re-run
- F1: CLOSED. All 46 probed blank-only code points are refused under READ_ONLY as "unnamed control". They are U+034F, U+FE00, U+FE0F, U+E0100, U+180B, U+180F, U+17B4, U+17B5, U+2065, U+0301, U+16FE4, U+FFF0-FFF8, U+E0FFF, U+2800, the Hangul fillers, the tag characters and all the Cf characters. Mark-only combinations (U+0300+U+0301, U+3164+U+0301, space+U+20DD) are refused too. `is_ignorable_char` returns True for every Default_Ignorable code point probed. U+2800 and U+0301 are False, and the guard covers those itself.
- F2: CLOSED. `_FILLERS` is gone and the guard imports `core.redact_wrap.is_ignorable_char`. Doctor is clean.
- F3: the cycle-0 names are CLOSED. "De<U+115F>lete", "Del<U+034F>ete", "Dele<U+FE0F>te", "Del<U+180B>ete", "Sa<U+115F>ve", "Purch<U+034F>ase" and "Sub<U+FE0F>mit" are all refused, along with the tag, VS17 and U+17B4 variants. A new bypass of the same class is listed under N1 below.
- F4: CLOSED for the required forms. Determiner, plural and adjective forms, stop/end, plan, auto-renew and "turn off auto-renew" are all refused. So are the full-width, newline/tab, NBSP and lowercase-Cyrillic forms.

## Findings (FAIL)
N1 - Proven READ_ONLY regression against the base, introduced by this change (blocking). `_click_names(strict=True)` now treats U+2800 and the Hangul fillers as hidden, so they are dropped in the "drop" reading. Before the change, U+2800 survived NFKC and acted as a regex word boundary. As a result, a Cf character inside a word combined with a U+2800 word separator was REFUSED at the base and is ALLOWED at the candidate:
- 'Pur​chase⠀now'
- 'De​lete⠀item'
- 'Sub​mit⠀form'
- 'Sa​ve⠀draft'
- 'Pa​y⠀now'
- 'Unsub​scribe⠀now'

Source: regress-base.out vs regress-cand.out. The same mixed shape built from non-Cf hidden characters is ALLOWED at both base and candidate. That is the F3 class this cycle claimed to close: 'De͏lete⠀item', 'Can͏cel⠀plan', 'Cancel⠀subscri͏ption', 'Sa͏ve⠀draft', 'Sub️mitㅤform' and 'Cancelㅤmember​ship'. Root cause: the two readings use one rule for every hidden character, either drop all of them or space all of them. A word-joining invisible character and a word-separating visible blank need different readings in the same name. Fix direction: read visible blanks (U+2800, U+115F, U+1160, U+3164, U+FFA0) as a space in BOTH readings, and drop or space only the zero-width ignorables. Alternatively, add a mixed reading. Add these names as tests, including the six base-refused ones.

## Advisories (not blocking on their own)
- More than 2 words between verb and noun are ALLOWED: "Cancel my current premium subscription" and "Cancel your Premium Plus subscription". Punctuation that is not a separator also passes: "Cancel: subscription", "Cancel, subscription", "Cancel—subscription", "Cancel (subscription)" and "Cancel 'subscription'". The pre-existing `\bcancel subscription\b` has the same gap, because normalise_label folds only `-_./+|`. Consider widening the gap to about 4 words and adding `:,;()'"` and the dashes to the separators.
- Capital Cyrillic homoglyphs are ALLOWED ("Сancel plan"). `_CONFUSABLE_TABLE` is applied before casefold and maps lowercase only, so this is pre-existing and also open at the base. Macron "Delēte" is visible, so it is out of scope.
- False positives in the safe direction under READ_ONLY and TEST_ACCOUNT (crawler deny_reason too): "Close account menu", "Close this account menu", "Close plan details", "Close subscription details", "End of plan" and "Close the plan comparison" are now refused. This is acceptable for a fail-closed tier: it costs a little coverage and blocks nothing destructive. "Close", "×", "✕", "X", "Close dialog", "Close menu", "Cancel", "Back", "Plan your trip", "Subscription details", "Membership benefits", "View plan", "Change plan", "Stop video", "Close account settings" and "Cancel and go back" all remain allowed.
- Test weakness: the SAFE list in tests/test_agent_write_guard_gaps.py has the literal string "00d7", not "×". The multiplication-sign close button is not actually tested. It passes in the probe.
- ALLOW_WRITES: guards output is identical between base and candidate for all 20 probed names (cmp.diff shows no ALLOW_WRITES rows). The only ALLOW_WRITES change is the declared `is_destructive` ordering ("Cancel membership", "Close subscription", "Cancel plan" and "Close this account menu" now sort last). That is declared, pinned by test_is_destructive_reads_deny_list_at_every_policy, and accepted.
- The TEST_ACCOUNT tier's crawler deny_reason widens the same way as READ_ONLY. The manifest names deny_reason as a consumer, so this is in scope.

## Required to pass
Close N1: no READ_ONLY name refused at the base may be allowed, and the mixed invisible-in-word plus visible-blank-separator shapes must be refused. Add tests for the listed names. Fix the "00d7" test literal.

## Independent vs reused
All evidence was produced independently by this checker at 5dbbe33c. No maker receipts were reused. The maker's test-count claim was not relied on.

## Accounting
Maker usage is self-reported and unverified: about 184k actual_total tokens and about 1330 s across both cycles. The standing escalation applies (Umesh CLAUDE.md, 2026-10-16): the per-cycle cap is 1.0x maker tokens and 433 s. The cumulative limits are 945 s and 284,000 tokens, which include the cycle-0 debit of 512 s and 100k tokens. The cycle-1 review phase ran from epoch 1792150309 to 1792151628, 1319 s with no excluded waits. That includes about 120 s for a first probe run that hung on cp1252 stdout, 68 s of pytest and two doctor runs. Time is BREACHED: the cumulative checker time is 1831 s, a 1.38x active-time ratio, against a 0.10 target. The breach is recorded, not waived, and the assess result is NEEDS_EXTRA_REVIEW (exit 2). Host token usage is not exposed, so tokens are null and only a 120k debit is recorded. Metrics: .work/check-awgg-c1/metrics-phase1b.json, assess-phase1b.out, metrics-final.json and assess-final.out.
