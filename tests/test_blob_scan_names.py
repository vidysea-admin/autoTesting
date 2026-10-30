"""mongo-store M54 (blob body scan is a deny-list) and M55 (hostile Windows names refused up front).

Both run against `FileBlobStore` and `MongoBlobStore` (the guard + the hand-written fake).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from blob_support import SECRET, MongoRig, tree

from autotester.core.redact import Redactor
from autotester.core.safe_names import UnsafeName, safe_key
from autotester.store.blobs import BlobRefused, FileBlobStore

PNG = b"\x89PNG\r\n\x1a\n" + bytes(range(128, 256))


def clean() -> Redactor:
    return Redactor({"TEST_PASSWORD": SECRET})


@pytest.fixture(params=["file", "mongo"])
def rig(request: pytest.FixtureRequest, tmp_path: Path) -> Any:
    """(store, write_root): every byte either store may write lives under write_root."""
    if request.param == "file":
        root = tmp_path / "data"
        root.mkdir()
        return FileBlobStore(root, redactor=clean), tmp_path
    mongo = MongoRig(tmp_path, redactor=clean)
    return mongo.blobs, tmp_path


SECRET_TYPES = ["application/ndjson", "application/jsonl", "application/sql", "application/toml",
                "application/x-sh", "text/csv", "multipart/form-data", "message/rfc822",
                "application/rtf", "", "text", "application/x-unknown", "TEXT/PLAIN; charset=utf-8"]


@pytest.mark.parametrize("ctype", SECRET_TYPES)
def test_a_secret_in_a_text_like_body_is_refused_whatever_the_declared_type(
        rig: Any, ctype: str) -> None:
    store, root = rig
    before = tree(root)
    with pytest.raises(BlobRefused) as err:
        store.put("p/runs/r1/dump.dat", f"row,{SECRET}\n".encode(), kind="console", masked=True,
                  content_type=ctype)
    assert SECRET not in str(err.value)
    assert tree(root) == before


@pytest.mark.parametrize("ctype", ["image/png", "video/webm", "audio/ogg", "application/pdf",
                                   "application/zip", "application/octet-stream"])
def test_a_utf8_body_is_scanned_even_under_a_binary_type(rig: Any, ctype: str) -> None:
    store, _ = rig
    with pytest.raises(BlobRefused):
        store.put("p/runs/r1/x.bin", SECRET.encode(), kind="source", masked=False,
                  content_type=ctype)


@pytest.mark.parametrize("ctype", ["image/png", "video/webm", "audio/ogg", "application/pdf",
                                   "application/zip", "application/octet-stream"])
def test_a_binary_body_under_a_binary_type_is_not_text_scanned(rig: Any, ctype: str) -> None:
    store, _ = rig
    body = PNG + SECRET.encode() + b"\xff\xfe"  # undecodable: the bytes are not text
    info = store.put("p/runs/r1/x.bin", body, kind="source", masked=False, content_type=ctype)
    assert info.size == len(body)


@pytest.mark.parametrize("ctype", ["application/ndjson", "", "text", "application/x-sh"])
def test_an_undecodable_body_under_a_text_like_type_is_still_scanned(rig: Any, ctype: str) -> None:
    store, _ = rig
    with pytest.raises(BlobRefused):
        store.put("p/runs/r1/y.dat", b"\xff\xfe" + SECRET.encode() + b"\xff", kind="console",
                  masked=True, content_type=ctype)


HOSTILE = ["PROFIL~1/x.png", "p/PROFIL~1/x.png", "p/PROFIL~1", "p/WORK~2.TXT",
           "a::$INDEX_ALLOCATION",
           "p/a::$INDEX_ALLOCATION/x.png", "p/foo:bar", "foo:bar", "p/nul", "p/con.png", "p/aux",
           "p/prn.txt", "p/com1", "p/lpt1.png", "nul", "p/NUL.tar.gz"]


@pytest.mark.parametrize("key", HOSTILE)
def test_every_blob_entry_point_refuses_a_hostile_name_before_any_io(rig: Any, key: str) -> None:
    store, root = rig
    before = tree(root)
    calls = [lambda: store.put(key, PNG, kind="screenshot", masked=True, content_type="image/png"),
             lambda: store.get(key), lambda: store.stat(key), lambda: store.delete(key),
             lambda: store.materialize(key)]
    for call in calls:
        with pytest.raises(UnsafeName):
            call()
    assert tree(root) == before


@pytest.mark.parametrize("name", ["PROFIL~1", "WORK~2.TXT", "a~12", "x~1.png", "ABCDEF~123"])
def test_an_8_3_short_name_is_unsafe(name: str) -> None:
    with pytest.raises(UnsafeName):
        safe_key(f"p/{name}")


@pytest.mark.parametrize("name", ["report~final.png", "a~b", "my~file", "tilde~.png", "x.png",
                                  "screenshot-1.png", "a~1b.txt", "backup~1.long"])
def test_a_name_that_is_not_an_8_3_alias_is_still_safe(name: str) -> None:
    assert safe_key(f"p/{name}") == f"p/{name}"
