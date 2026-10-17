"""T-208 (MP4, MP5): the role-onboarding stage -- scope refusal and key hygiene (synthetic).

The stage is pure: it takes typed `Platform`/`RoleAccount` models, the optional per-account scope
the onboarder typed, and the env values, and returns the `SecretRef`s to declare or raises
`OnboardingError` with a message that names accounts, platforms and hosts but never a value.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from autotester.browser.secrets import parse_env
from autotester.schema.platform import Platform
from autotester.schema.role_account import RoleAccount
from autotester.stages import role_onboarding as ro

SENTINEL = "Zx9-synthetic-value-not-a-real-credential"


def _platform(pid: str, *domains: str, subs: bool = True) -> Platform:
    return Platform(id=pid, name=pid.title(), base_url=f"https://{domains[0]}/",
                    allowed_domains=list(domains), include_subdomains=subs)


def _account(aid: str, platform_id: str, **kw: object) -> RoleAccount:
    return RoleAccount(id=aid, role=kw.pop("role", "Teacher"), platform_id=platform_id,
                       username_key=f"NW_{aid.upper()}_USER",
                       password_key=f"NW_{aid.upper()}_PASS", **kw)


def _sibling_platforms(*, school_subs: bool) -> list[Platform]:
    """`admin.school.test` sits under `school.test`: the suffix-match hazard (MPI5)."""
    return [_platform("school", "school.test", subs=school_subs),
            _platform("admin", "admin.school.test", subs=False)]


# -- MP5: scope refusal names the account, the platform and the wider host --------------------

def test_mp5_suffix_scope_admitting_a_sibling_platform_is_refused_by_name() -> None:
    platforms = _sibling_platforms(school_subs=True)
    with pytest.raises(ro.OnboardingError) as caught:
        ro.validate_accounts(platforms, [_account("teacher", "school")], {}, {})
    message = str(caught.value)
    assert "teacher" in message and "school" in message and "admin.school.test" in message


def test_mp5_exact_scope_beside_a_sibling_platform_is_accepted() -> None:
    platforms = _sibling_platforms(school_subs=False)
    refs = ro.validate_accounts(platforms, [_account("teacher", "school")], {}, {})
    assert {r.key for r in refs} == {"NW_TEACHER_USER", "NW_TEACHER_PASS"}
    assert all(r.domains == ["school.test"] and r.include_subdomains is False for r in refs)


def test_mp5_typed_scope_outside_the_platform_is_refused_naming_the_host() -> None:
    platforms = [_platform("school", "school.test")]
    with pytest.raises(ro.OnboardingError) as caught:
        ro.validate_accounts(platforms, [_account("teacher", "school")],
                             {"teacher": ["elsewhere.test"]}, {})
    message = str(caught.value)
    assert "teacher" in message and "school" in message and "elsewhere.test" in message


def test_mp5_typed_scope_inside_the_platform_narrows_the_default() -> None:
    platforms = [_platform("school", "school.test", "www.school.test", subs=False)]
    refs = ro.validate_accounts(platforms, [_account("teacher", "school")],
                                {"teacher": ["www.school.test"]}, {})
    assert all(r.domains == ["www.school.test"] for r in refs)


# -- structure and hygiene --------------------------------------------------------------------

def test_default_scope_is_the_platform_domains_and_inherits_include_subdomains() -> None:
    platforms = [_platform("school", "school.test", subs=True)]
    refs = ro.validate_accounts(platforms, [_account("teacher", "school")], {}, {})
    assert all(r.domains == ["school.test"] and r.include_subdomains is True for r in refs)


def test_one_key_cannot_serve_two_accounts() -> None:
    platforms = [_platform("school", "school.test")]
    accounts = [_account("a", "school"), _account("b", "school").model_copy(
        update={"username_key": "NW_A_USER"})]
    with pytest.raises(ro.OnboardingError, match=r"NW_A_USER.*'a'.*'b'"):
        ro.validate_accounts(platforms, accounts, {}, {})


def test_an_account_on_an_undeclared_platform_is_refused_by_name() -> None:
    with pytest.raises(ro.OnboardingError, match=r"teacher.*nowhere"):
        ro.validate_accounts([_platform("school", "school.test")],
                             [_account("teacher", "nowhere")], {}, {})


def test_a_value_for_an_undeclared_key_is_refused_without_echoing_it() -> None:
    platforms = [_platform("school", "school.test")]
    with pytest.raises(ro.OnboardingError) as caught:
        ro.validate_accounts(platforms, [_account("teacher", "school")], {},
                             {"NW_STRAY_PASS": SENTINEL})
    assert "NW_STRAY_PASS" in str(caught.value) and SENTINEL not in str(caught.value)


def test_a_value_shaped_key_is_reported_without_the_value() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError) as caught:
        RoleAccount(id="t", role="Teacher", platform_id="school", username_key=SENTINEL,
                    password_key="NW_T_PASS")
    message = ro.safe_validation_message(caught.value)
    assert "username_key" in message and SENTINEL not in message


def test_write_values_goes_through_the_env_editor_and_keeps_other_keys(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text("OTHER_KEY=keep\n", encoding="utf-8")
    ro.write_values(env, {"NW_T_USER": "t@school.test", "NW_T_PASS": SENTINEL})
    stored = parse_env(env.read_text(encoding="utf-8"))
    assert stored == {"OTHER_KEY": "keep", "NW_T_USER": "t@school.test", "NW_T_PASS": SENTINEL}


def test_write_values_refuses_an_unsafe_value_without_echoing_it(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    with pytest.raises(ro.OnboardingError) as caught:
        ro.write_values(env, {"NW_T_PASS": f"{SENTINEL}\nINJECTED=1"})
    assert SENTINEL not in str(caught.value) and not env.exists()


def test_merge_keeps_untouched_rows_and_replaces_by_id() -> None:
    old = [_platform("school", "school.test"), _platform("admin", "admin.school.test")]
    new = [_platform("school", "school.test", "www.school.test")]
    merged = ro.merge_by_id(old, new)
    assert [p.id for p in merged] == ["school", "admin"]
    assert merged[0].allowed_domains == ["school.test", "www.school.test"]
