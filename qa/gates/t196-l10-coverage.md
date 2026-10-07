# HUMAN_GATE: T-196, L10 citation coverage over immutable history

**Opened:** 2026-10-07 by /maker. Source: T-196 build agent stop report (worktree `.worktrees/t196-citation-subjects`, master 2fae2504 merged, tree clean).
**Blocks:** wiring `check_citation_subjects` into `doctor.run` (T-196 reaching ready-for-check).

**Facts (measured with the held-back doctor patch applied, then reverted):** doctor exits 1 with 1599 violations:
1213 decision-citation-coverage plus 385 decision-citation-declaration. The inventory has 877 reviewed rows.
Most of the unreviewed remainder is in qa/manifests and qa/verdicts.

`qa/contracts/living-ledger.md` L10 requires every visible citation occurrence to have an independently reviewed inventory row.
That includes immutable history, and no automated inference is allowed. A maker therefore cannot close this: it may not self-classify the occurrences, and it may not edit verdicts or contracts.
Two early historical claims are already flagged as failing the What-only boundary, and L10 has no disposition for them.

**Options:**
- A: Dispatch independent reviewers for the ~1200 remaining occurrences, keeping L10 as written. This means hundreds of reviews of dead records.
- B: Have /checker amend L10 to add an immutable-history disposition. A sealed historical file gets one reviewed "sealed record" row with a reason. Doctor still fails on any new, changed or unreviewed occurrence. You also give a ruling on the two disputed historical claims.
- C: Keep the doctor wiring held until the review work is done.

**Recommendation:** B (from the build agent; the maker concurs).

**Answer format:** reply "t196: A", "t196: B" or "t196: C".

Answered: 2026-10-07T01:34:13Z — B — chat (Umesh): "logic badalte rehte hai, product evolve hota hai, purane ka acha part rakh kar later update kar sakte hai". Ruling on the 2 disputed historical claims still to be shown to Umesh.
