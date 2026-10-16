# Manifest - agent-write-guard-gaps

**Status:** ready-for-check
**Fix cycle:** 1
**Base SHA:** c4d48ad109f1ef77f73ee9172866cc5feeca7063
**Cycle-0 SHA:** 4119e0a0c153f86ff06ab7dd2eb5f2ffec224640 (FAIL, verdict commit 0d0b5b68)
**Candidate SHA:** the head commit of branch worktree-agent-a1af8a18cb4bcb723 that carries this manifest
**Issues addressed:** ISS-t179b-hg1-1, ISS-t179b-hg1-2

## What changed (cycle 1)
- `agents/guards.py`: removed the duplicate `_FILLERS`; the READ_ONLY blank-name test and the click-name cleaning reuse `core.redact_wrap.is_ignorable_char` (plus U+2800). Names made only of combining marks (Mn/Me) are blank. Hidden characters inside a name are both dropped and read as a space before deny and commit matching (F1, F2, F3). ALLOW_WRITES keeps the old Cf-only cleaning (unchanged).
- `schema/crawl.py`: deny list covers close/cancel/end/stop + up to two words + account, subscription(s), membership(s), plan, auto-renew; also "turn off auto-renew". The "settings" exclusion applies only when the label ends with "settings" (F4).
- Side effect, declared: `explore_safety.is_destructive` reads the deny list at every policy, so under ALLOW_WRITES these labels now sort last in the crawl. Chosen: intended (safe direction, ordering only, nothing is blocked); pinned by a test.

## Consumers
`guards.write_policy_refusal` (agents/tools.py, agent_actuator, browser_use_backend); `DEFAULT_DENY_PATTERNS` via `explore_safety.deny_reason` and `is_destructive`.

## Required checks
pytest on tests/test_agent_write_guard_gaps.py, test_never_click_destroy*.py, test_agent_tools.py, test_agent_destination_seam.py, test_browser_use_guard.py, test_explore_safety.py; ruff on changed paths; autotester doctor.
