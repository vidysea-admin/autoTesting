"""mongo-store M23, M25, M8: one contract suite over BOTH blob stores (file and fake-GridFS).

Every test runs against `FileBlobStore` and `MongoBlobStore` (the guard + the hand-written fake, no
socket). Mongo-only behaviour (revisions, the cache, the fence, fail-closed) is in test_blobs_mongo.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from blob_support import SECRET, MongoRig, file_count, tree
from fake_mongo import CANARY

from autotester.core.redact import Redactor
from autotester.core.safe_names import UnsafeName
from autotester.store.blobs import (
    BlobNotFound,
    BlobRefused,
    BlobStore,
    FileBlobStore,
)

PNG = b"\x89PNG\r\n\x1a\n" + bytes(range(256))


def clean() -> Redactor:
    return Redactor({"TEST_PASSWORD": SECRET})


@pytest.fixture(params=["file", "mongo"])
def rig(request: pytest.FixtureRequest, tmp_path: Path) -> Any:
    """(store, snapshot, count): a picture of all writes, and the stored revisions of a key."""
    if request.param == "file":
        root = tmp_path / "data"
        root.mkdir()
        store = FileBlobStore(root, redactor=clean)
        return store, lambda: tree(root, stamps=True), file_count(root)
    mongo = MongoRig(tmp_path, redactor=clean)
    return mongo.blobs, mongo.snapshot, mongo.count


def put(store: BlobStore, key: str = "p/runs/r1/s1.png", data: bytes = PNG, **kw: Any) -> Any:
    kw = {"kind": "screenshot", "masked": True, "content_type": "image/png", **kw}
    return store.put(key, data, **kw)


def test_put_get_round_trip_records_sha_kind_masked_and_content_type(rig: Any) -> None:
    store, _, _ = rig
    info = put(store)
    assert info.sha256 == hashlib.sha256(PNG).hexdigest()
    assert (info.size, info.kind, info.masked, info.content_type) == (
        len(PNG), "screenshot", True, "image/png")
    assert store.get("p/runs/r1/s1.png") == PNG
    assert store.stat("p/runs/r1/s1.png") == info


def test_an_unmasked_screenshot_is_refused_and_nothing_is_written(rig: Any) -> None:
    store, snapshot, _ = rig
    before = snapshot()
    with pytest.raises(BlobRefused):
        put(store, masked=False)
    assert snapshot() == before
    assert store.stat("p/runs/r1/s1.png") is None


def test_an_unmasked_non_screenshot_is_accepted_and_recorded_as_such(rig: Any) -> None:
    store, _, _ = rig
    info = put(store, "p/runs/r1/net.json", b"{}", kind="network", masked=False,
               content_type="application/json")
    assert (info.kind, info.masked) == ("network", False)
    assert store.stat("p/runs/r1/net.json").masked is False


def test_an_equal_put_is_a_no_op(rig: Any) -> None:
    store, snapshot, _ = rig
    first = put(store)
    if isinstance(store, FileBlobStore):  # make any rewrite visible: age every file's mtime
        for path in store._root.rglob("*"):
            path.is_file() and os.utime(path, ns=(10**9, 10**9))
    before = snapshot()
    assert put(store) == first
    assert snapshot() == before


def test_a_changed_put_replaces_the_content_and_leaves_exactly_one_revision(rig: Any) -> None:
    store, _, count = rig
    put(store)
    other = PNG + b"changed"
    info = put(store, data=other)
    assert store.get("p/runs/r1/s1.png") == other
    assert info.sha256 == hashlib.sha256(other).hexdigest()
    assert store.stat("p/runs/r1/s1.png") == info
    assert count("p/runs/r1/s1.png") == 1


def test_the_same_bytes_with_new_metadata_are_a_change_not_a_no_op(rig: Any) -> None:
    store, _, _ = rig
    put(store, "p/x.json", b"{}", kind="network", masked=False, content_type="application/json")
    info = put(store, "p/x.json", b"{}", kind="trace", masked=True, content_type="application/json")
    assert (store.stat("p/x.json").kind, store.stat("p/x.json").masked) == ("trace", True)
    assert info.kind == "trace"


def test_delete_removes_the_blob_and_reports_whether_it_existed(rig: Any) -> None:
    store, snapshot, count = rig
    put(store)
    assert store.delete("p/runs/r1/s1.png") is True
    assert store.stat("p/runs/r1/s1.png") is None
    assert store.delete("p/runs/r1/s1.png") is False
    with pytest.raises(BlobNotFound):
        store.get("p/runs/r1/s1.png")
    assert count("p/runs/r1/s1.png") == 0
    assert "s1.png" not in repr(snapshot())


def test_get_and_materialize_of_a_missing_key_raise_not_found(rig: Any) -> None:
    store, _, _ = rig
    for call in (store.get, store.materialize):
        with pytest.raises(BlobNotFound):
            call("p/none.png")
    assert store.stat("p/none.png") is None


@pytest.mark.parametrize("key", ["../x.png", "a/../b.png", "/abs.png", "C:/x.png", "a\\b.png",
                                 "a//b.png", "", "a/./b.png", "x\x00y.png"])
def test_an_unsafe_key_is_refused_before_any_write(rig: Any, key: str) -> None:
    store, snapshot, _ = rig
    before = snapshot()
    with pytest.raises(UnsafeName):
        put(store, key)
    assert snapshot() == before


@pytest.mark.parametrize("key", [
    ".work/ceo-bench/answers.json", ".work/blob-cache/x.png", "profiles/pathlynks/Default/x",
    "p/sources/s1/chunks/c0.json", "p/crawl_summaries/c1.json", ".env", "sub/.env",
    "p/.env.local", "p/ai/ai-report.xlsx", "p/ai/REPORT.XLSX", ".blobmeta/x.json"])
def test_data_that_never_moves_is_refused_and_nothing_is_written(rig: Any, key: str) -> None:
    """M25: ceo-bench, scratch, Chromium profiles, teaching chunks, summaries, .env, exports."""
    store, snapshot, _ = rig
    before = snapshot()
    with pytest.raises(BlobRefused):
        put(store, key, kind="dom", masked=True)
    assert snapshot() == before


def test_an_export_kind_is_refused(rig: Any) -> None:
    store, snapshot, _ = rig
    before = snapshot()
    with pytest.raises(BlobRefused):
        put(store, "p/report.html", b"<html>", kind="export", masked=True, content_type="text/html")
    assert snapshot() == before


@pytest.mark.parametrize("kind", ["", "Screenshot", "screen shot", "a/b", "x" * 40, "1x"])
def test_a_malformed_kind_is_refused(rig: Any, kind: str) -> None:
    store, snapshot, _ = rig
    before = snapshot()
    with pytest.raises(BlobRefused):
        put(store, "p/k.bin", b"x", kind=kind, masked=True)
    assert snapshot() == before


def test_a_non_bytes_body_is_refused(rig: Any) -> None:
    store, _, _ = rig
    with pytest.raises(BlobRefused):
        store.put("p/k.txt", "text", kind="dom", masked=True)  # type: ignore[arg-type]


PLANTS: list[tuple[str, Callable[[], dict[str, Any]]]] = [
    ("key", lambda: {"key": f"p/{SECRET}.png"}),
    ("content_type", lambda: {"content_type": f"image/{SECRET}"}),
    ("text body", lambda: {"key": "p/page.html", "data": f"<p>{SECRET}</p>".encode(),
                           "content_type": "text/html", "kind": "dom"}),
    ("json body", lambda: {"key": "p/n.json", "data": f'{{"t":"{SECRET}"}}'.encode(),
                           "content_type": "application/json", "kind": "network"}),
]


@pytest.mark.parametrize(("where", "plant"), PLANTS, ids=[p[0] for p in PLANTS])
def test_a_declared_secret_is_refused_everywhere_it_can_ride(rig: Any, where: str,
                                                             plant: Callable[[], dict[str, Any]]
                                                             ) -> None:
    """M8: key, metadata and a text body are gated; nothing is written; the error shows no value."""
    store, snapshot, _ = rig
    before = snapshot()
    with pytest.raises(BlobRefused) as err:
        put(store, **plant())
    assert SECRET not in str(err.value) and SECRET not in repr(err.value)
    assert snapshot() == before
    assert SECRET not in repr(snapshot())


def test_a_folded_or_encoded_secret_in_a_text_body_is_refused(rig: Any) -> None:
    import base64
    store, snapshot, _ = rig
    before = snapshot()
    body = base64.b64encode(SECRET.encode()).decode().encode()
    with pytest.raises(BlobRefused):
        put(store, "p/n.txt", body, kind="console", masked=True, content_type="text/plain")
    assert snapshot() == before


def test_binary_bytes_are_not_text_scanned_so_a_png_is_not_falsely_refused(rig: Any) -> None:
    store, _, _ = rig
    put(store, data=PNG + SECRET.encode()[:3])  # a short coincidence inside a PNG is not a leak
    assert store.get("p/runs/r1/s1.png").startswith(b"\x89PNG")


def test_the_redactor_is_asked_at_every_put_so_a_later_secret_is_seen(tmp_path: Path) -> None:
    held = {"v": Redactor({})}
    mongo = MongoRig(tmp_path, redactor=lambda: held["v"])
    for store in (mongo.blobs, FileBlobStore(tmp_path / "d", redactor=lambda: held["v"])):
        held["v"] = Redactor({})
        store.put("p/a.txt", b"hello", kind="console", masked=True, content_type="text/plain")
        held["v"] = Redactor({"K": "hello"})
        with pytest.raises(BlobRefused):
            store.put("p/b.txt", b"say hello", kind="console", masked=True,
                      content_type="text/plain")


def test_the_default_redactor_reads_the_repo_env(tmp_path: Path, monkeypatch: Any) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / ".env").write_text(f"PATHLYNKS_PASSWORD={CANARY}\n", encoding="utf-8")
    monkeypatch.setenv("AUTOTESTER_ROOT", str(root))
    for store in (FileBlobStore(root), MongoRig(tmp_path).blobs):
        with pytest.raises(BlobRefused):
            store.put("p/a.txt", f"x {CANARY}".encode(), kind="console", masked=True,
                      content_type="text/plain")
        store.put("p/ok.txt", b"fine", kind="console", masked=True, content_type="text/plain")


def test_a_file_store_ignores_a_sidecar_that_no_longer_matches_its_bytes(tmp_path: Path) -> None:
    """A crash between the sidecar and the data (or an edited file) must not lie about the sha."""
    store = FileBlobStore(tmp_path, redactor=clean)
    put(store)
    (tmp_path / "p/runs/r1/s1.png").write_bytes(b"edited behind its back")
    info = store.stat("p/runs/r1/s1.png")
    assert info.sha256 == hashlib.sha256(b"edited behind its back").hexdigest()
    assert (info.kind, info.masked) == ("unknown", False)  # nothing is claimed that is not known


def test_a_file_with_no_sidecar_reports_what_it_can_and_claims_no_mask(tmp_path: Path) -> None:
    (tmp_path / "p").mkdir()
    (tmp_path / "p" / "old.png").write_bytes(PNG)
    info = FileBlobStore(tmp_path, redactor=clean).stat("p/old.png")
    assert (info.content_type, info.kind, info.masked, info.size) == (
        "image/png", "unknown", False, len(PNG))
