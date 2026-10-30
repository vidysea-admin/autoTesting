"""mongo-store M25 and the `materialize` contract for `MongoBlobStore`: the verified local copy.

A reader never opens a state path: it gets a file from `.work/blob-cache/` whose bytes were hashed
against the recorded sha256, kept at 512 MB (here shrunk) by least-recently-used eviction.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from blob_support import KEY, MongoRig, clean, put, tree

from autotester.store.blobs import BlobCorrupt, BlobNotFound


def test_materialize_writes_a_verified_copy_that_keeps_the_extension(tmp_path: Path) -> None:
    rig = MongoRig(tmp_path, redactor=clean)
    put(rig, data=b"png-bytes")
    path = rig.blobs.materialize(KEY)
    assert path.name == "s1.png" and path.read_bytes() == b"png-bytes"
    assert rig.cache in path.parents


def test_a_cache_hit_does_not_download_again_and_a_tampered_copy_is_refetched(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rig = MongoRig(tmp_path, redactor=clean)
    put(rig, data=b"png-bytes")
    calls: list[str] = []
    real = type(rig.blobs)._verified
    monkeypatch.setattr(type(rig.blobs), "_verified",
                        lambda self, key, info: calls.append(key) or real(self, key, info))
    first = rig.blobs.materialize(KEY)
    assert rig.blobs.materialize(KEY) == first and len(calls) == 1
    first.write_bytes(b"tampered")
    assert rig.blobs.materialize(KEY).read_bytes() == b"png-bytes" and len(calls) == 2


def test_a_blob_whose_bytes_do_not_match_its_recorded_sha_is_corrupt(tmp_path: Path) -> None:
    rig = MongoRig(tmp_path, redactor=clean)
    put(rig, data=b"good")
    rig.files[0]["data"] = b"bad!"
    for read in (rig.blobs.materialize, rig.blobs.get):
        with pytest.raises(BlobCorrupt):
            read(KEY)
    assert not rig.cache.exists() or not tree(rig.cache)


def test_a_missing_key_does_not_create_a_cache(tmp_path: Path) -> None:
    rig = MongoRig(tmp_path, redactor=clean)
    with pytest.raises(BlobNotFound):
        rig.blobs.materialize(KEY)
    assert not rig.cache.exists()


def test_the_cache_evicts_the_least_recently_used_past_its_cap(tmp_path: Path) -> None:
    """M25 falsifier: a cache run past the cap must evict (oldest first), not grow."""
    rig = MongoRig(tmp_path, redactor=clean, cap=250)
    paths = []
    for i in range(3):
        put(rig, f"p/s{i}.png", bytes([65 + i]) * 100)
        paths.append(rig.blobs.materialize(f"p/s{i}.png"))
        os.utime(paths[-1], ns=(1_000_000_000 * (i + 1),) * 2)  # strictly increasing recency
    assert [p.exists() for p in paths] == [False, True, True]
    assert sum(len(b) for b in tree(rig.cache).values()) <= 250


def test_a_hit_refreshes_recency_so_the_touched_blob_survives(tmp_path: Path) -> None:
    rig = MongoRig(tmp_path, redactor=clean, cap=250)
    paths = {}
    for i in range(2):
        put(rig, f"p/s{i}.png", bytes([65 + i]) * 100)
        paths[i] = rig.blobs.materialize(f"p/s{i}.png")
        os.utime(paths[i], ns=(1_000_000_000 * (i + 1),) * 2)
    rig.blobs.materialize("p/s0.png")  # s0 is now the most recently used
    put(rig, "p/s2.png", b"C" * 100)
    rig.blobs.materialize("p/s2.png")
    assert paths[0].exists() and not paths[1].exists()


def test_a_blob_bigger_than_the_cap_is_still_served(tmp_path: Path) -> None:
    rig = MongoRig(tmp_path, redactor=clean, cap=10)
    put(rig, data=b"X" * 100)
    assert rig.blobs.materialize(KEY).read_bytes() == b"X" * 100


