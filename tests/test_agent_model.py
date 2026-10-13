"""T-181: the agent layer's production model constructor picks the first configured vendor."""

from __future__ import annotations

import pytest

from autotester.providers.agent_model import agent_chat_model
from autotester.providers.base import ProviderError


def test_first_configured_vendor_wins_and_is_built_lazily() -> None:
    built: list[str] = []

    def make(name: str):  # type: ignore[no-untyped-def]
        return lambda: built.append(name) or f"model-{name}"

    pid, model = agent_chat_model([("gemini", make("gemini")), ("ollama", make("ollama"))])
    assert (pid, model, built) == ("gemini", "model-gemini", ["gemini"])


def test_no_credential_is_a_clear_error_naming_no_key(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ProviderError, match="no model provider"):
        agent_chat_model([])
