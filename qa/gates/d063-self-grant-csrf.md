# HUMAN_GATE: D-063 self-grant and an unauthenticated local UI (P6)

**Opened:** 2026-10-06T20:30Z by /maker. Source: HUMAN_GATE-REQUEST in `qa/verdicts/d063-grant-budget.b.md`, in worktree `.worktrees/d063-grant-budget`, cycle 0.
**Blocks:** d063-grant-budget shipping (it does not block the fix cycle).

**Question:** Under D-063 a run mints its own LIVE_CASE approval from the account. The local UI has no auth.
So any page that can POST to it can edit a project's credential domains and then trigger a run that
types a credential. Do you accept that risk?

**Options:**
- A: Accept the risk as is. The UI is localhost only and is your machine.
- B: Add an Origin/CSRF check on the state-changing UI routes (credential edits and run triggers).
- C: Require a one-time human confirmation the first time a project's account-derived grant is used.
- B+C: Do both.

**Answer format:** reply "d063-csrf: A", "d063-csrf: B", "d063-csrf: C" or "d063-csrf: B+C".

Answered: 2026-10-07T01:34:13Z — B — chat (Umesh): Origin/CSRF check now; role-based auth later. Note from Umesh: after go-live the UI runs on a server URL, not localhost, so real auth becomes a follow-up requirement.
