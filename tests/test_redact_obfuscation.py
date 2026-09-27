"""Regression suite for core.redact's obfuscated/encoded-spelling immunity.

AT-347 (the model-prompt gate was not fold-aware), AT-352 (encoded/reversed
spellings), and AT-356 (visible combining marks) across three fix cycles --
see qa/manifests/at347-352-356-redact-fold.md for the full history. Split out
of test_core.py (AT-352 cycle 3 -- that file crossed the C2 300-line cap; this
suite is one coherent, still-growing concern distinct from the Redactor/
placeholder basics that stay in test_core.py). Synthetic fake secrets only.
"""

from __future__ import annotations

import base64
import binascii

import pytest

from autotester.core.redact import (
    ASCII_CONFUSABLES,
    Redactor,
    assert_no_raw_secrets,
    fold_credential,
)

# Synthetic fake secret used throughout this repo's fold-coverage tests/evidence
# (AT-339/AT-345/AT-346/AT-351) -- not a real credential.
CRED = "ZEBRA_QUILT_APIKEY_31"


def _interleave(text: str, mark: str) -> str:
    return mark.join(text)


def test_fold_credential_strips_visible_combining_marks_after_decomposition() -> None:
    # AT-356: U+0301 (combining acute) and U+0335 (combining short stroke
    # overlay) interleaved between every character render as a struck-through
    # or accented but perfectly readable credential in a real browser. Neither
    # is Default_Ignorable (unlike AT-351's U+034F/variation selectors), so
    # they must be handled by NFKD-decompose-then-strip-Mn, not by
    # `_is_ignorable`.
    plain_fold = fold_credential(CRED)
    assert fold_credential(_interleave(CRED, "́")) == plain_fold
    assert fold_credential(_interleave(CRED, "̵")) == plain_fold


def test_fold_credential_keeps_precomposed_and_decomposed_accents_symmetric() -> None:
    # AT-351's own scenario must stay fixed: a precomposed accented stored
    # value and the same value spelled with a decomposed combining accent
    # still fold identically (both now fold to the bare letter, which is
    # STRONGER than AT-351's original "both fold to the accented letter"
    # resolution, but the equality -- the property AT-351 needed -- holds).
    precomposed = "CAFÉ_QUILT_APIKEY_31"  # accented E precomposed
    # E + combining acute, as an explicit \u0301 escape -- a raw combining
    # char here gets NFC-normalised back to precomposed on save (AT-347 cycle 4).
    decomposed = "CAFE\u0301_QUILT_APIKEY_31"
    assert decomposed != precomposed  # never again silently compare a string with itself
    assert fold_credential(precomposed) == fold_credential(decomposed)


@pytest.mark.parametrize(
    "label,payload",
    [
        ("base64", base64.b64encode(CRED.encode()).decode()),
        ("base32", base64.b32encode(CRED.encode()).decode()),
        ("hex", binascii.hexlify(CRED.encode()).decode()),
        ("html-dec-entities", "".join(f"&#{ord(c)};" for c in CRED)),
        ("html-hex-entities", "".join(f"&#x{ord(c):X};" for c in CRED)),
        ("double-percent", "".join(f"%25{ord(c):02X}" for c in CRED)),
        ("plain-reversed", CRED[::-1]),
    ],
)
def test_contains_folded_catches_encoded_and_reversed_spellings(label: str, payload: str) -> None:
    # AT-352: each of these six spellings used to sail past `contains_folded`
    # -- the UI intake door -- because it folded only the literal text.
    redactor = Redactor({"DEMO_PASSWORD": CRED})
    assert redactor.contains_folded(payload), f"{label} bypassed contains_folded"


@pytest.mark.parametrize(
    "label,payload",
    [
        ("base64", base64.b64encode(CRED.encode()).decode()),
        ("base32", base64.b32encode(CRED.encode()).decode()),
        ("hex", binascii.hexlify(CRED.encode()).decode()),
        ("html-dec-entities", "".join(f"&#{ord(c)};" for c in CRED)),
        ("html-hex-entities", "".join(f"&#x{ord(c):X};" for c in CRED)),
        ("double-percent", "".join(f"%25{ord(c):02X}" for c in CRED)),
        ("plain-reversed", CRED[::-1]),
        ("combining-acute", _interleave(CRED, "́")),
        ("combining-short-stroke", _interleave(CRED, "̵")),
    ],
)
def test_assert_no_raw_secrets_blocks_obfuscated_spelling_in_prompt_text(
    label: str, payload: str,
) -> None:
    # AT-347: assert_no_raw_secrets is the hard gate before a model prompt
    # (browser/secrets.py::guard_prompt's only caller path) and was never
    # taught to fold, so any of these spellings reached an external provider
    # verbatim. Embedded inside a larger sentence, matching how a real prompt
    # looks -- a bare payload alone is not the realistic caller shape.
    text = f"Here is some context: {payload} -- please proceed."
    with pytest.raises(ValueError, match="raw secret"):
        assert_no_raw_secrets(text, [CRED])


@pytest.mark.parametrize(
    "label,text",
    [
        ("filename_b64.png", f"filename_{base64.b64encode(CRED.encode()).decode()}.png"),
        ("prefix_b64_suffix", f"prefix_{base64.b64encode(CRED.encode()).decode()}_suffix"),
        ("prefix-b64-suffix", f"prefix-{base64.b64encode(CRED.encode()).decode()}-suffix"),
        ("prefixXXb64YYsuffix", f"prefixXX{base64.b64encode(CRED.encode()).decode()}YYsuffix"),
        ("tok_b64_end", f"tok_{base64.b64encode(CRED.encode()).decode()}_end"),
        ("SECRETb32CODE", f"SECRET{base64.b32encode(CRED.encode()).decode()}CODE"),
        ("cafe_hex_beef", f"cafe{CRED.encode().hex()}beef"),
        ("abc_hex_def", f"abc{CRED.encode().hex()}def"),
    ],
)
def test_contains_folded_catches_encoded_secret_next_to_its_own_alphabet(
    label: str, text: str,
) -> None:
    # AT-352 cycle 2 (checker cycle-1 FAIL, both verdicts): the cycle-1 fix
    # scanned `text` for base64/base32/hex-SHAPED runs and tried to decode
    # them, but the greedy token regex swallowed adjacent alphanumeric
    # characters (a filename's `_`/`-`, a variable-name-style prefix/suffix)
    # into one oversized run that never decoded, so the credential inside it
    # was never recovered. Fixed by searching for the SECRET's own
    # precomputed encodings as an exact substring instead -- immune to
    # whatever sits next to it.
    redactor = Redactor({"DEMO_PASSWORD": CRED})
    assert redactor.contains_folded(text), f"{label} bypassed contains_folded"


@pytest.mark.parametrize(
    "label,text",
    [
        ("filename_b64.png", f"filename_{base64.b64encode(CRED.encode()).decode()}.png"),
        ("prefix_b64_suffix", f"prefix_{base64.b64encode(CRED.encode()).decode()}_suffix"),
        ("prefix-b64-suffix", f"prefix-{base64.b64encode(CRED.encode()).decode()}-suffix"),
        ("prefixXXb64YYsuffix", f"prefixXX{base64.b64encode(CRED.encode()).decode()}YYsuffix"),
        ("tok_b64_end", f"tok_{base64.b64encode(CRED.encode()).decode()}_end"),
        ("SECRETb32CODE", f"SECRET{base64.b32encode(CRED.encode()).decode()}CODE"),
        ("cafe_hex_beef", f"cafe{CRED.encode().hex()}beef"),
        ("abc_hex_def", f"abc{CRED.encode().hex()}def"),
    ],
)
def test_assert_no_raw_secrets_blocks_encoded_secret_next_to_its_own_alphabet(
    label: str, text: str,
) -> None:
    # Same 8 adjacency cases, through the model-prompt gate this time --
    # both doors share `_contains_folded_secret`, but each has its own test
    # so a regression in either caller's wiring is caught directly.
    with pytest.raises(ValueError, match="raw secret"):
        assert_no_raw_secrets(text, [CRED])


def test_ascii_confusables_still_importable_from_redact() -> None:
    # A checker (verdict .b, "Also noted") caught this live: splitting the
    # fold internals into core.redact_fold in cycle 1 dropped ASCII_CONFUSABLES
    # from core.redact's public surface, breaking `from autotester.core.redact
    # import ASCII_CONFUSABLES` even though no in-tree caller used it at the
    # time. Re-exported now; this pins it so the next split doesn't repeat it.
    assert ASCII_CONFUSABLES[ord("\u0430")] == "a"  # Cyrillic a -> Latin a, spot check


def test_assert_no_raw_secrets_does_not_false_positive_on_ordinary_prose() -> None:
    # The widened check must not turn every unrelated model prompt into a
    # run-killing exception -- the false-positive-rate concern AT-347's own
    # issue text raised. MIN_FOLDED_LEN and the byte-level word-boundary
    # requirement of the actual secret keep ordinary text clean.
    prose = (
        "You are grading a student essay for clarity and structure. "
        "Respond with a JSON object containing a score and a short rationale."
    ) * 5
    assert_no_raw_secrets(prose, [CRED])  # must not raise


def test_assert_no_raw_secrets_short_secret_stays_floorless_on_exact_match() -> None:
    # AT-002, preserved: MIN_FOLDED_LEN only gates the WIDENED (folded/
    # obfuscated) check. A short secret is still refused byte-exact.
    assert_no_raw_secrets("nothing secret here", ["ab"])
    with pytest.raises(ValueError, match="raw secret"):
        assert_no_raw_secrets("value=ab", ["ab"])


# -- Cycle 3: both cycle-2 verdicts FAILed on three gaps in the same exact- --
# -- encoding search mechanism (fold-floor starvation, missing base32       --
# -- alignment, missing base32 case). Synthetic secrets only.               --

SHORT_SECRET = "Zq7!kP2x"  # 8 raw chars, but folds to 7 (punctuation stripped)
ALIGN_SECRET = "Sup3rS3cretValue!42"  # matches the checkers' own cycle-2/3 repro


@pytest.mark.parametrize(
    "label,payload",
    [
        ("b64", base64.b64encode(SHORT_SECRET.encode()).decode()),
        ("b32", base64.b32encode(SHORT_SECRET.encode()).decode()),
        ("hex", SHORT_SECRET.encode().hex()),
    ],
)
def test_contains_folded_catches_short_fold_secret_isolated_encoding(
    label: str, payload: str,
) -> None:
    # AT-352/AT-347 cycle 3 (both verdicts): Redactor.__init__ used to
    # pre-filter `widened_secrets` to secrets whose FOLDED form was at least
    # MIN_FOLDED_LEN long, before the exact-encoding search ever ran -- so a
    # declared secret with one punctuation mark ("Zq7!kP2x" is 8 raw chars,
    # folds to 7) got NO encoding protection, not even isolated. The exact
    # search is now gated on the RAW value's length instead.
    redactor = Redactor({"SHORT": SHORT_SECRET})
    assert redactor.contains_folded(payload), f"{label} bypassed contains_folded"


@pytest.mark.parametrize(
    "label,payload",
    [
        ("b64", base64.b64encode(SHORT_SECRET.encode()).decode()),
        ("b32", base64.b32encode(SHORT_SECRET.encode()).decode()),
        ("hex", SHORT_SECRET.encode().hex()),
    ],
)
def test_assert_no_raw_secrets_blocks_short_fold_secret_isolated_encoding(
    label: str, payload: str,
) -> None:
    # Same gap, through the model-prompt gate.
    with pytest.raises(ValueError, match="raw secret"):
        assert_no_raw_secrets(payload, [SHORT_SECRET])


@pytest.mark.parametrize("prefix_len", [0, 1, 2, 3, 4])
def test_contains_folded_catches_base32_at_every_byte_alignment_offset(
    prefix_len: int,
) -> None:
    # AT-352 cycle 3 (verdict .b): base32 groups 5 bytes into 8 characters, so
    # a secret co-encoded into ONE base32 blob together with `prefix_len`
    # bytes of other material shifts through 5 possible byte offsets (0-4),
    # not base64's 3. Cycle 2 computed only the isolated encoding (offset 0),
    # so prefix lengths 1-4 all bypassed. Critically, this RE-ENCODES
    # `prefix + secret` as ONE `base64.b32encode` call -- wrapping an
    # independently-encoded isolated secret in literal surrounding text (as
    # cycle 2's own `SECRETb32CODE`-style tests did) never exercises
    # alignment at all, which is exactly why cycle 2's tests missed this.
    prefix = b"x" * prefix_len
    combined = base64.b32encode(prefix + ALIGN_SECRET.encode()).decode()
    redactor = Redactor({"ALIGN": ALIGN_SECRET})
    assert redactor.contains_folded(combined), f"prefix_len={prefix_len} bypassed contains_folded"


@pytest.mark.parametrize("prefix_len", [0, 1, 2, 3, 4])
def test_assert_no_raw_secrets_blocks_base32_at_every_byte_alignment_offset(
    prefix_len: int,
) -> None:
    # Same 5-offset base32 alignment check, through the model-prompt gate.
    prefix = b"x" * prefix_len
    combined = base64.b32encode(prefix + ALIGN_SECRET.encode()).decode()
    with pytest.raises(ValueError, match="raw secret"):
        assert_no_raw_secrets(combined, [ALIGN_SECRET])


def test_contains_folded_catches_lowercase_base32_isolated() -> None:
    # AT-352 cycle 3 (verdict primary): base32 needles were uppercase only
    # (`base64.b32encode`'s own default output). Lowercase base32 is genuinely
    # different bytes -- `b32decode` only accepts it via `casefold=True` on
    # decode, which the exact-encoding search does not do (and should not,
    # the same way base64 stays case-significant) -- so it needs its own
    # needle, not a decode-time accommodation.
    lower = base64.b32encode(ALIGN_SECRET.encode()).decode().lower()
    redactor = Redactor({"ALIGN": ALIGN_SECRET})
    assert redactor.contains_folded(lower)


def test_assert_no_raw_secrets_blocks_lowercase_base32_isolated() -> None:
    lower = base64.b32encode(ALIGN_SECRET.encode()).decode().lower()
    with pytest.raises(ValueError, match="raw secret"):
        assert_no_raw_secrets(lower, [ALIGN_SECRET])


def test_hex_needles_unchanged_no_mixed_case_variant_added() -> None:
    # Do NOT change hex this cycle (per the fix brief -- the mixed-case-hex
    # claim from one of the two cycle-2 verdicts did not reproduce under the
    # coordinator's own re-check). Pin the two existing needles (lower, upper)
    # so a future cycle doesn't accidentally widen or narrow hex while working
    # on base32 nearby.
    from autotester.core.redact_encodings import declared_secret_encodings

    hexed = ALIGN_SECRET.encode().hex()
    needles = declared_secret_encodings(ALIGN_SECRET)
    assert hexed in needles
    assert hexed.upper() in needles
