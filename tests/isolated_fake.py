"""Picklable provider factories for the isolated-provider tests (they run in a spawned child)."""

from __future__ import annotations

import time
from typing import Any

from pydantic import BaseModel, ConfigDict

from autotester.providers.base import Provider, ProviderError


class Answer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str


class Scripted(Provider):
    id = "scripted"

    def __init__(self, mode: str = "ok", **options: Any) -> None:
        super().__init__(**options)
        self.mode = mode

    def available(self) -> bool:
        return True

    def act(self, prompt: str, schema: Any = None, *, prompt_file: str | None = None,
            fed_id: str | None = None) -> Any:
        if self.mode == "hang":
            time.sleep(120)  # a vendor client stuck in a read
        if self.mode == "boom":
            raise ProviderError("quota exceeded")
        self.record("agent", input_tokens=7, output_tokens=3)
        if schema is None:
            return f"echo:{prompt}"
        return schema(text=f"echo:{prompt[:12]}") if schema is Answer else prompt


def scripted(mode: str = "ok") -> Provider:
    return Scripted(mode)
