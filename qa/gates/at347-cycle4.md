# GATE — at347-cycle4

**Opened:** 2026-09-26
**Blocks:** merging at347-352-356-redact-fold (AT-347, AT-352, AT-356), which is the credential gate before every model call
**Unit that stalled on it:** `at347-352-356-redact-fold`, with 3 of 3 fix cycles spent
**Evidence:** `qa/verdicts/at347-352-356-redact-fold.md` cycle 3 (a5118c4)

## The question in one line

Should the maker get a narrow cycle 4, scoped to a single test literal, beyond the 3-cycle cap?

## Why the cap was hit

- **Security fixes:** all three security fixes PASSed in cycle 3.
  - Fold-floor gating
  - b32 alignment
  - b32 lowercase
  - 0 false positives on 518 KB.
- **The one remaining FAIL is a test-integrity defect from the file split.** `test_fold_credential_keeps_precomposed_and_decomposed_accents_symmetric` moved into `tests/test_redact_obfuscation.py`. On the way, its `decomposed` literal lost the combining U+0301 (the file was NFC-normalised on write), so the test now compares a string with itself and can never fail.

## Options

- **A — narrow cycle 4 (checker recommends).**
  - Change: rewrite `decomposed` as an explicit escape (`"CAFE\u0301_QUILT_APIKEY_31"`) and add `assert decomposed != precomposed`.
  - Scope: that test only; no source change.
  - Checker's estimate: a re-check within minutes.
- **B — STALL.** Leave the unit unmerged and run the stall diagnosis. The three security fixes stay off master.

Answered: A — narrow cycle 4 (Umesh, 2026-09-26, via AskUserQuestion in the maker session). Scope: that one test literal plus `assert decomposed != precomposed`; no source change.
