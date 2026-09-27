# Manifest — at347-352-356-redact-fold
**Contract:** qa/contracts/core-invariants.md C5 (secrets never reach a model, log, or artifact) ·
qa/contracts/browser-and-secrets.md B2 ("any string headed for a provider passes
`core.redact.assert_no_raw_secrets` first")
**Goal task:** none (security-hardening fix against open checker findings)
**Date:** 2026-09-25 (cycle 1) / 2026-09-26 (cycles 2, 3, and 4)
**Fix cycle:** 4 — narrow, gated beyond the 3-cycle cap by `qa/gates/at347-cycle4.md` (Umesh,
answer A, 2026-09-26)
**Dual check:** no
**Issues addressed:** AT-347 (medium, open), AT-352 (medium, open), AT-356 (medium, open)

## Cycle 4 — narrow, test-integrity-only fix under `qa/gates/at347-cycle4.md` (answer A)

Cycle 3's actual security fixes PASSed both checker verdicts (fold-floor gating, base32 alignment,
base32 lowercase, 0 false positives on 518 KB — nothing here reopens any of that). The one
remaining FAIL (`qa/verdicts/at347-352-356-redact-fold.md` cycle 3, commit a5118c4) was not a
security gap: cycle 3's file split moved
`test_fold_credential_keeps_precomposed_and_decomposed_accents_symmetric` into
`tests/test_redact_obfuscation.py`, and its `decomposed` literal — written as a raw combining
U+0301 character — was silently NFC-normalised back to the precomposed form by the editor on save.
The test then compared `"CAFÉ_QUILT_APIKEY_31"` to itself and could never go red. This stalled the
unit at 3 of 3 cycles; `qa/gates/at347-cycle4.md` records Umesh's decision (option A over option B
"STALL"): one narrow cycle 4, scoped to exactly this test, no source change.

| # | Finding | Answer |
|---|---|---|
| 1 | `decomposed`'s literal was byte-identical to `precomposed` (both U+00C9, precomposed É — confirmed via a hex dump of the on-disk bytes before the fix). | **Fixed.** Rewritten as an explicit `́` escape — six literal ASCII characters in the source (backslash, `u`, `0`, `3`, `0`, `1`) — which Python's tokenizer expands to the real combining acute at parse time. This is immune to an editor's NFC normalisation because the escape itself is plain ASCII on disk, never a live combining character. |
| 2 | Nothing in the test would have caught a future regression back to this exact defect (comparing a string with itself). | **Fixed.** Added `assert decomposed != precomposed` before the fold-equality assertion, so an accidental re-normalisation fails loudly instead of silently passing. |

### What changed in cycle 4

- `tests/test_redact_obfuscation.py:46-58` (`test_fold_credential_keeps_precomposed_and_decomposed_accents_symmetric`
  only) — `decomposed`'s literal changed from a raw (silently re-normalised) combining character to
  an explicit `"CAFÉ_QUILT_APIKEY_31"` escape; added
  `assert decomposed != precomposed`. No other line in the file changed. **No source file touched**
  this cycle (`core/redact.py`, `core/redact_fold.py`, `core/redact_encodings.py` all unchanged) —
  per the gate's scope.

### Red-first (throwaway copy outside the worktree, never the tracked file)

Copied `redact.py`/`redact_fold.py`/`redact_encodings.py` into a scratch directory outside the
worktree. Two mutations, both run against the fixed literals:

- **Mutation A — reintroduce the exact cycle-3 defect** (set `decomposed` to the same bytes as
  `precomposed`, simulating the silent re-normalisation): `assert decomposed != precomposed` goes
  **red**, as it must. Separately confirmed that *without* that new assert, the old test body
  (`fold_credential(precomposed) == fold_credential(decomposed)` alone) evaluates to `True` and
  would have silently PASSED on this exact mutant — reproducing precisely why cycle 3's checker
  called the test vacuous. This is what proves the new assert, not the fold-equality assert, is
  what now holds the test honest (a self-comparison always trivially folds equal, so the
  fold-equality assert alone is blind to this specific defect).
- **Mutation B — break the real capability under test** (a naive fold stand-in doing plain
  `.casefold()` with no NFKD/mark-stripping): `fold_credential(precomposed)` (`'caf\xe9_...'`) no
  longer equals `fold_credential(decomposed)` (`'café_...'`) under the mutant, so the
  pre-existing fold-equality assert still goes **red** against a real regression — the new assert
  did not displace or weaken that check.
- Green baseline (real `fold_credential`, fixed literals): both `decomposed != precomposed` and
  `fold_credential(precomposed) == fold_credential(decomposed)` hold (`'cafequiltapikey31'` on both
  sides).

### Verification

- On-disk confirmation the escape survived: `grep -n 'u0301' tests/test_redact_obfuscation.py` →
  ```
  53:    # E + combining acute, as an explicit ́ escape -- a raw combining
  55:    decomposed = "CAFÉ_QUILT_APIKEY_31"
  ```
  Confirmed at the character level in the scratch copy: the parsed literal is
  `C A F E U+0301 _ Q U I L T ...` (a real combining mark following a plain `E`), not a
  re-normalised precomposed `É`.
- `uv run pytest tests/test_redact_obfuscation.py tests/test_core.py tests/test_ids.py` — summary
  line read directly, never a piped exit code:
  ```
  65 passed in 0.59s
  ```
- `uv run ruff check src tests scripts` → `All checks passed!`
- `uv run autotester doctor` → clean except the two pre-existing `ledger-row-lost` rows for
  AT-598/AT-599 (out of scope for this unit, carried forward unchanged from cycle 3 — see Gaps);
  no new violations from this cycle.

### Capability coverage (cycle 4 addition)

| Claim | Falsifying edit | Check that goes red |
|---|---|---|
| The symmetric-fold test can never again silently compare a string with itself | Set `decomposed`'s literal to the same bytes as `precomposed` (Mutation A) | `assert decomposed != precomposed` |
| The symmetric-fold test still exercises real fold behaviour, not just the new guard | Replace `fold_credential` with a naive `.casefold()`-only stand-in (Mutation B) | `assert fold_credential(precomposed) == fold_credential(decomposed)` |

## LIVE-BROWSER: not-applicable (cycle 4)

No UI/route/browser surface touched. This cycle changed one test literal and added one assert; no
source file.

## Gaps (cycle 4)

- Carried forward unchanged from cycle 3: AT-598/AT-599 (split needles) are filed separately and
  intentionally out of scope; the full non-browser `pytest` suite was not run this cycle either
  (targeted set only, same standing RAM-ceiling gap already declared in cycle 3 — not re-raised as
  new).
- No new gaps introduced by cycle 4: the change is exactly one test literal plus one assert, per
  the gate's scope.

## Cycle 3 (kept as history, superseded by Cycle 4 above where they overlap)

## Cycle 3 — both cycle-2 verdicts were FAIL; last cycle

`qa/verdicts/at347-352-356-redact-fold.md` (primary, commit 4ca4721) and
`qa/verdicts/at347-352-356-redact-fold.b.md` cycle-2 entry (commit ab60d4e) both FAILed cycle 2 on
three gaps in the SAME exact-encoding-search mechanism cycle 2 introduced. Both verdicts confirmed
the cycle-2 adjacency fix itself holds (base64 alignment including `"user:"+secret`, hex isolated,
ASCII_CONFUSABLES) — nothing here reopens that. This section answers every finding, narrowly, in
only `core/redact.py`, `core/redact_encodings.py`, and tests, per the dispatch brief.

| # | Verdict finding | Severity | Answer |
|---|---|---|---|
| 1 | Primary + blind second: `Redactor.__init__` (redact.py:62-65) and `assert_no_raw_secrets` (redact.py:134-137) pre-filtered every secret into `widened_secrets` by its FOLDED length (>= `MIN_FOLDED_LEN`) before the exact-encoding search ever ran. `"Zq7!kP2x"` (8 raw chars, folds to 7) got no encoding protection at all, not even isolated. Primary reproduced 70/70 misses across 7 encodings x 10 contexts. | high | **Fixed.** The two floors are now applied separately, INSIDE `_contains_folded_secret` (not by either caller): the heuristic fold-based search keeps the original folded-length floor; the exact-encoding search is now gated on `len(raw_value) >= MIN_FOLDED_LEN` instead — an exact substring match is not the heuristic widening the floor's docstring argues against (AT-002's floorless-exact principle), so it needed its own, narrower floor, not the same one reused for the wrong reason. `Redactor.__init__`/`assert_no_raw_secrets` no longer filter at all — they build `widened` unconditionally and let `_contains_folded_secret` decide. |
| 2 | Blind second: base32 has zero alignment-offset handling — `declared_secret_encodings` computed only the isolated `base64.b32encode(secret_bytes)`. base32 groups 5 bytes into 8 characters (one more offset than base64's 3), so `b32encode(prefix + secret)` misses at prefix lengths 1-4 mod 5. Deterministically reproduced: offsets 0 and 5 caught, offsets 1-4 all MISS. | high | **Fixed.** `_base64_alignment_needles` generalised into `_alignment_needles(secret_bytes, encoder, group_bytes, group_chars)`; base32 now gets `range(5)` offsets with 8-character groups, the same technique base64 already had with `range(3)`/4. Per the brief: tests re-encode `prefix + secret` as ONE `base64.b32encode` call for `k in 0..4`, not a literal-text wrap around an isolated encoding (the brief's own diagnosis of why cycle 2's `SECRETb32CODE`-style tests never exercised alignment). |
| 3 | Primary: base32 needles were uppercase only (`redact_encodings.py:82-83`); lowercase base32 of any secret misses both doors in every context (40/40). | medium-high | **Fixed.** Lowercase base32 needles added, generated through the SAME alignment machinery as uppercase (`encoder=lambda b: base64.b32encode(b).lower()`), so lowercase gets the identical adjacency immunity, not a narrower one — plus the plain isolated encoding of each case with and without `=` padding stripped, as explicit belt-and-suspenders pairs alongside the alignment needles (mirroring how hex already has upper+lower). |
| — | Both verdicts, explicitly: hex is fine; AT-598/AT-599 (split needles) are separate issues. | — | **Left alone**, per the brief. `test_hex_needles_unchanged_no_mixed_case_variant_added` pins the two existing hex needles so a future cycle working on base32 doesn't accidentally touch hex. AT-598/AT-599 not addressed — see Gaps. |
| — | Both verdicts: keep what holds — b64 alignment incl. `"user:"+secret`, 0 false positives on 121 KB, ~0.24s at 50KB. Re-run false-positive + timing since shorter needles at more offsets raise both risks. | — | **Re-verified below** (regression run + fresh false-positive/timing numbers). |

### What changed in cycle 3

- `src/autotester/core/redact_fold.py` — `_contains_folded_secret` now applies `len(raw_value) >=
  MIN_FOLDED_LEN` to gate the exact-encoding half and `len(folded) >= MIN_FOLDED_LEN` to gate the
  fold-based half, instead of a single pre-filter the caller applied to both. `MIN_FOLDED_LEN`'s
  docstring extended (not trimmed) to explain the second, narrower use of the same constant.
- `src/autotester/core/redact.py` — `Redactor.__init__`'s `self._widened` and
  `assert_no_raw_secrets`'s `widened` no longer filter by folded length; both now build the full
  `(raw, folded)` list unconditionally.
- `src/autotester/core/redact_encodings.py` — `_base64_alignment_needles` → `_alignment_needles`
  (generalised, `group_bytes`/`group_chars` parameters; its historical rationale moved to a
  preceding comment block, not trimmed, to stay under the 50-line function cap — see Gaps for why
  that was needed). `declared_secret_encodings` now computes base32 through the alignment
  machinery (uppercase and lowercase) plus the isolated padded/unpadded pair of each case. hex
  untouched.
- `tests/test_core.py` crossed the C2 300-line cap growing this suite across three cycles (348
  lines before this split). Split by responsibility: `tests/test_ids.py` (core.ids tests, an
  unrelated concept) and `tests/test_redact_obfuscation.py` (the full AT-347/352/356 regression
  suite, all cycles) — `tests/test_core.py` now holds only the Redactor/placeholder basics. New
  tests added to `test_redact_obfuscation.py`: `test_contains_folded_catches_short_fold_secret_isolated_encoding`
  / `test_assert_no_raw_secrets_blocks_short_fold_secret_isolated_encoding` (finding 1, 3 encodings x
  2 doors), `test_contains_folded_catches_base32_at_every_byte_alignment_offset` /
  `test_assert_no_raw_secrets_blocks_base32_at_every_byte_alignment_offset` (finding 2, 5 offsets x 2
  doors, re-encoding `prefix+secret` as one call per the brief), `test_contains_folded_catches_lowercase_base32_isolated`
  / `test_assert_no_raw_secrets_blocks_lowercase_base32_isolated` (finding 3), and
  `test_hex_needles_unchanged_no_mixed_case_variant_added` (pins the "leave hex alone" decision).

### Red-first (throwaway copy, cycle-2 code at 01f8867, before this cycle's edit)

Reproduced all three findings against the EXACT cycle-2 commit (01f8867), copied to a scratch
mini-package, never the tracked worktree:

```
== Finding 1: short-fold secret gets no encoding protection ==
short-b64-isolated               ui=False gate=False
short-b32-isolated               ui=False gate=False
short-hex-isolated               ui=False gate=False

== Finding 2: b32 alignment (prefix + secret encoded as ONE call) ==
b32-coencoded-prefix0            ui=True  gate=True
b32-coencoded-prefix1            ui=False gate=False
b32-coencoded-prefix2            ui=False gate=False
b32-coencoded-prefix3            ui=False gate=False
b32-coencoded-prefix4            ui=False gate=False

== Finding 3: b32 lowercase, isolated ==
b32-lowercase-isolated           ui=False gate=False

BYPASSED (expected all 3 findings to bypass): [... all 8 red cases above ...]
```

Prefix-offset pattern (0 caught, 1-4 miss) matches the blind-second verdict's own reproduction
exactly. Re-ran the identical probe against the fixed code — all 9 checks flip to `ui=True gate=True`.

### Cycle 3 verification

```
$ uv run pytest tests/test_core.py tests/test_ids.py tests/test_redact_obfuscation.py
65 passed in 0.68s

$ uv run pytest tests/test_core.py tests/test_ids.py tests/test_redact_obfuscation.py tests/test_secrets.py tests/test_ui_secrets_declaration.py tests/test_check_no_secrets.py tests/test_db.py tests/test_network_assertions.py tests/test_portal_persona.py tests/test_run_trace.py tests/test_source_adapters_drive.py tests/test_prompt_skills.py
168 passed, 1 skipped, 6 warnings in 10.20s

$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester doctor
ledger-row-lost: qa/verdicts/at347-352-356-redact-fold.md — AT-598 is named here but has no row in qa/issues.jsonl
ledger-row-lost: qa/verdicts/at347-352-356-redact-fold.md — AT-599 is named here but has no row in qa/issues.jsonl
2 violation(s)
```

The 2 remaining `doctor` violations are the checker's own ledger bookkeeping (AT-598/AT-599 named in
a verdict with no `qa/issues.jsonl` row yet) — maker never edits `qa/issues.jsonl`, and the brief
explicitly says not to take on AT-598/AT-599 this cycle. Not a code or test defect; flagged, not
fixed. `file-too-long`/`function-too-long` (present before this section's edits — `test_core.py` at
348 lines, `_alignment_needles` at 53 lines) are both resolved (see What changed).

Regression check — every prior cycle's caught case, re-verified against the fixed code (9 cycle-1
vectors + 9 cycle-2 adjacency/isolated vectors including `"user:"+secret` Basic-auth shape):

```
ALL REGRESSION CASES STILL CAUGHT: True   (18/18)
```

**False-positive and timing re-check** (explicitly requested — shorter needles at more offsets
raise both risks):

```
corpus size: 127.3 KB (realistic prose + filename/token/hex/b32/b64 decoys + random alnum blobs)
assert_no_raw_secrets: no raise (clean)
elapsed=0.753s

corpus size: 33.6 KB (same shape)
assert_no_raw_secrets: no raise (clean)   elapsed=0.255s
contains_folded: False                     elapsed=0.248s

50 KB slice: elapsed=0.270s
```

Cycle 2's own number was ~0.24s at 50KB; this cycle's 50KB slice measures 0.270s — a mild, expected
increase (more offsets, one more secret in the declared set for this specific test), still roughly
linear with corpus size and in the same order of magnitude. No false positive at either scale, on a
corpus deliberately salted with filename/token/hex/base32/base64-shaped decoys designed to stress
the exact-encoding search's over-triggering risk.

**Full non-browser suite: still NOT RUN.** RAM measured 728 MB-1.7 GB free across cycles 2 and 3
sessions, never reaching the 3.5 GB ceiling. Same declared gap as cycles 1 and 2.

### Cycle 3 capability coverage (mutation-tested, scratch copy only)

Baseline (11 checks: 3 finding-1 isolated encodings, 5 finding-2 alignment offsets, 1 finding-3
lowercase, 2 cycle-2 regression spot-checks) asserted green first:

```
BASELINE: {'short-b64-isolated': True, 'short-b32-isolated': True, 'short-hex-isolated': True,
           'b32-coencoded-prefix0': True, 'b32-coencoded-prefix1': True, 'b32-coencoded-prefix2': True,
           'b32-coencoded-prefix3': True, 'b32-coencoded-prefix4': True,
           'b32-lowercase-isolated': True, 'cycle2-tok_b64_end': True, 'cycle2-cafe_hex_beef': True}
-- all caught, asserted green
```

| capability | falsifying edit (single-hunk, scratch copy only) | targeted rows go red | others stay green |
|---|---|---|---|
| Finding 1 — exact-encoding search gated on raw length, not fold length | `redact_fold.py`: revert the `if len(raw_value) >= MIN_FOLDED_LEN` guard back to `if len(_folded) >= MIN_FOLDED_LEN` | `short-b64-isolated`, `short-b32-isolated`, `short-hex-isolated` (all 3) | yes |
| Finding 2 — base32 alignment (5 offsets) | `redact_encodings.py`: drop the two `_alignment_needles(raw, base64.b32encode, 5, 8)` / lowercase-b32 alignment lines | `b32-coencoded-prefix1..4` (offset 0 stays green by construction — it equals the isolated case) | yes |
| Finding 3 — base32 lowercase | `redact_encodings.py`: drop the lowercase-alignment call AND the `b32_lower` isolated-needle lines (one hunk) | `b32-lowercase-isolated` | yes |

Full runner output (`mutation_runner_cycle3.py`, scratch dir):

```
finding1-fold-floor-gate      targeted_red=True  others_green=True
finding2-b32-alignment        targeted_red=True  others_green=True
finding3-b32-lowercase        targeted_red=True  others_green=True

ALL CYCLE-3 FINDINGS PROPERLY DEFENDED: True
```

### Cycle 3 gaps

- **AT-598/AT-599 (split needles) not addressed** — explicitly out of scope per the brief ("keep
  this cycle narrow"). `doctor`'s `ledger-row-lost` violation for both is a pre-existing checker-side
  ledger gap (verdict named them, `qa/issues.jsonl` has no row yet), not something this cycle's code
  or tests can fix — maker never edits `qa/issues.jsonl`.
- Hex deliberately unchanged, per the brief's explicit instruction (the mixed-case-hex claim from
  one of the two cycle-2 verdicts did not reproduce under the coordinator's own re-check). If a
  future check reproduces it independently, that is new evidence for a new cycle, not something
  silently folded in here.
- Same standalone-mutation-runner-vs-pytest method note as cycles 1-2 (editable-install path); a
  checker wanting a literal pytest-attributed kill can apply the same one-hunk edits to the tracked
  file in its own throwaway copy.
- The belt-and-suspenders isolated base32 needles (padded/unpadded, both cases) are technically
  redundant with the alignment needles' offset-0 case for a secret whose length happens to make the
  natural encoding needle-safe, per `_alignment_needles`'s own construction — kept anyway per the
  brief's explicit "plus the unpadded variant of each case" instruction, and as a simpler, more
  obviously-correct fallback independent of the generalised alignment machinery.

---

## Cycle 2 (kept as history, superseded by Cycle 3 above where they overlap)

## Cycle 2 — both cycle-1 verdicts were FAIL

`qa/verdicts/at347-352-356-redact-fold.md` (primary, commit 010c2e2) and
`qa/verdicts/at347-352-356-redact-fold.b.md` (independent blind second, commit e956664) both FAILed
cycle 1 on the same root cause, found independently by two different routes. This section answers
every finding of both verdicts, one row per finding, before the rest of this manifest (which is
cycle 1's original text, kept as history rather than rewritten) is read.

| Verdict finding | Where | Answer |
|---|---|---|
| Primary: `_B64_TOKEN_RE = r"[A-Za-z0-9+/_-]{8,}={0,2}"` swallows adjacent `_`, `-` and alphanumerics into one greedy span; whole-span decode fails; bypasses both doors. Repro: `filename_<b64>.png`, `prefix_<b64>_suffix`, `prefix-<b64>-suffix`, `prefixXX<b64>YYsuffix`; hex has a narrower form (`abc<hex>def`). | `src/autotester/core/redact_fold.py` (cycle 1) | **Fixed.** Removed `_B64_TOKEN_RE`/`_B32_TOKEN_RE`/`_HEX_TOKEN_RE`/`_decode_block` entirely — the decode-the-text-then-compare direction is gone for these three encodings. Replaced with `redact_encodings.declared_secret_encodings(value)`: precompute the DECLARED secret's own base64 (std + URL-safe, 3 byte-alignment offsets, padding-free — `_base64_alignment_needles`), base32, and hex (upper+lower) encodings, and search for each as an exact literal substring of the raw text. Substring search doesn't care what sits next to the match, so adjacency can't break it. |
| Blind second (independent route): same family — `tok_<b64>_end`, `prefix<b64>suffix`, `SECRET<b32>CODE`, `cafe<hex>beef` all MISS in the orchestrator's own reproduction (`Sup3rS3cretValue!42`). | same | **Fixed**, same change — re-verified with the checker's own secret value and exact failing shapes (see Cycle 2 verification below); all 8 named repro strings from both verdicts now caught by both doors. |
| Blind second, "Also noted": `ASCII_CONFUSABLES` was public on pre-split `core/redact.py`; `from autotester.core.redact import ASCII_CONFUSABLES` now raises `ImportError`. No current caller, but the manifest claimed every prior import still resolved. | `src/autotester/core/redact.py` | **Fixed.** `ASCII_CONFUSABLES` added to `redact.py`'s import-from-`redact_fold` block and `__all__`. Pinned by `tests/test_core.py::test_ascii_confusables_still_importable_from_redact`. |
| Both verdicts: capability coverage (8/8 rows), no false positives (50-53 KB corpora), diff scope, and raise-not-warn (B2) all held — no change requested there. | — | Unchanged from cycle 1; re-verified this cycle (see below), nothing regressed. |

### What changed in cycle 2

- `src/autotester/core/redact_fold.py` — `_B64_TOKEN_RE`, `_B32_TOKEN_RE`, `_HEX_TOKEN_RE`,
  `_decode_block` removed; `_obfuscated_spellings` now only produces reversed / HTML-unescaped /
  percent-decoded candidates (all substring-safe, unchanged behaviour, per the brief: "keep
  reversed, HTML and percent-encoded handling as it is"). `_contains_folded_secret`'s signature
  changed from `(text, folded_secrets: Sequence[str])` to
  `(text, widened_secrets: Sequence[tuple[str, str]])` — `(raw_value, folded_value)` pairs, because
  the new exact-encoding search needs the RAW secret bytes (folding would destroy base64's
  case-significant output), checked first, before falling through to the existing fold-based check.
- `src/autotester/core/redact_encodings.py` (new file) — `_base64_alignment_needles` (the
  YARA-style 3-offset technique: pad the secret with 0/1/2 leading zero bytes standing in for
  "however many unknown bytes precede it", pad the tail to a multiple of 3 so no `=` appears, drop
  the leading/trailing 4-character group whenever it mixes in an unknown byte — correctness over a
  couple of characters of needle length) and `declared_secret_encodings` (base64 std+urlsafe via
  the above, plus base32 and hex upper/lower).
- `src/autotester/core/redact.py` — `Redactor.__init__` now builds `self._widened: list[tuple[str,
  str]]` (was `self._folded: list[str]`) so both the raw value and its fold travel together;
  `contains_folded` and `assert_no_raw_secrets` pass `_widened`/`widened` through unchanged
  otherwise. `ASCII_CONFUSABLES` re-exported (see table above).
- `tests/test_core.py` — added `test_ascii_confusables_still_importable_from_redact`, and two new
  parametrized tests covering the exact 8 failing inputs named across both verdicts
  (`test_contains_folded_catches_encoded_secret_next_to_its_own_alphabet` and
  `test_assert_no_raw_secrets_blocks_encoded_secret_next_to_its_own_alphabet`, one door each).
- `docs/MAP.md` — regenerated; new row for `core/redact_encodings.py`.

### Cycle 2 verification

Reproduced the checker's own secret (`Sup3rS3cretValue!42`) and all 8 named failing inputs plus the
3 isolated (non-adjacent) forms, through both doors, in a throwaway scratch copy before touching the
tracked worktree:

```
OK   filename_<b64>.png       ui=True  gate=True
OK   prefix_<b64>_suffix      ui=True  gate=True
OK   prefix-<b64>-suffix      ui=True  gate=True
OK   prefixXX<b64>YYsuffix    ui=True  gate=True
OK   tok_<b64>_end            ui=True  gate=True
OK   SECRET<b32>CODE          ui=True  gate=True
OK   cafe<hex>beef            ui=True  gate=True
OK   abc<hex>def              ui=True  gate=True
OK   isolated b64             ui=True  gate=True
OK   isolated b32             ui=True  gate=True
OK   isolated hex             ui=True  gate=True

ALL CAUGHT: True
```

Re-ran every cycle-1 vector (`CRED = "ZEBRA_QUILT_APIKEY_31"`) to confirm no regression — still all
9 CAUGHT (base64/base32/hex isolated, html dec/hex entities, double-percent, plain-reversed,
combining-acute, combining-short-stroke) — and the ~12-15 KB false-positive prose check (this time
including filename/token-shaped decoys like `filename_abcxyz123.png`, `cafefeedbeefdeadf00dbabe1234`
to specifically probe the new needle search for over-triggering) still raised nothing, ~0.07 s.

```
$ uv run pytest tests/test_core.py
46 passed in 0.24s

$ uv run pytest tests/test_core.py tests/test_secrets.py tests/test_ui_secrets_declaration.py tests/test_check_no_secrets.py tests/test_db.py tests/test_network_assertions.py tests/test_portal_persona.py tests/test_run_trace.py tests/test_source_adapters_drive.py tests/test_prompt_skills.py
149 passed, 1 skipped, 6 warnings in 4.19s

$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester doctor
doctor: clean
```

(The 1 skip and 6 warnings are the same pre-existing/unrelated `test_run_trace.py` AT-561 items
noted in cycle 1 — not caused by this change.)

**Full non-browser suite: still NOT RUN.** RAM measured 0.7-1.7 GB free at various points this
session (`Get-CimInstance Win32_OperatingSystem`), never reaching the 3.5 GB ceiling. Same declared
gap as cycle 1.

### Cycle 2 capability coverage (mutation-tested, scratch copy only)

Same method as cycle 1 (throwaway mini-package under scratch, `sys.path`-imported, never pytest
against a mutated copy — see cycle 1's note on why). Baseline asserted green first:

```
BASELINE: {'combining-marks': True, 'html-entities': True, 'double-percent': True, 'reversed': True,
           'base64-isolated': True, 'base32-isolated': True, 'hex-isolated': True,
           'base64-adjacent': True, 'base64-adjacent-filename': True, 'base32-adjacent': True,
           'hex-adjacent': True} -- all caught, asserted green
```

| capability | falsifying edit (single-hunk, scratch copy only) | targeted rows go red | others stay green |
|---|---|---|---|
| combining marks (AT-356, re-verified) | `redact_fold.py`: strip-`Mn` line → no-op | `combining-marks` | yes |
| HTML entities (re-verified) | `forms = [text[::-1], html.unescape(text)]` → drop `html.unescape` | `html-entities` | yes |
| double/triple percent-decoding (re-verified) | `range(4)` → `range(1)` | `double-percent` | yes |
| plain reversal (re-verified) | drop `text[::-1]` from `forms` | `reversed` | yes |
| base64 needle search (std+urlsafe, all offsets) — **new** | `redact_encodings.py`: `needles: list[str] = [...]` → `needles: list[str] = []` | `base64-isolated`, `base64-adjacent`, `base64-adjacent-filename` (all 3, one hunk) | yes |
| base32 needle search — **new** | `redact_encodings.py`: drop the `b32 = ...` / `needles.extend((b32, ...))` lines | `base32-isolated`, `base32-adjacent` | yes |
| hex needle search — **new** | `redact_encodings.py`: drop the `hexed = ...` / `needles.extend((hexed, ...))` lines | `hex-isolated`, `hex-adjacent` | yes |
| AT-347 gate itself (re-verified against the new `_widened`-pair signature) | `redact.py`: `assert_no_raw_secrets` body reverted to exact-match-only | every family (UI door alone still catches — the AND collapses every row) | n/a |
| `ASCII_CONFUSABLES` re-export — **new** | `redact.py`: drop `ASCII_CONFUSABLES,` from the `redact_fold` import block | mutant import raises `ImportError`; fixed copy imports cleanly | n/a |

Full runner output (`mutation_runner_cycle2.py`, scratch dir):

```
combining-marks                                          targeted_red=True  others_green=True
html-entities                                            targeted_red=True  others_green=True
double-percent                                           targeted_red=True  others_green=True
reversed                                                 targeted_red=True  others_green=True
base64-isolated+base64-adjacent+base64-adjacent-filename targeted_red=True  others_green=True
base32-isolated+base32-adjacent                          targeted_red=True  others_green=True
hex-isolated+hex-adjacent                                targeted_red=True  others_green=True
AT-347-gate-itself                                       targeted_red=True  (every family red)
ASCII_CONFUSABLES-reexport                               fixed_copy_imports=True  mutant_import_broke=True

ALL FAMILIES PROPERLY DEFENDED: True
```

One false start recorded rather than hidden (same C7 spirit as cycle 1): the ASCII_CONFUSABLES
mutation test's first version only re-imported the whole `autotester.core.redact` *module* (which
succeeds regardless of whether `ASCII_CONFUSABLES` is bound in it) instead of the specific `from
autotester.core.redact import ASCII_CONFUSABLES` a real caller would write, so it read
`mutant_import_broke=False` on a mutation that should have broken it. Fixed by asserting the actual
`from ... import ASCII_CONFUSABLES` form; re-ran and it correctly flipped to `True`.

### Cycle 2 gaps

- Same full-non-browser-suite and standalone-mutation-runner-vs-pytest gaps as cycle 1, for the same
  reasons (RAM ceiling; editable-install path) — not repeated in full here.
- The 3-alignment-offset base64 technique is coarse (drops a whole 4-character group where only 1-2
  characters are actually affected by an unknown neighbouring byte), so the needle is a few
  characters shorter than the theoretical maximum in the offset-1/offset-2 cases. Not scoped as a
  risk: exact substring matching on even a shortened needle (still many characters for any
  realistic secret) carries no meaningful false-positive exposure, and correctness (never including
  an unstable character) was prioritized over needle length.
- This fix only searches for a secret encoded ALONE next to arbitrary surrounding text (the shape
  every reproduced failing input used). A secret byte-concatenated with OTHER real secret material
  before the whole blob is base64-encoded (e.g. `base64(nonce + secret + suffix)` as one encode
  call) is exactly what the 3-alignment-offset technique is built to catch too, and was not
  separately re-tested with a non-zero, non-secret neighbour — the mutation/verification above uses
  zero-byte neighbours (per the technique's own construction) and plain-text neighbours (per the
  reproduced attack shape), not a THIRD real-secret-byte neighbour. Flagged for a checker who wants
  to push on it specifically.

---

## Cycle 1 (original, kept as history)

## Issues addressed

- **AT-347** — `core.redact.assert_no_raw_secrets`, the hard gate before every model prompt
  (`browser/secrets.py::SecretStore.guard_prompt` is its only caller path), tested `value in text`
  only. A folded/case/punctuation-varied spelling of a live credential reached an external model
  provider verbatim even though the UI intake door (`Redactor.contains_folded`) already folded.
- **AT-352** — that fold itself covered only the literal text, so a credential spelled in base64,
  base32, hex, HTML numeric/hex entities, double percent-encoding, or plain reversal passed both
  the UI door and (once AT-347 is fixed) would still have passed the model-prompt door.
- **AT-356** — a credential with a VISIBLE combining mark interleaved between every character
  (U+0301 combining acute, U+0335 combining short stroke overlay) rendered legibly (accented /
  struck-through) but was not `Default_Ignorable`, so `_is_ignorable` correctly left it alone
  (that is AT-351's fix, not a gap in it) and the fold never stripped it.

## What changed

- `src/autotester/core/redact_fold.py` (new file) — the folding/decoding internals, split out of
  `redact.py` because the fix would otherwise cross the C2 300-line cap:
  - `fold_credential` (redact_fold.py:139) — switched from NFKC to **NFKD-then-strip-`Mn`**
    (AT-356). NFKD decomposes a precomposed accented character the same way a hostile decomposed
    spelling already arrives, so stripping every remaining `Mn` mark afterward is symmetric on
    both sides — unlike stripping `Mn` *before* composition (AT-351's rejected approach, which
    made a decomposed hostile spelling lose its accent while a precomposed stored value kept its).
  - `_decode_block` (redact_fold.py:196), `_obfuscated_spellings` (redact_fold.py:215),
    `_B64_TOKEN_RE`/`_B32_TOKEN_RE`/`_HEX_TOKEN_RE` (redact_fold.py:191-193) — new. Reversed,
    HTML-unescaped, up to 4 passes of percent-decoded, and base64/base32/hex-decoded candidate
    spellings of the input (AT-352). Percent-decoding, HTML-unescape and reversal are substring-
    safe and run once over the whole text; base64/base32/hex are not (a decoder needs the *entire*
    input to be valid alphabet), so those three additionally scan for base64/base32/hex-**shaped**
    runs inside a larger string and decode each — needed because `assert_no_raw_secrets`'s real
    callers pass full prompt text, not bare field values, and an embedded encoded credential broke
    whole-text decoding in testing (see Actual outputs below).
  - `_contains_folded_secret` (redact_fold.py:261) — new. Folds the text and every
    `_obfuscated_spellings` candidate, checks each against the caller's already-folded,
    `MIN_FOLDED_LEN`-gated secret list. One shared implementation for both hard gates.
- `src/autotester/core/redact.py` (rewritten as the thin public façade + gate logic):
  - `Redactor.contains_folded` (redact.py:83) now delegates to `_contains_folded_secret` — same
    method name/signature, strictly widened behaviour (AT-352 fix reaches the UI door for free,
    since `ui/credential_guard.py` already calls this method — no other file needed editing).
  - `assert_no_raw_secrets` (redact.py:112) — AT-347's actual fix: after the existing floorless
    exact check, it now also folds `text` and its secrets and raises on a widened match, using the
    same `MIN_FOLDED_LEN` floor `Redactor` already applies (so a short secret stays exact-match
    only, per AT-002).
  - `__all__` + re-exports (redact.py:15-35) so `BIDI_OVERRIDES`, `fold_credential`,
    `MIN_FOLDED_LEN` and everything else any other module imports from `autotester.core.redact`
    still resolves — no other file's import line changed.
- `tests/test_core.py` — 12 new tests: `test_fold_credential_strips_visible_combining_marks_after_decomposition`,
  `test_fold_credential_keeps_precomposed_and_decomposed_accents_symmetric` (AT-351 regression),
  parametrized `test_contains_folded_catches_encoded_and_reversed_spellings` (7 cases),
  parametrized `test_assert_no_raw_secrets_blocks_obfuscated_spelling_in_prompt_text` (9 cases,
  each payload embedded in a sentence, matching real caller shape),
  `test_assert_no_raw_secrets_does_not_false_positive_on_ordinary_prose`,
  `test_assert_no_raw_secrets_short_secret_stays_floorless_on_exact_match` (AT-002 regression).
- `docs/MAP.md` — regenerated (`autotester map`); one new row for `core/redact_fold.py`.

## Red-first (throwaway copy, current code, before any edit)

Scratch dir (outside the worktree): `probe_red.py` imported the **unfixed**
`src/autotester/core/redact.py` (copied out, never edited in place) via `importlib` and ran the 9
target vectors through both `Redactor.contains_folded`/`is_clean` and `assert_no_raw_secrets`
(payload embedded in a sentence, matching the real caller shape):

```
BYPASS  base32                           ui_guard_caught=False model_gate_raised=False
BYPASS  base64                           ui_guard_caught=False model_gate_raised=False
BYPASS  combining-acute-U+0301           ui_guard_caught=False model_gate_raised=False
BYPASS  combining-short-stroke-U+0335    ui_guard_caught=False model_gate_raised=False
BYPASS  double-percent                   ui_guard_caught=False model_gate_raised=False
BYPASS  hex                              ui_guard_caught=False model_gate_raised=False
BYPASS  html-dec-entities                ui_guard_caught=False model_gate_raised=False
BYPASS  html-hex-entities                ui_guard_caught=False model_gate_raised=False
BYPASS  plain-reversed                   ui_guard_caught=False model_gate_raised=False

ANY BYPASS FOUND: True
```

All 9 confirmed red before the fix landed.

## How to verify

- `uv run pytest tests/test_core.py tests/test_secrets.py tests/test_ui_secrets_declaration.py tests/test_check_no_secrets.py`
- `uv run pytest tests/test_db.py tests/test_network_assertions.py tests/test_portal_persona.py tests/test_run_trace.py tests/test_source_adapters_drive.py tests/test_prompt_skills.py` (other `Redactor`/`assert_no_raw_secrets`/`PLACEHOLDER_RE` importers, to confirm the public surface stayed compatible)
- `uv run ruff check src tests scripts`
- `uv run autotester doctor`

## Actual outputs (maker's run, commit a95ca6a)

```
$ uv run pytest tests/test_core.py tests/test_secrets.py tests/test_ui_secrets_declaration.py tests/test_check_no_secrets.py
........................................................................ [ 94%]
....                                                                     [100%]
76 passed, 1 warning in 3.50s
```

```
$ uv run pytest tests/test_db.py tests/test_network_assertions.py tests/test_portal_persona.py tests/test_run_trace.py tests/test_source_adapters_drive.py tests/test_prompt_skills.py
.....s...................................................                [100%]
56 passed, 1 skipped, 5 warnings in 6.62s
```
(1 skip and the 5 warnings are pre-existing/unrelated — `test_run_trace.py`'s AT-561 no-`secrets=`
fixture warning — not caused by this change.)

```
$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester doctor
doctor: clean
```

**Full non-browser suite: NOT RUN.** RAM was ~0.7-1.2 GB free throughout this session (measured via
`Get-CimInstance Win32_OperatingSystem`), below the 3.5 GB ceiling for a full-suite run. Declared
gap per the dispatch brief. No browser tests run (not applicable to this unit).

## Capability coverage

Mutation-tested in a throwaway scratch copy (`autotester/core/redact.py` + `redact_fold.py` copied
into a standalone mini-package outside the worktree, imported via `sys.path`, never pytest against
a mutated copy — the venv's editable install points at the worktree, and re-pointing it risked
touching tracked state; the runner instead mirrors the exact assertions `tests/test_core.py` makes,
same payloads, same functions, so a checker can re-derive the same result against the real pytest
suite by applying the same one-line edits to the tracked file). Baseline (unmutated) asserted green
first — printed, not just claimed:

```
BASELINE: {'base64': True, 'base32': True, 'hex': True, 'html-entities': True,
           'double-percent': True, 'reversed': True, 'combining-marks': True}
-- all caught, asserted green
```

| capability | falsifying edit (single-hunk, scratch copy only) | check that goes red | other families stay green |
|---|---|---|---|
| AT-356 combining marks (U+0301/U+0335) fold to the plain spelling | `redact_fold.py`: `unmarked = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")` → `unmarked = decomposed` | `combining-marks: True → False` | yes |
| AT-352 base64 (standard + URL-safe) | remove both `base64.b64decode(...)`/`base64.urlsafe_b64decode(...)` `out.append` lines in `_decode_block` | `base64: True → False` | yes |
| AT-352 base32 | remove `base64.b32decode(...)` `out.append` line | `base32: True → False` | yes |
| AT-352 hex | remove `bytes.fromhex(...)` `out.append` line | `hex: True → False` | yes |
| AT-352 HTML numeric/hex entities | `forms = [text[::-1], html.unescape(text)]` → `forms = [text[::-1]]` | `html-entities: True → False` | yes |
| AT-352 double (and triple) percent-encoding | `for _ in range(4)` → `for _ in range(1)` (single decode pass) | `double-percent: True → False` | yes |
| AT-352 plain reversal | `forms = [text[::-1], html.unescape(text)]` → `forms = [html.unescape(text)]` | `reversed: True → False` | yes |
| AT-347 — `assert_no_raw_secrets` itself became fold-aware (not just the UI door) | reverted `assert_no_raw_secrets`'s body in `redact.py` to its pre-fix exact-match-only form | **every** family flips to red on the model-gate side alone (UI door still catches; the AND collapses every row) | n/a — this row IS the cross-family check |

Full runner output (`mutation_runner.py`, scratch dir):

```
combining-marks  targeted_check_red=True  other_checks_still_green=True
base64           targeted_check_red=True  other_checks_still_green=True
base32           targeted_check_red=True  other_checks_still_green=True
hex              targeted_check_red=True  other_checks_still_green=True
html-entities    targeted_check_red=True  other_checks_still_green=True
double-percent   targeted_check_red=True  other_checks_still_green=True
reversed         targeted_check_red=True  other_checks_still_green=True
AT-347-gate-itself targeted_check_red=True  (every family red because assert_no_raw_secrets stopped folding)

ALL FAMILIES PROPERLY DEFENDED: True
```

One false start recorded rather than hidden: the first base64 mutation removed only
`base64.b64decode`, and the check stayed GREEN because `base64.urlsafe_b64decode` alone still
decodes this test vector (`ZEBRA_QUILT_APIKEY_31`'s base64 encoding happens to contain no `+`/`/`
characters for `urlsafe_b64decode` to need translating). Widened to a single hunk removing both
lines, which then reddened correctly — noted here rather than only shown fixed, per C7's spirit on
reporting real experiments.

**False-positive check** (not in the family table, but load-bearing for AT-347's own "would this
turn every prompt into a run-killing exception" concern): ~12 KB of ordinary grading-prompt-style
prose with no secret present did not raise (`assert_no_raw_secrets` and `contains_folded` both
returned clean), at ~0.1s per call — see `test_assert_no_raw_secrets_does_not_false_positive_on_ordinary_prose`
in the committed suite.

## LIVE-BROWSER: not-applicable

No UI/route/browser surface touched — `core/redact.py` and `core/redact_fold.py` are pure-Python,
`ui/credential_guard.py` and every other caller are unchanged (they get the AT-352 UI-door fix for
free via `Redactor.contains_folded`, without their own files changing).

## Gaps

- Full non-browser `pytest` suite not run (RAM below the 3.5 GB ceiling all session — declared,
  not silently skipped); targeted files covering every `Redactor`/`assert_no_raw_secrets`/
  `PLACEHOLDER_RE` importer were run instead (13 files, 132 tests total, all green).
- The mutation/capability-coverage run used a standalone script mirroring the pytest assertions
  (same payloads, same functions), not `pytest` itself against a mutated copy, for the reason
  stated above (editable-install path). A checker wanting a literal pytest-attributed kill can
  apply the same one-hunk edits to the tracked file in its own throwaway copy and run
  `tests/test_core.py -k <family>` directly.
- Token-shaped base64/base32/hex scanning (`_B64_TOKEN_RE` etc.) matches any 8+/16+-character
  alphanumeric run, including ordinary English words — deliberate over-triggering (see
  `_obfuscated_spellings`'s docstring): every failed decode contributes nothing, and a decode that
  happens to succeed still has to survive `fold_credential` + the `MIN_FOLDED_LEN`-gated substring
  check. Not scoped as a false-positive risk given the empirical prose check above, but flagged in
  case a checker wants to measure it on a different/larger corpus.
- AT-347's own issue text offered "leave it byte-exact, document the residual" as an equally valid
  alternative to fixing it. This manifest took the fix path per the dispatch brief; if a checker
  judges the availability argument (a false positive now raises inside a model-call path) as
  requiring the WARNING-not-raise shape instead, that is cycle 2's redesign, not a defect in what
  shipped — the false-positive check above found no live case, but the checker's own Mode D/live
  probing is a stronger instrument than this manifest's synthetic prose sample.

## Status: checked-PASS (cycle 4, qa/verdicts/at347-352-356-redact-fold.md c3a2ce1)
