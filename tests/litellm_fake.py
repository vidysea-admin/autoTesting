"""An injected stand-in for the `litellm` module (T-202, D-070: no network in tests).

`install()` puts a `FakeLiteLLM` in `sys.modules`, so the provider's lazy
`import litellm` resolves to it. Every `completion()` call is recorded with the
exact kwargs the provider passed, which is what the routing, retry, secret and
credential tests assert on.
"""

from __future__ import annotations

import json
import socket
import sys
import types
from typing import Any

import pytest


def reply(content: str | None = None, *, tool_args: dict[str, Any] | str | None = None,
          prompt_tokens: int = 11, completion_tokens: int = 7) -> types.SimpleNamespace:
    """A `ModelResponse`-shaped object: `choices[0].message` and `usage`."""
    tool_calls = None
    if tool_args is not None:
        args = tool_args if isinstance(tool_args, str) else json.dumps(tool_args)
        tool_calls = [types.SimpleNamespace(function=types.SimpleNamespace(
            name="answer", arguments=args))]
    message = types.SimpleNamespace(content=content, tool_calls=tool_calls)
    usage = types.SimpleNamespace(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
    return types.SimpleNamespace(choices=[types.SimpleNamespace(message=message)], usage=usage)


class FakeLiteLLM(types.ModuleType):
    """Scripted `litellm`: `responses` are returned (or raised) in order."""

    def __init__(self, responses: list[Any], *, response_schema: bool = True,
                 function_calling: bool = True, missing_keys: list[str] | None = None) -> None:
        super().__init__("litellm")
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []
        self.response_schema = response_schema
        self.function_calling = function_calling
        self.missing_keys = missing_keys or []
        self.success_callback: list[Any] = []
        self.failure_callback: list[Any] = []
        self.callbacks: list[Any] = []

    def completion(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    def supports_response_schema(self, model: str, custom_llm_provider: str | None = None) -> bool:
        return self.response_schema

    def supports_function_calling(self, model: str, custom_llm_provider: str | None = None) -> bool:
        return self.function_calling

    def validate_environment(self, model: str | None = None, api_key: str | None = None,
                             api_base: str | None = None, api_version: str | None = None) -> dict:
        missing = [] if (api_key or api_base) else list(self.missing_keys)
        return {"keys_in_environment": not missing, "missing_keys": missing}


def install(monkeypatch: pytest.MonkeyPatch, responses: list[Any], **flags: Any) -> FakeLiteLLM:
    """Install a scripted fake and pin the two flag env vars the provider sets, so
    a test can assert `os.environ` is untouched without the first import leaking."""
    fake = FakeLiteLLM(responses, **flags)
    monkeypatch.setitem(sys.modules, "litellm", fake)
    monkeypatch.setenv("LITELLM_MODE", "PRODUCTION")
    monkeypatch.setenv("LITELLM_LOCAL_MODEL_COST_MAP", "True")
    for key in ("AUTOTESTER_MODEL", "LITELLM_API_KEY", "LITELLM_API_BASE",
                "OLLAMA_BASE_URL", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    return fake


@pytest.fixture
def no_network(monkeypatch: pytest.MonkeyPatch) -> list[object]:
    """LL12: a test that forgets the fake must fail loudly, not call out. Any real
    socket connect raises, so a stray real `litellm.completion` surfaces as an error."""
    attempts: list[object] = []

    def refuse(self: socket.socket, address: object) -> None:
        attempts.append(address)
        raise AssertionError(f"test tried a real network connection to {address!r}")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket.socket, "connect_ex", lambda self, address: refuse(self, address))
    return attempts
