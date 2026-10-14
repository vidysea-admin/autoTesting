# Verdict - ta16-recall

Cycle checked: 1
Branch: wave/ta16-recall @ ddf68906
Verdict: FAIL (one mechanical fix, plus one flagged design issue)

## Findings
1. BLOCKING - doctor: branch reports 1 violation `stale-generated: docs/MAP.md`; master a172f38a is clean. The branch introduces it (new schema/stage modules not in the generated map). Fix: run `autotester map` and commit docs/MAP.md.
2. DESIGN (should fix) - matches.json is a hand-made item-to-oracle judgement. TA16 does not require a human to do it; it asks for k re-derivable from listed ids and the unconfirmed count. Existing code already carries the oracle-row link as `Finding.matched_bug_id` (schema/bench.py, used by acceptance_comparison._bug_rows and BenchTrial scoring). Review items should be turned into Findings and matched automatically (route/screen/timestamp + text against SeededBug.location/detect_hint, no model call or a provider-judged match), with matches.json kept only as an optional human override. Minimise human dependency.
3. Reuse: PASS. RECALL_BASIS and DENOMINATOR_PROVENANCE are imported, not copied. ReviewRecall/OracleRef are `extra="forbid"`-compatible: OracleRef explicit; ReviewRecall inherits Artifact - confirm Artifact base forbids extras.
4. Shape vs TA16: PASS. k of n (S1), missed_ids, unconfirmed_count, redaction_windows, not_reviewed, "measured on N videos", threshold "none", independent=false with "not independent" basis label. Minor: n is derived from the oracle severity filter; if the oracle's S1 count is not 13 nothing flags it.
5. Checks: tests/test_review_recall.py + acceptance comparison tests 18 passed; ruff clean; merge-tree with master clean.

## Cycle 2 (head 3372a11f)

Cycle checked: 2
Verdict: FAIL

- (a) No existing text matcher in acceptance_comparison, bench, known_bugs (grep for similarity/difflib/jaccard/overlap: none). Not a duplication. `Finding.matched_bug_id` is reused.
- (b) BLOCKING - the lexical matcher over-matches. Adversarial probe (3 oracle rows; items on the same screen with a different defect): 5 of 5 different-bug items matched an oracle row, e.g. "emails sent successfully with correct student name displayed" -> the placeholder-name bug; "charge shown once after retry works correctly" -> the duplicate-charge bug; an unrelated profile-page defect -> the phone-field bug. Cause: the item's screen text is in the matched string and equals the row's location, so location words alone plus 1 common word clear MIN_SHARED=3 / MIN_COVER=0.4. A false match inflates recall. Fix: exclude screen/location tokens from the overlap (match on seen vs detect_hint only), require a higher shared count, and add these pairs as negative tests; or only propose matches and leave confirmation to the override.
- (c) Partial - `match_method: "automatic lexical"` is in recall.json, but "untuned" and the thresholds (MIN_SHARED, MIN_COVER) are not. Add them to the output.
- (d) PASS - 21 scoped tests, ruff clean, doctor clean (MAP fixed), merge-tree clean, 13-row guard present.

## Cycle 3 (head cdc8f344)

Cycle checked: 3
Verdict: FAIL (narrow)

- Original 5 probes: 3 now unmatched; 2 still match (items 3 and 4: same-screen items repeating the row's key words, arguably ambiguous). Genuine true match still found.
- New defect-vocabulary probes: "duplicate entry shown twice on profile save after retry" -> matched the duplicate-charge row (WRONG); "error toast shown on login after submit" -> matched the checkout error-toast row (WRONG, the same flaw as the example you named); two contrived probes that quote most of a row's hint also matched (acceptable). Cause: the screen is now ignored entirely and only generic words (error, toast, shown, after, submit) carry the 3/0.6 test, so a different screen with the same defect vocabulary matches.
- Required fix: gate a match on screen agreement (item.screen shares a token with the row location) in addition to the hint overlap, or demand the row's rarest/most specific token (e.g. "charge", "phone"); add the login-vs-checkout and profile-duplicate pairs as negative tests. Alternatively mark auto matches as "proposed" and count only confirmed ones.
- Disclosure OK (method string "conservative, untuned"). Scoped tests 23 passed, ruff clean, doctor clean, merge-tree clean.

## Cycle 4 (head f13f43a5)

Cycle checked: 4
Verdict: FAIL (one residual over-match; otherwise much improved)

Probed on a 13-row oracle so the 20% distinctive-token cap is realistic.
- Earlier probes (5 original + 4 cycle-3): the login-vs-checkout and profile-duplicate pairs are now unmatched, and 3 of the originals stay unmatched. Still matched: 4 same-screen items that quote the row's own words (history list/placeholder, checkout retry/charge, duplicate charge amount, phone field slow/invalid). These are ambiguous, near-restatements, tolerable.
- True matches: exact, reordered paraphrase with extra words, and near-duplicate wording all match (B3, B3, B2). Recall is not trivially 0. Pure synonym ("double debit") is missed, acceptable.
- NEW over-match (blocking): same screen, different specific noun. Item "profile photo upload fails silently without message" matched the row "profile email update fails silently without message" (B5). The distinguishing noun (email vs photo) is not required: 0.6 coverage is met by the generic remainder (fails, silently, without, message).
- Fix: require the row's most specific token (rarest across rows, e.g. "email") to appear in the item, or require coverage 0.8 / >=3 distinctive tokens when the row's hint is short; add the photo-vs-email pair as a negative test.
- Scoped tests 26 passed, ruff clean, doctor clean, merge-tree clean.
