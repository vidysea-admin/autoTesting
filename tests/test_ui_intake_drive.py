"""The Drive-link door: background job, hostile links, typed failures, the gate re-check.

(team-intake.md TI7, TI8, TI10-seam; hosting.md HO32, HO33.) The Drive is a fake: no `gws`, no
network.
"""
# ruff: noqa: F811  (pytest fixtures imported from ui_intake_support are re-declared as arguments)


import json

import pytest
from ui_intake_support import (  # noqa: F401  (fixtures)
    DRIVE,
    FakeGate,
    _leftovers,
    client,
    drive,
    gate,
    store,
)
from zip_fixtures import video

from autotester.schema.intake import DriveOrigin
from autotester.ui import intake_gate

# ---- TI7 / HO32 / HO33: a pasted Drive link becomes a job ---------------------------------------

def test_ti7_a_pasted_link_fetches_in_the_background_and_the_job_page_shows_the_table(
        client, store, tmp_path, gate, drive):
    fid = drive.add("FILE000001", video("drv"), name="Walkthrough.mp4")
    response = client.post(DRIVE, data={"link": f"https://drive.google.com/file/d/{fid}/view",
                                        "uploaded_by": "attacker@evil.test"})
    assert response.status_code == 200  # the redirect to the job page was followed
    assert "Walkthrough.mp4" in response.text and "registered" in response.text
    [source] = store.list_sources()
    assert source.origin == DriveOrigin(file_id=fid)
    assert source.uploaded_by == "dev@vidysea.test"
    assert gate.rechecks == [("dev@vidysea.test", "demo")]  # checked again when the job started
    assert _leftovers(tmp_path) == []


def test_ho32_a_hostile_link_is_refused_and_not_echoed_and_makes_no_job(
        client, store, tmp_path, gate, drive):
    secret = "ya29.CANARY-TOKEN"
    for bad in [f"http://127.0.0.1/x?t={secret}", "file:///etc/passwd",
                f"https://drive.google.com.evil.io/file/d/FILE000001?t={secret}",
                f"https://evil.io/?u=https://drive.google.com/file/d/FILE000001&t={secret}"]:
        response = client.post(DRIVE, data={"link": bad}, follow_redirects=False)
        assert response.status_code == 400
        assert secret not in response.text and "evil.io" not in response.text
    assert drive.opened == [] and not (tmp_path / ".work" / "drive-jobs").exists()


def test_ho33_a_drive_failure_reaches_the_page_as_its_message_never_a_trace(
        client, store, gate, drive):
    from autotester.sources.drive_errors import MESSAGES, DriveError, DriveFailure
    drive.add("FILE000002", video("e"))
    drive.error = DriveError(DriveFailure.PERMISSION_DENIED)
    text = client.post(DRIVE, data={"link": "FILE000002"}).text
    assert MESSAGES[DriveFailure.PERMISSION_DENIED][:40] in text
    assert "Traceback" not in text and store.list_sources() == []


def test_ho33_the_job_page_says_fetching_while_it_runs(client, store, gate, drive, tmp_path):
    from autotester.schema.intake import DriveJob
    from autotester.sources.drive_jobs import save_job
    job = DriveJob(id="01J00000000000000000000000", project="demo", state="fetching")
    save_job(tmp_path, job)
    text = client.get(f"{DRIVE}/{job.id}").text
    assert "fetching" in text.lower() and 'http-equiv="refresh"' in text


def test_ti10_seam_the_queued_fetch_checks_again_and_a_refusal_fetches_no_bytes(
        client, store, tmp_path, drive):
    refusing = FakeGate(refuse_recheck=(403, "your account was disabled"))
    previous = intake_gate.set_gate(refusing)
    try:
        drive.add("FILE000003", video("late"))
        text = client.post(DRIVE, data={"link": "FILE000003"}).text
    finally:
        intake_gate.set_gate(previous)
    assert "refused" in text.lower() and "disabled" in text
    assert drive.opened == [] and store.list_sources() == []


def test_ti10_seam_a_refused_member_creates_no_job(client, store, tmp_path, drive):
    refusing = FakeGate(refuse=(404, "no such project"))
    previous = intake_gate.set_gate(refusing)
    try:
        response = client.post(DRIVE, data={"link": "FILE000004"}, follow_redirects=False)
    finally:
        intake_gate.set_gate(previous)
    assert response.status_code == 404 and not (tmp_path / ".work" / "drive-jobs").exists()


@pytest.mark.parametrize("job_id", ["x", "../../etc/passwd", "01J0000000000000000000000Z!"])
def test_a_job_id_that_is_not_one_of_ours_is_a_404(client, store, job_id):
    assert client.get(f"{DRIVE}/{job_id}").status_code in (404, 422)


def test_the_job_file_holds_no_token_or_raw_link(client, store, tmp_path, gate, drive):
    fid = drive.add("FILE000005", video("job"))
    client.post(DRIVE, data={"link": f"https://drive.google.com/open?id={fid}&usp=CANARY-USP"})
    stored = "".join(p.read_text(encoding="utf-8")
                     for p in (tmp_path / ".work" / "drive-jobs").rglob("*.json"))
    assert "CANARY-USP" not in stored and "drive.google.com" not in stored
    assert json.loads(next((tmp_path / ".work" / "drive-jobs").rglob("*.json")).read_text(
        encoding="utf-8"))["state"] == "done"


def test_a_form_with_too_many_fields_is_a_400_not_a_500(client, store, gate, drive):
    data = {f"f{i}": "x" for i in range(60)} | {"link": "FILE000006"}
    assert client.post(DRIVE, data=data, follow_redirects=False).status_code == 400


def test_at758_a_hostile_host_on_the_drive_route_is_403_and_makes_no_job(
        client, store, tmp_path, gate, drive):
    response = client.post(DRIVE, data={"link": "FILE000007"}, headers={"Host": "evil.example"},
                           follow_redirects=False)
    assert response.status_code == 403 and response.content == b""
    assert gate.checks == [] and not (tmp_path / ".work" / "drive-jobs").exists()
