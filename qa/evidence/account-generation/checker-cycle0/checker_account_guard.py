"""Independent disabled-account and foreign-root consent guard probe."""
import pytest
from auth_harness import ADMIN,account,gate_on
from autotester.auth import db
from autotester.store.notification_prefs import load_notification_pref,save_notification_pref
from autotester.store.filestore import write_json

def test_disabled_and_foreign_root_fail_closed(tmp_path,monkeypatch):
 root=gate_on(tmp_path,monkeypatch);uid=account(ADMIN)
 pref=save_notification_pref(uid,True)
 original=load_notification_pref(uid);assert original.email_run_reports
 foreign=tmp_path/'foreign';write_json(foreign/'.work'/'notification_prefs'/f'{uid}.json',original)
 assert not load_notification_pref(uid,foreign).email_run_reports
 with pytest.raises(ValueError,match='identity'):save_notification_pref(uid,True,foreign)
 with db.transaction() as conn:conn.execute('UPDATE users SET disabled=1 WHERE id=?',(uid,))
 assert not load_notification_pref(uid).email_run_reports
 with pytest.raises(ValueError,match='identity'):save_notification_pref(uid,True)
