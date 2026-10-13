"""T-198c TI10 + TI11: intake needs a signed-in member holding `video.upload` on that project.

The matrix (admin, assigned sub-admin, own developer, other developer, tester, no-group,
anonymous) x (file upload, zip upload, Drive link), the recheck when a queued fetch starts, and
the uploader taken from the session, never the form. Real accounts and groups, no fake gate.
"""

from __future__ import annotations

import pytest
from portal_support import SLUG, build_world, email
from zip_fixtures import build_zip, video

from autotester.auth import accounts
from autotester.schema.intake import IntakeActor
from autotester.store.project_store import ProjectStore
from autotester.ui import intake_gate, routes_intake
from autotester.ui.intake_gate import IntakeRefused
from autotester.ui.intake_gate_auth import AuthGate

UPLOAD = f"/projects/{SLUG}/sources/upload"
DRIVE = f"/projects/{SLUG}/sources/drive"
ALLOWED = ("admin", "sub", "dev")        # @all, @assigned, @own
REFUSED_403 = ()                           # a viewer without the key: none in the default groups
HIDDEN = ("dev2", "tester", "tester2")   # cannot view the project at all


@pytest.fixture
def world(tmp_path, monkeypatch):
    previous = intake_gate.set_gate(AuthGate())
    yield build_world(tmp_path, monkeypatch)
    intake_gate.set_gate(previous)


def _file(world, who, data: bytes, name="clip.mp4", **form):
    return world.users[who].post(UPLOAD, files={"file": (name, data, "video/mp4")}, data=form)


def _sources(world):
    return ProjectStore(SLUG, world.root).list_sources()


@pytest.mark.parametrize("who", ALLOWED)
def test_ti10_a_member_with_the_key_on_this_project_adds_a_video(world, who):
    before = len(_sources(world))
    assert _file(world, who, video(who)).status_code == 303
    added = _sources(world)[before:]
    assert [s.uploaded_by for s in added] == [email(who)]


@pytest.mark.parametrize("who", ALLOWED)
def test_ti10_a_member_with_the_key_adds_a_zip(world, tmp_path, who):
    archive = build_zip(tmp_path / "a.zip", [("one.mp4", video("z" + who))])
    before = len(_sources(world))
    response = _file(world, who, archive.read_bytes(), "a.zip")
    assert response.status_code == 200
    assert [s.uploaded_by for s in _sources(world)[before:]] == [email(who)]


@pytest.mark.parametrize("who", HIDDEN)
def test_ti10_a_member_who_cannot_see_the_project_gets_404_and_nothing_is_written(world, who):
    before = len(_sources(world))
    assert _file(world, who, video("no" + who)).status_code == 404
    assert world.users[who].post(DRIVE, data={"link": "FILE000001"}).status_code == 404
    assert len(_sources(world)) == before


def test_ti10_an_account_in_no_group_is_refused_403_and_nothing_is_written(world):
    before = len(_sources(world))
    assert _file(world, "nogroup", video("ng")).status_code == 403
    assert world.users["nogroup"].post(DRIVE, data={"link": "FILE000002"}).status_code == 403
    assert len(_sources(world)) == before


def test_ti10_anonymous_is_sent_to_sign_in_or_401_and_nothing_is_written(world):
    from portal_support import anonymous
    anon = anonymous()
    before = len(_sources(world))
    page = anon.post(UPLOAD, files={"file": ("c.mp4", video("anon"), "video/mp4")},
                     headers={"Accept": "text/html"})
    api = anon.post(UPLOAD, files={"file": ("c.mp4", video("anon"), "video/mp4")})
    assert page.status_code == 302 and "/auth/login" in page.headers["location"]
    assert api.status_code == 401
    assert len(_sources(world)) == before


def test_ti10_viewer_without_the_key_is_403_naming_the_permission(world):
    """A shared viewer holds project.view@shared but not video.upload: 403, not 404."""
    from autotester.auth.access import set_relation
    from autotester.schema.auth import ProjectRelation
    set_relation(SLUG, accounts.find_user(email("tester")).id, ProjectRelation.SHARED, True)
    from autotester.auth.access import resource_for
    from autotester.ui.intake_gate_auth import _decide, principal_for_email
    with pytest.raises(IntakeRefused) as refused:
        _decide(principal_for_email(email("tester")), SLUG)
    assert refused.value.status == 403 and "video.upload" in refused.value.message
    assert resource_for(SLUG).shared_with == frozenset({email("tester")})


def test_ti11_the_uploader_is_the_session_never_a_form_field(world):
    assert _file(world, "dev", video("spoof"), uploaded_by=email("admin")).status_code == 303
    assert _sources(world)[-1].uploaded_by == email("dev")


def test_ti10_recheck_refuses_a_member_disabled_since_the_job_was_queued(world):
    gate, actor = AuthGate(), IntakeActor(email=email("dev"))
    gate.recheck(actor, SLUG)
    accounts.set_disabled(accounts.find_user(email("dev")).id, True)
    with pytest.raises(IntakeRefused) as refused:
        gate.recheck(actor, SLUG)
    assert refused.value.status == 401


def test_ti10_recheck_refuses_a_member_moved_out_of_the_developer_group(world):
    gate, actor = AuthGate(), IntakeActor(email=email("dev"))
    accounts.set_user_groups(accounts.find_user(email("dev")).id, [])
    with pytest.raises(IntakeRefused):
        gate.recheck(actor, SLUG)


def test_ti10_a_disabled_member_between_queue_and_start_fetches_no_bytes(world, monkeypatch):
    from drive_fakes import FakeDrive
    fake = FakeDrive()
    fake.add("FILE000009", video("late"))
    monkeypatch.setattr(routes_intake, "drive_factory", lambda _store: fake)
    uid = accounts.find_user(email("dev")).id
    real = AuthGate.recheck

    def disable_then_recheck(self, actor, slug):
        accounts.set_disabled(uid, True)
        return real(self, actor, slug)

    monkeypatch.setattr(AuthGate, "recheck", disable_then_recheck)
    before = len(_sources(world))
    queued = world.users["dev"].post(DRIVE, data={"link": "FILE000009"})
    assert queued.status_code == 303
    text = world.users["admin"].get(queued.headers["location"]).text
    assert "refused" in text.lower()
    assert fake.opened == [] and len(_sources(world)) == before
