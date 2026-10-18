"""T-208 cycle 1: re-pointing a declared key is a credential action (P1, MP6), a bare TLD is not a
platform (P3, MP5), and a failed write never leaves a saved project (P4, MP4). Shares the form
builders and the gate fixture with `test_role_accounts_routes.py`. Every value here is synthetic.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from auth_harness import gate_on, team
from test_role_accounts_routes import MARK, _env, _form, _member

from autotester.auth.access import resource_for
from autotester.stages import role_onboarding as ro
from autotester.store.project_store import ProjectStore
from autotester.ui import routes_role_accounts as rra


@pytest.fixture()
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    return gate_on(tmp_path, monkeypatch)

# -- P1 (cycle 1): re-pointing a declared key is a credential action ---------------------------

def _repoint_form(domain: str = "parent.nw.test", subs: str = "yes") -> dict[str, list[str] | str]:
    """acct0 on its platform `parent`, the platform re-declared with another host/subdomain rule."""
    data = _form(count=1, values=False)
    for key in ("platform_id", "platform_name", "platform_base_url", "platform_domains",
                "platform_subdomains"):
        data[key] = data[key][:1]  # type: ignore[index]
    data["platform_base_url"], data["platform_domains"] = [f"https://{domain}/"], [domain]
    data["platform_subdomains"] = [subs]
    return data


def _project_json(root: Path) -> str:
    return (root / "projects" / "northwind" / "project.json").read_text(encoding="utf-8")


@pytest.mark.parametrize("form", [_repoint_form("parent.evil.test"), _repoint_form(subs="no")],
                         ids=["new-domain", "include-subdomains-flip"])
def test_mp6_project_edit_alone_cannot_repoint_a_declared_key(
        root: Path, form: dict[str, list[str] | str]) -> None:
    team()["dev"].post("/onboard/roles", data=_form(count=3))
    editor = _member("editor@team.test", ["project.view@all", "project.edit@all"])
    before, env_before = _project_json(root), _env(root)
    resp = editor.post("/projects/northwind/accounts", data=form)
    assert resp.status_code == 403 and MARK not in resp.text
    assert _project_json(root) == before and _env(root) == env_before


def test_mp6_a_credentials_edit_holder_may_repoint_a_declared_key(root: Path) -> None:
    team()["dev"].post("/onboard/roles", data=_form(count=3))
    both = _member("both@team.test", ["project.view@all", "project.edit@all",
                                      "credentials.edit@all"])
    resp = both.post("/projects/northwind/accounts", data=_repoint_form("parent.evil.test"))
    assert resp.status_code == 303
    saved = ProjectStore("northwind", root).load_project()
    ref = saved.secret("NORTHWIND_ACCT0_USER") if saved else None
    assert ref is not None and ref.domains == ["parent.evil.test"]


def test_mp6_project_edit_alone_cannot_bind_a_key_that_already_has_a_stored_value(
        root: Path) -> None:
    team()["dev"].post("/onboard/roles", data=_form(count=3, values=False))
    (root / ".env").write_text(f"NORTHWIND_ACCT3_USER={MARK}orphan\n", encoding="utf-8")
    editor = _member("editor@team.test", ["project.view@all", "project.edit@all"])
    before = _project_json(root)
    assert editor.post("/projects/northwind/accounts", data=_form(count=4, values=False)
                       ).status_code == 403
    assert _project_json(root) == before


# -- P3 (cycle 1): a bare TLD is not a platform ------------------------------------------------

@pytest.mark.parametrize("domain", ["com", "intranet"])
def test_a_dotless_platform_domain_is_refused_and_nothing_is_saved(root: Path, domain: str) -> None:
    data = _form(count=3)
    data["platform_domains"] = [domain, *data["platform_domains"][1:]]  # type: ignore[index]
    data["platform_base_url"] = [f"https://{domain}/", *data["platform_base_url"][1:]]  # type: ignore[index]
    resp = team()["dev"].post("/onboard/roles", data=data)
    assert resp.status_code == 400 and domain in resp.text and MARK not in resp.text
    assert ProjectStore("northwind", root).load_project() is None and not _env(root)


# -- P4 (cycle 1): a failed write never leaves a saved project ---------------------------------

def test_a_failed_env_write_leaves_no_new_project_and_no_owner(
        root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_a: object, **_k: object) -> None:
        raise OSError("disk full")

    dev = team()["dev"]
    monkeypatch.setattr(ro, "write_values", boom)
    with pytest.raises(OSError):
        dev.post("/onboard/roles", data=_form(count=3))
    assert ProjectStore("northwind", root).load_project() is None
    assert resource_for("northwind").owner_email is None and not _env(root)


def test_a_failed_owner_grant_rolls_back_the_new_project_and_its_env(
        root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_a: object, **_k: object) -> None:
        raise OSError("db locked")

    dev = team()["dev"]
    monkeypatch.setattr(rra, "set_owner", boom)
    with pytest.raises(OSError):
        dev.post("/onboard/roles", data=_form(count=3))
    assert ProjectStore("northwind", root).load_project() is None and not _env(root)


def test_a_failed_project_save_on_edit_restores_project_and_env(
        root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dev = team()["dev"]
    dev.post("/onboard/roles", data=_form(count=3))
    before, env_before = _project_json(root), _env(root)

    def boom(self: ProjectStore, project: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(ProjectStore, "save_project", boom)
    changed = _form(count=4)
    changed["account_pass_value"] = [f"{MARK}changed{i}" for i in range(4)]
    with pytest.raises(OSError):
        dev.post("/projects/northwind/accounts", data=changed)
    monkeypatch.undo()
    assert _project_json(root) == before and _env(root) == env_before
