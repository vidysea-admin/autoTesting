"""AT-651: _host_matches normalisation quirks (exact host, one trailing dot only)."""
from __future__ import annotations

from pathlib import Path

import pytest

from autotester.browser.secrets import SecretScopeError, SecretStore, _host_matches
from autotester.schema.project import Project, SecretRef


def loaded(tmp_path: Path) -> SecretStore:
    project = Project(
        slug="pathlynks", name="Pathlynks", base_url="https://app.pathlynks.test",
        allowed_domains=["pathlynks.test"],
        secrets=[SecretRef(key="PATHLYNKS_EMAIL", domains=["app.pathlynks.test"])],
    )
    env = tmp_path / ".env"
    env.write_text("PATHLYNKS_EMAIL=tester@pathlynks.test\n", encoding="utf-8")
    return SecretStore.load(project, env)


def test_host_match_ignores_one_trailing_dot_only() -> None:
    assert _host_matches("app.pathlynks.test.", "app.pathlynks.test")
    assert not _host_matches("app.pathlynks.test..", "app.pathlynks.test")


def test_host_match_does_not_strip_a_leading_dot() -> None:
    assert not _host_matches(".app.pathlynks.test", "app.pathlynks.test")


def test_subdomains_of_a_scoped_domain_are_refused(tmp_path: Path) -> None:
    store = loaded(tmp_path)
    with pytest.raises(SecretScopeError):
        store.resolve("{{SECRET:PATHLYNKS_EMAIL}}", "https://staging.app.pathlynks.test")
    with pytest.raises(SecretScopeError):
        store.resolve("{{SECRET:PATHLYNKS_EMAIL}}", "https://pathlynks.test")
