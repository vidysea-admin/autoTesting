"""TA14: each user type completes the goal the intent gave them, and each stated dead end explains
itself (a page or message that names the reason: never a blank page, a 500 or a stack trace).
Journeys are HTTP; click counts belong to TA15. The subadmin's schedule journey and the
stale-mapping row are absent: no schedule route on master, and D-090 removed the sheet mapping."""

from __future__ import annotations

import re
import time

import pytest
from auth_harness import user_id
from review_support import UPLOAD, grant_review, make_zip, review, upload, upload_video
from rig import CRED_KEY, HTML, SLUG, World, email, press
from zip_fixtures import video

from autotester.schema.server_settings import ServerSettings
from autotester.sources.drive_errors import DriveError, DriveFailure
from autotester.store.server_settings import save_server_settings
from autotester.ui import run_queue

LINK = re.compile(r"/v/([A-Za-z0-9_-]+)")
REQUEST = re.compile(r"/access-requests/(\d+)/approve")


def explained(resp, *needles: str) -> None:
    assert resp.status_code < 500 and resp.text.strip(), resp.status_code
    assert "Traceback" not in resp.text and "File \"" not in resp.text
    for needle in needles:
        assert needle.lower() in resp.text.lower(), (needle, resp.text[:300])


def test_dev_adds_videos_presses_test_and_reads_the_report(world: World) -> None:
    upload_video(world, "dev")
    run_id = press(world, "dev")
    status = world.users["dev"].get(f"/projects/{SLUG}/test/{run_id}", headers=HTML)
    assert status.status_code in (200, 303)
    assert world.users["dev"].get(f"/projects/{SLUG}/runs/{run_id}", headers=HTML
                                  ).status_code == 200


def test_tester_share_link_watch_comment_and_admin_review_with_pointers(world: World) -> None:
    source = upload_video(world, "dev")
    page = f"/projects/{SLUG}/videos/{source.id}"
    token = LINK.search(world.users["dev"].post(page + "/share-link").text)
    assert token
    world.users["tester"].post(page + "/request-access")
    rid = REQUEST.search(world.users["admin"].get("/access-requests", headers=HTML).text)
    assert rid and world.users["admin"].post(
        f"/access-requests/{rid.group(1)}/approve").status_code == 303
    assert world.users["tester"].post(page + "/comments", data={"at_s": "7", "text": "slow"}
                                      ).status_code == 303
    grant_review(world)
    assert review(world, source, "0:30 | look here").status == "ok"


def test_over_limit_upload_names_the_limit(world: World) -> None:
    save_server_settings(ServerSettings(max_upload_bytes=2 * 1024 * 1024), world.root)
    resp = world.users["dev"].post(UPLOAD, data={"label": "big"}, headers=HTML, files={
        "recording": ("big.mp4", video("big", size=3 * 1024 * 1024), "video/mp4")})
    assert resp.status_code == 413
    explained(resp, "2 MiB")


def test_a_non_video_member_is_named(world: World) -> None:
    resp = upload(world, "dev", "clips.zip", make_zip())
    explained(resp, "notes.md")


def test_drive_permission_denied_names_the_sharing_step(world: World) -> None:
    world.drive.error = DriveError(DriveFailure.PERMISSION_DENIED)
    dev = world.users["dev"]
    resp = dev.post(f"/projects/{SLUG}/sources/drive", headers=HTML, data={
        "link": "https://drive.google.com/file/d/denied-1/view"})
    page = resp
    deadline = time.time() + 10
    while resp.status_code == 303 and time.time() < deadline:
        page = dev.get(resp.headers["location"], headers=HTML)
        if "fetching" not in page.text.lower() and "queued" not in page.text.lower():
            break
        time.sleep(0.2)
    explained(page)
    assert "share" in page.text.lower()


def test_no_credentials_names_the_credentials_page(world: World) -> None:
    (world.root / ".env").write_text("", encoding="utf-8")
    resp = world.users["dev"].post(f"/projects/{SLUG}/test", headers=HTML)
    explained(resp, CRED_KEY, "Credentials")


def test_a_double_press_shows_the_existing_request(world: World, monkeypatch) -> None:
    jobs: list = []
    monkeypatch.setattr("autotester.ui.run_queue._QUEUE", run_queue.RunQueue(
        spawn=jobs.append, runner=run_queue._registered_runner))
    first = press(world, "dev")
    assert press(world, "dev") == first
    explained(world.users["dev"].get(f"/projects/{SLUG}/test/{first}", headers=HTML),
              "in progress")


def test_no_access_waiting_and_unassigned_pages_explain_themselves(world: World) -> None:
    source = upload_video(world, "dev")
    token = LINK.search(world.users["dev"].post(
        f"/projects/{SLUG}/videos/{source.id}/share-link").text)
    assert token
    explained(world.users["tester"].get(f"/v/{token.group(1)}", headers=HTML), "request access")
    explained(world.users["pending"].get("/auth/waiting", headers=HTML))
    assert world.users["dev"].get("/projects/other", headers=HTML).status_code == 404
    explained(world.users["dev"].get("/projects/other", headers=HTML))


def test_removing_the_last_admin_is_refused_with_a_reason(world: World) -> None:
    admin_id = user_id(email("admin"))
    resp = world.users["admin"].post(f"/admin/users/{admin_id}/delete", headers=HTML)
    assert resp.status_code in (400, 403, 409), resp.status_code
    explained(resp, "admin")
    assert world.users["admin"].get("/admin/users", headers=HTML).status_code == 200


@pytest.mark.xfail(strict=True, reason="blocked: no schedule save route or schedule card on "
                   "master (T-200 UI HELD), so the subadmin journey and the stale-scheduler dead "
                   "end cannot be driven")
def test_subadmin_schedules_and_sees_the_next_fire_times(world: World) -> None:
    resp = world.users["subadmin"].post(f"/projects/{SLUG}/schedule", data={
        "mode": "fixed", "fixed_at": "09:00", "timezone": "UTC"})
    assert resp.status_code == 303
