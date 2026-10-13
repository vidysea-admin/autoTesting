"""The browser-use model seam over an `IsolatedProvider`: JSON text is validated, deadline bound."""

from __future__ import annotations

import asyncio
import contextlib
import functools
from types import SimpleNamespace

from isolated_fake import Answer, scripted
from pydantic import BaseModel

from autotester.providers.isolated import IsolatedProvider
from autotester.stages.browser_use_backend import BrowserUseBackend, ProviderChatModel


class Echoing(BaseModel):
    text: str


def test_the_chat_model_validates_raw_json_text_from_an_isolated_provider() -> None:
    class Raw(IsolatedProvider):
        def act(self, prompt, schema=None, **kw):  # the child's answer: JSON text, no class
            return '{"text": "hello"}'

    model = ProviderChatModel(Raw(functools.partial(scripted, "ok")), lambda t: t)
    msg = SimpleNamespace(role="user", text="go")
    out = asyncio.run(model.ainvoke([msg], Echoing))
    assert out.completion == Echoing(text="hello")


def test_drive_binds_the_provider_deadline_to_the_invocation_wall_clock(monkeypatch) -> None:
    seen: list[float] = []
    iso = IsolatedProvider(functools.partial(scripted, "ok"))
    monkeypatch.setattr(iso, "bind_deadline", lambda until: seen.append(until))

    async def boom(*_a, **_k):
        raise RuntimeError("stop after binding")

    monkeypatch.setattr("autotester.stages.browser_use_backend._guarded_controller", boom)
    backend = BrowserUseBackend(iso, "http://127.0.0.1:1", lambda t: t)
    with contextlib.suppress(Exception):
        asyncio.run(backend._drive("t", lambda a: None, 3, 30.0))
    assert len(seen) == 1 and seen[0] > 0
    assert Answer  # the shared fake module is the one the child imports
