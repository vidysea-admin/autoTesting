# HUMAN_GATE — live acceptance runs for T-136, T-169, T-206 (opened 2026-10-17T09:50Z)

**Question:** May the maker run headed-browser runs against production Pathlynks on this Windows host with the PATHLYNKS_* test account, under a signed `production: true` RunApproval (D-096)? And for T-136, which route to a non-empty AutoTester findings column?

**Why it blocks:** facts in .work/facts-a1.md and .work/facts-a2.md.
- T-136: `scripts/check_acceptance_comparison.py pathlynks` exits 1. The stored trial (run-01M4KRJXJ652T8BCHRF2M7CB5Q) has PASS 4 / FAIL 0 / INCONCLUSIVE 37, so there are 0 findings and the FP rate is unavailable.
- T-169: the local tests pass. The real-target run needs an isolated baseline, signed approvals and a headed browser.
- T-206: the rig is done (qa/verdicts/t206-rig.md). TA15/16/17 live evidence and qa/verdicts/t-206-g10-acceptance.md are missing.

**Options (T-136 route):**
(a) A new live graded run with ≥1 FAIL verdict, then `bench_from_run.py` (needs the signed production approval).
(b) Build a crawl-issue → findings converter (Umesh decides whether crawl issues count as findings).

**Also needed from Umesh:**
- Confirm that Karunn's "8 Oct Release Review" (D-094) is the 6 Oct Drive doc at .work/karunn-review-oracles-2026-10-07.md.
- Later: adjudicate false positives and sign the comparison verdict (AT-281).

**Answer format:** `Answered: <ISO> — approve live runs yes/no; T-136 route a|b; Karunn doc confirmed yes/no — <where>`
**Blocks:** T-136, T-169, T-206.


Answered: 2026-10-17T18:10:00Z — approve live runs yes; T-136 route a; Karunn doc confirmed no (not blocking) — Umesh, maker session chat ("tu autotester se test krwaa aur report ready krr, human ka mai validate kr lungaa"); qa/gates/umesh-decisions-2026-10-17.md
