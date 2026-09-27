# Verdict — at347-352-356-redact-fold

**Date:** 2026-09-26 · **Cycle checked:** 1 · **Checker:** claude-sonnet-subagent (primary; independent of `.b.md`)
**Base:** bb4be39 (merge-base with origin/master)

```
VERDICT: FAIL
SCOREBOARD: AT-347 and AT-356 mechanisms met; AT-352 (encoded spellings) NOT met — base64 embedded next to token-alphabet characters bypasses both doors
FAILURES:
- [AT-352 / B2] sev: medium→high (security gate) · _B64_TOKEN_RE = r"[A-Za-z0-9+/_-]{8,}={0,2}" (src/autotester/core/redact_fold.py:191) swallows adjacent `_`, `-` and alphanumerics into one greedy span; the whole-span decode fails, and the credential escapes BOTH Redactor.contains_folded (UI door) and assert_no_raw_secrets (model gate). Reproduced: `filename_<b64>.png`, `prefix_<b64>_suffix`, `prefix-<b64>-suffix`, `prefixXX<b64>YYsuffix` → BYPASS. Hex has a narrower form of the same flaw (`abc<hex>def`). · Fix: substring-match each declared secret's own precomputed encodings (b64 at its 3 alignment offsets, std + urlsafe, b32, hex upper/lower) instead of decoding greedy regex spans; or retry decode over shrinking windows. · issue: AT-352
CAPABILITY-COVERAGE: 8/8 rows reproduced (own copy c347a-baseline, 29 passed green-before; each mutation red on its named rows only; byte-identical after revert)
LIVE-BROWSER: not-applicable (changed paths: core/redact.py, core/redact_fold.py, tests/test_core.py, docs/MAP.md — no UI surface)
ISSUES-WRITTEN: none new (the finding stays under AT-352, open)
EXECUTOR: maker builder (checker: claude-sonnet-subagent)
EXPLANATION: The fold is real and well isolated: all 8 capability rows falsify cleanly, the public names of core.redact still import for every in-tree importer, the diff matches "What changed", and a 50 KB realistic corpus produced no false positives (~0.21 s/call, roughly linear). Raising, not warning, is contract-mandated (browser-and-secrets B2). But AT-352's own scope, base64, has a realistic bypass (an id-derived filename), so the cycle cannot close. The independent .b.md check reached the same finding by another route (b32/hex adjacency too) — fix both in one cycle.
```

## Security probes (primary)
ZWJ-separated caught · fullwidth caught · double-percent caught · split across newline caught · case variants caught · **base64 mid-word MISSED**. Delimiters outside the token alphabet (space, `:`, `/`, `&`, `=`) bound the match correctly.

## Re-run evidence
- `uv run pytest tests/test_core.py tests/test_secrets.py tests/test_ui_secrets_declaration.py tests/test_check_no_secrets.py -p no:cacheprovider` → 76 passed
- `uv run pytest tests/test_db.py tests/test_network_assertions.py tests/test_portal_persona.py tests/test_run_trace.py tests/test_source_adapters_drive.py tests/test_prompt_skills.py -p no:cacheprovider` → 56 passed, 1 skipped
- ruff: All checks passed · doctor: clean · redact.py 136 lines, redact_fold.py 277 lines
- Mutation rows (tests/test_core.py): combining 3 red · base64 2 · base32 2 · hex 2 · html-entities 4 · reversed 2 · double-percent 2 · gate-itself 9 red (UI door test stays green)
- Diff scope: `git diff bb4be39..HEAD --stat` → docs/MAP.md, manifest, core/redact.py, core/redact_fold.py (new), tests/test_core.py (+98/-0, additive). Nothing outside the manifest.

---

# Verdict — at347-352-356-redact-fold, cycle 2 (primary)

**Date:** 2026-09-26 · **Cycle checked:** 2 · **Checker:** claude-sonnet-subagent + orchestrator reproduction

```
VERDICT: FAIL
SCOREBOARD: the cycle-1 adjacency bypass is fixed for b64 (real neighbour bytes, offsets 0-5, and b64("user:"+secret) all caught) and for hex, and ASCII_CONFUSABLES is re-exported; AT-352/AT-347 still open on three gaps in the same mechanism
FAILURES:
- [AT-352 + AT-347 / B2, C5] sev: high · MIN_FOLDED_LEN also gates the exact-encoding search: Redactor.__init__ (redact.py:62-65) and assert_no_raw_secrets (redact.py:134-137) only pass secrets whose FOLDED form is ≥8 on to the encoding search, and _contains_folded_secret returns False when none qualify. A declared 8-char secret with one punctuation mark ("Zq7!kP2x" folds to 7) gets no encoding protection at all, even isolated. Orchestrator reproduced: isolated b64 → MISS on both doors (primary: 70/70 misses across 7 encodings × 10 contexts). · Fix: run the exact-encoding search for every declared secret, gated on the raw value's length or the needle's length rather than the fold floor (the exact search is not a heuristic widening, AT-002's floorless-exact principle). · issue: AT-352
- [AT-352 / B2] sev: medium-high · base32 is only ever uppercase (redact_encodings.py:82-83); lowercase b32 of any secret misses both doors in every context (40/40). Orchestrator reproduced: isolated lowercase b32 → MISS, uppercase → caught. · Fix: also add b32.lower() and the unpadded variants, as hex already does. · issue: AT-352
- [AT-352 / B2] sev: high (from .b.md cycle 2, ab60d4e; orchestrator reproduced) · b32 has no alignment handling: b32encode(prefix+secret) misses both doors at prefix lengths 1-4. · Fix: needles at all 5 byte offsets, mixed edge groups dropped, as for b64. · issue: AT-352
CAPABILITY-COVERAGE: 3/9 rows independently spot-checked (needle-list zeroing, ASCII_CONFUSABLES import) and reproduced; the other 6 rows are unchanged from cycle 1 (8/8 there), and test_core stays 46 passed in the checker's copy
LIVE-BROWSER: not-applicable (core/redact*.py, tests/test_core.py)
ISSUES-WRITTEN: AT-598 (double b64 and UTF-16 hex not covered), AT-599 (a needle split by a newline or MIME wrap is not caught; undisclosed)
EXECUTOR: maker (checker: claude-sonnet-subagent)
EXPLANATION: The precomputed-needle design is sound and fixes cycle 1's adjacency class (b64 alignment and the Basic-auth shape hold). But the fold floor was left in front of it, and b32 got neither case variants nor alignment offsets. False positives: 0 on a 121 KB corpus with secrets on both sides of the floor. Perf: about 0.24 s per call at 50 KB, roughly linear, dominated by the pre-existing _is_ignorable scan. Diff scope is clean: the token regexes and _decode_block are fully removed, every core.redact importer resolves, and files are 142/261/86 lines. The dual check's mixed-case-hex claim did not reproduce (the orchestrator's interleaved-case hex was caught).
```

---

# Verdict — at347-352-356-redact-fold, cycle 3 (final)

**Date:** 2026-09-26 · **Cycle checked:** 3 · **Checker:** orchestrator (checker seat), direct re-run (RAM 0.27 GB ruled out a second subagent)

```
VERDICT: FAIL
SCOREBOARD: all 3 cycle-2 security findings are FIXED and verified; one 4c defect in the test split: a moved AT-351 regression test was made vacuous
FAILURES:
- [4c / AT-351 regression] sev: medium · The split moved test_fold_credential_keeps_precomposed_and_decomposed_accents_symmetric into tests/test_redact_obfuscation.py, but its `decomposed` literal lost its combining acute: it was "CAFE\u0301_QUILT_APIKEY_31" (E + U+0301) at 4ca4721 and is now "CAF\xc9_QUILT_APIKEY_31", byte-identical to `precomposed`. The test now asserts fold(x) == fold(x) and cannot fail. The old test_core.py had 5 combining characters; the three new files together have 4. It is the only moved test whose AST changed (all 18 moved names are present; AST-compared). · Fix: restore the decomposed spelling, written as an escape ("CAFE\u0301_QUILT_APIKEY_31") so no editor or tool can NFC-normalise it again, and assert `decomposed != precomposed` as a guard line. · issue: AT-351 (regression guard), AT-352
CAPABILITY-COVERAGE: not re-run this cycle (FAIL on 4c); the security behaviour was verified directly by the probes below
LIVE-BROWSER: not-applicable (core/redact*.py, tests)
ISSUES-WRITTEN: none new (the perf note is below, for the ledger at close-out)
EXECUTOR: maker (checker: orchestrator direct)
EXPLANATION: Security probes on HEAD 8081c32 (5 secrets × offsets 0-9 × b64/b64url/b32/b32-lower × 5 contexts, plus hex, HEX and b64("user:"+secret), both doors). The fold floor no longer starves the exact search: every isolated encoding of "Zq7!kP2x" is caught. b32 alignment and lowercase are fixed. Coverage boundary, stated so it is known: a raw secret of 7 or fewer characters gets no encoding protection by design (it stays exact-match-only, floorless per AT-002); an 8-character secret misses b32 only at alignment offset 1 (mod 5), where no pure 5-byte group exists (inherent to the prescribed technique, not an implementation defect); 9 or more characters has no misses. False positives: 0 on a 518 KB corpus (prose, UUIDs, sha256, base64 image data, random b32). Perf note: 518 KB with 5 secrets took 11.8 s for assert plus contains_folded, more than linear from the 0.27 s/50 KB claim; worth an issue at close-out. 4c otherwise clean: all 18 moved test names are kept (+7 new), and the redact_fold.py docstring change removes "already filtered to folded_value at least MIN_FOLDED_LEN" because this fix made it false, with the replacement text explaining why. Verify: 65 passed (the 3 test files), ruff clean, doctor has only the 2 known ledger-row-lost rows (the branch predates master 2d1858b). Files 144/123/292 lines.
```

This is fix cycle 3 of 3. The remaining defect is a one-line test restoration; everything the unit set out to fix now holds. What happens next (a human-approved cycle 4 or a gate) is the maker's protocol decision, per the cycle cap.

---

# Verdict — at347-352-356-redact-fold, cycle 4 (narrow, gate qa/gates/at347-cycle4.md answer A)

**Date:** 2026-09-26 · **Cycle checked:** 4 · **Checked commit:** f7b1eec (code), e99d424 (manifest) · **Checker:** orchestrator (checker seat), direct re-run

```
VERDICT: PASS
SCOREBOARD: the single cycle-3 failure is closed; all 3 cycle-2 security findings stay fixed (verified at cycle 3, no src change since)
FAILURES: none
CAPABILITY-COVERAGE: 2/2 rows reproduced (own copies, green before, named test red after), plus a cycle-3 control
LIVE-BROWSER: not-applicable (tests/test_redact_obfuscation.py only)
ISSUES-WRITTEN: AT-606 (perf, medium), AT-607 (coverage boundary, low) -- both on master b92ff77
EXECUTOR: maker builder (checker: claude-opus session)
EXPLANATION: The moved AT-351 test once again compares a real decomposed spelling (`"CAFÉ_QUILT_APIKEY_31"`, an explicit escape that survives NFC-normalising editors) against the precomposed one, and a new `assert decomposed != precomposed` guards against it collapsing again. The diff is 4 added lines and 1 replaced line in one test file, with no source change.
```

## Re-run evidence

- Bytes checked with `cat -A`: line 55 is the literal backslash escape `́`; line 52 `precomposed` is the UTF-8 `É`.
- `uv run pytest` (full, no -q): **1768 passed, 6 skipped, 32 xfailed, 0 failed** in 913 s, EXIT 0.
- `uv run ruff check src tests scripts`: All checks passed.
- `uv run autotester doctor`: 2 `ledger-row-lost` (AT-598, AT-599), only because this branch's ledger predates master's rows. Both rows exist on master and clear on merge.
- Diff scope: `git diff a5118c4..e99d424 --stat` touches only the test file (+4 -1) and the manifest. The one replaced line is the vacuous literal itself.

## Capability rows (own copies)

| row | edit | test | before | after |
|---|---|---|---|---|
| A | `redact_fold.py:206` `unicodedata.normalize("NFKD", stripped).translate(...)` -> `stripped.translate(...)` | test_fold_credential_keeps_precomposed_and_decomposed_accents_symmetric | 1 passed | FAIL: `assert 'café…quiltapikey31' == 'cafequiltapikey31'` (the fold-equality assert) |
| A-control | the same edit in a copy of cycle 3 (a5118c4) | same test | 1 passed | **still 1 passed**, proving the cycle-3 test was vacuous and cycle 4 fixes it |
| B | test line 55 `decomposed = precomposed` | same test | 1 passed | FAIL on the new `assert decomposed != precomposed` |

## Close-out notes

The issues this unit addresses (AT-347, AT-352, AT-356 and the rest named in the manifest) flip to `fixed` only after the
merge is verified with `git merge-base --is-ancestor`. AT-606 and AT-607 carry the known residuals: the 11.8 s superlinear scan on
518 KB, and the ≤7-char / 8-char-b32-offset-1 boundary.
