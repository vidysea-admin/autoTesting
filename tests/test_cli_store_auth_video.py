"""E10.1 (e2e-fixes, mongo-store U8 follow-up to U6c): the auth importer also carries the four
video tables (shares, links, access requests, comments) into the Mongo auth store, in the same
journalled transaction as the users, idempotently, counts only, with a verify row per table.

Fake Mongo and tmp dirs only; every address, token hash and comment text is synthetic."""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
from fake_mongo import seams
from store_migrate_support import Rig, make_rig, seed_auth

from autotester.auth import db
from autotester.auth import migrate_auth as ma
from autotester.auth.store_mongo import MongoAuthStore, reset_auth_store
from autotester.auth.store_mongo_tx import JOURNAL_COLL, MongoTxBase
from autotester.store.mongo_backend import default_store, reset_default_backend

CANARY_MAIL, CANARY_TOKEN = "canary-share@leak.test", "tok-canary-hash-0001"
CANARY_TEXT, CANARY_WHO = "canary comment text 77", "canary-requester@leak.test"
ROWS = ("auth_shares", "auth_links", "auth_access_requests", "auth_comments")
SHARES = [("p", "v1", CANARY_MAIL, "up@team.test", "2026-01-01"),
          ("p", "v2", "b@leak.test", "up2@team.test", "2026-01-02")]
LINKS = [(CANARY_TOKEN, "p", "v1", "up@team.test", "2026-01-03", None),
         ("tok-canary-hash-0002", "p", "v2", "up@team.test", "2026-01-04", "2026-02-01")]
REQUESTS = [(4, "p", "v1", CANARY_WHO, "pending", "2026-01-05", None, None),
            (7, "p", "v1", "c@leak.test", "approved", "2026-01-06", "up@team.test", "2026-01-07"),
            (9, "p", "v2", "d@leak.test", "denied", "2026-01-08", "up@team.test", "2026-01-09")]
COMMENTS = [(3, "p", "v1", "a@leak.test", 1.5, CANARY_TEXT, "2026-01-10", None, None),
            (5, "p", "v1", "b@leak.test", 2.5, "edited one", "2026-01-11", "2026-01-12", None),
            (8, "p", "v2", "c@leak.test", 0.5, "pointed", "2026-01-13", None, "line 12")]


@pytest.fixture
def rig(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Rig:
    return make_rig(tmp_path, monkeypatch)


def _seed_video(rig: Rig) -> None:
    seed_auth(rig)
    with sqlite3.connect(db.auth_db_path()) as con:
        for table, rows in (("video_shares", SHARES), ("video_links", LINKS),
                            ("access_requests", REQUESTS), ("video_comments", COMMENTS)):
            marks = ",".join("?" * len(rows[0]))
            con.executemany(f"INSERT INTO {table} VALUES ({marks})", rows)


@contextmanager
def _store(rig: Rig) -> Iterator[MongoAuthStore]:
    """The Mongo auth store the CLI wrote, read the way the application reads it."""
    reset_default_backend()
    reset_auth_store()
    with seams(client_factory=rig._client):
        yield MongoAuthStore(default_store())
    reset_default_backend()
    reset_auth_store()


def _cells(output: str, name: str) -> dict[str, int]:
    line = next(x for x in output.splitlines() if x.strip().startswith(name + " "))
    return {k: int(v) for k, v in re.findall(r"([a-z_-]+)=(\d+)", line)}


def _apply(rig: Rig) -> Any:
    return rig.invoke("migrate", "--apply", "--only", "auth")


def test_every_row_comes_across_and_the_application_reads_it_back(rig: Rig) -> None:
    _seed_video(rig)
    done = _apply(rig)
    assert done.exit_code == 0, done.output
    for name, rows in zip(ROWS, (SHARES, LINKS, REQUESTS, COMMENTS), strict=True):
        assert _cells(done.output, name)["written"] == len(rows)
    with _store(rig) as store, store.reading() as tx:
        assert tx.share_emails("p", "v1") == {CANARY_MAIL}
        assert tx.share_emails("p", "v2") == {"b@leak.test"}
        assert tx.link_target(CANARY_TOKEN) == ("p", "v1")
        assert tx.link_target("tok-canary-hash-0002") is None  # revoked stays revoked
        got = [tuple(r[c] for c in ("id", "slug", "video_id", "requester", "status",
                                    "created_at", "decided_by", "decided_at"))
               for r in tx.request_rows()]
        assert got == REQUESTS  # ids kept, columns verbatim, oldest first
        pins = [tuple(r[c] for c in ("id", "slug", "video_id", "author", "at_s", "text",
                                     "created_at", "edited_at", "pointer_line"))
                for v in ("v1", "v2") for r in tx.comment_rows("p", v)]
        assert sorted(pins) == sorted(COMMENTS)
    docs = {d["_id"]: d for d in rig.docs("video_shares") if not str(d["_e"]).startswith("G:")}
    assert {(d["granted_by"], d["granted_at"]) for d in docs.values()} == {
        ("up@team.test", "2026-01-01"), ("up2@team.test", "2026-01-02")}


def test_a_second_apply_writes_nothing_and_never_replaces(rig: Rig) -> None:
    _seed_video(rig)
    _apply(rig)
    again = _apply(rig)
    assert again.exit_code == 0 and "written: 0" in again.output
    for name, rows in zip(ROWS, (SHARES, LINKS, REQUESTS, COMMENTS), strict=True):
        cells = _cells(again.output, name)
        assert cells["unchanged"] == len(rows) and cells["to_insert"] == 0
        assert "written" not in cells or cells["written"] == 0


def test_the_allocators_start_above_every_imported_id(rig: Rig) -> None:
    _seed_video(rig)
    with _store(rig) as store, store.transaction() as tx:  # the target's counters already run
        tx.request_access("p", "v5", "early@leak.test", "2026-01-01")  # id 1
        tx.add_comment("p", "v5", "early@leak.test", 1.0, "t", "2026-01-01")  # id 1
    _apply(rig)
    with _store(rig) as store, store.transaction() as tx:
        fresh, made = tx.request_access("p", "v9", "new@leak.test", "2026-03-01")
        assert made and fresh is not None and fresh["id"] == 10  # max(1, 4, 7, 9) + 1
        assert tx.add_comment("p", "v1", "z@leak.test", 9.0, "t", "2026-03-01")["id"] == 9


def test_the_report_and_logs_carry_counts_never_a_value(
        rig: Rig, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture) -> None:
    _seed_video(rig)
    shown = ""
    for args in (("migrate", "--only", "auth"), ("migrate", "--apply", "--only", "auth"),
                 ("migrate", "--apply", "--only", "auth"), ("verify", "--only", "auth")):
        shown += rig.invoke(*args).output
    shown += capsys.readouterr().out + capsys.readouterr().err + caplog.text
    for banned in (CANARY_MAIL, CANARY_TOKEN, CANARY_TEXT, CANARY_WHO, "b@leak.test", "line 12"):
        assert banned not in shown


def test_a_dry_run_opens_no_client_and_counts_each_table(rig: Rig) -> None:
    _seed_video(rig)
    done = rig.invoke("migrate", "--only", "auth")
    assert done.exit_code == 0 and rig.opened == 0
    for name, rows in zip(ROWS, (SHARES, LINKS, REQUESTS, COMMENTS), strict=True):
        assert _cells(done.output, name)["to_insert"] == len(rows)
    checked = rig.invoke("migrate", "--only", "auth", "--check-remote")
    assert rig.opened >= 1 and _cells(checked.output, "auth_links")["to_insert"] == 2


def test_a_differing_target_row_is_reported_and_verify_fails(rig: Rig) -> None:
    _seed_video(rig)
    _apply(rig)
    assert rig.invoke("verify", "--only", "auth").exit_code == 0
    share = next(d for d in rig.docs("video_shares") if d.get("email") == CANARY_MAIL)
    link = next(d for d in rig.docs("video_links") if d["_id"] == "tok-canary-hash-0002")
    text = next(d for d in rig.docs("video_comments") if d["_id"] == 3)
    share["granted_by"], link["revoked_at"], text["text"] = "someone@else.test", None, "changed"
    done = rig.invoke("verify", "--only", "auth")
    assert done.exit_code == 1
    for name in ("auth_shares", "auth_links", "auth_comments"):
        assert _cells(done.output, name)["conflicting-id"] == 1
    assert _cells(done.output, "auth_access_requests")["conflicting-id"] == 0
    again = _apply(rig)  # never replaced
    assert again.exit_code == 1 and "written: 0" in again.output
    assert (share["granted_by"], link["revoked_at"], text["text"]) == (
        "someone@else.test", None, "changed")


def test_a_pending_request_for_the_same_person_and_video_is_not_duplicated(rig: Rig) -> None:
    _seed_video(rig)
    with _store(rig) as store, store.transaction() as tx:  # the target already has one
        held, _ = tx.request_access("p", "v1", CANARY_WHO, "2026-02-02")
    done = _apply(rig)
    cells = _cells(done.output, "auth_access_requests")
    assert done.exit_code == 1 and cells["conflicting-id"] == 1
    with _store(rig) as store, store.reading() as tx:
        pending = tx.request_rows(requester=CANARY_WHO, status="pending")
    assert [r["id"] for r in pending] == [held["id"]]  # type: ignore[index]
    assert cells["written"] == 2  # the other two came across


def test_the_video_rows_are_journalled(
        rig: Rig, monkeypatch: pytest.MonkeyPatch) -> None:
    _seed_video(rig)
    real, entries = MongoTxBase.commit, set()

    def spy(self: MongoTxBase) -> None:  # raw collection writes would leave no undo entry
        entries.update(d["coll"] for d in rig.docs(JOURNAL_COLL) if d.get("kind") == "undo")
        real(self)
    monkeypatch.setattr(MongoTxBase, "commit", spy)
    _apply(rig)
    assert {"video_shares", "video_links", "access_requests", "video_comments"} <= entries


def test_a_failure_after_the_video_rows_were_written_undoes_them_whole(
        rig: Rig, monkeypatch: pytest.MonkeyPatch) -> None:
    _seed_video(rig)
    real_video = ma._import_video

    def then_boom(*args: Any) -> None:
        real_video(*args)
        raise RuntimeError("after the video rows")
    monkeypatch.setattr(ma, "_import_video", then_boom)
    assert _apply(rig).exit_code == 1
    live = [d for n in ("video_links", "access_requests", "video_comments")
            for d in rig.docs(n)]
    assert live == []
    assert all(str(d["_e"]).startswith("G:") for d in rig.docs("video_shares"))
