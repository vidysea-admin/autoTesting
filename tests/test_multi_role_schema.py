"""T-207 (multi-role-platform.md MP1-MP3, MPI3): Platform, PlatformLink, RoleAccount, MailboxRef
and the optional `Project` fields are closed shapes that hold keys, never values, and an old
project.json still loads and writes back byte-identical."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from autotester.core.redact import assert_no_raw_secrets
from autotester.schema import multi_role_enums as enums
from autotester.schema.mailbox_ref import MailboxRef
from autotester.schema.platform import IMPLICIT_PLATFORM_ID, Platform
from autotester.schema.platform_link import PlatformLink
from autotester.schema.project import Project
from autotester.schema.role_account import RoleAccount
from autotester.store.filestore import read_json, write_json

ROOT = Path(__file__).resolve().parents[1]
PRE_G11 = Path(__file__).parent / "golden" / "pre_g11_project.json"
VALUE_SHAPED = ["hunter2", "Pa55 word", "alice@example.com", "lower_case", "9LEADING_DIGIT",
                "KEY\n", "", "A" * 65]


def _platform(pid: str = "parent", **over: object) -> Platform:
    fields: dict[str, object] = {
        "id": pid, "name": pid.title(), "base_url": f"https://{pid}.example.test/",
        "allowed_domains": [f"{pid}.example.test"]}
    return Platform(**{**fields, **over})


def _link(src: str = "parent", dst: str = "school", **over: object) -> PlatformLink:
    fields: dict[str, object] = {
        "from_platform": src, "to_platform": dst, "kind": enums.LinkKind.SSO,
        "control_name": "Open school portal", "expected_landing_host": f"{dst}.example.test"}
    return PlatformLink(**{**fields, **over})


def _mailbox(**over: object) -> MailboxRef:
    fields: dict[str, object] = {
        "host_key": "MAIL_HOST", "user_key": "MAIL_PARENT_USER", "password_key": "MAIL_PARENT_PASS"}
    return MailboxRef(**{**fields, **over})


def _account(aid: str = "parent-1", **over: object) -> RoleAccount:
    fields: dict[str, object] = {
        "id": aid, "role": "Parent", "platform_id": "parent",
        "username_key": "PARENT_USER", "password_key": "PARENT_PASS", "tenant_label": "school-a"}
    return RoleAccount(**{**fields, **over})


def _g11_project(**over: object) -> Project:
    fields: dict[str, object] = {
        "slug": "demo", "name": "Demo", "base_url": "https://parent.example.test/",
        "platforms": [_platform("parent"), _platform("school")],
        "platform_links": [_link("parent", "school")],
        "role_accounts": [
            _account("parent-1"),
            _account("teacher-1", role="Teacher", platform_id="school", mailbox_ref=_mailbox())]}
    return Project(**{**fields, **over})


# MP1 -- closed shapes ---------------------------------------------------------------------------


def test_link_kind_is_the_closed_set() -> None:
    assert {k.value for k in enums.LinkKind} == {"redirect", "sso", "shared_account", "handoff"}


def test_g11_project_round_trips() -> None:
    project = _g11_project()
    again = Project.model_validate_json(project.model_dump_json())
    assert again == project
    assert [p.id for p in again.effective_platforms()] == ["parent", "school"]


@pytest.mark.parametrize("build", [
    lambda: _platform(surprise=1), lambda: _link(surprise=1),
    lambda: _account(surprise=1), lambda: _mailbox(surprise=1),
    lambda: _g11_project(surprise=1)])
def test_unknown_field_is_rejected_on_every_model(build) -> None:
    with pytest.raises(ValidationError, match="surprise"):
        build()


def test_dangling_link_is_rejected_on_either_end() -> None:
    with pytest.raises(ValidationError, match="ghost"):
        _g11_project(platform_links=[_link("parent", "ghost")])
    with pytest.raises(ValidationError, match="ghost"):
        _g11_project(platform_links=[_link("ghost", "school")])


def test_link_with_platforms_undeclared_only_sees_the_implicit_one() -> None:
    legacy = {"slug": "old", "name": "Old", "base_url": "https://old.example.test/"}
    with pytest.raises(ValidationError, match="school"):
        Project(**legacy, platform_links=[_link(IMPLICIT_PLATFORM_ID, "school")])


def test_dangling_role_account_platform_is_rejected() -> None:
    with pytest.raises(ValidationError, match="nowhere"):
        _g11_project(role_accounts=[_account(platform_id="nowhere")])


def test_duplicate_ids_are_rejected() -> None:
    with pytest.raises(ValidationError, match="duplicate"):
        _g11_project(platforms=[_platform("parent"), _platform("parent")], platform_links=None)
    with pytest.raises(ValidationError, match="duplicate"):
        _g11_project(role_accounts=[_account("x"), _account("x")])


def test_link_needs_a_trigger_and_a_bare_host() -> None:
    with pytest.raises(ValidationError, match="trigger"):
        _link(control_name=None, url_template=None)
    _link(control_name=None, url_template="https://parent.example.test/go/{id}")
    for bad in ("https://school.example.test/", "school.example.test/path", "has space", ""):
        with pytest.raises(ValidationError):
            _link(expected_landing_host=bad)


def test_platform_blank_domain_is_rejected_but_empty_list_is_allowed() -> None:
    assert _platform(allowed_domains=[]).allowed_domains == []
    with pytest.raises(ValidationError, match="non-empty"):
        _platform(allowed_domains=["  "])
    assert _platform(allowed_domains=[" .Host.Test "]).allowed_domains == ["host.test"]


def test_strict_bools_and_defaults() -> None:
    with pytest.raises(ValidationError):
        _platform(include_subdomains="false")
    with pytest.raises(ValidationError):
        _link(carries_session="yes")
    assert _platform().include_subdomains is True
    assert _link().carries_session is False
    assert _account().provided_by is enums.AccountOrigin.ONBOARDER


# MP2 -- keys, never values ------------------------------------------------------------------------


@pytest.mark.parametrize("field", ["username_key", "password_key"])
@pytest.mark.parametrize("value", VALUE_SHAPED)
def test_role_account_key_fields_reject_value_shaped_text(field: str, value: str) -> None:
    with pytest.raises(ValidationError):
        _account(**{field: value})


@pytest.mark.parametrize("field", ["host_key", "user_key", "password_key"])
@pytest.mark.parametrize("value", VALUE_SHAPED)
def test_mailbox_ref_key_fields_reject_value_shaped_text(field: str, value: str) -> None:
    with pytest.raises(ValidationError):
        _mailbox(**{field: value})


def test_nested_mailbox_ref_is_checked_through_role_account() -> None:
    with pytest.raises(ValidationError):
        _account(mailbox_ref={"host_key": "MAIL_HOST", "user_key": "bob@x.test",
                              "password_key": "MAIL_PASS"})


def test_persona_ref_and_account_id_patterns() -> None:
    for bad in ("Has Caps", "", "-lead"):
        with pytest.raises(ValidationError):
            _account(user_persona_ref=bad)
    for bad in ("Bad Id", "", "1abc"):
        with pytest.raises(ValidationError):
            _account(aid=bad)
    assert _account(user_persona_ref="parent_walker").user_persona_ref == "parent_walker"


def test_secretref_key_rule_is_shared_not_copied() -> None:
    from autotester.schema.mailbox_ref import SECRET_KEY_PATTERN
    from autotester.schema.project import SecretRef

    assert SecretRef.model_fields["key"].metadata[0].pattern == SECRET_KEY_PATTERN


def test_serialised_project_carries_no_value_and_passes_the_prompt_gate(tmp_path: Path) -> None:
    values = ["s3cr3t-parent-pw!", "t3acher#pw-9", "mailbox-pw-77x"]
    project = _g11_project()
    text = project.model_dump_json(exclude_none=True)
    assert "@" not in text
    assert_no_raw_secrets(text, values)
    write_json(tmp_path / "project.json", project)
    assert_no_raw_secrets((tmp_path / "project.json").read_text(encoding="utf-8"), values)
    with pytest.raises(Exception):  # noqa: B017 -- the gate itself must still bite on a leaked value
        assert_no_raw_secrets(text + values[0], values)


# MP3 -- old projects still load ------------------------------------------------------------------


def test_pre_g11_fixture_is_byte_identical_after_round_trip(tmp_path: Path) -> None:
    project = read_json(PRE_G11, Project)
    assert project is not None
    out = tmp_path / "project.json"
    write_json(out, project)
    assert out.read_bytes() == PRE_G11.read_bytes()
    written = json.loads(out.read_text(encoding="utf-8"))
    assert not {"platforms", "platform_links", "role_accounts"} & set(written)


def test_pre_g11_project_is_one_implicit_platform() -> None:
    project = read_json(PRE_G11, Project)
    assert project is not None and project.platforms is None
    (only,) = project.effective_platforms()
    assert only.id == IMPLICIT_PLATFORM_ID
    assert only.allowed_domains == project.allowed_domains
    assert only.base_url == project.base_url and only.login_case_id == project.login_case_id


def test_every_committed_project_loads_without_the_new_fields() -> None:
    files = sorted((ROOT / "projects").glob("*/project.json"))
    assert files
    for path in files:
        loaded = Project.model_validate_json(path.read_text(encoding="utf-8"))
        assert loaded.platforms is None and loaded.role_accounts is None, path
        assert len(loaded.effective_platforms()) == 1, path


def test_effective_platforms_copies_domains_not_aliases_them() -> None:
    project = Project(slug="old", name="Old", base_url="https://o.test/",
                      allowed_domains=["o.test"])
    project.effective_platforms()[0].allowed_domains.append("evil.test")
    assert project.allowed_domains == ["o.test"]


# MPI3 -- one enums file -------------------------------------------------------------------------


def test_every_g11_enum_lives_in_the_one_enums_file() -> None:
    expected = {"LinkKind", "AccountOrigin", "Priority", "FindingClass", "AssertChannel",
                "Expectation", "OracleName"}
    names = {n for n, v in vars(enums).items()
             if isinstance(v, type) and issubclass(v, enums.StrEnum) and v is not enums.StrEnum}
    assert names == expected
    assert {m.value for m in enums.Priority} == {"P0", "P1", "P2"}
    assert {m.value for m in enums.AssertChannel} == {"ui", "mailbox", "api"}
    assert {m.value for m in enums.Expectation} == {"present", "absent"}
    assert {m.value for m in enums.AccountOrigin} == {"onboarder", "created_in_run"}
    # the oracle value is the stage module suffix: stages/oracle_<value>.py (MP15 imports by name)
    assert all(m.value.isidentifier() for m in enums.OracleName) and len(enums.OracleName) == 13
