# Verdict (B — independent second check) — at347-352-356-redact-fold

**Date:** 2026-09-26 · **Head checked:** 0c56c5b (fix a95ca6a, base bb4be39) · **Cycle checked: 1** · **Issues addressed (claimed):** AT-347, AT-352, AT-356
**Independence:** a blind checker subagent that never read the primary verdict. The orchestrating checker reproduced the failing case itself before writing this file.

```
VERDICT: FAIL
SCOREBOARD: 22/22 whole-secret obfuscations caught (NFKD, combining marks, fullwidth, zero-width, reversed, HTML named/numeric/hex entities, percent x1/x2/x3, base64/base32/hex whole, case variants, whitespace-split); no false positive on ~53 KB of prose/JSON/data-URI/hash text (~0.27 s); FAILS the embedded mid-token encoded family the unit claims to cover
FAILURES:
- [AT-352 / AT-347] sev: high · an encoded credential embedded next to characters of its own encoding alphabet bypasses assert_no_raw_secrets (and contains_folded). _B64_TOKEN_RE / _B32_TOKEN_RE / _HEX_TOKEN_RE in core/redact_fold.py match greedily across the neighbours, so the single oversized run fails to decode and the secret is never recovered. The unit's own docstring claims to "scan for base64/base32/hex-shaped runs inside a larger string". · fix: when a whole-run decode fails, also try the sub-runs, bounded by the encoded length of each declared secret (e.g. slide a window of exactly len(encode(secret)) and its padding variants over each run); or search for each secret's own encodings directly (compute b64/b32/hex of every declared secret, plus the 3 base64 alignment offsets, and do substring matching), which is exact, cheap and immune to adjacency. Add parametrized tests for tok_<b64>_end, prefix<b64>suffix, SECRET<b32>CODE and cafe<hex>beef. · issue: AT-352 (stays open)
CAPABILITY-ISOLATION: 3/3 own falsifying edits red on the named assertions (Mn strip removed; base64 decode removed; assert_no_raw_secrets reverted to exact-match), each green before in an own-venv copy
LIVE-BROWSER: not-applicable (changed paths: core/redact.py, core/redact_fold.py, tests/test_core.py, docs/MAP.md)
ISSUES-WRITTEN: none (AT-352 stays open with this evidence)
EXECUTOR: claude-sonnet-subagent (checker B: claude-sonnet subagent; reproduction: claude-opus-session)
EXPLANATION: The fold and whole-token decoding are solid, with no false positives. But ordinary variable-name-style adjacency (tok_…_end) defeats the embedded-encoding scan, and that is exactly the AT-352 shape this gate exists to close before a prompt reaches an external model.
```

## Orchestrator reproduction (own run, the c347b-1 copy, whose core/ matches the worktree)

Secret `Sup3rS3cretValue!42`, gate `assert_no_raw_secrets(text, [secret])`:

```
b64 isolated         caught (ValueError)
b64 tok_x_end        MISS
b64 prefix/suffix    MISS
b32 isolated         caught (ValueError)
b32 SECRETxCODE      MISS
hex isolated         caught (ValueError)
hex cafe..beef       MISS
```

## Also noted (low, not scored)

`ASCII_CONFUSABLES` was a public name in the pre-split `core/redact.py`. `from autotester.core.redact import ASCII_CONFUSABLES` now raises ImportError, although the manifest says every previous import still resolves. No current caller exists (grepped). Re-export it, or state the change.

## Status: FAIL (cycle 1)

## Cycle 2 — independent dual check (2026-09-26)

**Head checked:** 01f8867 (manifest f6b4649, base = `git merge-base HEAD origin/master`) · **Cycle checked: 2** · **Issues addressed (claimed):** AT-347, AT-352, AT-356
**Independence:** never read `qa/verdicts/at347-352-356-redact-fold.md` (primary). Read only this file's own cycle-1 content above. All reproduction run in own venv copies (`c347b2-1` = worktree HEAD, `c347b2-prefix` = pre-fix 010c2e2), using the worktree's `.venv`.

```
VERDICT: FAIL
SCOREBOARD: base64 alignment claim VERIFIED (3 offsets x 6 embedding lengths, all caught, both pre-fix MISS -> post-fix CAUGHT); hex isolated/upper/lower VERIFIED; base32 alignment claim FALSE -- zero offset handling exists, 4/5 embedding offsets MISS; hex case-folding INCOMPLETE -- genuine interleaved-case hex bypasses both doors even isolated; existing suite (5 redact tests) passes, ruff clean; no stale-cache or pre-search-normalisation defect found
FAILURES:
- [AT-352] sev: high (~97% confidence) · `declared_secret_encodings` in `core/redact_encodings.py` gives base64 a `_base64_alignment_needles` treatment (3 byte-offsets, dropping the boundary-mixed 4-char group at each end) but gives base32 NO analogous treatment -- it computes only `base64.b32encode(secret_bytes)` on the isolated secret, with zero offset handling, despite base32's 5-byte-to-8-char grouping having 5 alignment offsets (0-4), one more than base64's 3. When the secret is embedded inside a byte string that is base32-encoded AS ONE BLOB together with neighbouring bytes -- exactly the scenario `_base64_alignment_needles`'s own docstring names ("anything containing secret_bytes as a contiguous run") -- the isolated-secret needle fails to appear as a substring for any prefix length not a multiple of 5. Reproduced deterministically with secret `Sup3rS3cretValue!42`: prefix lengths 0 and 5 (offset 0) CAUGHT; prefix lengths 1, 2, 3, 4 (offsets 1-4) all MISS on both `Redactor.contains_folded` and `assert_no_raw_secrets`. This is the same "encoded credential embedded in a token" class of leak AT-352 exists to close, just left open for one of the three named encodings. The maker's own new tests (`tests/test_core.py:172,200`, `"SECRETb32CODE"`) do not catch this because they wrap an INDEPENDENTLY base32-encoded isolated secret in literal surrounding text (`f"SECRET{b32encode(secret)}CODE"`), which any substring search catches trivially since the literal wrap never touches the encoding stream -- it is not the same shape as the base64 regression tests, which correctly re-encode `prefix + secret` as one call. Fix: add `_base32_alignment_needles` mirroring `_base64_alignment_needles` with `offset in range(5)` and byte-group size 5; add a test that base32-encodes `("x" * k) + secret` for k in 0..4 as ONE call and asserts each is caught. · issue: AT-352 (stays open)
- [AT-352] sev: medium (~90% confidence) · hex needles are only `hexed` (lowercase, from `bytes.hex()`) and `hexed.upper()`; hex decoding is case-insensitive per nibble (unlike base64, which is correctly left case-significant per this module's own docstring), so a genuinely interleaved-case spelling of the same encoding -- one that differs from both the all-lower and all-upper forms -- matches neither needle. Reproduced with a secret whose hex has 3 letter positions: flipping alternating letter-positions' case (not just the whole string) produces a string that equals neither `hexed` nor `hexed.upper()`, and both `contains_folded` and `assert_no_raw_secrets` MISS it, isolated as well as embedded (`cafe<mixed>beef`). (My first attempt at this probe used a secret whose hex had only 1 letter position, where any single-letter case flip coincides with the all-upper form by construction -- that gave a false "caught" and would have been a false negative in this verdict; re-derived with a secret carrying 3 letter positions to get a genuine 3rd case-pattern.) Fix: casefold the hex needle and the corresponding slice of `text` specifically for the hex check (not base64/base32, which must stay case-significant).
CAPABILITY-COVERAGE:
- base64 adjacency, 3 offsets x 6 prefix lengths (0-5): pre-fix (010c2e2) MISS on `tok_<b64>_end` / `prefix<b64>suffix`; post-fix (01f8867) CAUGHT on all 6 -- claim holds.
- hex adjacency, literal-wrap shape (`cafe<hex>beef`): pre-fix MISS, post-fix CAUGHT -- holds for this shape; see FAILURE 2 for the case-mixing gap this shape never exercises.
- base32 adjacency: pre-fix MISS (cycle 1 had no per-encoding handling at all); post-fix CAUGHT only for the maker's flawed literal-wrap test shape, still MISS (red) for the real "secret embedded in a shared byte stream before encoding" shape at 4 of 5 offsets -- see FAILURE 1.
- `uv run pytest tests/test_core.py -k redact`: 5 passed, 41 deselected. `uv run ruff check` on the 4 touched files: all checks passed. Neither gap above is covered by any existing test.
- Stale-cache check (declare secret, add another, probe for the second): clean. `Redactor` has no incremental add API; `assert_no_raw_secrets` recomputes `widened` fresh from its `secrets` argument on every call, so nothing can go stale. A secret NOT in the declared set is correctly MISSED; both secrets declared together are both caught.
- Pre-normalisation check (does anything lowercase/NFKC text before the exact b64/b32/hex search): clean. `_contains_folded_secret` checks the raw-text exact-encoding needles first, before computing `fold_credential(text)` -- no folding happens ahead of the case-significant base64/base32 comparison.
- Diff scope: `redact.py` 142 lines, `redact_fold.py` 261 lines, `redact_encodings.py` 86 lines -- all under the 300-line cap; every function body in the three files is well under 50 lines. Nothing required was deleted or renamed.
- Also noted, not scored (~75% confidence, a pre-existing design choice extended into new code without being re-justified there): `MIN_FOLDED_LEN` (8) gates entry into `widened_secrets`, and cycle 2 reuses that same pre-filtered list to gate the NEW exact-encoding search, not just the pre-existing heuristic fold search. A secret whose folded form is under 8 characters gets zero protection from the exact base64/base32/hex needle search, even fully isolated (reproduced with a 5-char secret: raw isolated match still caught via `is_clean`'s floorless exact check, but its b64/hex encodings, isolated, are both MISS). The floor's documented rationale is heuristic-fold false positives on short strings; that rationale does not obviously extend to an exact substring search of a computed encoding, whose false-positive rate is not materially affected by secret length.
LIVE-BROWSER: not-applicable (changed paths: core/redact.py, core/redact_fold.py, core/redact_encodings.py, tests/test_core.py, docs/MAP.md)
ISSUES-WRITTEN: none (AT-352 stays open with this evidence; issue-ledger ownership stays with the primary checker)
EXECUTOR: claude-sonnet-5-subagent (checker B, cycle 2; reproduction in `c347b2-1` (HEAD 01f8867) and `c347b2-prefix` (010c2e2) copies, run under the worktree's own `.venv`)
EXPLANATION: The cycle-2 fix's central claim -- exact per-secret encoding needles beat the old greedy-decode scanner -- is correct and verified for base64 (all 3 alignment offsets, red before / green after) and for the literal-adjacency shape of hex and base32. But the fix is asymmetric: base64 got a from-first-principles alignment treatment (`_base64_alignment_needles`) that the module's own docstring reasons through carefully, while base32 -- named in the same claim, sharing the same "encoded credential embedded in a token" threat model, and mathematically requiring the same kind of treatment with 5 offsets instead of 3 -- got none at all. The gap is invisible in the maker's own tests because those tests wrap an isolated encoding in literal text rather than encoding the secret as part of a larger byte stream, which is adjacency-immune by construction and proves nothing about alignment. Hex has a smaller, second gap: its case-insensitive decoding means the two needles computed (all-lower, all-upper) do not cover the interleaved-case spellings that are equally valid hex. Both gaps let an encoded credential reach a model prompt undetected, which is exactly what B2 exists to prevent.
```

Cycle checked: 2
