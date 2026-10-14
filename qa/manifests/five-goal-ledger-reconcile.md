# Manifest — four stale issue rows reconciled

Unit: five-goal-ledger-reconcile
Contract: qa/contracts/core-invariants.md; qa/adapter.json
Policy-Version: proportional-verification/2026-10-10.9
Tier: S (historical issue metadata only)
Fix cycle: 1
Executor: integration coordinator; Umesh authorized normal override
Status: checked-PASS
Base code SHA: 26e6866140506745697bfeaa2d6739593e3395c1
Changed path: qa/issues.jsonl
Canonical verdict: qa/verdicts/five-goal-ledger-reconcile.md

## Change and limits

Exactly AT-112, AT-959, AT-875 and AT-855 change open to fixed, with fixed_date 2026-10-14
and a resolution explaining existing committed historical evidence. Original evidence and
all other row keys are preserved. No row changes to verified, no verified_date is added,
no new behavioral PASS is asserted, and no goal is closed.

AT-112: approval-prod-gate code be2f0bd3, checked-PASS cycle 2 and dual cycle-2 PASS verdicts.
AT-959: t200-schedule-wiring code 8b67fb04, checked-PASS and matching cycle-0 PASS.
AT-875: required-scrub repair 6d6bc318 and wiring 8b67fb04; t200b cycle-1 and wiring cycle-0
PASS. Untested missing-project fallback is expressly not waived.
AT-855: checker contract-authoring 1c52bf71 and amendment b85dbbd3 establish actual T-206
criteria. Proposed-header ambiguity does not establish owner approval or T-206 PASS.

## Verification requested

Independent checker confirms each cited commit is an ancestor of base/current HEAD,
matching historical manifest/verdict cycles, exactly four changed unique rows, allowed keys
only status/fixed_date/resolution, all unchanged rows byte-identical apart from line endings,
and preserved original evidence. Existing targeted static diff check reports no whitespace
errors and numstat 4 additions/4 deletions. No test, full suite, browser, lint or doctor run is
claimed by this metadata unit; repository gates remain owed on the final merged candidate.
