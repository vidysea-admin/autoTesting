# Manifest — sdk-cause-contract

**Status:** ready-for-check
**Fix cycle:** 1
**Unit:** Narrow checker-owned I9/C5 compatibility clarification for safe SDK diagnostics.
**Branch:** codex/sdk-cause-contract
**Base commit:** 921a4ac5e8c8b8f77b1752bb285c82034ae2db26
**Owner authorization:** parent request to reconcile existing approved privacy/safe-error policy; no new approach.

## What changed
- `qa/contracts/ingest.md`: append-only I9 clarification. Safe category/diagnostic (or sanitized surrogate) satisfies attribution intent; raw secret-bearing original causes must not be chained/exposed. Raw context rendering is suppressed. Typed ProviderError and explicit MAX_TOKENS/truncation remain required, no JSON repair of truncation.
- `qa/manifests/sdk-cause-contract.md`: this packet.

## Source feedback and authority
Maker's exact feedback is preserved in its separate unit at `C:/Users/product/Desktop/autoTesting/.work/gemini-media-guard/qa/feedback-inbox.md`, section `Gemini media guard — I9 safe cause-chain conflict (2026-10-15)`. This unit does not rewrite or duplicate its tracked feedback path.
Original I9 requires cause chaining; core C5 prohibits secret-bearing model/log/artifact output. The addendum clarifies compatible implementation under C5 and D-101/D-102, not a new privacy exception or fallback rule. No decision log, unrelated contract, runtime, test, credential, dependency or enforcement change.

## Checks and compact fresh-review packet
Docs-only D-100 scope: `git diff --check` exit 0; historical-prefix assertion exit 0. No pytest/build/browser/model/secret read. Runtime traceback/privacy/MAX_TOKENS proof remains in separate gemini-media-guard unit and combined release checks; this unit claims no runtime PASS.
Review exact candidate against base, these two paths and I9/C5/D101/D102 only. Verify preserved original contract bytes, typed/sanitized diagnostic, raw-cause suppression, explicit truncation, unchanged polling/cache/timeout/fallback boundaries. Write `qa/verdicts/sdk-cause-contract.md` with authoritative Verdict, Cycle checked 1 and Reviewed SHA; no intended verdict supplied.
Maker prior active/token/cost usage unavailable (null), no efficiency ratio claim. Fresh docs checker bootstrap allocation: 60 active seconds/2500 allocated tokens (parent may adjust explicitly), scoped diff/structure only. Keep actual unknown token/cost as null and assess budget before review phases per checker skill.
