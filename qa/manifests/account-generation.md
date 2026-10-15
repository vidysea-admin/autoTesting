# Immutable account generation — notification consent prerequisite

Status: checked-PASS
Fix cycle: 0
Risk: high (account identity and persisted consent; no external delivery)
Base: ac1efde173d4dc1d5fe8259f30888655a0072f08
Source candidate: e75b6ccbe64ef2b3cbd9e78068fc2397610091c3
Branch: codex/account-generation

## Problem, contract and consumer map

SQLite can reuse a deleted user's numeric ID. Numeric ID plus creation time cannot establish
account continuity: a replacement under a fixed clock can otherwise inherit old report-email
consent. This unit adds a random, stable 128-bit generation to each account and binds M1
NotificationPref to that generation. Legacy unbound consent deliberately becomes default-off.

AU account/session boundaries and TT8 own-profile consent remain authoritative. Existing
signup/bootstrap -> auth DB -> User consumers retain their roles and session behavior. Profile
-> preference store resolves the current enabled account itself; submitted identity fields are
not trusted. Schema shapes remain strict Pydantic models; atomic preference storage is reused.
No contracts, queue/caller, SMTP transport or parked M2 implementation are changed.

## Exact source ownership

- auth/db.py: random generation factory, transactional one-time legacy migration, unique index,
  and DB trigger rejecting generation changes.
- auth/accounts.py and schema/auth.py: allocation on new account only and typed User exposure.
- schema/delivery.py and store/notification_prefs.py: typed binding, fail-closed reads for legacy,
  malformed/mismatched/missing identity, current-account binding on consent writes.
- ui/routes_profile.py: account disappearance returns a safe 409.
- tests/test_account_generation.py plus one fixture adjustment in test_notification_profile.py.

## Immutable evidence

qa/evidence/account-generation/cycle2/binding.json binds exact base/source, executable hash and
version, lockfile, dependency and controlled environment inventories, and raw harness/spec
hashes. Complete src/tests/scripts/config inventory contains 1,043 files. Every child command
has a before snapshot, after receipt, actual import/runtime/dependency marker and hashed log.

- control.log: import and scratch preflight, changed-file AST/size rules and eight-path Ruff green.
- green.log: exact selection in spec.json collected 17 and passed 17 in 6.96 seconds.
- reuse.json: original green source/copy/environment/runtime/harness unchanged before proofs.
- mutation-ledger.json: three distinct-risk mutations, unique anchors and applied byte hashes;
  each caused its named pytest failure, then exact bytes were restored and its node passed.
  Risks: entropy allocation under fixed clock, stale-consent rejection, DB immutability.
- readiness.py re-derived eight command receipts, logs, runtime identities and restoration;
  readiness.json records MAKER_READINESS_VALIDATED, not an independent checker verdict.
- Earlier root-level evidence preserves the initial mechanical lint stop; pytest never ran
  there. Cycle2 is the final candidate's successful packet.

Maker active seconds/tokens/cost: null (unavailable). Checker ratios unverified. Process wall
times must not be represented as active maker usage. No full suite, browser, model or SMTP run.

## Independent review and integration limits

Review the eight-file diff and sealed packet; independently probe fixed-clock ID replacement,
legacy migration stability and fail-closed consent. Reuse deterministic evidence where valid.
Only an independent checker may PASS. Parent release gates still require combined pytest,
repository Ruff/doctor and generated-map freshness on the integrated candidate.

Future notification enqueue must capture this generation and revalidate it at each attempt;
that queue seam and all SMTP M2 remain parked and outside this unit. Production delivery is
not certified. The generation column requires the updated account writer after migration;
rolling back to an older account-creation writer needs a separate compatibility decision.
