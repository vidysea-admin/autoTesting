"""TT8 own-profile preference: authenticated, default-off, persistent and Origin guarded."""

from pathlib import Path

import pytest
from auth_harness import ADMIN, account, client, gate_on, login
from fastapi import HTTPException

from autotester.auth.policy import ROUTE_POLICY
from autotester.schema.auth import Principal
from autotester.store.notification_prefs import load_notification_pref, save_notification_pref
from autotester.ui import routes_profile

SMTP_KEYS = ("HOST", "PORT", "USER", "PASSWORD", "FROM", "FROM_NAME", "TLS")


@pytest.fixture()
def profile_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for suffix in SMTP_KEYS:
        monkeypatch.delenv("AUTOTESTER_SMTP_" + suffix, raising=False)
    return gate_on(tmp_path, monkeypatch)


def test_profile_anonymous_cannot_read_or_write(profile_root: Path) -> None:
    outsider = client()
    for method in ("GET", "POST"):
        response = outsider.request(method, "/profile", headers={"accept": "application/json"})
        assert response.status_code == 401
    assert not (profile_root / ".work" / "notification_prefs").exists()


def test_profile_session_policy_and_handler_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    assert all(ROUTE_POLICY[(method, "/profile")].kind == "session" for method in ("GET", "POST"))
    for principal in (None, Principal()):
        monkeypatch.setattr(routes_profile, "current_principal", lambda p=principal: p)
        with pytest.raises(HTTPException) as caught:
            routes_profile.notification_profile()
        assert caught.value.status_code == 401


def test_profile_default_off_and_boolean_config_only(profile_root: Path,
                                                    monkeypatch: pytest.MonkeyPatch) -> None:
    user_id = account(ADMIN)
    person = login(ADMIN)
    response = person.get("/profile")
    assert response.status_code == 200
    assert "Email me run reports" in response.text and " checked" not in response.text
    assert "Email is not configured on this server." in response.text
    assert not load_notification_pref(user_id).email_run_reports
    for key, value in {"HOST": "smtp.example.test", "PORT": "587", "USER": "private-user",
                       "PASSWORD": "canary-password", "FROM": "sender@example.test"}.items():
        monkeypatch.setenv("AUTOTESTER_SMTP_" + key, value)
    text = person.get("/profile").text
    assert "Email is configured on this server." in text
    for private in ("smtp.example.test", "private-user", "canary-password", "sender@example.test"):
        assert private not in text


def test_profile_own_identity_enable_revoke_and_reload(profile_root: Path) -> None:
    admin_id = account(ADMIN)
    other_id = account("new@team.test")  # session-only: groups are unnecessary for own preference
    admin, other = login(ADMIN), login("new@team.test")
    forged = {"email_run_reports": "on", "user_id": str(admin_id), "email": ADMIN,
              "to": "attacker@example.test", "recipient": ADMIN, "cc": ADMIN}
    assert other.post("/profile?user_id=" + str(admin_id), data=forged).status_code == 303
    assert load_notification_pref(other_id).email_run_reports
    assert not load_notification_pref(admin_id).email_run_reports
    assert " checked" in login("new@team.test").get("/profile").text
    assert " checked" not in admin.get("/profile").text
    assert other.post("/profile", data={}).status_code == 303
    assert not load_notification_pref(other_id).email_run_reports
    assert " checked" not in login("new@team.test").get("/profile").text
    stored = (profile_root / ".work" / "notification_prefs" / f"{other_id}.json").read_text()
    assert "attacker" not in stored and ADMIN not in stored


def test_profile_cross_origin_and_invalid_input_preserve_preference(profile_root: Path) -> None:
    user_id = account(ADMIN)
    person = login(ADMIN)
    refused = person.post("/profile", data={"email_run_reports": "on"},
                          headers={"origin": "https://attacker.example"})
    assert refused.status_code == 403
    assert not load_notification_pref(user_id).email_run_reports
    invalid = person.post("/profile", data={"email_run_reports": "private-canary"})
    assert invalid.status_code == 400 and "private-canary" not in invalid.text
    assert not load_notification_pref(user_id).email_run_reports
    assert person.post("/profile", data={"email_run_reports": "on"},
                       headers={"origin": "http://localhost"}).status_code == 303
    assert load_notification_pref(user_id).email_run_reports


def test_profile_store_fails_closed_for_corrupt_or_wrong_identity(profile_root: Path) -> None:
    save_notification_pref(1, True)
    path = profile_root / ".work" / "notification_prefs" / "1.json"
    path.write_text('{"user_id":"2","email_run_reports":true}')
    assert not load_notification_pref(1).email_run_reports
    path.write_text("not JSON")
    assert not load_notification_pref(1).email_run_reports
    for bad_id in (0, -1, True, "../1"):
        with pytest.raises(ValueError, match="positive numeric"):
            load_notification_pref(bad_id)
    with pytest.raises(ValueError, match="boolean"):
        save_notification_pref(1, "on")
