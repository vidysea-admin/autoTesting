# GATE ANSWERED - run approvals for the T-145 live crawl and the T-154 adversarial pass

**Opened:** 2026-10-10 (D-081 item 3). **Decider:** Umesh. **Status:** ANSWERED. Asked once; this file is the record.
**Blocks:** T-145 (live bounded crawl of pathlynks.vidysea.com with the PATHLYNKS_USER_* test account) and T-154 (bounded adversarial pass on the same target). T-154 is no longer held (supersedes the 2026-09-27 hold in `docs/plan.md`).

Question: may the maker mint the signed per-run RunApproval rows (D-018)? Options: (A) full approval; (B) ask per run.

Umesh: "full approvaal hai".

Scope of the answer: authority for the maker to mint each row. Each run still writes its own signed row naming target and scope (D-052); the approval does not replace the row. Write tier stays as `qa/gates/write-policy-tier.md` (ALLOW_WRITES).

Answered: 2026-10-10 - A (full approval; maker mints per-run rows) - D-081
