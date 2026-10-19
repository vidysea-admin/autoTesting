# Gate: T-169 live acceptance inputs (2026-10-19)
Blocks: T-169. Source: .work/t169-live-report.md (agent run 2026-10-19, BLOCKED, 0/4 GR criteria run).
1. Isolated baseline: acceptance refuses a project that already has cases (real_acceptance.py:209-216, by design). Default: new isolated slug `pathlynks-acc` (empty), maker mints its signed approvals under D-081.
2. Teaching inputs for mode 1: one Pathlynks walkthrough video + one doc. Default: none -> run URL-only mode now, teaching mode when Umesh drops files in projects/pathlynks-acc/sources/.
3. AutoTester harness login: run_real_acceptance.py:83-84 prompts interactively (no non-interactive path). Default: Umesh runs that one command himself, or adds AUTOTESTER_HARNESS_EMAIL/PASSWORD keys to repo-root .env + a small unit to read them.
4. GR3 is a human verdict on the produced artifacts.
