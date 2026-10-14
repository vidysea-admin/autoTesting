# Verdict - approval-revoke

**Verdict:** PASS
**Cycle checked:** 1
**Commit:** 6ce80275

## Findings
- (a) Forged/unsigned/edited/other-key revocations: is_valid False (HMAC, constant-time, key required). No DoS by forgery. Verified by probe.
- (b) HMAC binds approval_id but NOT the project slug. Isolation holds because each revocation file is per-project and approval ids are content-addressed over a payload including project; a signed row copied between projects only matters on an id collision. Advisory: bind slug.
- (c) All readers (guards, explore_consent, orchestrate_gate, schedule_wiring, adversarial, video_review, UI cards, scripts/check_crawl_approval.py) go through ProjectStore.list_approvals; none read approvals.jsonl directly except the revoke CLI's existence check. No bypass.
- (d) Replay against a different approval id: signature fails (probe).
- (e) extra="forbid" confirmed; malformed revocation row fails loud (fail closed).
- Residual: deleting a revocation line un-revokes (needs file write; same trust as approvals.jsonl).
- Tests 83 passed; ruff clean; doctor 1 violation identical to master (stale MAP.md); merge-tree clean.
