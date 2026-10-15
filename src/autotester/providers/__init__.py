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
from autotester.providers.model_chain import ModelChainProvider
from autotester.providers.vision_roles import VISION_POLICY_ID, VisionChainProvider
from autotester.schema.enums import ProviderRole, SourceKind
from autotester.schema.project import ProviderConfig

if TYPE_CHECKING:
    from autotester.schema.project import Project

_REGISTRY: dict[str, type[Provider]] = {
    "mock": MockProvider,
    "anthropic": AnthropicProvider,
    "langchain-fallback": LangChainFallbackProvider,
    "gemini": GeminiProvider,
    "litellm": LiteLLMProvider,
    "model-chain": ModelChainProvider,
    VISION_POLICY_ID: VisionChainProvider,
}

_CREDENTIAL_IN_SPEC = re.compile(r"://|@|\s")
_DEFAULTS = ProviderConfig()
DEFAULT_SPEC = _DEFAULTS.agent
"""The shipped default `--provider` for every CLI caller: the model chain (not a vendor)."""


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
    """Resolve one configured role; visual ensembles use for_teaching_group.

    Precedence: a project that names something other than the schema default for
    this role (`providers.judge = "litellm:openai/gpt-4o"`) wins; else the
    `AUTOTESTER_MODEL` env var selects a LiteLLM model for everyone; else the
    shipped text chain. The vision default is a receipt-bound independent policy
    and never inherits the text model override."""
    role = ProviderRole(role)
    if role is ProviderRole.VISION:
        members = for_teaching_group(project, SourceKind.VIDEO)
        if len(members) != 1:
            raise ProviderError("vision ensemble requires for_teaching_group")
        return members[0]
    default = _DEFAULTS.for_role(role)
    spec = project.providers.for_role(role) if project is not None else default
    env_model = os.environ.get(MODEL_ENV, "").strip()
    if spec == default and env_model:
        return get("litellm", model=env_model)
    provider_id, options = parse_spec(spec)
    return get(provider_id, **options)


def for_teaching_group(project: Project | None, kind: SourceKind, *,
                       override: str | None = None) -> list[Provider]:
    """Lazily resolve all ordered ensemble members; fallback remains inside a member."""
    kind = SourceKind(kind)
    if override is None and kind is not SourceKind.VIDEO:
        return [for_role(project, ProviderRole.AGENT)]
    config = project.providers if project is not None else _DEFAULTS
    spec = override if override is not None else config.vision
    if override is None and not config._configured_vision_providers():
        spec = config.vision_ensemble()[0]
    members = []
    for member in dict.fromkeys(part.strip() for part in spec.split(",")):
        name, member_options = parse_spec(member)
        if name == VISION_POLICY_ID:
            member_options["allow_gemini_fallback"] = config.vision_allow_gemini_fallback
        members.append(get(name, **member_options))
    return members


def for_teaching(project: Project | None, kind: SourceKind, *,
                 override: str | None = None) -> Provider:
    """Singleton convenience; video ensemble consumers must use the group API."""
    members = for_teaching_group(project, kind, override=override)
    if len(members) != 1:
        raise ProviderError("teaching ensemble requires for_teaching_group")
    return members[0]


def why_unavailable(provider: Provider) -> str | None:
    """None when the provider can serve a call; else the one-line reason it cannot,
    naming the model and the one thing to set (LL11) -- the provider's own
    `unavailable_reason` when it has one. Never a key, a prompt or an endpoint."""
    if provider.available():
        return None
    reason = getattr(provider, "unavailable_reason", None)
    return (reason() if callable(reason) else None) or "no credentials on this machine"


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


__all__ = ["DEFAULT_SPEC", "ModelChainProvider", "Provider", "ProviderError", "Unsupported",
           "available_ids", "for_role", "for_teaching", "for_teaching_group", "get",
           "parse_spec", "register", "why_unavailable"]
