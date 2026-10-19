# Gate: T-206 TA17 - one signed approval row reused for two runs

Raised: 2026-10-19 by checker t206-modeD (verdict qa/verdicts/t206-modeD.md, commit fa18f30f on the live-t206 worktree).

Question for Umesh: the button run (run-01M5A1GY1VT5T4XA2V8NT831W1) and the scheduled run (run-01M5A66Z9RVXNE01E6Y2FZW6ZN) both used one human-signed production approval, appr_99ba814cd8df, whose scope names both the Test button and the schedule tick (valid to 2026-10-21T23:59:59Z). D-081 item 3 (docs/DECISIONS.md:2337) says "Each run still writes its own signed row", and TA17 says "one signed approval each". The code accepts any covering unexpired row (core/consent.py:204-249, 253-274) and run.json records which one was used.

- Option A (recommended by checker and maker): accept one scoped row covering both runs for TA17. Attribution is already per run in run.json. No re-run needed.
- Option B: require one signed row per run; sign two rows and re-run both (about 30 min plus Pathlynks traffic).

Blocks: TA17 PASS and the T-206 close-out.
