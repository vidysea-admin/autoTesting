"""The Add-videos upload route: streaming limit, zip outcome table, gate seam, uploaded_by.

(team-intake.md TI3, TI5, TI9, TI10-seam, TI11; hosting.md HO30.) TI10 itself (real accounts and
groups) is HELD on T-204; what is proved is the seam. The endless-body and lying-Content-Length
cases drive the app at the ASGI level (`asgi_helpers`), since a `TestClient` reads a whole body.
"""
# ruff: noqa: F811  (pytest fixtures imported from ui_intake_support are re-declared as arguments)


from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

from asgi_helpers import (
    BOUNDARY,
    CHUNK,
    chunked,
    endless,
    multipart_head,
    multipart_tail,
    post_stream,
)
from ui_intake_support import (  # noqa: F401  (fixtures)
    DRIVE,
    MIB,
    UPLOAD,
    FakeGate,
    _body,
    _leftovers,
    _limit,
    _recordings,
    client,
    drive,
    gate,
    store,
)
from zip_fixtures import add_member, build_zip, flip_data_byte, video

from autotester.schema.intake import UploadOrigin
from autotester.ui import intake_gate

# ---- the page ---------------------------------------------------------------------------------

def test_ti9_the_page_shows_the_current_limit_and_labelled_zip_and_drive_controls(
        client, tmp_path):
    _limit(tmp_path, 5 * MIB)
    text = client.get("/projects/demo/sources").text
    assert "5 MiB" in text and "largest" in text.lower()
    assert 'for="recording"' in text and ".zip" in text
    assert 'for="drive-link"' in text and 'name="link"' in text
    _limit(tmp_path, 7 * MIB)  # read at request time: no restart
    assert "7 MiB" in client.get("/projects/demo/sources").text


# ---- TI9 / HO30: the upload limit while streaming -------------------------------------------

def test_ho30_exactly_the_limit_succeeds_and_one_byte_more_is_a_413_with_nothing_left(
        store, tmp_path):
    _limit(tmp_path, 5 * MIB)
    exact = b"E" * (5 * MIB)
    status, _, _ = post_stream(UPLOAD, _body("exact.mp4", exact))
    assert status == 303
    [source] = store.list_sources()
    assert Path(source.path).read_bytes() == exact
    assert source.sha256 == hashlib.sha256(exact).hexdigest()

    status, page, _ = post_stream(UPLOAD, _body("over.mp4", b"O" * (5 * MIB + 1)))
    assert status == 413 and b"5 MiB" in page
    assert len(store.list_sources()) == 1 and len(_recordings(store)) == 1
    assert _leftovers(tmp_path) == []


def test_ti9_changing_the_setting_changes_the_next_request(store, tmp_path):
    data = b"C" * (3 * MIB)
    _limit(tmp_path, 2 * MIB)
    assert post_stream(UPLOAD, _body("c.mp4", data))[0] == 413
    _limit(tmp_path, 5 * MIB)
    assert post_stream(UPLOAD, _body("c.mp4", data))[0] == 303
    assert len(store.list_sources()) == 1


def test_ti9_an_endless_body_is_cut_at_the_limit_plus_one_chunk(store, tmp_path):
    """No end, no Content-Length: the server stops reading at the limit, not when it runs dry."""
    _limit(tmp_path, 2 * MIB)
    head = multipart_head("forever.mp4")
    status, _, served = post_stream(UPLOAD, endless(head))
    assert status == 413
    assert served.bytes <= len(head) + 2 * MIB + 2 * CHUNK
    assert store.list_sources() == [] and _leftovers(tmp_path) == []
    assert _recordings(store) == []


def test_ho30_a_lying_content_length_changes_nothing(store, tmp_path):
    _limit(tmp_path, 2 * MIB)
    big = _body("big.mp4", b"B" * (2 * MIB + 5))
    assert post_stream(UPLOAD, big, content_length=10)[0] == 413  # claims tiny, sends too much
    ok = _body("ok.mp4", b"K" * (1 * MIB))
    assert post_stream(UPLOAD, ok, content_length=10 * 1024**3)[0] == 303  # claims huge, sends fine
    assert len(store.list_sources()) == 1


def test_ti9_a_request_with_no_content_length_still_works(store):
    assert post_stream(UPLOAD, _body("a.mp4", video("nolen")))[0] == 303


def _fields(count: int, size: int) -> dict[str, str]:
    return {f"f{i}": "v" * size for i in range(count)}


def test_f2_many_small_form_fields_are_refused_early_and_write_no_file_byte(store, tmp_path):
    """1,000 tiny fields ahead of the file: refused 400 near the cap, not read to the end."""
    _limit(tmp_path, 2 * MIB)
    head = multipart_head("a.mp4", extra=_fields(1000, 100))
    status, _, served = post_stream(UPLOAD, [head, *chunked(b"V" * 4096), multipart_tail()])
    assert status == 400 and store.list_sources() == [] and _leftovers(tmp_path) == []
    assert served.bytes <= len(head)  # the whole head is one chunk; nothing after it was pulled
    assert not (tmp_path / ".work" / "uploads").exists() or not list(
        (tmp_path / ".work" / "uploads").rglob("*"))


def test_f2_a_few_large_fields_are_refused_by_the_total_cap(store, tmp_path):
    """Five fields of 15 KiB each pass the per-field cap but break the total field cap."""
    _limit(tmp_path, 2 * MIB)
    status, _, _ = post_stream(UPLOAD, _body("a.mp4", video("a"), extra=_fields(5, 15 * 1024)))
    assert status == 400 and store.list_sources() == [] and _leftovers(tmp_path) == []


def test_f2_the_reader_holds_a_bounded_amount_however_many_fields_arrive(tmp_path):
    """Feed the parser directly: it raises before the retained fields pass the caps."""
    import pytest
    from python_multipart.multipart import MultipartParser

    from autotester.ui import upload_stream as us

    reader = us._Reader(tmp_path / "stage", 2 * MIB)
    parser = MultipartParser(BOUNDARY.encode(), reader.callbacks())
    head = multipart_head("a.mp4", extra=_fields(5000, 200))
    with pytest.raises(us.UploadRefused) as caught:
        for start in range(0, len(head), 1024):
            parser.write(head[start:start + 1024])
    assert caught.value.status == 400
    kept = sum(len(k) + len(v) for k, v in reader.fields.items())
    assert len(reader.fields) <= us.MAX_FIELDS and kept <= us.FIELDS_TOTAL_CAP
    assert not (tmp_path / "stage").exists()


def test_a_body_that_is_not_multipart_is_refused_cleanly(store):
    status, page, _ = post_stream(UPLOAD, [b"just some bytes"], content_type="text/plain")
    assert status == 400 and b"Traceback" not in page and store.list_sources() == []


def test_ti3_a_non_recording_non_zip_name_is_refused_before_any_byte_is_stored(store, tmp_path):
    status, page, _ = post_stream(UPLOAD, _body("run.ps1", b"Write-Host hi"))
    assert status == 400 and b"not a recording" in page
    assert _leftovers(tmp_path) == [] and store.list_sources() == []


# ---- TI3 / TI5: a zip through the same form, with the outcome table -----------------------------

def _zip_post(client, path: Path, **kw):
    return client.post(UPLOAD, files={"recording": (path.name, path.read_bytes(),
                                                    "application/zip")}, data={"label": "x"}, **kw)


def test_ti3_a_zip_of_three_videos_a_pdf_and_a_text_file_shows_one_row_per_member(
        client, store, tmp_path, gate):
    archive = build_zip(tmp_path / "ok.zip", [("a.mp4", video("a")), ("b.mp4", video("b")),
                                              ("c.mp4", video("c")), ("notes.pdf", b"%PDF"),
                                              ("readme.txt", b"hi")])
    response = _zip_post(client, archive)
    assert response.status_code == 200
    text = response.text
    for name in ("a.mp4", "b.mp4", "c.mp4", "notes.pdf", "readme.txt"):
        assert name in text
    assert text.count("registered") >= 3 and "skipped" in text and "not a recording" in text
    assert len(store.list_sources()) == 3
    assert {s.uploaded_by for s in store.list_sources()} == {"dev@vidysea.test"}
    assert all(s.origin.kind == "zip" and s.origin.archive_name == "ok.zip"
               for s in store.list_sources())
    assert _leftovers(tmp_path) == []


def test_ti5_a_zip_with_a_bad_member_reads_as_partial_not_success(client, store, tmp_path, gate):
    archive = build_zip(tmp_path / "p.zip", [("good.mp4", video("g")), ("bad.mp4", video("bad"))])
    flip_data_byte(archive, "bad.mp4")
    with zipfile.ZipFile(archive, "a") as zf:
        add_member(zf, "../../escape.mp4", video("esc"))
    text = _zip_post(client, archive).text
    assert "Partial" in text and "corrupt member" in text and "path traversal" in text
    assert "../../escape.mp4" in text
    assert len(store.list_sources()) == 1
    assert not (tmp_path.parent / "escape.mp4").exists()


def test_a_member_name_is_escaped_never_executed_by_the_table(client, store, tmp_path):
    archive = build_zip(tmp_path / "x.zip", [("<img src=x onerror=alert(1)>.mp4", video("xss"))])
    text = _zip_post(client, archive).text
    assert "<img src=x onerror=alert(1)>" not in text and "&lt;img" in text


def test_ti9_a_zip_bigger_than_the_limit_is_a_413_like_any_upload(client, store, tmp_path):
    _limit(tmp_path, 2 * MIB)
    archive = build_zip(tmp_path / "big.zip", [("a.mp4", video("big", size=3 * MIB))])
    assert archive.stat().st_size > 2 * MIB
    assert _zip_post(client, archive).status_code == 413 and store.list_sources() == []


# ---- TI10 seam + TI11 ----------------------------------------------------------------------------

def test_ti10_seam_a_refused_member_is_stopped_before_a_single_body_byte_is_read(store, tmp_path):
    refusing = FakeGate(refuse=(403, "you need the video.upload permission on this project"))
    previous = intake_gate.set_gate(refusing)
    try:
        status, page, served = post_stream(UPLOAD, endless(multipart_head("a.mp4")))
    finally:
        intake_gate.set_gate(previous)
    assert status == 403 and b"video.upload" in page
    assert served.bytes == 0 and store.list_sources() == [] and _leftovers(tmp_path) == []
    assert refusing.checks == ["demo"]


def test_ti11_uploaded_by_comes_from_the_gate_and_a_form_field_is_ignored(store, gate):
    body = _body("who.mp4", video("who"), extra={"uploaded_by": "attacker@evil.test"})
    assert post_stream(UPLOAD, body)[0] == 303
    [source] = store.list_sources()
    assert source.uploaded_by == "dev@vidysea.test"
    assert source.uploaded_at is not None
    assert source.origin == UploadOrigin(file_name="who.mp4")


def test_ti11_with_no_sign_in_yet_nobody_is_recorded_as_the_uploader(store):
    """Until T-204 the default gate is open and says so; the row is owned by nobody."""
    assert post_stream(UPLOAD, _body("anon.mp4", video("anon")))[0] == 303
    assert store.list_sources()[0].uploaded_by is None


def test_d066_a_cross_origin_post_is_refused_before_the_gate_or_any_write(client, store, gate):
    response = client.post(UPLOAD, files={"recording": ("a.mp4", video("o"), "video/mp4")},
                           headers={"Origin": "http://evil.test"})
    assert response.status_code == 403 and gate.checks == [] and store.list_sources() == []


def test_the_archive_name_in_the_page_heading_is_escaped(client, store, tmp_path):
    archive = build_zip(tmp_path / "h.zip", [("a.mp4", video("h"))])
    sent = {"recording": ("<img src=x onerror=alert(1)>.zip", archive.read_bytes(),
                          "application/zip")}
    text = client.post(UPLOAD, files=sent, data={"label": "x"}).text
    assert "<img src=x onerror" not in text and "&lt;img" in text


def test_a_truncated_multipart_body_is_refused_not_stored(store, tmp_path):
    body = [multipart_head("cut.mp4"), b"V" * 5000]  # no closing boundary
    status, _, _ = post_stream(UPLOAD, body)
    assert status == 400 and store.list_sources() == [] and _leftovers(tmp_path) == []


def test_a_huge_part_header_is_refused_before_it_is_buffered(store):
    head = b"--" + BOUNDARY.encode() + b"\r\nX-Pad: " + b"a" * (40 * 1024) + b"\r\n\r\n"
    assert post_stream(UPLOAD, [head, b"x"])[0] == 400


def test_at758_a_hostile_host_on_the_upload_route_is_403_before_any_body_byte(store, gate):
    """The Host allow-list sits in front of the gate and the body (AT-758)."""
    for host in ("evil.example", "localhost:8000.evil.com", ""):
        status, page, served = post_stream(UPLOAD, endless(multipart_head("a.mp4")), host=host)
        assert status == 403 and page == b"" and served.bytes == 0
    assert gate.checks == [] and store.list_sources() == []


def test_at758_a_hostile_host_on_the_upload_route_is_403_before_any_body_byte(store, gate):
    """The Host allow-list sits in front of the gate and the body (AT-758)."""
    for host in ("evil.example", "localhost:8000.evil.com", ""):
        status, page, served = post_stream(UPLOAD, endless(multipart_head("a.mp4")), host=host)
        assert status == 403 and page == b"" and served.bytes == 0
    assert gate.checks == [] and store.list_sources() == []
