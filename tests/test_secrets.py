"""Credential-boundary tests. Contract: qa/contracts/browser-and-secrets.md B1-B4.

These are security-control tests, so each criterion gets an explicit case,
including the negative ones (wrong host, undeclared key, leaked prompt).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from autotester.browser.secrets import (
    MissingSecret,
    SecretScopeError,
    SecretStore,
    UndeclaredSecret,
    host_of,
    parse_env,
)
from autotester.schema.project import Project, SecretRef

PASSWORD = "hunter2-trombone-staple"


def make_project(domains: list[str] | None = None) -> Project:
    return Project(
        slug="pathlynks",
        name="Pathlynks",
        base_url="https://app.pathlynks.test",
        allowed_domains=["pathlynks.test"],
        secrets=[
            SecretRef(key="PATHLYNKS_EMAIL", domains=domains or ["app.pathlynks.test"]),
            SecretRef(key="PATHLYNKS_PASSWORD", domains=domains or ["app.pathlynks.test"]),
        ],
    )


def write_env(tmp_path: Path, body: str) -> Path:
    path = tmp_path / ".env"
    path.write_text(body, encoding="utf-8")
    return path


def loaded(tmp_path: Path, domains: list[str] | None = None) -> SecretStore:
    env = write_env(
        tmp_path,
        f"# creds\nPATHLYNKS_EMAIL=tester@pathlynks.test\nPATHLYNKS_PASSWORD={PASSWORD}\n",
    )
    return SecretStore.load(make_project(domains), env)


# -- B1 loading ------------------------------------------------------------

def test_parse_env_handles_comments_quotes_and_export() -> None:
    parsed = parse_env('# c\n\nexport A=1\nB="two"\nC=\'three\'\nbad line\n')
    assert parsed == {"A": "1", "B": "two", "C": "three"}


def test_declared_key_missing_from_env_raises_and_names_the_key(tmp_path: Path) -> None:
    env = write_env(tmp_path, "PATHLYNKS_EMAIL=tester@pathlynks.test\n")
    with pytest.raises(MissingSecret, match="PATHLYNKS_PASSWORD"):
        SecretStore.load(make_project(), env)


def test_missing_env_file_raises_rather_than_silently_empty(tmp_path: Path) -> None:
    with pytest.raises(MissingSecret):
        SecretStore.load(make_project(), tmp_path / "absent.env")


def test_undeclared_key_is_reported_and_never_loaded(tmp_path: Path) -> None:
    env = write_env(
        tmp_path,
        f"PATHLYNKS_EMAIL=a@b.test\nPATHLYNKS_PASSWORD={PASSWORD}\nSTRAY_TOKEN=zzz\n",
    )
    store = SecretStore.load(make_project(), env)
    assert store.undeclared == ["STRAY_TOKEN"]
    assert "STRAY_TOKEN" not in store


# -- B2 placeholders only --------------------------------------------------

def test_resolve_substitutes_on_an_allowed_host(tmp_path: Path) -> None:
    store = loaded(tmp_path)
    out = store.resolve("{{SECRET:PATHLYNKS_PASSWORD}}", "https://app.pathlynks.test/login")
    assert out == PASSWORD


def test_resolve_passes_through_plain_values_untouched(tmp_path: Path) -> None:
    store = loaded(tmp_path)
    assert store.resolve("Nathan", "https://app.pathlynks.test") == "Nathan"
    assert store.resolve(None, "https://app.pathlynks.test") is None


def test_resolve_rejects_a_key_the_project_never_declared(tmp_path: Path) -> None:
    store = loaded(tmp_path)
    with pytest.raises(UndeclaredSecret, match="OTHER_APP_KEY"):
        store.resolve("{{SECRET:OTHER_APP_KEY}}", "https://app.pathlynks.test")


def test_guard_prompt_blocks_a_prompt_carrying_a_raw_secret(tmp_path: Path) -> None:
    store = loaded(tmp_path)
    store.guard_prompt("type {{SECRET:PATHLYNKS_PASSWORD}} into the field")
    with pytest.raises(ValueError, match="raw secret"):
        store.guard_prompt(f"the password is {PASSWORD}")


# -- B3 domain scoping is enforced ----------------------------------------

def test_resolve_refuses_a_host_outside_the_secret_scope(tmp_path: Path) -> None:
    store = loaded(tmp_path)
    with pytest.raises(SecretScopeError, match=re.escape("evil.test")):
        store.resolve("{{SECRET:PATHLYNKS_PASSWORD}}", "https://evil.test/login")


def test_lookalike_domain_is_not_a_subdomain(tmp_path: Path) -> None:
    store = loaded(tmp_path)
    with pytest.raises(SecretScopeError):
        store.resolve("{{SECRET:PATHLYNKS_EMAIL}}", "https://notpathlynks.test")


def test_secret_scoped_narrower_than_the_project_allowlist_is_still_refused(
    tmp_path: Path,
) -> None:
    # Project allows pathlynks.test, but this secret is scoped to auth.pathlynks.test only.
    store = loaded(tmp_path, domains=["auth.pathlynks.test"])
    store.resolve("{{SECRET:PATHLYNKS_EMAIL}}", "https://auth.pathlynks.test")
    with pytest.raises(SecretScopeError):
        store.resolve("{{SECRET:PATHLYNKS_EMAIL}}", "https://app.pathlynks.test")


# -- AT-076: resolve_for_navigation, for a placeholder used as a goto target -

LOGIN_URL = "https://app.pathlynks.test/login?token=xyz789"


def loaded_with_login_url(tmp_path: Path, domains: list[str] | None = None) -> SecretStore:
    project = Project(
        slug="pathlynks", name="Pathlynks", base_url="https://app.pathlynks.test",
        allowed_domains=["pathlynks.test"],
        secrets=[SecretRef(key="PATHLYNKS_LOGIN_URL", domains=domains or ["app.pathlynks.test"])],
    )
    env = write_env(tmp_path, f"PATHLYNKS_LOGIN_URL={LOGIN_URL}\n")
    return SecretStore.load(project, env)


def test_resolve_for_navigation_substitutes_a_bare_placeholder(tmp_path: Path) -> None:
    """The whole navigation target can be the placeholder — there is no
    literal host around it to scope by up front, unlike `fill`."""
    store = loaded_with_login_url(tmp_path)
    assert store.resolve_for_navigation("{{SECRET:PATHLYNKS_LOGIN_URL}}") == LOGIN_URL


def test_resolve_for_navigation_substitutes_a_placeholder_embedded_in_a_url(
    tmp_path: Path,
) -> None:
    store = loaded_with_login_url(tmp_path)
    out = store.resolve_for_navigation(
        "https://app.pathlynks.test/sso?next={{SECRET:PATHLYNKS_LOGIN_URL}}"
    )
    assert out == f"https://app.pathlynks.test/sso?next={LOGIN_URL}"


def test_resolve_for_navigation_passes_plain_urls_through_untouched(tmp_path: Path) -> None:
    store = loaded_with_login_url(tmp_path)
    assert store.resolve_for_navigation("https://app.pathlynks.test/") == (
        "https://app.pathlynks.test/"
    )


def test_resolve_for_navigation_rejects_an_undeclared_key(tmp_path: Path) -> None:
    store = loaded_with_login_url(tmp_path)
    with pytest.raises(UndeclaredSecret, match="OTHER_APP_KEY"):
        store.resolve_for_navigation("{{SECRET:OTHER_APP_KEY}}")


def test_resolve_for_navigation_rejects_a_missing_value(tmp_path: Path) -> None:
    project = Project(
        slug="pathlynks", name="Pathlynks", base_url="https://app.pathlynks.test",
        allowed_domains=["pathlynks.test"],
        secrets=[SecretRef(key="PATHLYNKS_LOGIN_URL", domains=["app.pathlynks.test"])],
    )
    store = SecretStore(project, {})
    with pytest.raises(MissingSecret, match="PATHLYNKS_LOGIN_URL"):
        store.resolve_for_navigation("{{SECRET:PATHLYNKS_LOGIN_URL}}")


def test_resolve_for_navigation_refuses_a_secret_scoped_to_a_different_domain(
    tmp_path: Path,
) -> None:
    """The resolved DESTINATION is app.pathlynks.test, but the secret is only
    scoped to some other host — the post-substitution check must still bite."""
    store = loaded_with_login_url(tmp_path, domains=["not-the-login-host.test"])
    with pytest.raises(SecretScopeError, match=re.escape("app.pathlynks.test")):
        store.resolve_for_navigation("{{SECRET:PATHLYNKS_LOGIN_URL}}")


def test_host_of_strips_scheme_port_and_case() -> None:
    assert host_of("https://App.Pathlynks.test:8443/login") == "app.pathlynks.test"
    assert host_of("app.pathlynks.test") == "app.pathlynks.test"


# -- checker findings, cycle 1 (each pinned so it cannot regress) ----------

def test_at001_empty_host_fails_closed(tmp_path: Path) -> None:
    store = loaded(tmp_path)
    for destination in ("", "   ", "not a url at all", "://broken"):
        with pytest.raises(SecretScopeError):
            store.resolve("{{SECRET:PATHLYNKS_PASSWORD}}", destination)


def test_at001_blank_domain_is_rejected_at_declaration() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        SecretRef(key="PW", domains=[""])
    with pytest.raises(ValueError, match="non-empty"):
        SecretRef(key="PW", domains=["pathlynks.test", "  "])
    assert SecretRef(key="PW", domains=[" .Pathlynks.TEST "]).domains == ["pathlynks.test"]


def test_at002_short_secret_is_still_guarded_and_masked(tmp_path: Path) -> None:
    env = write_env(tmp_path, "PATHLYNKS_EMAIL=a@b.test\nPATHLYNKS_PASSWORD=abc\n")
    store = SecretStore.load(make_project(), env)
    with pytest.raises(ValueError, match="raw secret"):
        store.guard_prompt("password is abc")
    assert "abc" not in store.redactor().scrub("password=abc")


def test_at003_inline_comment_is_stripped_from_unquoted_values() -> None:
    parsed = parse_env('PW=abc # note\nQ="kept # inside"\nURL=http://x/#frag\n')
    assert parsed["PW"] == "abc"
    assert parsed["Q"] == "kept # inside"
    assert parsed["URL"] == "http://x/#frag"  # no space before '#': not a comment


def test_at004_undeclared_values_are_masked_but_never_resolvable(tmp_path: Path) -> None:
    env = write_env(
        tmp_path,
        f"PATHLYNKS_EMAIL=a@b.test\nPATHLYNKS_PASSWORD={PASSWORD}\nOTHER_APP_TOKEN=strayvalue123\n",
    )
    store = SecretStore.load(make_project(), env)
    assert "strayvalue123" not in store.redactor().scrub("log strayvalue123")
    with pytest.raises(ValueError, match="raw secret"):
        store.guard_prompt("token strayvalue123")
    with pytest.raises(UndeclaredSecret):
        store.resolve("{{SECRET:OTHER_APP_TOKEN}}", "https://app.pathlynks.test")


def test_at005_non_strict_load_still_fails_closed_at_resolve(tmp_path: Path) -> None:
    env = write_env(tmp_path, "PATHLYNKS_EMAIL=a@b.test\n")
    store = SecretStore.load(make_project(), env, strict=False)
    assert "PATHLYNKS_PASSWORD" not in store
    assert store.resolve("{{SECRET:PATHLYNKS_EMAIL}}", "https://app.pathlynks.test") == "a@b.test"
    with pytest.raises(MissingSecret):
        store.resolve("{{SECRET:PATHLYNKS_PASSWORD}}", "https://app.pathlynks.test")


def test_at006_tab_comment_and_quoted_then_comment() -> None:
    body = "PW=abc\t# note\nQ=\"abc\" # c\nR='x y'   # z\nS=a#b\n"
    assert parse_env(body) == {"PW": "abc", "Q": "abc", "R": "x y", "S": "a#b"}


def test_at007_backslash_and_userinfo_destinations_fail_closed(tmp_path: Path) -> None:
    store = loaded(tmp_path)
    destinations = (
        "https://evil.test\\@pathlynks.test",  # WHATWG host = evil.test
        "https://pathlynks.test\\evil.test",  # backslash anywhere
        "https://user@app.pathlynks.test/login",  # any userinfo
        "https://a:b@app.pathlynks.test",
    )
    for destination in destinations:
        with pytest.raises(SecretScopeError):
            store.resolve("{{SECRET:PATHLYNKS_PASSWORD}}", destination)
    assert host_of("https://evil.test\\@pathlynks.test") == ""
    assert host_of("https://x@app.pathlynks.test") == ""

# -- B4 evidence is clean --------------------------------------------------

def test_redactor_masks_every_loaded_value(tmp_path: Path) -> None:
    store = loaded(tmp_path)
    scrubbed = store.redactor().scrub(f"POST /login body=password={PASSWORD}")
    assert PASSWORD not in scrubbed
    assert "PATHLYNKS_PASSWORD" in scrubbed


def test_repr_never_renders_a_value(tmp_path: Path) -> None:
    store = loaded(tmp_path)
    assert PASSWORD not in repr(store)
    assert "PATHLYNKS_PASSWORD" in repr(store)


def test_masked_field_keys_reports_what_screenshots_must_hide(tmp_path: Path) -> None:
    store = loaded(tmp_path)
    assert store.masked_field_keys() == {"PATHLYNKS_EMAIL", "PATHLYNKS_PASSWORD"}
