"""U2 checker-B W1: `safe_key` gives the same answer on Windows and Linux (mongo-store M17).

A key that Windows would alias (trailing dot or space, a device name with any extension, a `:`
that is a drive letter, a stream or `nul:`) must be refused on every platform, so two keys that
collide on one OS can never both be stored on the other.
"""

from __future__ import annotations

import pytest

from autotester.core.safe_names import UnsafeName, safe_key

ALIASED = [
    "a/x.", "a/x ", "x.", "x ", "a/b./c", "a/b /c", "a/..x./y",
    "a/CON", "a/con", "a/Con.json", "a/nul.txt", "a/NUL.tar.gz", "a/PRN", "a/aux.log",
    "a/COM1", "a/com9.json", "a/LPT1", "a/lpt9.x", "a/CON .json", "CON", "a/COM\u00b9",
    "a:b", "a/b:stream", "nul:", "C:/x", "c:x", "a/C:/y", "a/b/c:",
    "a/b|c", "a/<x>", "a/q?", "a/s*", 'a/"q"', "a/tab\tx", "a/\x7f",
]


@pytest.mark.parametrize("key", ALIASED)
def test_a_windows_aliased_key_is_refused(key: str) -> None:
    with pytest.raises(UnsafeName):
        safe_key(key)


@pytest.mark.parametrize("prefix", ["a/CON/", "a/x./", "a/nul.txt/", "a:b", "a/b:", "a/x /"])
def test_a_complete_segment_of_a_prefix_is_judged_like_a_key(prefix: str) -> None:
    with pytest.raises(UnsafeName):
        safe_key(prefix, prefix=True)


@pytest.mark.parametrize("key", [
    "a/b.json", "projects/p/runs/r1/result.json", ".work/team/x.json", "a/.hidden", "a/b.c.d",
    "a/console.log", "a/COM0.json", "a/COM10", "a/LPT", "a/auxiliary", "a/nullable.json",
    "a/con2.json", "a/x y.json", "a/ b.json", "a/b-c_d~1.json", "a/...x",
])
def test_an_ordinary_key_is_accepted(key: str) -> None:
    assert safe_key(key) == key


@pytest.mark.parametrize("prefix", ["", "a/", "a", "p/co", "p/CON", "p/nul", "p/x.", "p/COM",
                                    "p/a b", "p/a "])
def test_a_partial_last_segment_of_a_prefix_may_be_the_start_of_a_longer_name(
        prefix: str) -> None:
    """`p/CON` is a prefix of `p/CONFIG.json`; only a finished segment is judged."""
    assert safe_key(prefix, prefix=True) == prefix
