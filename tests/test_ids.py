"""Tests for core.ids: content-addressed ids and ulid generation.

Split out of test_core.py (AT-352 cycle 3 -- that file crossed the C2
300-line cap growing the redact-obfuscation regression suite; ids is an
unrelated concept and belongs in its own file "split by responsibility",
per `autotester doctor`'s own message).
"""

from __future__ import annotations

import time

from autotester.core.ids import content_hash, content_id, run_id, ulid


def test_content_hash_ignores_key_order() -> None:
    assert content_hash({"a": 1, "b": 2}) == content_hash({"b": 2, "a": 1})


def test_content_id_is_prefixed_and_stable() -> None:
    first = content_id("case", {"x": 1})
    assert first.startswith("case_")
    assert first == content_id("case", {"x": 1})


def test_ulids_are_unique_and_time_ordered() -> None:
    ids = [ulid() for _ in range(50)]
    assert len(set(ids)) == 50
    assert all(len(i) == 26 for i in ids)
    # Ordering is by the 10-char millisecond prefix; ids from the same
    # millisecond are unordered by design (the remaining 16 chars are random).
    time.sleep(0.002)
    later = ulid()
    assert later[:10] >= max(i[:10] for i in ids)
    assert run_id().startswith("run_")
