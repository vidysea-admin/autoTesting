# Manifest - agent-write-guard-gaps

**Status:** ready-for-check
**Fix cycle:** 0
**Base SHA:** c4d48ad109f1ef77f73ee9172866cc5feeca7063
**Candidate SHA:** the commit carrying this manifest (git log -1 on branch worktree-agent-a1af8a18cb4bcb723)
**Issues addressed:** ISS-t179b-hg1-1, ISS-t179b-hg1-2 (AT-1017, AT-1018)

## What changed
- `src/autotester/agents/guards.py`: under READ_ONLY only, a click name that is blank after NFKC and removal of whitespace/Cc/Cf and filler code points (U+2800, U+115F, U+1160, U+3164, U+FFA0) is "unnamed control"; fillers inside a name are read as spaces before matching. ALLOW_WRITES path unchanged.
- `src/autotester/schema/crawl.py`: `DEFAULT_DENY_PATTERNS` gains close/cancel + account/subscription/membership (not "... settings"). Deny-list is already off under ALLOW_WRITES. Deactivate/terminate were already present. Close/cancel/deactivate/terminate account is already refused at all policies by `account_destroy`; the subscription forms were the real gap.
- Tests: `tests/test_agent_write_guard_gaps.py` (new), parametrized over each code point and phrase plus ALLOW_WRITES regression.

## Consumers
`guards.write_policy_refusal` (agents/tools.py, agent_actuator, browser_use_backend); `DEFAULT_DENY_PATTERNS` also read by the crawler (`explore_safety.deny_reason`, `is_destructive`) under non-ALLOW_WRITES policies.

## Required checks
pytest on tests/test_agent_write_guard_gaps.py test_never_click_destroy*.py test_agent_tools.py test_agent_destination_seam.py test_browser_use_guard.py test_explore_safety.py (393 passed); ruff on changed paths clean; autotester doctor clean.
