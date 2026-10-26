# Checkpoint - d109-claim-admin (cycle 0, coordinator A)
Code 4f26d490, head 304ccfc9 (head differs from code SHA by the manifest only). Tier L, auth.
Completed: claim file 8 passed + accounts + policy table = 23 passed; affected auth/route set 334 passed (19 files, 104s); ruff clean; doctor clean.
Falsifications (copies under scratchpad falsify/row1-5, baseline 8 passed): C1 drop claim form -> 3 red; C2 check outside write txn -> 1 red; C3 refusal 403->200 -> 3 red; C4 invert email test -> 1 red; C5 rename success audit action -> 1 red. All restored by discarding the copies.
Mode D: qa/evidence/browser-d109-claim-admin-2026-10-26-checker/report.json
Remaining: none.
