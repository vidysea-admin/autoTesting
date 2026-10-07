"""Provider registry. Stages ask for a role; this module resolves the vendor."""

from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING, Any

from autotester.providers.anthropic import AnthropicProvider
from autotester.providers.base import Provider, ProviderError, Unsupported
from autotester.providers.gemini import GeminiProvider
from autotester.providers.langchain_fallback import LangChainFallbackProvider
from autotester.providers.litellm_provider import MODEL_ENV, LiteLLMProvider
from autotester.providers.mock import MockProvider
from autotester.schema.enums import ProviderRole
from autotester.schema.project import ProviderConfig

if TYPE_CHECKING:
    from autotester.schema.project import Project

_REGISTRY: dict[str, type[Provider]] = {
    "mock": MockProvider,
    "anthropic": AnthropicProvider,
    "langchain-fallback": LangChainFallbackProvider,
    "gemini": GeminiProvider,
    "litellm": LiteLLMProvider,
}

_CREDENTIAL_IN_SPEC = re.compile(r"://|@|\s")
_DEFAULTS = ProviderConfig()


def register(provider_id: str, cls: type[Provider]) -> None:
    """Add a provider implementation. Called by each vendor module on import."""
    _REGISTRY[provider_id] = cls


def get(provider_id: str, **options: Any) -> Provider:
    """Instantiate a provider by id, raising a clear error when unknown."""
    try:
        cls = _REGISTRY[provider_id]
    except KeyError:
        known = ", ".join(sorted(_REGISTRY))
        raise ProviderError(f"unknown provider '{provider_id}'; known: {known}") from None
    return cls(**options)


def parse_spec(spec: str) -> tuple[str, dict[str, Any]]:
    """`<provider_id>[:<model>]` -> `(provider_id, options)`, the one grammar for
    every provider (it matches `Provider.label`, so labels round-trip). Only the
    FIRST colon splits, so `litellm:ollama/llama3:8b` keeps its tag. The `vision`
    comma list (`gemini,anthropic`) passes through whole, each id checked. A spec
    that names an unknown provider, no model, or carries `@`, `://` or whitespace
    (a URL or credential) is refused WITHOUT echoing it: keys live in `.env`,
    never in `project.json`."""
    provider_id, sep, model = spec.strip().partition(":")
    ids = [i.strip() for i in provider_id.split(",")]
    if not provider_id or any(i not in _REGISTRY for i in ids):
        known = ", ".join(sorted(_REGISTRY))
        raise ProviderError("provider spec names no known provider; expected "
                            f"`<provider>[:<model>]` with provider one of: {known}")
    if not sep:
        return provider_id, {}
    model = model.strip()
    if not model or len(ids) > 1:
        raise ProviderError(f"provider spec for '{provider_id}' names no usable model after ':'"
                            if not model else "a provider list cannot name a model")
    if _CREDENTIAL_IN_SPEC.search(model):
        raise ProviderError("provider spec carries what looks like a URL or credential; "
                            "keys live in .env, never in project config")
    return provider_id, {"model": model}


def for_role(project: Project | None = None,
             role: str | ProviderRole = ProviderRole.JUDGE) -> Provider:
    """THE place that picks the provider for an `agent` or `judge` call (T-202, LL2).

    Precedence: a project that names something other than the schema default for
    this role (`providers.judge = "litellm:openai/gpt-4o"`) wins; else the
    `AUTOTESTER_MODEL` env var selects a LiteLLM model for everyone; else the
    shipped default, the LangChain fallback chain. `vision` is refused: video
    understanding is Gemini's Files API, chosen per ensemble by the video stage."""
    role = ProviderRole(role)
    if role is ProviderRole.VISION:
        raise ProviderError("for_role serves the agent and judge roles; the vision "
                            "role is chosen by the video stage (Gemini)")
    default = _DEFAULTS.for_role(role)
    spec = project.providers.for_role(role) if project is not None else default
    env_model = os.environ.get(MODEL_ENV, "").strip()
    if spec == default and env_model:
        return get("litellm", model=env_model)
    provider_id, options = parse_spec(spec)
    return get(provider_id, **options)


def why_unavailable(provider: Provider) -> str | None:
    """A provider's own one-line reason it cannot serve a call (naming the model and
    the one thing to set), or None when it has none to give (LL11). Duck-typed so a
    provider that does not implement `unavailable_reason` is simply "no reason"."""
    reason = getattr(provider, "unavailable_reason", None)
    return reason() if callable(reason) else None


def available_ids() -> list[str]:
    """Providers whose credentials or binaries are actually present."""
    ready = []
    for provider_id, cls in _REGISTRY.items():
        try:
            if cls().available():
                ready.append(provider_id)
        except Exception:
            continue
    return sorted(ready)


__all__ = ["Provider", "ProviderError", "Unsupported", "available_ids", "for_role",
           "get", "parse_spec", "register", "why_unavailable"]
