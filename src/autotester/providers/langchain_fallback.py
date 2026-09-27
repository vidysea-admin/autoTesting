"""LangChain-backed provider with automatic fallback across configured vendors.

Umesh, 2026-09-03: no dependency on any single model vendor. If Anthropic
isn't reachable (no key, outage, rate limit) fall through to Gemini, then
Ollama, then ChatGPT, in that order -- each tier only enters the chain when
its credential/service is actually configured, so an unused tier costs
nothing and needs no SDK installed until someone configures it.

Built on LangChain's `ChatModel` + `with_structured_output` abstractions for
the actual model calls, but the fallback loop itself is explicit rather than
`.with_fallbacks()` -- this provider needs to report which vendor actually
answered a given call (`Verdict.grader_provider` must name the real one, not
a generic "langchain" label), which `.with_fallbacks()`'s return value alone
does not expose.
"""

from __future__ import annotations

import base64
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from autotester.providers.base import Provider, ProviderError

ModelT = TypeVar("ModelT", bound=BaseModel)

ChainEntry = tuple[str, Callable[[], Any]]


def _default_chain() -> list[ChainEntry]:
    """The ordered (id, factory) list built from whichever credentials are
    actually present in the environment. A factory is called lazily -- only
    a tier that is actually reached needs its SDK importable."""
    chain: list[ChainEntry] = []

    if os.environ.get("ANTHROPIC_API_KEY"):
        def make_anthropic() -> Any:
            from langchain_anthropic import ChatAnthropic

            return ChatAnthropic(model="claude-sonnet-5")

        chain.append(("anthropic", make_anthropic))

    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        def make_gemini() -> Any:
            from langchain_google_genai import ChatGoogleGenerativeAI

            key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            return ChatGoogleGenerativeAI(model="gemini-3.6-flash", google_api_key=key)

        chain.append(("gemini", make_gemini))

    if os.environ.get("OLLAMA_BASE_URL"):
        def make_ollama() -> Any:
            from langchain_ollama import ChatOllama

            return ChatOllama(
                model=os.environ.get("OLLAMA_MODEL", "llama3"),
                base_url=os.environ["OLLAMA_BASE_URL"],
            )

        chain.append(("ollama", make_ollama))

    if os.environ.get("OPENAI_API_KEY"):
        def make_openai() -> Any:
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(model="gpt-4o")

        chain.append(("chatgpt", make_openai))

    return chain


def _message(prompt: str, images: list[Path] | None) -> Any:
    """A plain string when there's nothing to attach (unchanged behavior for
    every existing caller); a real multimodal `HumanMessage` when there are
    real screenshot files to attach -- AT-049: `model.invoke(prompt)` with a
    bare string can never see an image, no matter how precisely `prompt`
    describes its filename. LangChain's `image_url` content-block format is
    understood by ChatAnthropic/ChatGoogleGenerativeAI/ChatOpenAI alike."""
    real_images = [p for p in (images or []) if p.exists()]
    if not real_images:
        return prompt
    from langchain_core.messages import HumanMessage

    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    for path in real_images:
        b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}})
    # .invoke() requires a str, PromptValue, or list[BaseMessage] -- a bare
    # HumanMessage is none of those.
    return [HumanMessage(content=content)]


class LangChainFallbackProvider(Provider):
    """`act`/`judge` try each configured chat model in order, falling through
    on any exception, until one succeeds or the chain is exhausted.

    `id` starts as the class default and becomes the winning tier's name
    (e.g. "gemini") after a successful call -- `grade.py`/callers read
    `provider.id` AFTER the call returns, so this needs no change to any
    existing caller of the `Provider` seam.
    """

    id = "langchain-fallback"

    def __init__(self, **options: Any) -> None:
        super().__init__(**options)
        self._chain: list[ChainEntry] = options.get("chain") or _default_chain()

    def available(self) -> bool:
        return bool(self._chain)

    def act(self, prompt: str, schema: type[ModelT] | None = None, *,
            prompt_file: str | None = None, fed_id: str | None = None) -> Any:
        return self._call(prompt, schema, role="agent", prompt_file=prompt_file, fed_id=fed_id)

    def judge(
        self, prompt: str, schema: type[ModelT], images: list[Path] | None = None, *,
        prompt_file: str | None = None, fed_id: str | None = None,
    ) -> ModelT:
        return self._call(prompt, schema, role="judge", images=images,
                           prompt_file=prompt_file, fed_id=fed_id)

    def _call(
        self, prompt: str, schema: type[ModelT] | None, *, role: str,
        images: list[Path] | None = None,
        prompt_file: str | None = None, fed_id: str | None = None,
    ) -> ModelT:
        if schema is None:
            raise ProviderError(f"{self.id} requires a schema for structured output (role={role})")
        if not self._chain:
            raise ProviderError(f"{self.id} has no configured provider (no API key/service found)")

        errors: list[str] = []
        for hop, (name, factory) in enumerate(self._chain):
            try:
                return self._try_tier(name, factory, prompt, schema, role, images,
                                       hop, prompt_file, fed_id)
            except Exception as exc:  # deliberately broad: any vendor failure falls through
                errors.append(f"{name}: {type(exc).__name__}: {exc}")
                continue
        raise ProviderError(
            f"{self.id}: every configured provider failed for role={role}: " + " | ".join(errors)
        )

    def _try_tier(
        self, name: str, factory: Callable[[], Any], prompt: str, schema: type[ModelT], role: str,
        images: list[Path] | None, fallback_hops: int,
        prompt_file: str | None, fed_id: str | None,
    ) -> ModelT:
        model = factory().with_structured_output(schema, include_raw=True)
        started = time.perf_counter()
        response = model.invoke(_message(prompt, images))
        latency_s = time.perf_counter() - started
        parsed = response["parsed"]
        if parsed is None:
            raise ProviderError(f"{name}: structured output did not parse")
        self.id = name
        usage = getattr(response.get("raw"), "usage_metadata", None) or {}
        self.record(role, input_tokens=usage.get("input_tokens", 0) or 0,
                    output_tokens=usage.get("output_tokens", 0) or 0,
                    prompt_file=prompt_file, fed_id=fed_id, latency_s=latency_s,
                    fallback_hops=fallback_hops)
        return parsed
