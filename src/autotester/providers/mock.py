"""Deterministic provider for tests and dry runs. Never calls a network."""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from autotester.providers.base import Provider, ProviderError
from autotester.schema.observation import VisionOptions

ModelT = TypeVar("ModelT", bound=BaseModel)


class MockProvider(Provider):
    """Returns pre-seeded responses keyed by role.

    Seed it with ready-made model instances; the mock records usage exactly like
    a real provider so cost-accounting tests are meaningful.
    """

    id = "mock"

    def __init__(self, **options: Any) -> None:
        super().__init__(**options)
        self.responses: dict[str, list[Any]] = options.get("responses", {})
        self.prompts: list[tuple[str, str]] = []
        self.judge_images: list[list[Path]] = []
        self.vision_options: list[VisionOptions | None] = []
        """What each see_video call was given — so a test can prove the options
        reached the provider instead of being built and dropped."""

    def available(self) -> bool:
        return True

    def _next(self, role: str, prompt: str, *,
              prompt_file: str | None = None, fed_id: str | None = None) -> Any:
        self.prompts.append((role, prompt))
        queue = self.responses.get(role) or []
        if not queue:
            raise ProviderError(f"mock provider has no queued response for role={role}")
        self.record(role, input_tokens=len(prompt) // 4, output_tokens=16,
                    prompt_file=prompt_file, fed_id=fed_id)
        return queue.pop(0)

    def see_video(self, path: Path, prompt: str, schema: type[ModelT],
                  options: VisionOptions | None = None, *,
                  prompt_file: str | None = None, fed_id: str | None = None) -> ModelT:
        self.vision_options.append(options)
        return self._next("vision", f"{path}:{prompt}", prompt_file=prompt_file, fed_id=fed_id)

    def act(self, prompt: str, schema: type[ModelT] | None = None, *,
            prompt_file: str | None = None, fed_id: str | None = None) -> Any:
        return self._next("agent", prompt, prompt_file=prompt_file, fed_id=fed_id)

    def judge(
        self, prompt: str, schema: type[ModelT], images: list[Path] | None = None, *,
        prompt_file: str | None = None, fed_id: str | None = None,
    ) -> ModelT:
        self.judge_images.append(images or [])
        return self._next("judge", prompt, prompt_file=prompt_file, fed_id=fed_id)
