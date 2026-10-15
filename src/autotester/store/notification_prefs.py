"""Persist only a numeric account's report-email preference, defaulting safely to off."""

from __future__ import annotations

from pathlib import Path

from autotester.core.paths import repo_root
from autotester.schema.delivery import NotificationPref
from autotester.store.filestore import read_json, write_json


def _preference_path(user_id: int, root: Path | None) -> Path:
    if type(user_id) is not int or user_id < 1:
        raise ValueError("a positive numeric account id is required")
    return (root or repo_root()) / ".work" / "notification_prefs" / f"{user_id}.json"


def load_notification_pref(user_id: int, root: Path | None = None) -> NotificationPref:
    """Missing, corrupt or mismatched records never opt anyone into mail."""
    path = _preference_path(user_id, root)
    try:
        pref = read_json(path, NotificationPref)
    except (OSError, ValueError):
        pref = None
    if pref is None or pref.user_id != str(user_id):
        return NotificationPref(user_id=str(user_id))
    return pref


def save_notification_pref(user_id: int, enabled: bool, root: Path | None = None) -> None:
    """An atomic per-account write; addresses and SMTP settings are never persisted here."""
    path = _preference_path(user_id, root)
    if type(enabled) is not bool:
        raise ValueError("the notification preference must be boolean")
    write_json(path, NotificationPref(user_id=str(user_id), email_run_reports=enabled))
