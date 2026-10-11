"""T-202 AT-790 (LL8): the Generate-cases route prints a ProviderError on its refusal page,
so a vendor error that echoes a vendor-native key must not get that far.

Moved here from tests/test_ui_learn.py, unchanged in what it asserts, only to keep that file
under the 300-line doctor cap after the t178 merge; it reuses that file's fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from litellm_fake import install
from test_ui_learn import _approve_proposals, _project, _spec, client, scratch_root  # noqa: F401

import autotester.ui.routes_learn as routes_learn_module
from autotester.providers.litellm_provider import LiteLLMProvider
from autotester.schema.enums import ReviewStatus


def test_generate_failure_page_does_not_carry_a_vendor_echoed_key(
    client: TestClient, scratch_root: Path, monkeypatch: pytest.MonkeyPatch  # noqa: F811
) -> None:
    canary = "AIza-ROUTE-CANARY-555"
    store = _project(scratch_root, spec=_spec(ReviewStatus.APPROVED))
    _approve_proposals(store)   # t178: the route stages proposals first and needs them approved
    install(monkeypatch, [RuntimeError(f"403 at https://vendor.test/x?key={canary}")] * 60)
    monkeypatch.setenv("LITELLM_API_KEY", "k-for-test")
    monkeypatch.setenv("GEMINI_API_KEY", canary)
    provider = LiteLLMProvider(model="gemini/gemini-2.5-pro")
    monkeypatch.setattr(routes_learn_module, "for_role", lambda project, role: provider)

    response = client.post("/projects/demo/cases/generate", follow_redirects=False)

    assert response.status_code == 400 and "could not complete" in response.text
    assert canary not in response.text
    assert store.list_cases() == []
