# Immutable account generation independent check
VERDICT: PASS
Status: PASS
Cycle checked: 0
Reviewed SHA: f1b345aa02f8e6673c3fc589239944ebb24f638e
Source SHA: e75b6ccbe64ef2b3cbd9e78068fc2397610091c3
Base SHA: ac1efde173d4dc1d5fe8259f30888655a0072f08

Independent scoped review of eight owned paths found the random generation allocated only on creation, transactionally migrated once, uniquely indexed and update-trigger protected; password resets preserve it. Strict schema binding and current enabled-account lookup reject legacy, mismatched, foreign-root and disabled identities. Missing-store reads do not create a store. Profile disappearance returns safe409. No queue, SMTP or M2 certified.

Authenticated reused evidence: cycle2 raw SHA256 logs, before/after receipts, Python executable/version, dependency/environment inventories, lock/harness/spec hashes; all1043 root/copy inventory files complete and matching. Git clean against source establishes declared checkout representation; raw logs were never normalized. Green17 and all3 attributable named red/restored proof chains reconstructed independently. Initial checker git argument-length failure was corrected using folder selectors; no pytest ran in that attempt.

Independent runtime: compatible preflight successful after one preserved sandbox tempACL denial and one standard escalated retry. Exact commands and output hashes in checker-cycle0/receipt.json; initial denial in receipt-denied.json. Focused run: fixed-clock ID replacement, legacy migration stability, unbound/invalid preference3 parameters, plus independent disabled-account/foreign-root guard:6 passed. Runtime command8.828s; preflight0.281s (denied0.265s). Final raw authentication repeated successfully before verdict.

Evidence: qa/evidence/account-generation/checker-cycle0/ and qa/evidence/account-generation/cycle2/. Guard source and unfiltered logs retained. Integration still requires combined pytest, repository Ruff/doctor and generated-map freshness. This PASS covers only this prerequisite candidate.

Accounting: bounded bootstrap180s/6000 allocated tokens; readiness30/1000, source/runtime110/3500, prerequisite closure10/700, finalization30/800. Maker/checker actual active seconds, tokens and cost unknown; no10% efficiency claim. CPU queue/wait excluded; only command durations measured. Runtime launch2026-10-15T12:53:34Z; retry12:53:45Z. Unknown phase overhead remains null and allocations remain conservative debits. ISSUES-WRITTEN: none.
