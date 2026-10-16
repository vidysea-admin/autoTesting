# Verdict - agent-write-guard-gaps

**Verdict:** FAIL
**Status:** FAIL
**Cycle checked:** 0
**Reviewed SHA:** 4119e0a0c153f86ff06ab7dd2eb5f2ffec224640 (base c4d48ad109f1ef77f73ee9172866cc5feeca7063, branch worktree-agent-a1af8a18cb4bcb723)

## Scope
ISS-t179b-hg1-1 (AT-1017: invisible blank click names not treated as unnamed under READ_ONLY) and ISS-t179b-hg1-2 (AT-1018: close/cancel account or subscription allowed under READ_ONLY). Diff verified independently: src/autotester/agents/guards.py (+_FILLERS, _blank_name, READ_ONLY branch in _click_refusal), src/autotester/schema/crawl.py (one DEFAULT_DENY_PATTERNS entry), tests/test_agent_write_guard_gaps.py (new), qa/manifests/agent-write-guard-gaps.md.

## Independent checks (evidence in .work/check-awgg/ of this worktree)
- preflight (review_budget.py): PREFLIGHT_OK, venv Python 3.11.16, import origin = worktree src (preflight.out).
- pytest test_agent_write_guard_gaps.py test_never_click_destroy.py test_never_click_destroy_2.py test_agent_tools.py test_browser_use_guard.py test_explore_safety.py test_agent_destination_seam.py: 393 passed, exit 0 (pytest.out, pytest.exit).
- ruff on the 3 changed source/test paths: All checks passed, exit 0 (ruff.out).
- doctor (uv run --no-sync, main .venv): clean, exit 0 (doctor.out).
- Red at base (base guards.py + crawl.py in an isolated src copy, autotester pre-imported from the copy): 17 failed / 30 passed, exit 1 (red-base.out). Tests bite.
- Mutation (READ_ONLY condition replaced with `if True`): 5 test_allow_writes_unchanged_for_fillers failures, exit 1 (red-mut.out). The ALLOW_WRITES regression test does exercise the policy split.
- Adversarial probe (probe.py / probe.out), all through guards.write_policy_refusal and explore_safety.deny_reason / is_destructive.

## Findings (FAIL)
F1 - AT-1017 not closed (proven). Under READ_ONLY these one-character names, all Unicode Default_Ignorable_Code_Point and drawn as nothing, are still ALLOWED as named clicks: U+034F (CGJ), U+FE00 and U+FE0F (variation selectors), U+E0100 (VS17), U+180B and U+180F (Mongolian FVS), U+17B4, U+17B5, U+2065. Lower confidence: a combining-mark-only name (U+0301, U+0300+U+0301) and U+16FE4 are also allowed. Refused correctly: U+180E, U+2060-2064, U+FEFF, U+00AD, U+115F, U+1160, U+3164, U+FFA0, U+2800, U+3000, U+200B, U+200E/F, U+202E, U+2066, U+061C, tag characters U+E0001/E0020/E0041, U+1BCA0, U+00A0.
F2 - One concept, one place. `_FILLERS` / `_blank_name` is a second definition of "invisible character". The canonical one is core/redact_wrap.py `_DEFAULT_IGNORABLE` / `is_ignorable_char`, and its AT-351 docstring records this exact miss (U+034F and FE00-FE0F are Mn, not Cf). The new set is narrower, and that is why F1 exists. Fix direction: reuse is_ignorable_char, plus U+2800, which is visible-blank So and not default-ignorable.
F3 - Fillers inside a name are read only as a space, never also dropped. The Cf characters get both readings in _click_names. So under READ_ONLY these render as the plain word and are ALLOWED: "De<U+115F>lete", "Del<U+034F>ete", "Dele<U+FE0F>te" and "Del<U+180B>ete". The commit-name check is evaded the same way: "Sa<U+115F>ve", "Purch<U+034F>ase" and "Sub<U+FE0F>mit". The deny-list bypass for U+115F, U+1160, U+3164 and U+FFA0 was handled inconsistently by this change. The others are pre-existing and belong to the same class.
F4 - AT-1018 residual phrase gaps under READ_ONLY (all ALLOWED): "Cancel subscriptions", "Cancel this subscription", "Cancel our subscription", "Cancel Premium subscription", "Stop subscription", "End membership", "Cancel plan", "Cancel auto-renew". "Close account settings now" and "Close account<U+2800>settings" are also allowed. Those two are ambiguous labels and acceptable. Refused correctly: Close account (already at base via account_destroy, confirmed), close  account, CLOSE ACCOUNT, Close my account, Cyrillic o/a lookalikes, Close-account, Close_account, NBSP/ZWSP/U+2800/U+3164 separated forms, Delete subscription, Unsubscribe, Cancel membership, Cancel your subscription, Cancel the membership.

## Observations (not blocking on their own)
- The "... settings" exclusion is moot for subscriptions. "Cancel subscription settings" is still refused by the pre-existing `\bcancel subscription\b`, which over-blocks a settings link (pre-existing behaviour). "Close account settings" is allowed.
- Crawler consumer: normal READ_ONLY navigation is not broken. "Close", "x", "X", "Close dialog", "Cancel", "Close menu", "Account settings" and "Next ->" all return deny_reason None.
- ALLOW_WRITES in guards is unchanged (probed and mutation-proven). The manifest's "deny-list is already off under ALLOW_WRITES" is incomplete, though. `explore_safety.is_destructive` reads deny_patterns at every policy, so under ALLOW_WRITES "Cancel membership" and "Close subscription" now count as destructive, and `destructive_last` ordering changes. That is the safe direction, but it is untested and undeclared.

## Required to pass
Close F1 and F2: reuse core.redact_wrap.is_ignorable_char (plus U+2800) for the READ_ONLY blank-name test. Close F3: give the fillers/ignorables the same drop-or-space two readings as Cf. Close F4 for at least the determiner/plural/adjective subscription forms ("cancel [any word] subscription(s)", "end membership"). Add tests for each.

## Independent vs reused
All evidence was produced independently by this checker. None of the maker's claims or receipts were reused. The maker's "393 passed" matched the independent run.

## Accounting
BOOTSTRAP_REVIEW (maker usage unknown; ratios unverified). Standing escalation applied (Umesh CLAUDE.md 2026-10-16) with finite limits of 480 s and 120,000 actual_total tokens. Review phase measured at about 442 s from 1792148755 to 1792149197 epoch. Finalization (verdict, commit, readback) was additional and pushes the total past 480 s, so the escalation is breached; this is recorded, not waived. Host token usage is not exposed, so tokens are null (debit only). Metrics: .work/check-awgg/metrics-phase1.json, assess-phase1.out, metrics-final.json.
