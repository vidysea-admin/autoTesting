"""T-208 (MP4, MP5, MP6): the role-account routes -- 8 accounts x 3 platforms in one submission,
scope refusal over HTTP, and the identity/permission split (project.create / project.edit /
credentials.edit). Every credential and value here is synthetic.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from auth_harness import ADMIN, PASSWORD, account, client, gate_on, login, project, team
from fastapi.testclient import TestClient

from autotester.auth import accounts, groups
from autotester.browser.secrets import parse_env
from autotester.store.project_store import ProjectStore

PLATFORMS = [("parent", "Parent app", "parent.nw.test"),
             ("school", "School portal", "school.nw.test"),
             ("admin", "Admin console", "admin.nw.test")]
ROLES = ["Parent", "Guardian", "Class teacher", "Subject teacher", "Principal", "Registrar",
         "School admin", "Support agent"]
MARK = "Qv7-synthetic-"


def _form(slug: str = "northwind", *, count: int = 8, scope: dict[int, str] | None = None,
          values: bool = True, subs: str = "yes") -> dict[str, list[str] | str]:
    """One submission: 3 platforms and `count` accounts spread over them."""
    data: dict[str, list[str] | str] = {"slug": slug, "name": slug.title()}
    data.update(platform_id=[p[0] for p in PLATFORMS], platform_name=[p[1] for p in PLATFORMS],
                platform_base_url=[f"https://{p[2]}/" for p in PLATFORMS],
                platform_domains=[p[2] for p in PLATFORMS], platform_subdomains=[subs] * 3)
    rows = range(count)
    pfx = slug.upper()
    data.update(
        account_id=[f"acct{i}" for i in rows], account_role=[ROLES[i % 8] for i in rows],
        account_platform=[PLATFORMS[i % 3][0] for i in rows],
        account_tenant=[f"tenant-{i % 2}" for i in rows],
        account_scope=[(scope or {}).get(i, "") for i in rows],
        account_user_key=[f"{pfx}_ACCT{i}_USER" for i in rows],
        account_user_value=[f"{MARK}user{i}" if values else "" for i in rows],
        account_pass_key=[f"{pfx}_ACCT{i}_PASS" for i in rows],
        account_pass_value=[f"{MARK}pass{i}" if values else "" for i in rows])
    return data


@pytest.fixture()
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    return gate_on(tmp_path, monkeypatch)


def _env(root: Path) -> dict[str, str]:
    path = root / ".env"
    return parse_env(path.read_text(encoding="utf-8")) if path.exists() else {}


def _member(email: str, perms: list[str]) -> TestClient:
    uid = accounts.signup(email, PASSWORD).id
    accounts.set_user_groups(uid, [groups.create_group(f"g-{email}", perms).id])
    return login(email)


# -- MP4 --------------------------------------------------------------------------------------

@pytest.mark.parametrize("count", [8, 24])
def test_mp4_n_accounts_across_three_platforms_in_one_submission(root: Path, count: int) -> None:
    dev = team()["dev"]
    resp = dev.post("/onboard/roles", data=_form(count=count))
    assert resp.status_code == 303 and resp.headers["location"] == "/projects/northwind/accounts"
    saved = ProjectStore("northwind", root).load_project()
    assert saved is not None and saved.role_accounts is not None
    assert [p.id for p in saved.platforms or []] == [p[0] for p in PLATFORMS]
    assert len(saved.role_accounts) == count
    for i, acct in enumerate(saved.role_accounts):
        assert (acct.role, acct.platform_id) == (ROLES[i % 8], PLATFORMS[i % 3][0])
        assert acct.tenant_label == f"tenant-{i % 2}"
    stored = _env(root)
    assert stored["NORTHWIND_ACCT0_PASS"] == f"{MARK}pass0"
    assert len(stored) == 2 * count
    assert {s.key for s in saved.secrets} == set(stored)


def test_mp4_the_saved_project_lists_every_account_with_role_platform_tenant(
        root: Path) -> None:
    dev = team()["dev"]
    dev.post("/onboard/roles", data=_form())
    page = dev.get("/projects/northwind/accounts")
    assert page.status_code == 200
    for i in range(8):
        for token in (f"acct{i}", ROLES[i], PLATFORMS[i % 3][0], f"tenant-{i % 2}"):
            assert token in page.text
    assert MARK not in page.text and MARK not in json.dumps(
        (root / "projects" / "northwind" / "project.json").read_text(encoding="utf-8"))


def test_mp4_the_form_renders_rows_for_three_platforms_and_eight_accounts(root: Path) -> None:
    page = team()["dev"].get("/onboard/roles")
    assert page.status_code == 200
    assert page.text.count("name='platform_id'") >= 3
    assert page.text.count("name='account_id'") >= 8
    assert "type='password'" in page.text and MARK not in page.text


def test_mp4_a_half_filled_row_is_refused_and_nothing_is_written(root: Path) -> None:
    bad = _form()
    bad["account_role"][3] = ""  # type: ignore[index]
    resp = team()["dev"].post("/onboard/roles", data=bad)
    assert resp.status_code == 400 and "account" in resp.text
    assert ProjectStore("northwind", root).load_project() is None and not _env(root)


# -- MP5 --------------------------------------------------------------------------------------

def test_mp5_a_typed_scope_admitting_a_sibling_platform_is_refused_over_http(root: Path) -> None:
    wide = _form(scope={0: "nw.test"})
    wide["platform_domains"] = ["nw.test", "school.nw.test", "admin.nw.test"]  # type: ignore[assignment]
    resp = team()["dev"].post("/onboard/roles", data=wide)
    assert resp.status_code == 400
    assert "acct0" in resp.text and "parent" in resp.text and "school.nw.test" in resp.text
    assert ProjectStore("northwind", root).load_project() is None and not _env(root)


def test_mp5_the_same_scope_with_exact_hosts_is_accepted(root: Path) -> None:
    wide = _form(scope={0: "nw.test"}, subs="no")
    wide["platform_domains"] = ["nw.test", "school.nw.test", "admin.nw.test"]  # type: ignore[assignment]
    wide["platform_base_url"] = ["https://nw.test/", "https://school.nw.test/",
                                 "https://admin.nw.test/"]
    assert team()["dev"].post("/onboard/roles", data=wide).status_code == 303


# -- MP6 --------------------------------------------------------------------------------------

def test_mp6_anonymous_and_no_group_requests_get_the_existing_refusal(root: Path) -> None:
    account(ADMIN)
    accounts.signup("nogroup@team.test", PASSWORD)
    for who in (client(), login("nogroup@team.test")):
        base = who.post("/onboard", data={"slug": "x", "name": "X"})
        assert who.get("/onboard/roles").status_code == who.get("/onboard").status_code
        assert who.post("/onboard/roles", data=_form()).status_code == base.status_code
        assert base.status_code in (303, 401, 403)
    assert ProjectStore("northwind", root).load_project() is None and not _env(root)


def test_mp6_a_tester_cannot_create_or_edit(root: Path) -> None:
    members = team()
    assert members["tester"].post("/onboard/roles", data=_form()).status_code == 403
    members["dev"].post("/onboard/roles", data=_form(count=3, values=False))
    resp = members["tester"].post("/projects/northwind/accounts", data=_form(count=1))
    assert resp.status_code in (403, 404) and not _env(root)


def test_mp6_a_developer_creating_a_project_with_values_becomes_its_owner(root: Path) -> None:
    dev = team()["dev"]
    assert dev.post("/onboard/roles", data=_form(count=3)).status_code == 303
    assert dev.get("/projects/northwind/accounts").status_code == 200
    assert dev.post("/projects/northwind/accounts", data=_form(count=1, values=False)
                    ).status_code == 303


def test_mp6_project_edit_alone_declares_keys_but_cannot_write_a_value(root: Path) -> None:
    team()["dev"].post("/onboard/roles", data=_form(count=3, values=False))
    editor = _member("editor@team.test", ["project.view@all", "project.edit@all"])
    before = (root / "projects" / "northwind" / "project.json").read_text(encoding="utf-8")
    declared = editor.post("/projects/northwind/accounts", data=_form(count=4, values=False))
    assert declared.status_code == 303
    after_declare = ProjectStore("northwind", root).load_project()
    assert after_declare is not None and len(after_declare.role_accounts or []) == 4
    valued = editor.post("/projects/northwind/accounts", data=_form(count=5, values=True))
    assert valued.status_code == 403 and MARK not in valued.text
    assert not _env(root)
    now = ProjectStore("northwind", root).load_project()
    assert now is not None and len(now.role_accounts or []) == 4
    assert before != (root / "projects" / "northwind" / "project.json").read_text(
        encoding="utf-8")


def test_mp6_credentials_edit_alone_is_refused(root: Path) -> None:
    team()["dev"].post("/onboard/roles", data=_form(count=3, values=False))
    only = _member("creds@team.test", ["project.view@all", "credentials.edit@all"])
    resp = only.post("/projects/northwind/accounts", data=_form(count=4, values=True))
    assert resp.status_code == 403 and not _env(root)


def test_mp6_both_permissions_write_the_value(root: Path) -> None:
    team()["dev"].post("/onboard/roles", data=_form(count=3, values=False))
    both = _member("both@team.test", ["project.view@all", "project.edit@all",
                                      "credentials.edit@all"])
    assert both.post("/projects/northwind/accounts", data=_form(count=4)).status_code == 303
    assert _env(root)["NORTHWIND_ACCT3_PASS"] == f"{MARK}pass3"


def test_the_form_page_is_reachable_for_a_member_with_view_only(root: Path) -> None:
    team()["dev"].post("/onboard/roles", data=_form(count=3, values=False))
    viewer = _member("viewer@team.test", ["project.view@all"])
    assert viewer.get("/projects/northwind/accounts").status_code == 200
    assert viewer.post("/projects/northwind/accounts", data=_form(count=1, values=False)
                       ).status_code == 403


def test_keys_outside_the_projects_namespace_are_refused(root: Path) -> None:
    bad = _form(count=2)
    bad["account_user_key"] = ["PATHLYNKS_X_USER", "NORTHWIND_ACCT1_USER"]  # type: ignore[assignment]
    resp = team()["dev"].post("/onboard/roles", data=bad)
    assert resp.status_code == 400 and "NORTHWIND_" in resp.text and not _env(root)


def test_an_already_used_key_is_refused_for_a_new_project(root: Path) -> None:
    (root / ".env").write_text("NORTHWIND_ACCT0_USER=old\n", encoding="utf-8")
    resp = team()["dev"].post("/onboard/roles", data=_form(count=2))
    assert resp.status_code == 400 and "old" not in resp.text


def test_html_in_a_role_or_tenant_is_escaped_on_the_listing(root: Path) -> None:
    data = _form(count=1, values=False)
    data["account_role"] = ["<script>alert(1)</script>"]
    data["account_tenant"] = ["<img src=x onerror=1>"]
    dev = team()["dev"]
    assert dev.post("/onboard/roles", data=data).status_code == 303
    page = dev.get("/projects/northwind/accounts").text
    assert "<script>alert(1)</script>" not in page and "&lt;script&gt;" in page
    assert "<img src=x" not in page


def test_a_stored_credential_pasted_into_a_text_field_is_refused(root: Path) -> None:
    (root / ".env").write_text("OTHER_SECRET=Hq4-pasted-synthetic-secret\n", encoding="utf-8")
    data = _form(count=1, values=False)
    data["account_tenant"] = ["Hq4-pasted-synthetic-secret"]
    resp = team()["dev"].post("/onboard/roles", data=data)
    assert resp.status_code == 400 and "Hq4-pasted" not in resp.text
    assert ProjectStore("northwind", root).load_project() is None


def test_editing_keeps_untouched_accounts_and_their_scope(root: Path) -> None:
    dev = team()["dev"]
    dev.post("/onboard/roles", data=_form(count=3, values=False,
                                          scope={0: "parent.nw.test"}, subs="no"))
    extra = _form(count=4, values=False)
    keep = {k: [v[3]] for k, v in extra.items() if k.startswith("account_")}
    data = {k: v for k, v in keep.items()}
    assert dev.post("/projects/northwind/accounts", data=data).status_code == 303
    saved = ProjectStore("northwind", root).load_project()
    assert saved is not None and [a.id for a in saved.role_accounts or []] == [
        "acct0", "acct1", "acct2", "acct3"]
    scoped = saved.secret("NORTHWIND_ACCT0_USER")
    assert scoped is not None and scoped.domains == ["parent.nw.test"]


def test_an_old_single_platform_project_takes_accounts_on_its_implicit_platform(
        root: Path) -> None:
    project(root, "legacy")
    admin = team()["admin"]
    data = {"account_id": ["a1"], "account_role": ["Owner"], "account_platform": ["primary"],
            "account_tenant": [""], "account_scope": [""], "account_user_key": ["LEGACY_A1_USER"],
            "account_user_value": [""], "account_pass_key": ["LEGACY_A1_PASS"],
            "account_pass_value": [f"{MARK}legacy"]}
    assert admin.post("/projects/legacy/accounts", data=data).status_code == 303
    saved = ProjectStore("legacy", root).load_project()
    assert saved is not None and saved.platforms is None and len(saved.role_accounts or []) == 1
    assert _env(root)["LEGACY_A1_PASS"] == f"{MARK}legacy"
