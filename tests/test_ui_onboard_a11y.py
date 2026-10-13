"""T-204 walk findings: /onboard has no unlabelled controls; sign-in pages skip /favicon.ico."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from auth_harness import ADMIN, account, gate_on, login
from fastapi.testclient import TestClient

from autotester.ui.app import app

_CONTROL = re.compile(r"<(input|select|textarea)\b([^>]*)>", re.I)


def unlabelled_controls(page: str) -> list[str]:
    """Visible form controls with neither `<label for=id>` nor a non-empty aria-label."""
    bad = []
    for kind, attrs in _CONTROL.findall(page):
        if re.search(r"type=['\"](hidden|submit)['\"]", attrs):
            continue
        ident = re.search(r"\bid='([^']+)'", attrs)
        labelled = (ident and f"<label for='{ident.group(1)}'" in page) or re.search(
            r"aria-label='[^']+'", attrs)
        if not labelled:
            bad.append(f"{kind} {attrs.strip()}")
    return bad


@pytest.fixture()
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    return gate_on(tmp_path, monkeypatch)


def test_onboard_form_has_no_unlabelled_controls(root: Path) -> None:
    account(ADMIN)
    page = login(ADMIN).get("/onboard").text
    assert page.count("<input") >= 10  # the form really rendered
    assert unlabelled_controls(page) == []


def test_helper_flags_a_bare_input() -> None:
    assert unlabelled_controls("<input name='x' placeholder='y'>")


def test_sign_in_pages_do_not_request_favicon_and_it_stays_off_the_public_set(root: Path) -> None:
    anon = TestClient(app)
    for path in ("/auth/login", "/auth/signup"):
        page = anon.get(path).text
        assert "rel='icon'" in page and "/favicon.ico" not in page
    assert anon.get("/favicon.ico", headers={"accept": "application/json"}).status_code == 401
