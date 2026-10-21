"""C2 (T-218 answer list), the storage stage on its own: the size cap is pinned at its edge, and
simultaneous uploads for one project neither raise nor leave the list and its pin disagreeing."""

from __future__ import annotations

import hashlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from autotester.stages import bench_inputs

ONE = {"items": [{"id": "A1", "priority": "P0", "technique": "inbox"}]}


def _padded(size: int) -> bytes:
    """Valid JSON of exactly `size` bytes (trailing spaces)."""
    raw = json.dumps(ONE).encode()
    return raw + b" " * (size - len(raw))


def test_a_list_of_exactly_the_cap_is_accepted_and_one_byte_more_is_refused(
        tmp_path: Path) -> None:
    pin = bench_inputs.save_atomic_list("demo", _padded(bench_inputs.MAX_BYTES), "u@x.test",
                                        tmp_path)
    assert pin.bytes == bench_inputs.MAX_BYTES
    with pytest.raises(bench_inputs.ListRefused, match="larger than"):
        bench_inputs.save_atomic_list("demo", _padded(bench_inputs.MAX_BYTES + 1), "u@x.test",
                                      tmp_path)
    assert bench_inputs.load_pin("demo", tmp_path).sha256 == pin.sha256  # nothing changed


def test_simultaneous_uploads_leave_the_list_matching_its_pin_and_record_every_hash(
        tmp_path: Path) -> None:
    lists = [json.dumps({"items": [{"id": f"A{i}", "priority": "P1", "technique": "inbox"}]}
                        ).encode() for i in range(12)]
    gate = threading.Barrier(len(lists))

    def upload(raw: bytes) -> None:
        gate.wait()
        bench_inputs.save_atomic_list("demo", raw, "u@x.test", tmp_path)

    with ThreadPoolExecutor(max_workers=len(lists)) as pool:
        list(pool.map(upload, lists))  # an upload that raises fails the test here
    pin = bench_inputs.load_pin("demo", tmp_path)
    _atomic, pinned = bench_inputs.load_pinned_list("demo", tmp_path)  # re-hashes the stored file
    assert pinned == pin.sha256
    seen = {*pin.replaced_sha256, pin.sha256}
    assert seen == {hashlib.sha256(raw).hexdigest() for raw in lists}
