# HUMAN_GATE (ANSWERED) - t179a HG-1: may READ_ONLY mode click?

**Opened:** 2026-10-10 (verdict qa/verdicts/t179a-lead-tester-core.r1.b.md:37, in .worktrees/t179-lead-tester). **Decider:** Umesh. **Status:** ANSWERED.
**Blocks:** the READ_ONLY branch of agents/guards.py `write_policy_refusal` (refuses every CLICK/PRESS_KEY/SELECT/UPLOAD; blocked 483 of 1,120 benign rows such as Home/Next/search).

Question: under the READ_ONLY write tier, may the lead tester click, press keys, select and type (navigation-type interaction), or must it refuse all of them?

Answered: 2026-10-12 - Umesh (chat): "hai allowed" - READ_ONLY mode may click. The guard must not refuse benign interaction steps under READ_ONLY; build as a follow-up slice of T-179 (not part of the t179a cycle-2 check).
