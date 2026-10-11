# Manifest — at345-346-fold-coverage

**Unit:** AT-345 / AT-346 — the transforms AT-339's fold still let through
**Contract:** `qa/contracts/ui.md` (U8/U9) · `qa/contracts/core-invariants.md` (C2, C7)
**Goal task:** none — issue-driven
**Date:** 2026-09-11
**Fix cycle:** 3 of max 3 — **exhausted; STALLED**
**Dual check:** no
**Issues addressed:** AT-345 (high, fixed) · AT-346 (medium, fixed) · AT-351 (high, fixed in cycle 2) · AT-353 (high, fixed in cycle 3) · AT-349, AT-352, AT-354 (filed, NOT fixed)

## What was wrong

A checker, attacking the fix I shipped one cycle earlier, walked a live `.env` credential past the
guard in six more forms. All were live-reproduced on its own server before this unit existed.

**The worst is not the one that sounds worst.** A **zero-width space between every character**
(U+200B) was accepted into git-tracked `project.json` — and because U+200B has no width, the
project name **renders as the exact credential on the home index**. A human reading the page sees
the secret, while every byte-comparison in the system says it is a different string. That is worse
than AT-339 itself.

The rest: `+`, `~`, `/`, `:` as separators; full-width Latin (`casefold` does not NFKC-normalise);
the Turkish dotless `ı`; and — separately, AT-346 — `zebra%5Fquilt%5Fapikey%5F31`, because
`contains_folded` was applied to the raw text only and never to `_credential_variants`, so each
guard covered exactly the half the other did not: the `%5F` survived folding intact, and the
`unquote_plus` form that would have exposed it was only ever compared byte-for-byte.

## What changed

- `src/autotester/core/redact.py::fold_credential` — strip Unicode format characters (category
  `Cf`), then NFKC, then `ASCII_CONFUSABLES`, then separators, then case. `_FOLD_STRIP` widened
  past `[\s-_.]` to the punctuation a human actually substitutes.
- `src/autotester/core/redact.py::ASCII_CONFUSABLES` — a curated homoglyph map (Cyrillic, Greek,
  the Turkish dotless i, dash-likes).
- `src/autotester/ui/helpers.py` — both call sites fold **every** variant, not just the raw text.
- `tests/test_ui_credential_unicode.py` — **new file** (C2 split at the 300-line cap): does the
  guard see through Unicode *spelling*? `test_ui_credential_transforms.py` keeps the ASCII-shaped
  substitutions. They fail for different reasons and are fixed in different lines.

## The confusable map is deliberately partial, and says so

`ASCII_CONFUSABLES` is a curated list, **not** an implementation of UTS #39. It covers the
homoglyph families that appear in Latin-script credentials and will not catch an exotic script
nobody has tried. **AT-349 is filed for the completeness gap** so the bound is visible rather than
assumed — this is the honest version of "state which transform classes are out of scope", which
the checker's own `expected` offered as an alternative to full coverage.

## What the mutation run corrected (first pass 3/6)

1. **`+` does NOT need the widened separator class.** `unquote_plus` turns `+` into a **space**,
   which AT-339's original `[\s-_.]` already stripped — so that case is caught by AT-346's
   composition, not by the widening. My `kills` claim was simply wrong, the harness refused it, and
   the parametrised table now carries a comment saying so, because the next reader would otherwise
   draw the same false conclusion I did.
2. **The AT-346 mutation touches one call site, and the joined guard still catches a single-field
   submission** — the same redundancy AT-339 hit. Only the *message* distinguishes them, so that is
   what the new test asserts.
3. **"Order is load-bearing" was an unproven claim in a docstring.** It is now measured: for `e` +
   U+200B + combining acute, strip-then-NFKC yields U+00E9 while NFKC-then-strip leaves a bare
   combining mark — different strings, so a credential containing an accented character can be
   spelled past a guard that gets the order wrong. Pinned by a test instead of asserted in prose.

## Deliberate scope boundaries

- `assert_no_raw_secrets` is still **not** folded — AT-347's question, filed by the checker and
  left for a decision rather than settled quietly here. Folding a gate that *raises* trades a leak
  for dead runs.
- The `MIN_FOLDED_LEN = 8` floor is unchanged and still means short credentials get no folded
  protection. The checker measured this last cycle (refused at 8+, accepted at 6–7) and did not
  charge it; nothing here changes that trade.

## How to verify (commands + expected)

- `uv run pytest -q` → expected: exit 0, no failures
- `uv run ruff check src scripts` → expected: `All checks passed!`
  (**not** a bare `ruff check tests` — `tests/test_explore_error_causes.py` is another session's
  uncommitted in-flight edit and reports unused imports that are not this unit's)
- `uv run autotester doctor` → expected: `doctor: clean` (the other loop committed its
  in-flight file in 656f7f8, so the violation cycle 2 attributed to it is gone)
- `uv run pytest tests/test_ui_credential_transforms.py tests/test_ui_credential_unicode.py -q`
  → expected: 31 passed (counted from the run)
- `uv run python scripts/mutation_check.py qa/evidence/at345-346-fold-coverage/mutations.json`
  → expected: `10/10 mutations killed` (C7 — cycle 3 added one)

## Actual outputs — CYCLE 1 (superseded; cycle 2's are below)

```
$ uv run pytest
1133 passed, 2 skipped, 1 warning in 187.46s (0:03:07)

$ uv run ruff check src ... scripts
All checks passed!

$ uv run autotester doctor
doctor: clean

$ uv run pytest tests/test_ui_credential_transforms.py tests/test_ui_credential_unicode.py
20 passed, 1 warning in 1.22s

$ uv run python scripts/mutation_check.py qa/evidence/at345-346-fold-coverage/mutations.json
KILLED  format characters are no longer stripped - the zero-width leak reopens
KILLED  NFKC normalisation dropped - full-width Latin walks through
KILLED  the confusable map is never applied - the dotless i walks through
KILLED  the separator class narrows back to AT-339's (not the + form: unquote_plus makes that a space)
KILLED  the fold stops composing with the variants (AT-346) - percent-escapes walk through
KILLED  stripping happens AFTER normalising - order is load-bearing, not decorative
6/6 mutations killed
```

One more thing the run caught: my first docstrings contained `\s` in non-raw strings, which emitted
45 `DeprecationWarning: invalid escape sequence` across the suite (1 → 45). Fixed; back to 1.

## Live browser evidence

**SKIP — stated gap, not a pass.** The maker did not run a live browser this cycle. The zero-width
case in particular has a *rendering* claim — that the home index shows the exact credential — which
a `TestClient` cannot verify and which was originally demonstrated by a checker in a real browser
with a screenshot. **The checker must run Mode D and treat its own result as authoritative**, and
should specifically re-check that the rendering leak is closed, not merely that the POST is refused.


## Cycle 2 — the checker FAILed cycle 1, and it was right

**Verdict:** `qa/verdicts/at345-346-fold-coverage.md`, cycle 1, **FAIL**, 0/2 criteria.
The checker confirmed everything cycle 1 claimed — all six AT-345 forms and AT-346's
percent-escape composition genuinely closed, verified by its own POSTs, 6/6 mutations
re-killed, 0 false positives in 36 legitimate submissions — and then **reopened the same
rendering leak one code point sideways**.

**AT-351.** `fold_credential` stripped `unicodedata.category(c) == "Cf"`. U+034F (combining
grapheme joiner) and U+FE00–U+FE0F (variation selectors) are category **`Mn`**. They survive
that strip and NFKC, they render as nothing, and the checker measured them at
192.5/192.5/191.5px against a 192.5px plain-credential control — pixel-identical — then read
the credential off the home index in a real browser. It also found the same three spellings
reaching git-tracked `cases.jsonl` through `title`, `step_value` and `step_expected`.

Fixed by keying on **invisibility** — Unicode's `Default_Ignorable_Code_Point` ranges, listed
explicitly because Python exposes no predicate for them — rather than on a category.

### The justification I first wrote for that was wrong, twice

I claimed keying on invisibility mattered because stripping all `Mn` "would silently mangle
every Hindi, Arabic and accented-Latin string the system stores". Both halves were false:

1. **`fold_credential` never rewrites anything.** It is a comparison function; stored text is
   untouched either way. There was no corruption to fear.
2. **The mutation proved it.** Stripping all `Mn` did not make my Hindi/Arabic test fail —
   that test asserts those names are *accepted*, and they still are. The test could not fail
   for the reason it named, which is the vacuous class C7 exists to refuse. **Deleted, not
   relabelled**; ordinary non-ASCII acceptance is already covered elsewhere in the file.

Measured, the real harm runs the **other way — a leak, not a false positive**:

```
stored   CAFE_QUILT_APIKEY_31 with a precomposed U+00C9
spelled  the same value, with E + U+200B + combining acute

keying on invisibility:  both fold to cafequiltapikey31 (e-acute)   MATCH
stripping all Mn:        the spelled form loses its accent          MISS
```

Stripping *visible* combining marks folds the two sides **asymmetrically**, because a stored
value tends to carry a precomposed character while a hostile input carries a decomposed one —
reopening the very class of bypass this fold exists to close. The mutation is re-attributed to
the test that actually dies, and the docstring now says this instead of the wrong thing.

### Cycle 2 verification

- `uv run pytest` → **1140 passed, 2 skipped, 1 warning**
- `uv run ruff check src scripts <this unit's three test files>` → `All checks passed!`
- `uv run python scripts/mutation_check.py qa/evidence/at345-346-fold-coverage/mutations.json`
  → **9/9 mutations killed** (three added this cycle: revert to `Cf`; strip all `Mn`; empty
  the default-ignorable ranges)

`uv run autotester doctor` reports one violation — `tests/test_explore_error_causes.py` at 330
lines. **That file is the other maker loop's uncommitted in-flight work**, not this unit's;
this unit's files are clean. Verify with `git status --porcelain tests/test_explore_error_causes.py`.

### Still open, and the checker should weigh them

- **AT-352 (medium, filed by the checker, NOT fixed):** base64/base32/hex, HTML entities,
  double percent-encoding and reversal all still write to disk. Not closed here because U8/U9
  pin byte-for-byte reassembly and each of these needs a decode step the guard does not
  currently take — a scope decision, not an oversight.
- **AT-349 (low, filed by me):** the confusable map is curated, not UTS #39. The checker
  independently agreed this was filed honestly and landed its Armenian/Cherokee probes inside
  it.
- The live browser pass is again a maker **SKIP**; the checker's own Mode D is authoritative,
  and should re-check the **rendering** of the three new spellings, not only that the POST is
  refused.


## Cycle 3 — FAILed again, same line, third time

**Verdict:** cycle 2, **FAIL**, 0/2. The checker confirmed both cycle-1 failures genuinely
closed — and did not take the negative on faith: it planted a U+034F-spelled name directly
into `project.json`, watched its DOM scan report 2 leaf nodes rendering the credential,
restored it, and watched the scan return to 0. It also **audited my hand-written
`_DEFAULT_IGNORABLE` list against Unicode data** rather than trusting it (4174 DI code points
vs 4199 stripped: zero under-inclusion), and found **zero false positives in 44 probes**
including Hindi, Arabic with shadda, Thai, Hebrew with niqqud, Khmer, Korean and five emoji
forms with U+FE0F and ZWJ.

Then it reopened the leak a **third** time.

**AT-353 — U+0000.** Category `Cc`, so neither the `Cf` test nor the default-ignorable ranges
caught it. It is the sharpest bypass in this whole thread because **it needs no decoding by
the reader at all**: the HTML parser *deletes* NUL, so the home index renders the credential
in plain type and `document.body.innerText` contains it verbatim. Same three case-form doors
too — 60 `\u0000` escapes in git-tracked `cases.jsonl`.

### The predicate was misnamed, and that is part of why this kept happening

`_is_invisible` was a promise the code did not keep — and not even the right promise. U+0001
and U+007F render as a **visible box** in Chromium (the checker measured 348px and 356.9px
against a 192.5px control), so *"renders as nothing"* was never the rule that mattered.
Renamed to **`_is_ignorable`**, with the rule stated as what actually holds: none of these
characters can carry meaning a reader takes off the screen, and all of them can be inserted
between the characters of a credential. Twice now the implementation was chasing a mis-stated
rule; a wrong name on a security predicate is not cosmetic.

### Cycle 3 verification

- `uv run pytest` → **1145 passed, 2 skipped, 1 warning**
- `uv run ruff check src scripts` → `All checks passed!` · `uv run autotester doctor` → `doctor: clean`
- `uv run pytest tests/test_ui_credential_transforms.py tests/test_ui_credential_unicode.py` → **31 passed**
- mutation spec → **10/10 killed** (cycle 3 adds "AT-353 reverted: control characters are
  ignorable again only if Cf")

### This is the last cycle the protocol allows

If cycle 3 FAILs, the unit flips to `STALLED` and stops for Umesh rather than going a fourth
round. That is worth saying plainly, because the pattern here is not random: **three FAILs, all
on one line, each a different character class nobody enumerated up front.** A fourth would be
evidence that character-class-at-a-time is the wrong shape for this guard, not that the fourth
class was unlucky — and the honest next move would be a design conversation (canonicalise to an
allow-list of readable characters, rather than subtracting unreadable ones one family at a
time), not another patch.

### Still open

- **AT-352 (medium):** base64/base32/hex, HTML entities, double percent-encoding, reversal.
  Each needs a decode step the guard does not take. Scope decision, not oversight.
- **AT-354 (low):** no standing test pins that Indic/Arabic/Hebrew/Thai/emoji names are
  *accepted*. Deliberately **not** added in this last cycle: such a test cannot be killed by
  any mutation of this guard, because the guard only ever refuses and over-stripping the input
  makes it match *less*, not more. Adding an unkillable test in the final cycle would be
  decoration. It deserves a unit that designs a falsifiable version.
- **AT-349 (low):** the confusable map is curated, not UTS #39 — the checker independently
  agreed this was filed honestly.

## STALLED after fix cycle 3 — handed to Umesh

Three cycles, three FAILs, all on one line. The protocol's cycle limit is reached, so this stops
here rather than going a fourth round. **The limit is not why it should stop** — the fourth
finding is.

### What is still failing: AT-355 (high), both doors

`U+202E` (RIGHT-TO-LEFT OVERRIDE) followed by the credential **written backwards** is accepted at
`/onboard` and by the case form, lands in git-tracked `project.json` and `cases.jsonl`, and renders
on the home index as **21 plain-type glyphs in the correct reading order** — visually identical to
a planted plain-credential control.

**It leaks *because* the guard strips it.** Verified directly:

```
fold("ZEBRA_QUILT_APIKEY_31")        -> zebraquiltapikey31
fold("\u202e" + the reverse of it)   -> 13yekipatliuqarbez
```

`_is_ignorable` removes `U+202E` as category `Cf` — deleting the character that *causes* the
leak — and then compares a string that is not the credential. Every previous fix in this unit
worked by *subtracting* characters that carry no meaning. That operation is exactly wrong for a
character whose effect is on **rendering order** rather than on content: subtracting it destroys
the evidence of the attack.

### Why a fourth patch would be the wrong call

The first three failures could be read as "another family nobody enumerated". This one cannot.
AT-355 is a character the guard **already handles**, failing in the opposite direction from the
fix. That is a shape problem, not a coverage problem:

- **Deny-listing is unbounded here.** The checker's count: 1,107,659 code points defeat the fold
  when interleaved; the strip set covers ~4,200.
- **The predicate's name is still wrong**, and I renamed it this cycle believing I had fixed
  that. `_is_ignorable` claims these characters carry no meaning a reader takes off the screen.
  The bidi controls *do* — that is their entire function.

**The checker's recommendation, which I agree with:** canonicalise to an **allow-list of readable
characters** and compare what a reader would actually see, rather than subtracting unreadable
families one at a time. It also built a `visualOrder` detector — glyphs sorted by screen x — which
is what caught AT-355, and that belongs in this repo rather than in a checker's scratch directory.

**This is a design decision, and it is Umesh's**, not something to settle inside a fix cycle. The
narrower option (refuse bidi controls outright instead of stripping them) closes AT-355 and leaves
the shape unchanged, which is the choice that matters.

### What DID hold, verified independently

Cycle 3's own work was confirmed: AT-353 closed at both doors using the planted-control technique,
10/10 mutations killed with attribution checked by hand, 11/11 legitimate submissions accepted
(multi-line expect text, emoji with `U+FE0F`), `doctor` clean, suite green at 1145. AT-345, AT-346
and AT-351 all re-verified as closed. The failure is one new finding, not a regression.

### A correction I owe

I deferred AT-354 on the reasoning that an acceptance test for Indic/Arabic/emoji names "cannot be
killed by any mutation of this guard". **The checker refuted it in one line**: mutate the strip to
`category(ch).startswith("M")` and a Hindi or Thai name folds to a stub, the guard refuses *more*,
and the acceptance test dies. A falsifiable version costs one spec line.

That is the **third** unreachability claim I have made in this repo and the third that has been
refuted. The pattern is mine, not the code's, and it should be treated as a standing rule rather
than a run of bad luck: **I do not get to assert that no mutation can reach a property.**

## Status: STALLED (resolved: gate qa/gates/at355-guard-shape.md Answered 2026-09-11; superseded work tracked there)

