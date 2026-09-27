"""Whitespace normalisation for the exact-encoding needle search, and a
CJK-safe fast path for `redact_fold.fold_credential`'s per-character
ignorable-code-point check.

AT-599: `redact_encodings.declared_secret_encodings` needles are literal,
unfolded substrings of an encoded secret -- exactly what makes them immune to
whatever sits next to them (AT-352 cycle 2). That same literalness makes them
blind to a needle broken by ANY whitespace, not only a line break: a
`\n`/`\r\n` inserted mid-token, MIME's fixed 76-character line wrapping once
the encoded form is longer than that, a single space or tab dropped mid-token,
or a newline followed by indentation (an RFC 5322 folded header, an indented
log dump, a YAML/PEM block) all put one or more bytes in the middle of the
needle that the needle itself does not contain, and a literal substring
search cannot see across any of them -- reproduced as 48 misses for a
newline-split needle and 2 for MIME-wrapped hex of a 40-char secret (checker
probe, at347 cycle 2), and separately for space/tab/indent splits (checker
probe, cycle 1 of this unit: newline caught, space and newline+4-space indent
both missed).

Split out of `core.redact_fold` (which was already at 292 of its 300-line C2
cap) rather than folded in inline, for the same reason `redact_encodings` was
split out in AT-352 cycle 2: a distinct concern -- this one widens by
stripping whitespace from the TEXT side, never the secret -- with its own
docstring and its own tests (`tests/test_redact_wrap_perf.py`).

AT-611: `is_ignorable_char` (moved here, was `redact_fold._is_ignorable`) and
its `_DEFAULT_IGNORABLE` table moved for the same C2 line-cap reason, and
because the fix below is the same shape as the whitespace fix above -- a
widening of what a per-character scan considers cheap, not what it matches.
The checker measured CJK-heavy text at ~8.4 s/MB against ~2 s/MB for ASCII:
the old `functools.lru_cache(maxsize=4096)` thrashed once a string's distinct
code points (CJK Unified Ideographs alone is ~21,000) exceeded the cache,
paying eviction-list overhead on top of every miss. The fix replaces the
cache with a range table over the Basic Multilingual Plane, computed ONCE at
import time from the exact same `unicodedata.category` + `_DEFAULT_IGNORABLE`
union the old per-character check used, so it is derived, not hand-duplicated.
`is_ignorable_char` then answers with one `bisect` lookup and no
`unicodedata` call at all for any BMP code point, so a document with 20,000
distinct characters costs the same per character as one with 20. Code points
above the BMP (astral emoji, historic scripts, CJK Extension B and further)
fall back to the original direct computation, uncached -- rare enough in
practice that this is not the path the CJK-heavy regression measured.
"""

from __future__ import annotations

import bisect
import re
import unicodedata
from collections.abc import Sequence

from autotester.core.redact_encodings import declared_secret_encodings

_WHITESPACE_RE = re.compile(r"\s+")

_DEFAULT_IGNORABLE = (
    (0x00AD, 0x00AD), (0x034F, 0x034F), (0x061C, 0x061C), (0x115F, 0x1160),
    (0x17B4, 0x17B5), (0x180B, 0x180F), (0x200B, 0x200F), (0x202A, 0x202E),
    (0x2060, 0x206F), (0x3164, 0x3164), (0xFE00, 0xFE0F), (0xFEFF, 0xFEFF),
    (0xFFA0, 0xFFA0), (0xFFF0, 0xFFF8), (0x1BCA0, 0x1BCA3), (0x1D173, 0x1D17A),
    (0xE0000, 0xE0FFF),
)
"""Unicode's `Default_Ignorable_Code_Point` ranges — the code points a
conforming renderer draws as nothing.

These ranges are only PART of what `is_ignorable_char` strips; the `Cf` and
`Cc` categories carry the rest.

AT-351: the first version of this fold stripped `unicodedata.category(c) ==
"Cf"`, which covers U+200B and the bidi controls but NOT U+034F (combining
grapheme joiner) or U+FE00 to U+FE0F (variation selectors). Those are category
`Mn`, they survived the strip and NFKC, and a checker measured them rendering
at 192.5px against a 192.5px plain-credential control — pixel-identical — then
read the credential off the home index in a real browser. Same defect as
AT-345, one code point sideways, on the line AT-345 had just rewritten.

The test has to be INVISIBILITY, not a category -- and the reason is a LEAK,
not the text corruption first claimed here. `fold_credential` only ever
compares; it never rewrites stored text. What stripping all of `Mn` does is
fold the two sides ASYMMETRICALLY, because a stored value tends to carry a
precomposed character while a hostile input carries a decomposed one:

    stored `CAFE_QUILT_APIKEY_31` with a precomposed U+00C9, versus the same
    value spelled `E` + U+200B + combining acute --
      keying on invisibility: both fold to `cafequiltapikey31` (e-acute), MATCH
      stripping all `Mn`:      the spelled form loses its accent,          MISS

which reopens the very class of bypass this fold exists to close. Arabic
shadda U+0651, Devanagari vowel signs and combining acute U+0301 are all `Mn`
and all visible. Python exposes no `Default_Ignorable_Code_Point` predicate, so
the ranges are listed."""

_BMP_LIMIT = 0xFFFF


def _build_bmp_ignorable_ranges() -> tuple[tuple[int, int], ...]:
    """One-time table build (~30 ms, measured): mark every Basic Multilingual
    Plane code point that is category `Cf`/`Cc` or inside a
    `_DEFAULT_IGNORABLE` range, then collapse the marks into sorted
    `(start, end)` runs for `is_ignorable_char`'s `bisect` lookup.

    AT-611: order matters for speed here, not just correctness. A `bytearray`
    flag pass over `_DEFAULT_IGNORABLE` FIRST, then exactly one
    `unicodedata.category` call per code point -- never `any(...)` over
    `_DEFAULT_IGNORABLE` inside the 65536-iteration hot loop -- is what keeps
    this near the cost of the category scan alone: measured 0.20 s for the
    naive "category call plus 17-range scan, every iteration" version against
    0.03 s for this one, for the identical 21-range result.
    """
    flags = bytearray(_BMP_LIMIT + 1)
    for low, high in _DEFAULT_IGNORABLE:
        if low > _BMP_LIMIT:
            continue
        for code in range(low, min(high, _BMP_LIMIT) + 1):
            flags[code] = 1
    for code in range(_BMP_LIMIT + 1):
        if not flags[code] and unicodedata.category(chr(code)) in ("Cf", "Cc"):
            flags[code] = 1

    ranges: list[tuple[int, int]] = []
    start: int | None = None
    for code, flag in enumerate(flags):
        if flag and start is None:
            start = code
        elif not flag and start is not None:
            ranges.append((start, code - 1))
            start = None
    if start is not None:
        ranges.append((start, _BMP_LIMIT))
    return tuple(ranges)


_BMP_IGNORABLE_RANGES = _build_bmp_ignorable_ranges()
_BMP_IGNORABLE_STARTS = tuple(low for low, _high in _BMP_IGNORABLE_RANGES)


def is_ignorable_char(ch: str) -> bool:
    """True when `ch` cannot be part of the credential a human reads off the
    page, so it must not change whether text matches one.

    AT-353, and the name is deliberately no longer `_is_invisible`. That name
    was a promise the code did not keep and, worse, a promise that was not even
    the right one: U+0001 and U+007F render as a visible BOX in Chromium
    (measured 348px and 356.9px against a 192.5px control), so "renders as
    nothing" was never the real rule. Three times this guard failed at this
    line, and twice the reason was that the implementation was chasing a
    mis-stated rule.

    The rule that actually holds: none of these characters can carry meaning a
    reader takes off the screen, and all of them can be inserted between the
    characters of a credential. U+0000 is the sharpest case — it needs no
    decoding by the reader at all, because the HTML parser DELETES it, so the
    page renders the credential in plain type.

    AT-606: `@lru_cache`d -- pure per-character function, called once per char
    of every string folded (measured superlinear: 11.8 s at 518 KB).

    AT-611: the cache above thrashed on CJK-heavy text -- a working set of
    distinct code points (CJK Unified Ideographs alone is ~21,000) many times
    the cache's 4096 entries, so it paid eviction overhead on top of every
    miss (~8.4 s/MB, only ~1.1x faster than pre-AT-606). Moved to
    `redact_wrap` and rewritten as a `bisect` lookup against a precomputed BMP
    range table -- no cache, no `unicodedata` call, for any BMP code point.
    Code points above the BMP keep the original direct computation (rare in
    practice, and not the path the CJK regression measured).
    """
    code = ord(ch)
    if code <= _BMP_LIMIT:
        idx = bisect.bisect_right(_BMP_IGNORABLE_STARTS, code) - 1
        return idx >= 0 and code <= _BMP_IGNORABLE_RANGES[idx][1]
    if unicodedata.category(ch) in ("Cf", "Cc"):
        return True
    return any(low <= code <= high for low, high in _DEFAULT_IGNORABLE)


def contains_wrapped_encoding(
    text: str, widened_secrets: Sequence[tuple[str, str]], min_raw_len: int,
) -> bool:
    r"""True when a declared secret's exact encoding (base64/base32/hex, from
    `declared_secret_encodings`) is present in `text` once every run of
    whitespace is removed -- catching a needle split by a single mid-token
    newline, by MIME's fixed-width wrapping, by a bare space or tab, or by a
    newline followed by indentation (RFC 5322 header folding, an indented log
    dump, a YAML/PEM block), none of which the unwrapped exact search in
    `redact_fold._contains_folded_secret` can see (AT-599).

    Widened from line-breaks-only to `\s+` in cycle 2: a checker's repro
    showed a needle split by a plain space or by a newline-plus-indent both
    still evaded the line-break-only strip, because neither is a `\r`/`\n`
    itself -- the earlier version searched for `\r\n|\r|\n` and left every
    other whitespace character untouched, so a run of `\n    ` (newline then
    4-space indent) removed only the newline and left the spaces splitting the
    needle in two.

    Deliberately unscoped to runs that already look encoded: every whitespace
    run in `text` is collapsed away, not only ones sitting inside something
    that already looks like base64/hex, because a wrapped needle by
    definition does not look like one yet on either side of the split. This
    does not widen the false-positive surface the way folding does -- the
    needle stays an exact, case-significant substring of a real secret's own
    computed encoding, so an accidental collision with ordinary wrapped prose
    needs the exact needle bytes to reappear right at the join, which is what
    `test_line_wrapped_benign_prose_has_no_false_positive` and
    `test_space_separated_benign_prose_has_no_false_positive` guard.

    Cheap on the common case: a `text` with no whitespace at all returns
    `False` before doing any work, so a caller that always asks this question
    pays nothing extra on the vast majority of real payloads.
    """
    if not _WHITESPACE_RE.search(text):
        return False
    unwrapped = _WHITESPACE_RE.sub("", text)
    return any(
        needle in unwrapped
        for raw_value, _folded in widened_secrets
        if len(raw_value) >= min_raw_len
        for needle in declared_secret_encodings(raw_value)
    )
