"""Coordinator B cycle-1 probes (synthetic values only; scratch AUTOTESTER_ROOT)."""
from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest
from auth_harness import gate_on, team
from test_role_accounts_routes import MARK, _env, _form, _member

from autotester.stages import role_onboarding as ro
from autotester.store.project_store import ProjectStore
from autotester.ui import routes_role_accounts as rra
from autotester.ui.env_editor import set_env_values


@pytest.fixture()
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    return gate_on(tmp_path, monkeypatch)


def _pj(root: Path) -> dict:
    return json.loads((root / "projects" / "northwind" / "project.json").read_text(encoding="utf-8"))


def _refs(root: Path) -> dict:
    return {s["key"]: (sorted(s["domains"]), s.get("include_subdomains")) for s in _pj(root)["secrets"]}


def _editor():
    return _member("editor@team.test", ["project.view@all", "project.edit@all"])


def _seed(root: Path, count: int = 3):
    team()["dev"].post("/onboard/roles", data=_form(count=count))


def test_q1a_editor_may_change_a_tenant_label(root):
    _seed(root)
    ed = _editor()
    data = _form(count=3, values=False)
    data["account_tenant"] = ["renamed-0", "renamed-1", "renamed-2"]
    before = _refs(root)
    r = ed.post("/projects/northwind/accounts", data=data)
    assert r.status_code == 303, r.text[:200]
    assert _refs(root) == before
    assert [a["tenant_label"] for a in _pj(root)["role_accounts"][:3]] == ["renamed-0", "renamed-1", "renamed-2"]


def test_q1b_key_swap_across_platforms_refused(root):
    _seed(root)
    ed = _editor()
    data = _form(count=3, values=False)
    u, p = data["account_user_key"], data["account_pass_key"]
    data["account_user_key"] = [u[1], u[0], u[2]]
    data["account_pass_key"] = [p[1], p[0], p[2]]
    before, envb = _refs(root), _env(root)
    r = ed.post("/projects/northwind/accounts", data=data)
    print("Q1b status", r.status_code)
    assert r.status_code in (400, 403)
    assert _refs(root) == before and _env(root) == envb


def test_q1c_account_platform_change_refused(root):
    _seed(root)
    ed = _editor()
    data = _form(count=3, values=False)
    data["account_platform"] = ["school", "school", "admin"]
    before, envb = _refs(root), _env(root)
    r = ed.post("/projects/northwind/accounts", data=data)
    print("Q1c status", r.status_code)
    assert r.status_code in (400, 403)
    assert _refs(root) == before and _env(root) == envb


def test_q1d_platform_domain_widen_then_default_scope_refused(root):
    _seed(root)
    ed = _editor()
    data = _form(count=3, values=False)
    data["platform_domains"] = ["parent.nw.test,school.nw.test", "school.nw.test", "admin.nw.test"]
    before, envb = _refs(root), _env(root)
    r = ed.post("/projects/northwind/accounts", data=data)
    print("Q1d status", r.status_code)
    assert r.status_code in (400, 403)
    assert _refs(root) == before and _env(root) == envb


def test_q1e_platform_widened_without_account_rows(root):
    _seed(root)
    ed = _editor()
    data = _form(count=0, values=False)
    data["platform_domains"] = ["parent.nw.test,school.nw.test", "school.nw.test", "admin.nw.test"]
    before, envb = _refs(root), _env(root)
    r = ed.post("/projects/northwind/accounts", data=data)
    print("Q1e status", r.status_code)
    assert _refs(root) == before and _env(root) == envb


def test_q1f_editor_adds_new_account_without_values(root):
    _seed(root)
    ed = _editor()
    data = _form(count=4, values=False)
    envb = _env(root)
    r = ed.post("/projects/northwind/accounts", data=data)
    assert r.status_code == 303
    assert _env(root) == envb and "NORTHWIND_ACCT3_USER" in _refs(root)


def test_q1g_env_key_existence_oracle(root):
    _seed(root)
    envp = root / ".env"
    envp.write_text(envp.read_text() + "ANTHROPIC_API_KEY=" + MARK + "secret-foreign\nPATHLYNKS_X=" + MARK + "other\n",
                    encoding="utf-8")
    ed = _editor()
    outcomes = {}
    for key in ("ANTHROPIC_API_KEY", "NOT_PRESENT_API_KEY", "PATHLYNKS_X", "PATHLYNKS_NOT_THERE"):
        data = _form(count=4, values=False)
        data["account_user_key"] = data["account_user_key"][:3] + [key]
        r = ed.post("/projects/northwind/accounts", data=data)
        outcomes[key] = (r.status_code, MARK in r.text)
    print("Q1g outcomes", outcomes)
    assert not any(v[1] for v in outcomes.values())


def test_q2_no_value_in_logs_or_bodies(root, caplog, capsys):
    _seed(root)
    ed = _editor()
    caplog.set_level(logging.DEBUG)
    data = _form(count=1, values=True)
    for key in ("platform_id", "platform_name", "platform_base_url", "platform_domains", "platform_subdomains"):
        data[key] = data[key][:1]
    data["platform_base_url"], data["platform_domains"] = ["https://parent.evil.test/"], ["parent.evil.test"]
    r = ed.post("/projects/northwind/accounts", data=data)
    assert r.status_code == 403
    both = _member("both@team.test", ["project.view@all", "project.edit@all", "credentials.edit@all"])
    r2 = both.post("/projects/northwind/accounts", data=data)
    out = capsys.readouterr()
    blob = r.text + r2.text + caplog.text + out.out + out.err
    assert MARK not in blob
    assert MARK not in (root / "projects" / "northwind" / "project.json").read_text(encoding="utf-8")


def test_q3a_rollback_restores_preexisting_env_bytes(root, monkeypatch):
    envp = root / ".env"
    original = "# comment\nOTHERPROJ_KEY=keep-me-Zq8x7\n\nANOTHER=Zq9w-long-value\n"
    envp.write_text(original, encoding="utf-8")

    def boom(*a, **k):
        raise OSError("db locked")

    real_owner = rra.set_owner
    monkeypatch.setattr(rra, "set_owner", boom)
    dev = team()["dev"]
    try:
        rr = dev.post("/onboard/roles", data=_form(count=3))
        print("Q3a status", rr.status_code, rr.text[:200])
    except OSError as e:
        print("Q3a raised", e)
    assert envp.read_text(encoding="utf-8") == original
    assert ProjectStore("northwind", root).load_project() is None
    monkeypatch.setattr(rra, "set_owner", real_owner)
    r = dev.post("/onboard/roles", data=_form(count=3))
    import re
    print("Q3a retry", r.status_code, " ".join(re.sub(r"<[^>]+>", " ", r.text)[-300:].split()))
    print("Q3a project dir:", sorted(p.name for p in (root / "projects" / "northwind").glob("*")) if (root / "projects" / "northwind").exists() else None)
    assert r.status_code == 303


def test_q3b_restore_vs_concurrent_write(root, monkeypatch):
    envp = root / ".env"
    envp.write_text("OTHERPROJ_KEY=keep-me\n", encoding="utf-8")

    def racing_then_fail(self, project):
        set_env_values(envp, {"CONCURRENT_KEY": "added-by-other-request"})
        raise OSError("disk full")

    monkeypatch.setattr(ProjectStore, "save_project", racing_then_fail)
    with pytest.raises(OSError):
        team()["dev"].post("/onboard/roles", data=_form(count=3))
    monkeypatch.undo()
    print("Q3b concurrent key survived rollback:", "CONCURRENT_KEY" in envp.read_text(encoding="utf-8"))


def test_q3c_failure_with_no_values_touches_env(root, monkeypatch):
    envp = root / ".env"

    def boom(self, p):
        raise OSError("x")

    monkeypatch.setattr(ProjectStore, "save_project", boom)
    with pytest.raises(OSError):
        team()["dev"].post("/onboard/roles", data=_form(count=3, values=False))
    print("Q3c env exists after failure w/o values:", envp.exists())


@pytest.mark.parametrize("dom,ok", [("com", False), ("COM", False), (".com", False), ("com.", False),
                                    ("intranet", False), ("localhost", True), ("app.example.com", True),
                                    ("co.uk", True), ("127.0.0.1", True)])
def test_q4_bare_tld(dom, ok):
    from autotester.schema.platform import Platform
    base = "http://localhost/" if dom == "localhost" else f"https://{dom.strip('.').lower()}/"
    plat = Platform(id="p", name="P", base_url=base, allowed_domains=[dom])
    if ok:
        ro.check_platforms([plat])
    else:
        with pytest.raises(ro.OnboardingError):
            ro.check_platforms([plat])
