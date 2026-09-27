"""Exact encoded-spelling search: precompute how a declared secret would look
base64/base32/hex-encoded, so a caller can search RAW (unfolded) text for
those exact substrings.

Split out of `core.redact_fold` (AT-352 cycle 2; that module was about to
cross the C2 300-line cap adding this) because it is the opposite direction
from everything else there: `redact_fold` widens by DECODING/folding the
candidate TEXT; this module widens by ENCODING the SECRET and searching for
the result, which is what makes it immune to adjacency (see
`_declared_secret_encodings`'s docstring). `core.redact_fold` imports the one
name it needs from here; nothing outside that pair imports this module.
"""

from __future__ import annotations

import base64
from collections.abc import Callable


# AT-352 cycle 2 gave base64 exactly the treatment `_alignment_needles` below
# implements (as `_base64_alignment_needles`, generalised into this shared
# form in cycle 3) but left base32 with none -- `declared_secret_encodings`
# computed only the isolated `base64.b32encode(secret_bytes)`, with zero
# offset handling, so a secret embedded inside a byte stream that is
# base32-encoded AS ONE BLOB together with neighbouring bytes missed at 4 of
# the 5 possible byte offsets (prefix lengths 1-4 mod 5; only offset 0 --
# and its restatement at offset 5 -- happened to line up). A checker caught
# this precisely because the maker's own cycle-2 base32 tests wrapped an
# already-isolated encoding in literal surrounding text
# (`f"SECRET{b32encode(secret)}CODE"`), which any substring search catches
# trivially since the literal wrap never touches the encoding stream -- it
# never exercised alignment at all. Named "alignment offsets" in the fix
# brief; this is the same technique YARA's `base64` string modifier uses to
# find a known plaintext inside a base64 blob without knowing what surrounds
# it, generalised here to any encoding with a fixed byte-group size.
def _alignment_needles(
    secret_bytes: bytes, encoder: Callable[[bytes], bytes], group_bytes: int, group_chars: int,
) -> list[str]:
    r"""`group_bytes` alignment-offset substrings of `encoder(secret_bytes)`,
    each guaranteed to appear byte-for-byte in `encoder(anything containing
    secret_bytes as a contiguous run)` regardless of what the neighbouring
    bytes actually ARE -- only their COUNT (the byte offset mod `group_bytes`)
    matters, because every output character is a function of exactly the
    `group_bytes`-byte group it belongs to, never of any other byte. Base64
    groups 3 bytes into 4 characters (`group_bytes=3, group_chars=4`); base32
    groups 5 bytes into 8 characters (`group_bytes=5, group_chars=8`) -- one
    more possible offset than base64 has, 0-4 instead of 0-2. See the comment
    above this function for why base32 needed this and base64 already had it.

    For offset `o` in `range(group_bytes)`: pad `secret_bytes` with `o`
    leading zero bytes standing in for "whatever `o` unknown bytes precede the
    secret at runtime", then with just enough trailing zero bytes to reach a
    multiple of `group_bytes` (so `encoder` never emits `=` padding, which
    would only be correct if the secret were the END of the real message).
    The leading `group_chars`-character group is dropped whenever `o > 0` (it
    mixes bits from the unknown prefix bytes) and the trailing `group_chars`-
    character group is dropped whenever trailing padding was added (it mixes
    bits from the unknown suffix bytes). Coarse -- an entire group is
    discarded even where only some of its characters are actually affected --
    deliberately: correctness over a few extra characters of needle length.
    """
    needles = []
    for offset in range(group_bytes):
        padded = (b"\x00" * offset) + secret_bytes
        tail_pad = (-len(padded)) % group_bytes
        padded += b"\x00" * tail_pad
        encoded = encoder(padded).decode("ascii")
        start = group_chars if offset else 0
        end = len(encoded) - group_chars if tail_pad else len(encoded)
        core = encoded[start:end]
        if core:
            needles.append(core)
    return needles


def _isolated_variant_needles(raw: bytes) -> list[str]:
    """Isolated base32 (upper/lower, padded and `=`-stripped) and hex
    (upper/lower) encodings of `raw` alone, with no byte-alignment handling
    -- hex needs none (see `_utf16_hex_needles` below for why), and these
    isolated spellings cover the "the entire payload IS this one blob, with
    real `=` padding" case the alignment needles never emit (they always pad
    to a multiple of `group_bytes` with zero filler instead).

    Split out of `declared_secret_encodings` (AT-598) purely to free lines
    under its 50-line C2 cap for the two new needle families below -- what
    it returns for base32/hex is unchanged.
    """
    b32_upper = base64.b32encode(raw).decode("ascii")
    b32_lower = b32_upper.lower()
    hexed = raw.hex()
    return [
        b32_upper, b32_upper.rstrip("="), b32_lower, b32_lower.rstrip("="),
        hexed, hexed.upper(),
    ]


def _double_b64_needles(raw: bytes) -> list[str]:
    """AT-598: base64-of-base64 -- `raw` base64-encoded once (the isolated
    inner layer; a log-scrubbing double-encode operates on the secret alone,
    not on a byte run sharing neighbours before the FIRST pass), then
    base64-encoded AGAIN, standard and URL-safe, at the OUTER layer's 3
    byte-alignment offsets via the same `_alignment_needles` technique a
    single level already uses -- so a double-encoded blob sitting inside a
    longer base64 stream is still caught, the same adjacency immunity a
    single level has. The isolated whole-blob spelling of each outer
    encoding (real `=` padding) is included too, for when the double-encoded
    text IS the entire payload.

    Evidence this closes: at347 cycle-2 probe, 5/5 secret lengths missed
    (qa/verdicts/at347-352-356-redact-fold.md) -- `declared_secret_encodings`
    never looked past one level of UTF-8 encoding.
    """
    inner = base64.b64encode(raw)
    return [
        base64.b64encode(inner).decode("ascii"),
        base64.urlsafe_b64encode(inner).decode("ascii"),
        *_alignment_needles(inner, base64.b64encode, 3, 4),
        *_alignment_needles(inner, base64.urlsafe_b64encode, 3, 4),
    ]


def _utf16_hex_needles(value: str) -> list[str]:
    """AT-598: hex of `value` encoded as UTF-16-LE and UTF-16-BE bytes --
    realistic in Windows/PowerShell logs, which are UTF-16 internally, and
    missed entirely before this: `declared_secret_encodings` only ever
    encoded the UTF-8 bytes. No alignment needed, same reason plain hex
    needs none: hex is a 1-byte group, so it has no cross-byte adjacency to
    lose the way base64/base32's multi-byte groups do.

    Evidence this closes: at347 cycle-2 probe, 10/10 misses across the
    lengths tried (qa/verdicts/at347-352-356-redact-fold.md).
    """
    le_hex = value.encode("utf-16-le").hex()
    be_hex = value.encode("utf-16-be").hex()
    return [le_hex, le_hex.upper(), be_hex, be_hex.upper()]


def _utf16_b64_needles(value: str) -> list[str]:
    """AT-617: base64 (standard and URL-safe, at each of the 3 byte-alignment
    offsets, plus the isolated whole-blob spelling) of `value` encoded as
    UTF-16-LE and UTF-16-BE bytes -- the wire format PowerShell's
    `-EncodedCommand` produces (it base64-encodes a UTF-16-LE script). Missed
    entirely before this: `declared_secret_encodings` computed UTF-16 only as
    hex (`_utf16_hex_needles` above) and double-base64 only of the UTF-8 bytes
    (`_double_b64_needles` above) -- neither combination reaches "base64 of
    UTF-16 bytes". Same technique as every other multi-byte-group encoding
    here (see `_alignment_needles`): the isolated spelling covers "the whole
    payload IS base64(utf16(secret))"; the 3 offsets cover the secret sitting
    inside a longer base64 stream alongside unrelated UTF-16 code units on
    either side (e.g. more of a `-EncodedCommand` script).

    Evidence this closes: checker probe 2026-09-26 (AT-617) -- 8/8 fake
    secrets (lengths 8/16/28/26, LE and BE) missed by both
    `assert_no_raw_secrets` and `Redactor.contains_folded` on master AND on
    the at598 branch (pre-existing, not a regression).
    """
    needles: list[str] = []
    for utf16_bytes in (value.encode("utf-16-le"), value.encode("utf-16-be")):
        needles.append(base64.b64encode(utf16_bytes).decode("ascii"))
        needles.append(base64.urlsafe_b64encode(utf16_bytes).decode("ascii"))
        needles.extend(_alignment_needles(utf16_bytes, base64.b64encode, 3, 4))
        needles.extend(_alignment_needles(utf16_bytes, base64.urlsafe_b64encode, 3, 4))
    return needles


def declared_secret_encodings(value: str) -> list[str]:
    """Every exact encoded spelling of one declared secret worth searching
    for as a literal substring of raw, unfolded text: base64 (standard and
    URL-safe, at each of the 3 possible byte-alignment offsets, so padding
    never appears), base32 (standard and lowercase, at each of the 5 possible
    byte-alignment offsets, PLUS the plain isolated encoding of each case with
    and without `=` padding stripped, as an explicit belt-and-suspenders pair
    alongside the alignment needles -- see `_alignment_needles`), and hex
    (upper and lower; unchanged since cycle 2 -- a checker's cycle-3 mixed-
    case-hex claim did not reproduce, so hex is deliberately left alone this
    cycle).

    AT-352 cycle 2: searching for the SECRET's own precomputed encodings is
    exact and immune to adjacency -- unlike scanning `text` for base64/
    base32/hex-SHAPED runs and trying to decode them (cycle 1's approach,
    which lived in `core.redact_fold._obfuscated_spellings` and was removed),
    which over-matched into neighbouring alphanumeric characters (a filename's
    `_`/`-`, a token prefix/suffix) into one oversized run that decoded as
    nothing, so the credential escaped both `Redactor.contains_folded` and
    `assert_no_raw_secrets`. Deliberately NOT folded/case-normalised before
    the substring check: base64 is case-significant by construction (`A` and
    `a` encode different bits), so folding the candidate text first would
    destroy the very encoding it is trying to match.

    AT-352 cycle 3: base32 got neither case variants nor alignment offsets in
    cycle 2 -- only the isolated uppercase encoding, decoded with `casefold`
    in cycle 1's now-removed scanner but never re-added when the search
    direction flipped. Lowercase base32 is genuinely different bytes from
    uppercase (`base64.b32decode` accepts both only because it casefolds on
    the way IN; there is no such step on the way out), so it needs its own
    needles, generated through the same alignment machinery as the uppercase
    ones (`encoder=lambda b: base64.b32encode(b).lower()`) so a lowercase
    spelling gets the SAME adjacency immunity the uppercase one does, not a
    narrower one.

    AT-606 cycle 1's `@lru_cache` here was unproven and retained raw secrets in memory, so cycle 2
    drops it -- the speed-up now is `redact_wrap.is_ignorable_char`'s bisect table (AT-611).
    AT-617 added `_utf16_b64_needles` (see its own docstring for why).
    """
    raw = value.encode("utf-8")
    needles: list[str] = [
        *_alignment_needles(raw, base64.b64encode, 3, 4),
        *_alignment_needles(raw, base64.urlsafe_b64encode, 3, 4),
        *_alignment_needles(raw, base64.b32encode, 5, 8),
        *_alignment_needles(raw, lambda b: base64.b32encode(b).lower(), 5, 8),
    ]
    needles.extend(_isolated_variant_needles(raw))
    needles.extend(_double_b64_needles(raw))
    needles.extend(_utf16_hex_needles(value))
    needles.extend(_utf16_b64_needles(value))
    return [needle for needle in needles if needle]
