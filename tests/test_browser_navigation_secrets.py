"""AT-076: a navigation target can itself be a `{{SECRET:KEY}}` placeholder.
Contract: qa/contracts/browser-and-secrets.md B2/B3.

Split from test_browser.py once that file passed doctor's 300-line cap —
`fill()`'s secret resolution stays there; `goto()`'s stays here.

Unlike `fill()` (always scoped to the CURRENT page host), a navigation
target can be the placeholder itself with no literal host around it — there
is nothing to scope by until AFTER substitution. `resolve_for_navigation`
flips the order: substitute, then check the resulting host against the
secret's own declared domains, then `session.goto` still runs
`check_destination` on the resolved value exactly as it would a plain URL.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from test_browser import LOGIN, FakePage

from autotester.browser.secrets import SecretScopeError, SecretStore
from autotester.browser.session import BrowserSession, NavigationRefused
from autotester.core.paths import ProjectPaths
from autotester.schema.project import Project, SecretRef

LOGIN_URL_VALUE = "https://app.pathlynks.test/login?token=xyz789"


def _session_with_secret_url(
    tmp_path: Path, *, key: str = "PATHLYNKS_LOGIN_URL", ref_domains: list[str] | None = None,
    project_domains: list[str] | None = None, value: str = LOGIN_URL_VALUE,
) -> BrowserSession:
    project = Project(
        slug="pathlynks", name="Pathlynks", base_url="https://app.pathlynks.test",
        allowed_domains=project_domains or ["pathlynks.test"],
        secrets=[SecretRef(key=key, domains=ref_domains or ["pathlynks.test"])],
    )
    env = tmp_path / ".env"
    env.write_text(f"{key}={value}\n", encoding="utf-8")
    store = SecretStore.load(project, env)
    paths = ProjectPaths("pathlynks", tmp_path)
    s = BrowserSession(project, store, tmp_path / "run", paths)
    s._page = FakePage(LOGIN)
    s.state.run_dir.mkdir(parents=True, exist_ok=True)
    return s


def test_goto_resolves_a_bare_secret_placeholder_navigation_target(tmp_path: Path) -> None:
    s = _session_with_secret_url(tmp_path)
    s.goto("{{SECRET:PATHLYNKS_LOGIN_URL}}")
    assert s.page.url == LOGIN_URL_VALUE
    assert "xyz789" not in " ".join(e.path for e in s.state.evidence)


def test_goto_resolves_a_secret_embedded_in_a_literal_url(tmp_path: Path) -> None:
    s = _session_with_secret_url(tmp_path)
    s.goto("https://app.pathlynks.test/sso?next={{SECRET:PATHLYNKS_LOGIN_URL}}")
    assert s.page.url == f"https://app.pathlynks.test/sso?next={LOGIN_URL_VALUE}"


def test_goto_still_refuses_a_resolved_destination_outside_project_domains(
    tmp_path: Path,
) -> None:
    """Per-secret domain scoping is not the only gate: `check_destination`
    still runs on the RESOLVED value exactly as it would a plain literal
    URL, so a secret whose own declared domains are wrong or stale cannot
    navigate the browser outside the project's allowed_domains."""
    s = _session_with_secret_url(
        tmp_path, key="ROGUE_URL", ref_domains=["evil.test"],
        value="https://evil.test/steal?token=SUPERSECRETTOKEN123",
    )
    with pytest.raises(NavigationRefused) as excinfo:
        s.goto("{{SECRET:ROGUE_URL}}")
    assert s.page.url == LOGIN
    # AT-341: check_destination's own refusal message must never embed the
    # resolved secret value — a host is not secret, the URL it came from is.
    assert "SUPERSECRETTOKEN123" not in str(excinfo.value)
    assert "SUPERSECRETTOKEN123" not in " ".join(e.path for e in s.state.evidence)


def test_goto_refuses_a_secret_scoped_to_a_different_domain_than_it_resolves_to(
    tmp_path: Path,
) -> None:
    """The secret's OWN declared domains must cover the host its value
    actually resolves to — a stale or wrong domains list fails closed."""
    s = _session_with_secret_url(
        tmp_path, key="MISBOUND_URL", ref_domains=["not-the-login-host.test"],
    )
    with pytest.raises(Exception, match=re.escape("not-the-login-host.test")):
        s.goto("{{SECRET:MISBOUND_URL}}")
    assert s.page.url == LOGIN


def test_goto_passes_a_plain_url_through_unchanged(tmp_path: Path) -> None:
    s = _session_with_secret_url(tmp_path)
    s.goto("https://app.pathlynks.test/dashboard")
    assert s.page.url == "https://app.pathlynks.test/dashboard"


@pytest.mark.parametrize("flag", [None, True, False])
@pytest.mark.parametrize("navigation", [False, True])
@pytest.mark.parametrize("host", [
    "auth.pathlynks.test", "child.auth.pathlynks.test", "sibling.pathlynks.test",
    "pathlynks.test", "notauth.pathlynks.test", "auth.pathlynks.test.evil.test",
])
def test_secret_host_mode_binds_both_resolution_paths(flag, navigation, host) -> None:
    declaration = {"key": "SCOPED_URL", "domains": ["auth.pathlynks.test"]}
    if flag is not None:
        declaration["include_subdomains"] = flag
    ref = SecretRef.model_validate(declaration)
    project = Project(slug="scope", name="Scope", base_url="https://auth.pathlynks.test",
                      allowed_domains=["pathlynks.test"], secrets=[ref])
    value = f"https://{host}/login?token=synthetic-only-token"
    store = SecretStore(project, {ref.key: value})
    template = "{{SECRET:SCOPED_URL}}"
    allowed = host == "auth.pathlynks.test" or (
        flag is not False and host == "child.auth.pathlynks.test"
    )
    if allowed:
        resolved = (store.resolve_for_navigation(template) if navigation
                    else store.resolve(template, f"https://{host}"))
        assert resolved == value
    else:
        with pytest.raises(SecretScopeError):
            if navigation:
                store.resolve_for_navigation(template)
            else:
                store.resolve(template, f"https://{host}")
    assert Project.model_validate_json(project.model_dump_json()).secret(ref.key) == ref
    assert ref.include_subdomains is (flag is not False)


@pytest.mark.parametrize("invalid", ["false", "true", "", 0, 1, None, [], {}])
def test_secret_host_mode_requires_a_real_boolean(invalid) -> None:
    with pytest.raises(ValueError):
        SecretRef(key="SCOPED_URL", domains=["auth.pathlynks.test"],
                  include_subdomains=invalid)


@pytest.mark.parametrize("key,host", [
    ("PATHLYNKS_USER_EMAIL", "pathlynks.vidysea.com"),
    ("PATHLYNKS_USER_PASSWORD", "pathlynks.vidysea.com"),
    ("PATHLYNKS_COUNSELLOR_EMAIL", "dev-new.vidysea.com"),
    ("PATHLYNKS_COUNSELLOR_PASSWORD", "dev-new.vidysea.com"),
])
def test_saved_pathlynks_config_isolates_each_role_host(key, host) -> None:
    config = Path(__file__).resolve().parents[1] / "projects/pathlynks/project.json"
    project = Project.model_validate_json(config.read_text(encoding="utf-8"))
    ref = project.secret(key)
    assert ref is not None and ref.domains == [host] and ref.include_subdomains is False
    assert project.allowed_domains == ["vidysea.com"]
    store = SecretStore(project, {key: "synthetic-role-value"})
    template = "{{SECRET:" + key + "}}"
    assert store.resolve(template, f"https://{host}/signin") == "synthetic-role-value"
    other = "dev-new.vidysea.com" if host == "pathlynks.vidysea.com" else "pathlynks.vidysea.com"
    for refused in (other, "vidysea.com", f"child.{host}", f"not{host}"):
        with pytest.raises(SecretScopeError):
            store.resolve(template, f"https://{refused}")
