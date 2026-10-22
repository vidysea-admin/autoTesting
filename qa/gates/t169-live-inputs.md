# Gate: T-169 live acceptance inputs (2026-10-19)
Blocks: T-169. Source: .work/t169-live-report.md (agent run 2026-10-19, BLOCKED, 0/4 GR criteria run).
1. Isolated baseline: acceptance refuses a project that already has cases (real_acceptance.py:209-216, by design). Default: new isolated slug `pathlynks-acc` (empty), maker mints its signed approvals under D-081.
2. Teaching inputs for mode 1: one Pathlynks walkthrough video + one doc. Default: none -> run URL-only mode now, teaching mode when Umesh drops files in projects/pathlynks-acc/sources/.
3. AutoTester harness login: run_real_acceptance.py:83-84 prompts interactively (no non-interactive path). Default: Umesh runs that one command himself, or adds AUTOTESTER_HARNESS_EMAIL/PASSWORD keys to repo-root .env + a small unit to read them.
4. GR3 is a human verdict on the produced artifacts.

Answered 2026-10-22 (Umesh, chat) for row 4 and AT-281: Umesh himself is the expert human tester. He goes through the whole product end to end with his own judgement, finds every issue and gap, and checks whether every button and URL works or breaks, across best, worst and back-and-forth (to-and-fro) screen paths. He then checks, issue by issue, whether AutoTester found the same issue. Pass/fail is his judgement on that comparison; no numeric threshold is set in advance (confirms the 2026-09-27 answer on AT-281). Verbatim: "my intelligcence and mai saare product ko end to end go through krunga and saare issues and gap nikalunga ... aur firr jo jo issues mujhe aaynge vo dekhunga ki ai nikaal apay aya nhi".
Rows 1-3 keep their defaults. Run inputs (date, build id, minutes log, role credentials, CEO list) will be entered by Umesh himself ("ye sabb mai daalunga").
