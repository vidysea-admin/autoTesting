"""Credential folding: normalise a string so a case, punctuation, homoglyph,
combining-mark, or encoded/reversed spelling of a secret compares equal to
the plain one.

Split out of `core/redact.py` (which was about to cross the C2 300-line cap
implementing AT-347/AT-352/AT-356) because folding is one self-contained
concern -- widening a comparison, never touching stored bytes -- distinct
from `redact.py`'s masking/gating logic. `redact.py` re-exports every name
here that anything outside this pair imports, so no other module's import
line changes. `core/redact_encodings.py` holds the exact base64/base32/hex
needle search (AT-352 cycle 2) -- split out again for the same C2 reason,
and imported here rather than by `redact.py` directly, since it is only ever
used from inside `_contains_folded_secret`. `core/redact_wrap.py` also now
holds `is_ignorable_char` (AT-611, was this module's `_is_ignorable`) and its
`_DEFAULT_IGNORABLE` table -- moved out, not just imported, since this file
was already at the 300-line cap and the CJK perf fix needed new lines.
"""

from __future__ import annotations

import html
import re
import unicodedata
from collections.abc import Sequence
from urllib.parse import unquote_plus

from autotester.core.redact_encodings import declared_secret_encodings
from autotester.core.redact_wrap import contains_wrapped_encoding, is_ignorable_char

_FOLD_STRIP = re.compile(r"[\s\-_.+~/:|,;!?*=^'\"`()\[\]{}<>\\]+")
r"""The punctuation a human actually substitutes for a separator. Widened from
`[\s-_.]` by AT-345, where `+`, `~`, `/` and `:` each carried a live credential
into a git-tracked file."""

ASCII_CONFUSABLES = str.maketrans({
    "\u0131": "i",  # Turkish dotless i -- NFKC leaves it, casefold leaves it
    "\u0130": "i",  # Turkish dotted capital I
    "\u0430": "a", "\u0435": "e", "\u043e": "o", "\u0440": "p",  # Cyrillic a e o r
    "\u0441": "c", "\u0445": "x", "\u0443": "y", "\u0456": "i",  # Cyrillic s h u i
    "\u0458": "j", "\u04bb": "h", "\u0432": "b",
    "\u03bf": "o", "\u03b1": "a", "\u03bd": "v", "\u03c1": "p",  # Greek o a n r
    "\u2044": "/", "\u2010": "-", "\u2011": "-", "\u2012": "-",  # dash-likes
    "\u2013": "-", "\u2014": "-", "\u2212": "-",
})
"""Characters that LOOK like ASCII letters a credential is made of.

Deliberately partial, and said plainly rather than implied: this is a curated
list, NOT an implementation of UTS #39 confusables. It covers the homoglyph
families that actually appear in Latin-script credentials -- Cyrillic, Greek,
the Turkish dotless i a checker used to walk a live value past the guard -- and
it will not catch an exotic script nobody has tried yet. AT-349 tracks the
completeness gap so this bound is visible instead of assumed."""

BIDI_OVERRIDES = ("‭", "‮")
"""LEFT-TO-RIGHT and RIGHT-TO-LEFT OVERRIDE: the two characters that force
rendering direction per character regardless of content.

AT-355. These are the one family the fold cannot handle by subtraction, and
subtracting them is what let the leak through: `_is_ignorable` removes them as
category `Cf`, deleting the character that CAUSES the reordering, and then
compares a string that is not the credential --

    fold("ZEBRA_QUILT_APIKEY_31")  -> zebraquiltapikey31
    fold(RLO + its reverse)        -> 13yekipatliuqarbez

while a reader sees the credential in plain type, in the correct order. Every
other fix in this family worked by subtracting more; here that makes it
strictly worse, so `ui/helpers.py` REFUSES text containing one instead.

Deliberately just the overrides. U+200E/U+200F (LRM/RLM) and the isolates are
ordinary punctuation in Hebrew and Arabic and do not reverse a pure-ASCII run;
refusing them would cost real input for no gain, and false-positive rate is a
term in this product's north star."""

MIN_FOLDED_LEN = 8
"""Folded matching needs a floor, because folding is a HEURISTIC widening: it
deliberately matches strings that are not byte-equal to any secret, so a very
short folded value would start refusing ordinary text that merely contains its
letters (`A-B` folds to `ab`, which appears in half the English language).
Exact and variant matching stay floorless, so AT-002 -- "a three-character
password is a bad password, but leaking it is still a leak" -- is untouched:
the real value is still refused at any length, by `is_clean`.

AT-352 cycle 3: this same constant also floors `_contains_folded_secret`'s
exact-encoding search (`declared_secret_encodings`), but against the RAW
secret's length, not its folded length -- a different floor on a different
value, reusing the number rather than the meaning. That search is an EXACT
substring match of a computed encoding, not a heuristic widening: a checker
found it pre-filtered by the FOLDED-length floor above (inherited from
`widened_secrets` before either half of `_contains_folded_secret` ran), so a
declared secret whose fold happened to fall under 8 -- one punctuation mark
is enough, `"Zq7!kP2x"` is 8 raw characters but folds to 7 -- got no encoding
protection at all, not even fully isolated. The false-positive argument this
docstring makes for the FOLDED floor does not carry over to the raw-length
one: an exact substring of a computed base64/base32/hex encoding is not
"ordinary text that merely contains a secret's letters" the way a folded
string is, so gating it at all is a deliberate, narrower choice (avoid a
1-2 byte secret's tiny, near-universal encoded fragment), not the same
argument restated."""


def fold_credential(text: str) -> str:
    r"""Normalise away the forms of a credential that anyone can reverse in
    their head, so they compare equal.

    Order is load-bearing. Format characters go FIRST: a zero-width space
    between every letter would otherwise sit inside each pair NFKD and the
    confusable map are trying to see. Then NFKD (full-width Latin, the Kelvin
    sign, other compatibility forms -- decomposed, not recomposed, see AT-356
    below), then the confusable map, then dropping combining marks, then
    separators, then case.

    AT-339: a checker put slug `zebra-quilt-apikey-31` past the guard for the
    live value `ZEBRA_QUILT_APIKEY_31`; it became the on-disk directory name,
    every page URL, and text on the home index. `is_clean` is a plain substring
    test, and `_credential_variants` had learned encoding (AT-074) and
    whitespace (AT-071) but never CASE -- because every test in the suite used
    a value that was already lowercase-with-hyphens, the one casing where a
    substring test happens to work.

    AT-345: the first version of this fold covered only `[\s-_.]` and a plain
    `casefold`, and a checker walked four more forms of the same live value
    into git-tracked files. The worst was a ZERO-WIDTH space between every
    character: U+200B has no width, so the project name rendered as the exact
    credential on the home index -- a human reading the page saw the secret.

    AT-351: and then the same leak reopened through U+034F and the variation
    selectors, because the strip keyed on the `Cf` category rather than on
    whether the character renders. `_is_ignorable` is the corrected test.

    AT-356: `_is_ignorable` deliberately does NOT strip a VISIBLE combining
    mark (U+0301 combining acute, U+0335 combining short stroke overlay) --
    that is the point of AT-351's fix, not a gap in it: stripping every `Mn`
    character BEFORE composition made a decomposed hostile spelling
    (`E` + combining acute) lose its accent while a precomposed stored value
    (`É`) kept its, an ASYMMETRY that MISSED the match. The fix here is not
    "strip more, earlier" but "strip AFTER decomposition, everywhere,
    uniformly": normalise with NFKD (decomposition only, no recomposition) so
    a precomposed stored value and a decomposed hostile spelling both end up
    as bare-letter-plus-mark, THEN drop every remaining `Mn` character. Both
    sides lose the accent together -- no asymmetry -- and a mark that has no
    legitimate base at all (`Z` + U+0335, which no font composes into
    anything) is dropped the same way. A checker's own probe interleaved
    U+034F/U+FE00/U+FE0F (already caught, see AT-351 above) and, separately,
    U+0301/U+0335 between every character of the credential; both render as
    the plain credential and both now fold to it.
    """
    stripped = "".join(c for c in text if not is_ignorable_char(c))
    decomposed = unicodedata.normalize("NFKD", stripped).translate(ASCII_CONFUSABLES)
    unmarked = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    return _FOLD_STRIP.sub("", unmarked).casefold()


def _obfuscated_spellings(text: str) -> list[str]:
    r"""Best-effort decodings of `text` worth folding and comparing against a
    secret, beyond the text itself: reversed, HTML entity-unescaped, and up to
    four passes of percent-decoding (so a doubly percent-encoded value decodes
    too).

    AT-352 cycle 1: `contains_folded` and `assert_no_raw_secrets` used to fold
    and compare only the literal text, so a credential spelled in HTML numeric/
    hex entities, double percent-encoding, or plain reversal passed both the
    UI intake guard and the model-prompt gate unremarked. All three are
    substring-safe: they decode a match wherever it sits in a larger string
    and leave the rest alone, so running them once over the whole `text` is
    correct even when the caller (`assert_no_raw_secrets`, given a full model
    prompt, not a bare field) passes a credential embedded in a sentence.

    Base64/base32/hex used to be handled here too, by scanning `text` for
    runs SHAPED like those alphabets and decoding each. AT-352 cycle 2
    (checker cycle-1 FAIL, both verdicts): that scan is not substring-safe --
    a decoder needs the ENTIRE run to be valid alphabet, and the regex greedily
    swallowed adjacent alphanumeric characters (a filename's `_`/`-`, a token
    prefix/suffix) into one oversized run that decoded as nothing, so the
    credential inside it was never recovered (`tok_<b64>_end`,
    `SECRET<b32>CODE`, `cafe<hex>beef` all bypassed). base64/base32/hex are
    handled the opposite direction now -- see `_declared_secret_encodings`,
    called with the SECRET, not the text -- because searching for a known
    exact substring is immune to whatever sits next to it.
    """
    forms = [text[::-1], html.unescape(text)]

    decoded = text
    for _ in range(4):  # a few passes catches double/triple percent-encoding
        next_decoded = unquote_plus(decoded)
        if next_decoded == decoded:
            break
        forms.append(next_decoded)
        decoded = next_decoded

    return forms


def _contains_folded_secret(text: str, widened_secrets: Sequence[tuple[str, str]]) -> bool:
    """True when a widened secret from `widened_secrets` -- each a
    `(raw_value, folded_value)` pair -- is found in `text` either as one of
    `raw_value`'s exact `redact_encodings.declared_secret_encodings` (a
    literal substring of the RAW text, unfolded -- AT-352 cycle 2's base64/
    base32/hex fix) or as a substring of `text`'s `fold_credential` or any of
    `text`'s `_obfuscated_spellings`, each independently folded.

    AT-352 cycle 3: the two halves are gated by DIFFERENT floors, applied
    HERE rather than by the caller, because a checker found `Redactor.__init__`
    and `assert_no_raw_secrets` pre-filtering `widened_secrets` to
    `folded_value` at least `MIN_FOLDED_LEN` long BEFORE either half ever ran
    -- so a declared secret whose folded form fell under the floor (one
    punctuation mark is enough: `"Zq7!kP2x"` is 8 raw characters but folds to
    7) got no encoding-search protection at all, not even fully isolated,
    even though the encoding search is an EXACT substring match, not the
    heuristic widening the floor exists to bound (AT-002's floorless-exact
    principle). The encoding search is now gated on `len(raw_value)`, not
    `len(folded_value)`; the heuristic fold search below keeps the original
    `folded_value` floor, because THAT half really is the heuristic widening
    the floor's own docstring describes.

    Shared by `Redactor.contains_folded` and `assert_no_raw_secrets` (AT-347)
    so the UI intake door and the model-prompt gate see the same widened
    match instead of drifting apart the way the two doors did before AT-346 --
    one place that composes Unicode folding, encoding/reversal folding, and
    exact-encoding substring matching, not separate copies that each cover
    part of it.
    """
    if not widened_secrets:
        return False
    if any(
        needle in text
        for raw_value, _folded in widened_secrets
        if len(raw_value) >= MIN_FOLDED_LEN
        for needle in declared_secret_encodings(raw_value)
    ):
        return True
    if contains_wrapped_encoding(text, widened_secrets, MIN_FOLDED_LEN):  # AT-599
        return True
    candidates = {fold_credential(text)}
    candidates.update(fold_credential(form) for form in _obfuscated_spellings(text))
    folded_secrets = [folded for _raw, folded in widened_secrets if len(folded) >= MIN_FOLDED_LEN]
    return any(secret in candidate for candidate in candidates for secret in folded_secrets)
