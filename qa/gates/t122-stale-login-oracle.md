# HUMAN_GATE — T-122 login case: stale oracle or real regression?

**Asked:** 2026-10-07 · **Unit:** T-122 (branch `wave/t122-first-login-run`, c265c19e) · **Owner:** Umesh

## Facts
- Logged-in run against production `pathlynks.vidysea.com/signin` with the PATHLYNKS_* test account
  **succeeded twice** (signed-in dashboard reached, Logout visible — evidence
  `qa/evidence/t122-first-login-run-2026-10-07/`, screenshot `04-step04-click.png`).
- The BEST login case `case_35b17ccece2d` step 4 asserts `visible_text: ['YOUR PROGRESS']`.
  The current dashboard does not show that text, so the real judge (gemini) returned FAIL.
- Changing the marker re-addresses the case id and `login_case_id` in tracked project data.

## Question
Was the "YOUR PROGRESS" section removed from the Pathlynks dashboard **on purpose**?

- **A (recommended if intentional):** stale oracle — re-author step 4 to assert a stable signed-in
  marker (the Logout control + the dashboard heading), update `login_case_id`, re-run, then check.
- **B:** not intentional — it is a real Pathlynks regression; keep the case as is, file it as a
  product bug for the Pathlynks team, T-122's C6 stays FAIL-by-design.

## Answer
Answered: 2026-10-07 — A — chat (Umesh): section removed on purpose; re-author the marker (D-072).
