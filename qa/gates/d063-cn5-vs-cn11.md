# HUMAN_GATE: CN5 vs CN11, account-derived rows in the human fall-through (P5)

**Opened:** 2026-10-06T20:30Z by /maker. Source: HUMAN_GATE-REQUEST in `qa/verdicts/d063-grant-budget.b.md`, cycle 0.
**Blocks:** d063-grant-budget shipping.

**Question:** A run looks for an approval row that matches its (project, kind, target). Should that
match be allowed to land on an account-derived row that was minted for a different case set, such as
a run that uses no credentials at all? Or should account-derived rows be excluded from that
fall-through, so that each one covers only the run that minted it?

**Options:**
- A: Exclude them. An account-derived row covers only the case set it was minted for (stricter; matches CN5).
- B: Allow it. Any (project, kind, target) match counts (current code).

**Answer format:** reply "cn5: A" or "cn5: B".

Answered: 2026-10-07T03:17:22Z — B, widened — chat (Umesh): "agar credentials hai tho run krroo, approved maano … baar baar approval nhi chahiye. credentials de denaa sabse bada approval hai". Provisioned credentials for a project are the standing run approval; no per-run human approval. Recorded as D-068.
