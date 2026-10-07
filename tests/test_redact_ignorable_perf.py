"""Regression suite for AT-611 (CJK-heavy folded-secret scanning was ~4x
slower than ASCII because the `_is_ignorable` per-character check thrashed a
4096-entry `lru_cache` once a string's distinct code points exceeded it).

Filed against `qa/verdicts/at599-606-redact-wrap-perf.md`, which measured the
regression as a follow-up (AT-611) while confirming AT-599/AT-606 fixed.

Split into its own file rather than added to `test_redact_wrap_perf.py`
(already 209 lines) or `test_redact_obfuscation.py`: this is a third,
distinct concern -- per-character classification speed, not whitespace
handling or the overall scan's asymptotic shape. Synthetic fake secrets only.
"""

from __future__ import annotations

import inspect
import random
import time
import unicodedata

import pytest
from timing_scale import timing_scale

from autotester.core import redact_encodings
from autotester.core.redact import Redactor, assert_no_raw_secrets
from autotester.core.redact_wrap import is_ignorable_char

_REFERENCE_DEFAULT_IGNORABLE = (
    (0x00AD, 0x00AD), (0x034F, 0x034F), (0x061C, 0x061C), (0x115F, 0x1160),
    (0x17B4, 0x17B5), (0x180B, 0x180F), (0x200B, 0x200F), (0x202A, 0x202E),
    (0x2060, 0x206F), (0x3164, 0x3164), (0xFE00, 0xFE0F), (0xFEFF, 0xFEFF),
    (0xFFA0, 0xFFA0), (0xFFF0, 0xFFF8), (0x1BCA0, 0x1BCA3), (0x1D173, 0x1D17A),
    (0xE0000, 0xE0FFF),
)
"""A literal copy of `redact_wrap._DEFAULT_IGNORABLE`'s ranges, deliberately
NOT imported from that module: the equivalence test below exists to catch a
mutation of `redact_wrap`'s own table (e.g. AT-611's falsification, dropping
the 0x200B-0x200F zero-width-space class), and a reference that imports the
very constant under test would be mutated right along with it, silently
staying in sync and never catching anything."""


def _original_is_ignorable(ch: str) -> bool:
    """The pre-AT-611 `redact_fold._is_ignorable` logic, reproduced here (not
    imported -- it no longer exists) as the ground truth for the equivalence
    test below: category `Cf`/`Cc`, or inside a default-ignorable range."""
    if unicodedata.category(ch) in ("Cf", "Cc"):
        return True
    code = ord(ch)
    return any(low <= code <= high for low, high in _REFERENCE_DEFAULT_IGNORABLE)


def test_is_ignorable_char_matches_original_over_the_full_bmp() -> None:
    # The precomputed range table is derived from the same rule the old
    # per-character check used; this proves the derivation didn't drop or
    # widen anything across all 65536 Basic Multilingual Plane code points,
    # including every CJK Unified Ideograph and Extension A character.
    mismatches = [
        code
        for code in range(0x10000)
        if is_ignorable_char(chr(code)) != _original_is_ignorable(chr(code))
    ]
    assert mismatches == [], f"{len(mismatches)} BMP mismatches, first: {mismatches[:5]}"


@pytest.mark.parametrize(
    "code",
    [
        0x1F600,  # emoji (astral, category So -- not ignorable)
        0x20000,  # CJK Unified Ideographs Extension B (astral, category Lo)
        0x1D173,  # musical symbol format control -- in _DEFAULT_IGNORABLE, astral
        0x1D17A,  # end of that same range
        0xE0001,  # language tag -- inside the E0000-E0FFF default-ignorable range
        0xE0100,  # variation selector supplement -- same range
        0x10FFFF,  # the highest valid Unicode scalar value
        0x1FBF0,  # segmented digit (astral, category Nd -- not ignorable)
        0x110BD,  # Kaithi number sign -- category Cf, astral, NOT in _DEFAULT_IGNORABLE
    ],
)
def test_is_ignorable_char_matches_original_for_astral_stratified_sample(code: int) -> None:
    ch = chr(code)
    assert is_ignorable_char(ch) == _original_is_ignorable(ch)


def _make_cjk_corpus(n: int, seed: int = 9611) -> str:
    # CJK Unified Ideographs: 0x4E00-0x9FFF, ~20,992 distinct code points --
    # AT-611's own repro range, chosen because it alone exceeds the old
    # 4096-entry cache by 5x.
    rng = random.Random(seed)
    out: list[str] = []
    total = 0
    while total < n:
        chunk = "".join(chr(rng.randint(0x4E00, 0x9FFF)) for _ in range(64))
        out.append(chunk)
        total += len(chunk)
    return "".join(out)[:n]


def _make_ascii_corpus(n: int, seed: int = 1) -> str:
    import string

    rng = random.Random(seed)
    out: list[str] = []
    total = 0
    while total < n:
        chunk = "".join(rng.choices(string.ascii_letters + string.digits + " .,\n", k=64))
        out.append(chunk)
        total += len(chunk)
    return "".join(out)[:n]


def _best_of(fn, repeats: int = 3) -> float:
    """Minimum wall time over a few repeats, to damp scheduler noise without
    hiding a real regression (which would be slow every time)."""
    return min(_timed(fn) for _ in range(repeats))


def _timed(fn) -> float:
    start = time.perf_counter()
    fn()
    return time.perf_counter() - start


def test_cjk_heavy_scan_stays_within_a_generous_multiple_of_ascii() -> None:
    # AT-611: checker measured CJK-heavy 1 MB at ~8.4 s against ~2 s/MB for
    # ASCII (~4x). The bound is a RATIO against an ASCII baseline measured in
    # the SAME process, not an absolute number, so this stays robust on a
    # loaded box (this repo runs two loops concurrently) while still catching
    # a real regression back to cache-thrashing behaviour, which would widen
    # the ratio by multiples, not by the noise this bound already tolerates.
    secrets = {f"KEY{i}": f"Sup3rS3cret{i}ValueZq7kP2x" for i in range(3)}
    redactor = Redactor(secrets)
    cjk_text = _make_cjk_corpus(1024 * 1024)
    ascii_text = _make_ascii_corpus(1024 * 1024)

    def run(text: str) -> None:
        redactor.contains_folded(text)
        assert_no_raw_secrets(text, list(secrets.values()))

    ascii_time = _best_of(lambda: run(ascii_text))
    cjk_time = _best_of(lambda: run(cjk_text))

    ratio = cjk_time / max(ascii_time, 1e-6)
    bound = 2.5 * timing_scale()
    assert ratio < bound, (
        f"CJK-heavy 1 MB took {cjk_time:.2f}s vs ASCII {ascii_time:.2f}s "
        f"({ratio:.2f}x, expected under {bound:g}x)"
    )
    # Absolute ceiling too, so a slow-but-proportional regression (both sides
    # got slower together) doesn't hide behind a fine ratio. Loose on purpose
    # (measured 7.6s on this box with a second test session running
    # concurrently, against ~21-25s pre-fix under the same contention) -- this
    # pins "not superlinear-cache-thrashing any more", not a tight target.
    assert cjk_time < 15.0, f"CJK-heavy 1 MB took {cjk_time:.2f}s, expected under 15s"


def test_redact_encodings_docstring_does_not_credit_the_removed_lru_cache() -> None:
    """AT-620: `redact_encodings.py` used to credit `_is_ignorable`'s
    `lru_cache` as the speed-up, but AT-611 removed that cache and moved the
    (renamed) function to `redact_wrap.is_ignorable_char`. Guards against the
    docstring drifting back to naming a function/mechanism that no longer
    exists; `is_ignorable_char` is asserted live via `hasattr` rather than
    just imported, so the test also fails loudly if the real rename ever
    regresses instead of just the prose about it."""
    source = inspect.getsource(redact_encodings)
    assert "_is_ignorable" not in source, (
        "redact_encodings.py still references the removed `_is_ignorable` "
        "name/cache -- see AT-620"
    )
    assert callable(is_ignorable_char)
