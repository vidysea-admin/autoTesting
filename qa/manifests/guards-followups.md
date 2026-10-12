# guards-followups

Status: ready-for-check
Fix cycle: 0
Issues: ISS-t179b-hg1-1, ISS-t179b-hg1-2
Branch: wave/guards-followups

- ISS-t179b-hg1-1: `_click_names` reads U+2800, U+3164, U+115F, U+1160, U+FFA0 as spaces (Cf and whitespace already handled), so such names are blank and refused as an unnamed control.
- ISS-t179b-hg1-2: `_COMMIT_NAME` in agents/guards.py gains close account, deactivate, delete account, remove account, cancel subscription, unsubscribe. explore_safety/crawler untouched.
- D-088 follow-up SKIPPED: master has no `Project.production` (require_approval already takes `production`). TODO comment left above `crawl_approval` in guards.py; pass `production=project.production` after d088-followups merges.

Tests: tests/test_agent_click_names.py (filler names refused, account-destructive refused, Home/Next/Search/Café/English/Close allowed). Per-file runs of read_only, click_names, credential_gate, destination_seam, tools pass; ruff and doctor clean.
