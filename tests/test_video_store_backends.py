"""Video shares, links, access requests and comments on both auth backends (mongo-store U6c, M30):
the same assertions run on SQLite and on Mongo (the `fake_mongo` double) through the unchanged
stage modules, plus the Mongo-only properties: a refused approval is undone whole, one pending
request per person under a race, a deleted share leaves nothing of the address, no argon2 hash
in any video collection, an unreachable store fails closed, and the principal reads of
`schedule_owner` / `intake_gate_auth` go through the store seam."""

from __future__ import annotations

import hashlib
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest
from auth_harness import ADMIN, PASSWORD
from auth_store_backends import BACKENDS, AuthEnv, auth_env

from autotester.auth import accounts
from autotester.auth.store_mongo_video import VideoOps
from autotester.schema.auth import ResourceRef
from autotester.schema.team_enums import AccessRequestStatus as Status
from autotester.stages import schedule_owner, video_access, video_comments, video_requests
from autotester.store.mongo_guard import StoreUnavailable
from autotester.ui import intake_gate_auth

SLUG, VID, OTHER = "proj", "v1", "dev@team.test"
VIDEO_COLLECTIONS = ("video_shares", "video_links", "access_requests", "video_comments")


@pytest.fixture(params=BACKENDS)
def env(request: pytest.FixtureRequest, tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch) -> Iterator[AuthEnv]:
    yield from auth_env(request.param, tmp_path, monkeypatch)


@pytest.fixture
def mongo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[AuthEnv]:
    yield from auth_env("mongo", tmp_path, monkeypatch)


@pytest.fixture
def video(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every video id exists and is uploaded by `up@team.test` (the project store is not the
    subject here)."""
    monkeypatch.setattr(video_requests, "video_resource", lambda slug, vid: ResourceRef(
        project_slug=slug, video_id=vid, owner_email="up@team.test"))


def test_shares_are_idempotent_and_removable(env: AuthEnv) -> None:
    assert video_access.shared_emails(SLUG, VID) == frozenset()
    video_access.set_share(SLUG, VID, " A@Team.test ", True, "Up@team.test")
    video_access.set_share(SLUG, VID, "a@team.test", True, "up@team.test")
    video_access.set_share(SLUG, "v2", "b@team.test", True, "up@team.test")
    assert video_access.shared_emails(SLUG, VID) == {"a@team.test"}
    video_access.set_share(SLUG, VID, "a@team.test", False, "up@team.test")
    video_access.set_share(SLUG, VID, "a@team.test", False, "up@team.test")  # no-op
    assert video_access.shared_emails(SLUG, VID) == frozenset()
    assert video_access.shared_emails(SLUG, "v2") == {"b@team.test"}
    video_access.set_share(SLUG, VID, "a@team.test", True, "up@team.test")  # the slot is reusable
    assert video_access.shared_emails(SLUG, VID) == {"a@team.test"}


def test_one_live_link_per_video_and_only_its_hash_is_stored(env: AuthEnv) -> None:
    assert video_access.live_link_since(SLUG, VID) is None
    first = video_access.create_link(SLUG, VID, "up@team.test")
    assert video_access.resolve_link(first) == (SLUG, VID)
    second = video_access.create_link(SLUG, VID, "up@team.test")
    assert video_access.resolve_link(first) is None and video_access.resolve_link(second)
    assert video_access.live_link_since(SLUG, VID) is not None
    assert video_access.resolve_link("not-a-token") is None
    assert video_access.revoke_links(SLUG, VID) == 1 and video_access.revoke_links(SLUG, VID) == 0
    assert video_access.resolve_link(second) is None
    assert video_access.live_link_since(SLUG, VID) is None
    if env.name == "mongo":
        dump = repr([env._coll("video_links").docs])
        assert hashlib.sha256(second.encode()).hexdigest() in dump
        assert first not in dump and second not in dump


def test_purge_removes_all_four_kinds_for_a_video_and_for_a_project(env: AuthEnv,
                                                                    video: None) -> None:
    for vid in (VID, "v2"):
        video_access.set_share(SLUG, vid, "a@team.test", True, "up@team.test")
        video_access.create_link(SLUG, vid, "up@team.test")
        video_requests.request_access(SLUG, vid, "r@team.test")
        video_comments.add_comment(SLUG, vid, "c@team.test", 1.0, "hello")
    video_access.purge_video(SLUG, VID)
    assert video_access.shared_emails(SLUG, VID) == frozenset()
    assert video_requests.latest_request(SLUG, VID, "r@team.test") is None
    assert video_comments.list_comments(SLUG, VID) == []
    assert video_access.live_link_since(SLUG, "v2") is not None  # the other video is untouched
    video_access.purge_project_videos(SLUG)
    assert video_access.shared_emails(SLUG, "v2") == frozenset()
    assert video_comments.list_comments(SLUG, "v2") == []
    assert video_requests.requests_by("r@team.test") == []


def test_request_access_decide_once_and_share(env: AuthEnv, video: None) -> None:
    accounts.signup(ADMIN, PASSWORD)
    me = "r@team.test"
    req, made = video_requests.request_access(SLUG, VID, me)
    again, made_again = video_requests.request_access(SLUG, VID, me)
    assert made and not made_again and req is not None and again is not None and again.id == req.id
    assert req.status is Status.PENDING and video_requests.latest_request(SLUG, VID, me) == req
    principal = intake_gate_auth.principal_for_email(ADMIN)
    assert principal is not None and video_requests.pending_for(principal) == [req]
    decided = video_requests.decide(principal, req.id, True)
    assert decided is not None and decided.status is Status.APPROVED
    assert decided.decided_by == ADMIN and video_access.shared_emails(SLUG, VID) == {me}
    replay = video_requests.decide(principal, req.id, False)  # a double click or replay
    assert replay is not None and replay.status is Status.APPROVED
    assert video_requests.pending_for(principal) == []
    nxt, made_next = video_requests.request_access(SLUG, VID, me)  # a new request is allowed
    assert made_next and nxt is not None and nxt.id > req.id
    assert [r.id for r in video_requests.requests_by(me)] == [nxt.id, req.id]  # newest first
    assert video_requests.latest_request(SLUG, VID, me) == nxt
    assert video_requests.get_request(9999) is None


def test_approvers_are_the_admins_and_the_uploader_never_the_requester(env: AuthEnv,
                                                                      video: None) -> None:
    accounts.signup(ADMIN, PASSWORD)
    res = video_requests.video_resource(SLUG, VID)
    assert res is not None
    assert video_requests.approvers(res, "r@team.test") == [ADMIN]
    assert video_requests.approvers(res, ADMIN) == []  # nobody approves their own request


def test_comments_order_edit_promote_delete_and_video_scope(env: AuthEnv) -> None:
    late = video_comments.add_comment(SLUG, VID, " C@Team.test ", 9.5, "late")
    early = video_comments.add_comment(SLUG, VID, "c@team.test", 2.0, "early")
    other = video_comments.add_comment(SLUG, "v2", "c@team.test", 1.0, "elsewhere")
    assert late.author == "c@team.test" and early.id > late.id
    assert [c.text for c in video_comments.list_comments(SLUG, VID)] == ["early", "late"]
    assert video_comments.get_comment(SLUG, VID, early.id) == early
    assert video_comments.get_comment(SLUG, VID, other.id) is None  # an id of another video
    edited = video_comments.edit_comment(early.id, "edited")
    assert edited is not None and edited.text == "edited" and edited.edited_at is not None
    first = video_comments.promote(early.id, "0:02 | edited")
    second = video_comments.promote(early.id, "different")
    assert first is not None and second is not None and second.pointer_line == "0:02 | edited"
    assert video_comments.pointer_text(SLUG, VID) == "0:02 | edited"
    video_comments.delete_comment(early.id)
    assert [c.text for c in video_comments.list_comments(SLUG, VID)] == ["late"]
    assert video_comments.edit_comment(9999, "x") is None


def test_a_refused_approval_is_undone_whole(mongo: AuthEnv, video: None,
                                            monkeypatch: pytest.MonkeyPatch) -> None:
    accounts.signup(ADMIN, PASSWORD)
    req, _ = video_requests.request_access(SLUG, VID, "r@team.test")
    principal = intake_gate_auth.principal_for_email(ADMIN)
    assert req is not None and principal is not None

    def refuse(*_a: object, **_k: object) -> None:
        raise RuntimeError("the share could not be written")
    with monkeypatch.context() as scoped:
        scoped.setattr(VideoOps, "set_share", refuse)
        with pytest.raises(RuntimeError):
            video_requests.decide(principal, req.id, True)
    raw = [d for d in mongo._coll("access_requests").docs if d["_id"] == req.id]
    assert raw and raw[0]["status"] == "pending"  # undone at once, not by the next holder's read
    after = video_requests.get_request(req.id)
    assert after is not None and after.status is Status.PENDING  # the decision was undone
    assert video_access.shared_emails(SLUG, VID) == frozenset()


def test_two_racing_requests_make_one_pending_request(mongo: AuthEnv, video: None) -> None:
    mongo.fresh(slow=True)
    results: list[tuple[object, bool]] = []
    barrier = threading.Barrier(4)

    def ask() -> None:
        barrier.wait()
        results.append(video_requests.request_access(SLUG, VID, "r@team.test"))
    threads = [threading.Thread(target=ask) for _ in range(4)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert sorted(made for _req, made in results) == [False, False, False, True]
    assert len(video_requests.requests_by("r@team.test")) == 1


def test_a_deleted_share_keeps_nothing_of_the_address_and_no_hash_is_in_a_video_collection(
        mongo: AuthEnv) -> None:
    accounts.signup(ADMIN, PASSWORD)
    video_access.set_share(SLUG, VID, "secret.person@team.test", True, ADMIN)
    video_access.set_share(SLUG, VID, "secret.person@team.test", False, ADMIN)
    docs = repr([mongo._coll(name).docs for name in VIDEO_COLLECTIONS])
    assert "secret.person" not in docs and "$argon2" not in docs
    assert "$argon2" in repr(mongo._coll("auth_users").docs)  # the hash lives only there (M30)


def test_an_unreachable_store_fails_closed_on_every_video_call(mongo: AuthEnv) -> None:
    video_access.set_share(SLUG, VID, "a@team.test", True, "up@team.test")
    mongo.server.down = True
    try:
        for call in (lambda: video_access.shared_emails(SLUG, VID),
                     lambda: video_access.set_share(SLUG, VID, "b@team.test", True, "u@t.test"),
                     lambda: video_access.resolve_link("a" * 40),
                     lambda: video_comments.list_comments(SLUG, VID),
                     lambda: video_requests.requests_by("r@team.test")):
            with pytest.raises(StoreUnavailable):
                call()
    finally:
        mongo.server.down = False
    assert video_access.shared_emails(SLUG, VID) == {"a@team.test"}


def test_principals_for_the_schedule_owner_and_the_intake_gate_come_from_the_seam(
        env: AuthEnv) -> None:
    assert intake_gate_auth.principal_for_email(ADMIN) is None  # no store yet: nobody
    assert schedule_owner.owner_principal(ADMIN) is None
    admin = accounts.signup(ADMIN, PASSWORD)
    other = accounts.signup(OTHER, PASSWORD)
    for read in (intake_gate_auth.principal_for_email, schedule_owner.owner_principal):
        who = read(ADMIN)
        assert who is not None and who.user_id == admin.id and "users.manage" in who.permissions
        none = read(OTHER)
        assert none is not None and none.user_id == other.id and not none.permissions
        assert read("nobody@team.test") is None
    accounts.set_disabled(other.id, True)
    assert intake_gate_auth.principal_for_email(OTHER) is None
    assert schedule_owner.owner_principal(OTHER) is None
    assert schedule_owner.owner_principal(None) is None


def test_the_schedule_owner_is_nobody_while_the_store_is_unreachable(mongo: AuthEnv) -> None:
    accounts.signup(ADMIN, PASSWORD)
    assert schedule_owner.owner_principal(ADMIN) is not None
    mongo.server.down = True
    try:
        assert schedule_owner.owner_principal(ADMIN) is None  # no owner can be proven: refuse
        assert schedule_owner.owner_refusal(SLUG, ADMIN) is not None
    finally:
        mongo.server.down = False


def test_audit_rows_go_to_the_store_with_no_file_and_no_secret(
        mongo: AuthEnv, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from autotester.auth import audit
    monkeypatch.setenv("AUTOTESTER_STORE_AREAS", "auth=mongo,settings=mongo")
    accounts.signup(ADMIN, PASSWORD)
    audit.record_request(ADMIN, "POST", "/projects/{slug}/run", 200)
    audit.record_action(ADMIN, "dev@team.test", "disable")
    rows = repr(mongo._coll("audit_log").docs)
    assert "/projects/{slug}/run" in rows and "disable" in rows and "$argon2" not in rows
    assert not list((tmp_path / "root").rglob("audit.jsonl"))  # nothing written to the disk
