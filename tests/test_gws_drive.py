"""The `gws` adapter (team-intake.md TI7, TI8, hosting.md HO32/HO33), with a scripted runner.

No process starts and nothing touches the network: `FakeRunner` answers the metadata and list
calls and writes the "downloaded" file. The cases are what a server operator meets: a good file,
a file over the limit, a Google Doc pasted by mistake, a folder, and the five ways Drive says no.
"""

from __future__ import annotations

import json
import logging

import pytest
from gws_fakes import CANARY, FakeRunner, error, meta, ok_json

from autotester.sources.drive_errors import MESSAGES, DriveError, DriveFailure
from autotester.sources.drive_verify import DriveVerifyError
from autotester.sources.gws_drive import GwsDrive, item_kind
from autotester.sources.gws_runner import GwsResult

FID = "1AbCdEfGhIjKlMnOpQrStUvWxYz_-0123"
MIB = 1024 * 1024


def _drive(tmp_path, runner, limit=5 * MIB):
    return GwsDrive(runner, tmp_path / "gws-work", limit_bytes=lambda: limit)


def _params(call: list[str]) -> dict:
    return json.loads(call[call.index("--params") + 1])


def test_ti7_metadata_turns_drive_strings_into_typed_values(tmp_path):
    """Drive reports `size` as a string; the adapter hands back an int and the md5."""
    runner = FakeRunner(lambda a: ok_json(meta(FID, size=1234, md5="ab" * 16)))
    item = _drive(tmp_path, runner).metadata(FID)
    assert (item.id, item.size, item.md5, item.mime_type) == (FID, 1234, "ab" * 16, "video/mp4")
    call = runner.run_calls[0]
    assert isinstance(call, list) and call[:3] == ["drive", "files", "get"]
    assert _params(call)["fileId"] == FID  # the id is passed, never a URL


def test_ti7_open_downloads_under_a_directory_the_adapter_controls(tmp_path):
    """`gws -o` writes under its cwd only, so the cwd is a private folder under the work root."""
    body = b"V" * 1000
    runner = FakeRunner(lambda a: ok_json(meta(FID, size=1000, md5="cd" * 16)), body=body)
    download = _drive(tmp_path, runner).open(FID)
    call = runner.download_calls[0]
    assert (tmp_path / "gws-work") in call["cwd"].parents
    assert _params(call["args"])["alt"] == "media" and "-o" in call["args"]
    assert call["out_name"] == call["args"][call["args"].index("-o") + 1]
    assert "/" not in call["out_name"] and "\\" not in call["out_name"]  # not Drive's name
    assert (download.size, download.md5) == (1000, "cd" * 16)
    assert b"".join(download.chunks()) == body
    download.close()
    assert not call["cwd"].exists()  # the private folder is gone after close


def test_ti9_declared_size_over_the_limit_is_refused_before_any_download(tmp_path):
    """Drive says 6 MiB and the limit is 5 MiB: nothing is transferred."""
    runner = FakeRunner(lambda a: ok_json(meta(FID, size=6 * MIB)))
    with pytest.raises(DriveVerifyError, match="5 MiB"):
        _drive(tmp_path, runner).open(FID)
    assert runner.download_calls == []


def test_ti9_the_limit_is_read_when_the_download_starts(tmp_path):
    """Lowering the setting between two requests changes the second one (same accessor)."""
    runner = FakeRunner(lambda a: ok_json(meta(FID, size=3 * MIB)), body=b"x")
    limits = iter([5 * MIB, 2 * MIB])
    drive = GwsDrive(runner, tmp_path / "w", limit_bytes=lambda: next(limits))
    drive.open(FID).close()
    with pytest.raises(DriveVerifyError, match="2 MiB"):
        drive.open(FID)


@pytest.mark.parametrize("mime", ["application/vnd.google-apps.document", "application/pdf",
                                  "text/plain", "application/x-msdownload", ""])
def test_ho33_only_video_and_zip_types_are_downloaded(tmp_path, mime):
    """A Google Doc or a PDF pasted by mistake is refused without transferring a byte."""
    runner = FakeRunner(lambda a: ok_json(meta(FID, mime=mime, name="notes.mp4")))
    with pytest.raises(DriveVerifyError, match="not a video"):
        _drive(tmp_path, runner).open(FID)
    assert runner.download_calls == []


@pytest.mark.parametrize("bad", ["", "a b", "../x", "short", "x" * 129, FID + "\n"])
def test_ti7_a_bad_id_never_reaches_the_command_line(tmp_path, bad):
    runner = FakeRunner(lambda a: pytest.fail("gws must not be called"))
    with pytest.raises(DriveVerifyError):
        _drive(tmp_path, runner).open(bad)
    with pytest.raises(DriveVerifyError):
        _drive(tmp_path, runner).list_folder(bad)


@pytest.mark.parametrize("mime, kind", [
    ("video/mp4", "video"), ("video/quicktime", "video"), ("video/x-matroska", "video"),
    ("application/zip", "zip"), ("application/x-zip-compressed", "zip"),
    ("application/vnd.google-apps.folder", "folder"),
    ("application/pdf", "other"), ("text/plain", "other"), ("", "other"),
])
def test_ti7_item_kind_is_decided_by_drives_type_not_the_file_name(mime, kind):
    from autotester.schema.intake import DriveItem
    assert item_kind(DriveItem(id=FID, name="x.exe", mime_type=mime)) == kind


def test_ti7_list_folder_lists_children_of_exactly_that_id(tmp_path):
    """A folder id lists its children; the query carries the validated id only."""
    files = [meta("v1aaaaaaaa", name="a.mp4", size=10), meta("p1aaaaaaaa", name="b.pdf",
                                                           mime="application/pdf")]
    runner = FakeRunner(lambda a: ok_json({"files": files}))
    items = _drive(tmp_path, runner).list_folder(FID)
    assert [i.id for i in items] == ["v1aaaaaaaa", "p1aaaaaaaa"]
    call = runner.run_calls[0]
    assert call[:3] == ["drive", "files", "list"]
    assert f"'{FID}' in parents" in _params(call)["q"]


def test_ti7_list_folder_follows_next_page_tokens_up_to_a_bound(tmp_path):
    pages = iter([ok_json({"files": [meta("aaaaaa0001")], "nextPageToken": "t1"}),
                  ok_json({"files": [meta("aaaaaa0002")]})])
    runner = FakeRunner(lambda a: next(pages))
    items = _drive(tmp_path, runner).list_folder(FID)
    assert [i.id for i in items] == ["aaaaaa0001", "aaaaaa0002"]
    assert _params(runner.run_calls[1])["pageToken"] == "t1"


# ---- TI8: five typed failures, distinct, and no token anywhere --------------------------------

FAILURES = [
    (DriveFailure.NOT_AUTHENTICATED, error(401, f"Invalid Credentials {CANARY}", "authError")),
    (DriveFailure.NOT_AUTHENTICATED, GwsResult(
        1, "", f"No credentials found for this account. Run `gws auth login` {CANARY}")),
    (DriveFailure.PERMISSION_DENIED, error(403, f"The caller does not have permission {CANARY}",
                                           "forbidden")),
    (DriveFailure.NOT_FOUND, error(404, f"File not found: {FID} {CANARY}", "notFound")),
    (DriveFailure.QUOTA_EXCEEDED, error(403, f"User rate limit exceeded {CANARY}",
                                        "userRateLimitExceeded")),
    (DriveFailure.QUOTA_EXCEEDED, error(429, f"Too many requests {CANARY}", "rateLimitExceeded")),
    (DriveFailure.QUOTA_EXCEEDED, error(403, f"Download quota exceeded {CANARY}",
                                        "downloadQuotaExceeded")),
    (DriveFailure.NETWORK_ERROR, GwsResult(
        1, "", f"error sending request: dns error: failed to lookup {CANARY}")),
    (DriveFailure.NETWORK_ERROR, error(503, f"Backend Error {CANARY}", "backendError")),
]


@pytest.mark.parametrize("kind, result", FAILURES)
def test_ti8_each_failure_class_is_typed_and_leaks_nothing(tmp_path, caplog, capsys, kind, result):
    """One fake gws failure per class: the kind is right and the canary never leaves."""
    runner = FakeRunner(lambda a: result)
    caplog.set_level(logging.DEBUG)
    with pytest.raises(DriveError) as caught:
        _drive(tmp_path, runner).metadata(FID)
    assert caught.value.kind is kind
    shown = f"{caught.value!s}|{caught.value!r}|{caught.value.args}"
    out = capsys.readouterr()
    assert CANARY not in shown + out.out + out.err + caplog.text
    assert str(caught.value) == MESSAGES[kind]


def test_ti8_the_five_messages_are_distinct_and_each_says_what_to_do_next():
    five = [DriveFailure.NOT_AUTHENTICATED, DriveFailure.PERMISSION_DENIED,
            DriveFailure.NOT_FOUND, DriveFailure.QUOTA_EXCEEDED, DriveFailure.NETWORK_ERROR]
    texts = [MESSAGES[k] for k in five]
    assert len(set(texts)) == 5
    assert "shar" in MESSAGES[DriveFailure.PERMISSION_DENIED].lower()  # HO33 wording
    assert "viewable" in MESSAGES[DriveFailure.PERMISSION_DENIED].lower()
    assert "gws auth login" in MESSAGES[DriveFailure.NOT_AUTHENTICATED]
    assert all(len(t) > 40 for t in texts)


def test_ti8_unparseable_output_is_a_network_error_not_a_traceback(tmp_path, capsys):
    runner = FakeRunner(lambda a: GwsResult(0, f"<html>{CANARY}", ""))
    with pytest.raises(DriveError) as caught:
        _drive(tmp_path, runner).metadata(FID)
    assert caught.value.kind is DriveFailure.NETWORK_ERROR
    assert CANARY not in str(caught.value) + repr(caught.value)


def test_ti8_a_failed_download_is_typed_and_its_folder_is_removed(tmp_path):
    runner = FakeRunner(lambda a: ok_json(meta(FID, size=10)),
                        on_download=error(403, f"nope {CANARY}", "forbidden"))
    with pytest.raises(DriveError) as caught:
        _drive(tmp_path, runner).open(FID)
    assert caught.value.kind is DriveFailure.PERMISSION_DENIED
    work = tmp_path / "gws-work"
    assert not work.exists() or list(work.iterdir()) == []


def test_ti8_a_download_that_wrote_no_file_is_not_a_success(tmp_path):
    """gws exits 0 yet leaves nothing: the fetch fails honestly, no empty file is registered."""
    runner = FakeRunner(lambda a: ok_json(meta(FID, size=10)),
                        on_download=GwsResult(0, "{}", ""))
    with pytest.raises(DriveError) as caught:
        _drive(tmp_path, runner).open(FID)
    assert caught.value.kind is DriveFailure.NETWORK_ERROR
