"""Ordered model chain over LiteLLM: Ollama GLM -> Ollama DeepSeek -> Gemini.

Umesh, 2026-10-13: GLM 5.3 Flash and DeepSeek 4.1 Flash (Ollama API) are primary,
Gemini is fallback only. Each tier is a `LiteLLMProvider`, so the redaction gate,
`RunBudget` visibility and key handling are LiteLLM's; this class only orders them
and falls through on any `ProviderError` (vendor error, timeout, unparsable answer).
A credential in the prompt is refused ONCE, up front, and never falls through.

Order: project spec `model-chain:<m1>,<m2>,...` > `AUTOTESTER_MODEL_ORDER` > default.
Tiers whose credentials are absent are skipped, so an unused tier costs nothing.
"""

from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from autotester.providers import ollama_cloud
from autotester.providers.base import Provider, ProviderError
from autotester.providers.litellm_provider import LiteLLMProvider
from autotester.schema.run import ProviderUsage

ModelT = TypeVar("ModelT", bound=BaseModel)

log = logging.getLogger(__name__)
CHAIN_ID = "model-chain"
ORDER_ENV = "AUTOTESTER_MODEL_ORDER"
DEFAULT_ORDER = (ollama_cloud.GLM, ollama_cloud.DEEPSEEK, "gemini/gemini-3.6-flash")


def configured_order(model: str | None = None) -> list[str]:
    """The ordered model ids: explicit comma list, else the env var, else default."""
    raw = model or os.environ.get(ORDER_ENV) or ""
    names = [m.strip() for m in raw.split(",") if m.strip()]
    return names or list(DEFAULT_ORDER)


class ModelChainProvider(Provider):
    """`act`/`judge` try each available tier in order until one answers."""

    def __init__(self, **options: Any) -> None:
        super().__init__(**options)
        self._call = threading.local()
        order = configured_order(options.get("model"))
        secrets = options.get("secrets") or []
        self._tiers = [LiteLLMProvider(model=m, secrets=secrets) for m in order]

    @property
    def id(self) -> str:  # type: ignore[override]
        """The tier that served THIS thread's latest call, else `model-chain`. Reset at
        the start of every call, so a failed call never leaves a stale serving id; per
        thread, so a judge shared by parallel graders cannot read another's tier."""
        return self.served or CHAIN_ID

    @property
    def served(self) -> str | None:
        """Label (`id:model`) of the tier that answered the latest call, None if it failed."""
        return getattr(self._call, "served", None)

    def order(self) -> list[str]:
        return [t._model for t in self._tiers]

    def ready_tiers(self) -> list[LiteLLMProvider]:
        return [t for t in self._tiers if t.available()]

    def available(self) -> bool:
        return bool(self.ready_tiers())

    def unavailable_reason(self) -> str | None:
        if self.available():
            return None
        return ("no AI provider is configured: set OLLAMA_API_KEY (primary) or "
                "GEMINI_API_KEY (fallback) in .env")

    def act(self, prompt: str, schema: type[ModelT] | None = None, *,
            prompt_file: str | None = None, fed_id: str | None = None) -> Any:
        return self._run("act", prompt, schema, prompt_file, fed_id)

    def judge(self, prompt: str, schema: type[ModelT], images: list[Path] | None = None, *,
              prompt_file: str | None = None, fed_id: str | None = None) -> ModelT:
        return self._run("judge", prompt, schema, prompt_file, fed_id, images=images)

    def _run(self, method: str, prompt: str, schema: type[BaseModel] | None,
             prompt_file: str | None, fed_id: str | None, **extra: Any) -> Any:
        if schema is None:
            raise ProviderError(f"{self.id} requires a schema for structured output")
        self._call.served = None  # reset: a failed call must not report the previous tier
        tiers = self.ready_tiers()
        if not tiers:
            raise ProviderError(self.unavailable_reason() or "no usable tier")
        tiers[0].guard_text(prompt)  # redaction gate: refuse once, never fall through
        errors: list[str] = []
        for tier in tiers:
            tier.trace = self.trace
            try:
                result = getattr(tier, method)(prompt, schema, prompt_file=prompt_file,
                                               fed_id=fed_id, **extra)
            except ProviderError as exc:
                errors.append(str(exc))
                log.warning("model-chain: tier %s failed (%s); falling through",
                            tier.label, type(exc).__name__)
                continue
            self._call.served = tier.label
            log.info("model-chain: tier %s served the %s call", tier.label, method)
            self._sync_usage()
            return result
        raise ProviderError("model-chain: every tier failed: " + " | ".join(errors))

    def _sync_usage(self) -> None:
        with self._usage_lock:
            self.usage = [ProviderUsage(provider=t.label, role=u.role, calls=u.calls,
                                        input_tokens=u.input_tokens,
                                        output_tokens=u.output_tokens)
                          for t in self._tiers for u in t.usage]
