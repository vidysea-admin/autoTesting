"""Checker B security probes (synthetic data only, scratch root)."""
from __future__ import annotations

import logging
from pathlib import Path

import pytest
from auth_harness import team, gate_on, login
from test_role_accounts_routes import MARK, _form, _env, _member  # reuse fixtures

from autotester.store.project_store import ProjectStore


@pytest.fixture()
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    return gate_on(tmp_path, monkeypatch)


def _all_text(root: Path) -> dict[str, str]:
    out = {}
    for p in root.rglob("*"):
        if p.is_file() and p.name != ".env":
            try:
                out[str(p.relative_to(root))] = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                pass
    return out


def test_p1_value_never_in_logs_responses_files_dom(root, caplog, capfd):
    caplog.set_level(logging.DEBUG)
    dev = team()["dev"]
    r = dev.post("/onboard/roles", data=_form())
    assert r.status_code == 303
    bodies = [r.text, dev.get("/projects/northwind/accounts").text,
              dev.get("/onboard/roles").text, dev.get("/projects/northwind").text]
    # a failing edit that carries values
    bad = _form(count=2); bad["account_pass_key"] = ["BAD", "NORTHWIND_ACCT1_PASS"]
    r2 = dev.post("/projects/northwind/accounts", data=bad)
    bodies.append(r2.text)
    for b in bodies:
        assert MARK not in b
    assert MARK not in caplog.text
    cap = capfd.readouterr()
    assert MARK not in cap.out and MARK not in cap.err
    for name, text in _all_text(root).items():
        assert MARK not in text, name
    # location header of redirect
    assert MARK not in str(r.headers)
    # admin (holds credentials.view) edit form must not prefill a value
    admin = login("admin@team.test")
    page = admin.get("/projects/northwind/accounts").text
    assert MARK not in page


def test_p2_env_preserved_atomic_no_tmp_left(root):
    (root / ".env").write_text("# keep me\nOTHER_KEY=keepme\nFOO=bar # c\n", encoding="utf-8")
    dev = team()["dev"]
    assert dev.post("/onboard/roles", data=_form(count=2)).status_code == 303
    text = (root / ".env").read_text(encoding="utf-8")
    assert "# keep me" in text and "OTHER_KEY=keepme" in text and "FOO=bar # c" in text
    assert not list(root.glob(".env-*.tmp"))
    assert _env(root)["NORTHWIND_ACCT1_PASS"] == f"{MARK}pass1"


@pytest.mark.parametrize("bad", ["a\nINJECT=1", "a\rb", "it's \"both\""])
def test_p3_bad_value_batch_writes_nothing(root, bad):
    d = _form(count=5)
    d["account_pass_value"][3] = bad
    before = (root / ".env").read_text() if (root / ".env").exists() else None
    r = team()["dev"].post("/onboard/roles", data=d)
    assert r.status_code == 400
    assert ProjectStore("northwind", root).load_project() is None
    after = (root / ".env").read_text() if (root / ".env").exists() else None
    assert before == after
    assert "INJECT" not in r.text and MARK not in r.text


def test_p3b_bad_value_on_edit_writes_nothing(root):
    dev = team()["dev"]
    dev.post("/onboard/roles", data=_form(count=3, values=False))
    d = _form(count=5)
    d["account_pass_value"][4] = "a\nINJECT=1"
    r = dev.post("/projects/northwind/accounts", data=d)
    assert r.status_code == 400
    assert not _env(root)
    now = ProjectStore("northwind", root).load_project()
    assert len(now.role_accounts or []) == 3


@pytest.mark.parametrize("scope", ["evil.test", "parent.nw.test:8080", "https://parent.nw.test/",
                                   "sub.parent.nw.test", "nw.test", "*.nw.test", "school.nw.test"])
def test_p4_scope_outside_platform_refused(root, scope):
    d = _form(count=3, values=False, scope={0: scope}, subs="no")
    r = team()["dev"].post("/onboard/roles", data=d)
    assert r.status_code == 400, (scope, r.status_code)
    assert ProjectStore("northwind", root).load_project() is None
    assert "acct0" in r.text and "parent" in r.text


@pytest.mark.parametrize("scope", ["Parent.NW.test.", ".parent.nw.test"])
def test_p4b_normalised_inside_scope_accepted_and_stored_normalised(root, scope):
    d = _form(count=3, values=False, scope={0: scope}, subs="no")
    r = team()["dev"].post("/onboard/roles", data=d)
    assert r.status_code == 303
    p = ProjectStore("northwind", root).load_project()
    assert p.secret("NORTHWIND_ACCT0_USER").domains == ["parent.nw.test"]


@pytest.mark.parametrize("key", ["ANTHROPIC_API_KEY", "AUTOTESTER_APPROVAL_KEY", "OPENAI_API_KEY",
                                 "PATH", "HOME", "OTHERPROJ_X_PASS"])
def test_p5_foreign_or_server_key_refused(root, key):
    d = _form(count=2)
    d["account_pass_key"][1] = key
    r = team()["dev"].post("/onboard/roles", data=d)
    assert r.status_code in (400, 403), (key, r.status_code)
    assert not _env(root) and ProjectStore("northwind", root).load_project() is None


def test_p5b_foreign_key_refused_on_edit(root):
    dev = team()["dev"]
    dev.post("/onboard/roles", data=_form(count=2, values=False))
    d = _form(count=3)
    d["account_pass_key"][2] = "ANTHROPIC_API_KEY"
    d["account_pass_value"][2] = "x"
    r = dev.post("/projects/northwind/accounts", data=d)
    assert r.status_code in (400, 403) and not _env(root)


def test_p6_value_for_undeclared_key_cannot_be_smuggled_via_other_project_key(root):
    # a second project's declared key cannot be claimed
    dev = team()["dev"]
    dev.post("/onboard/roles", data=_form("northwind", count=2, values=False))
    d = _form("southwind", count=2, values=False)
    d["account_pass_key"][0] = "NORTHWIND_ACCT0_PASS"
    r = dev.post("/onboard/roles", data=d)
    assert r.status_code == 400


def test_p7_pasted_value_in_id_field_observation(root):
    # a credential value typed into an *id* (lowercase, charset-valid) field
    (root / ".env").write_text("OTHER_SECRET=hunter2zebra\n", encoding="utf-8")
    d = _form(count=1, values=False)
    d["account_id"] = ["hunter2zebra"]
    r = team()["dev"].post("/onboard/roles", data=d)
    print("P7 status", r.status_code)
    p = ProjectStore("northwind", root).load_project()
    print("P7 saved?", p is not None)


def test_p8_env_write_failure_after_save(root, monkeypatch):
    from autotester.stages import role_onboarding as ro
    from autotester.auth import access
    dev = team()["dev"]
    def boom(*a, **k):
        raise OSError("lock timeout")
    with monkeypatch.context() as m:
        m.setattr(ro, "set_env_values", boom)
        try:
            status = dev.post("/onboard/roles", data=_form(count=2)).status_code
        except Exception as exc:
            status = repr(exc)
    p = ProjectStore("northwind", root).load_project()
    print("P8", status, "project saved:", p is not None, "env:", _env(root))
    r2 = dev.post("/onboard/roles", data=_form(count=2))
    print("P8 retry same slug", r2.status_code, r2.text[:120])
    print("P8 dev can open project page:", dev.get("/projects/northwind/accounts").status_code)


def test_p9_other_users_project_edit_denied_and_view_denied(root):
    m = team()
    m["dev"].post("/onboard/roles", data=_form(count=2, values=False))
    nogroup = _member("only@team.test", [])
    assert nogroup.get("/projects/northwind/accounts").status_code in (403, 404)
    assert nogroup.post("/projects/northwind/accounts", data=_form(count=1)).status_code in (403, 404)
    assert not _env(root)
    viewer_creator = _member("pc@team.test", ["project.create"])
    # project.create holder, not the owner of northwind
    assert viewer_creator.post("/projects/northwind/accounts", data=_form(count=3)).status_code in (403, 404)
    assert not _env(root)


def test_p10_creator_becomes_owner_and_own_scope_works(root):
    from auth_harness import account, ADMIN
    account(ADMIN)
    owner = _member("own@team.test", ["project.create", "project.view@own", "project.edit@own",
                                      "credentials.edit@own"])
    other = _member("oth@team.test", ["project.create", "project.view@own", "project.edit@own",
                                      "credentials.edit@own"])
    assert owner.post("/onboard/roles", data=_form(count=2)).status_code == 303
    assert owner.post("/projects/northwind/accounts", data=_form(count=3)).status_code == 303
    assert _env(root)["NORTHWIND_ACCT2_PASS"] == f"{MARK}pass2"
    before = dict(_env(root))
    r = other.post("/projects/northwind/accounts", data=_form(count=4))
    assert r.status_code in (403, 404)
    assert _env(root) == before
    # an owner without credentials.edit@own cannot write a value
    ro_ = _member("noc@team.test", ["project.create", "project.view@own", "project.edit@own"])
    assert ro_.post("/onboard/roles", data=_form("sw2", count=2, values=False)).status_code == 303
    assert ro_.post("/projects/sw2/accounts", data=_form("sw2", count=3)).status_code == 403
    assert not any(k.startswith("SW2_") for k in _env(root))
