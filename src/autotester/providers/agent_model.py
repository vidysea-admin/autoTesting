"""The production chat-model constructor for the agent layer (T-181, AL12).

One job: hand `agents/lead_agent.py::run_lead_agent` a real LangChain chat model built from
whichever credential is present, in the same preference order as the langchain fallback
chain (`langchain_fallback._default_chain` stays the one place that lists the vendors). Keys
come from the process environment (the repo-root `.env` loaded by `core/env.py`); nothing here
reads, prints or stores a key value.
"""

from __future__ import annotations

from typing import Any

from autotester.providers import langchain_fallback
from autotester.providers.base import ProviderError


def agent_chat_model(chain: list[langchain_fallback.ChainEntry] | None = None
                     ) -> tuple[str, Any]:
    """`(provider_id, chat_model)` for the first configured vendor; raises `ProviderError`
    (naming no key) when none is configured. `chain` is injectable for tests."""
    entries = chain if chain is not None else langchain_fallback._default_chain()
    if not entries:
        raise ProviderError("no model provider is configured for the agent layer; "
                            "see `autotester providers`")
    provider_id, factory = entries[0]
    return provider_id, factory()


def agent_chain_model(order: list[str] | None = None) -> tuple[str, Any, list[str]]:
    """`(id, chat_model, served_log)` over the Ollama GLM -> DeepSeek -> Gemini chain.

    A tool-calling LangChain model whose bound form tries each available tier in order and falls
    through on any error; `served_log` gets the serving tier label after every model call.
    Keys come from the process environment; nothing here reads or prints a value."""
    from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
    from langchain_core.runnables import RunnableLambda

    from autotester.providers import model_chain

    served: list[str] = []
    tiers = _build_tiers(order or model_chain.configured_order())
    if not tiers:
        raise ProviderError("no model-chain tier is configured for the agent layer")

    class ChainChat(GenericFakeChatModel):  # a BaseChatModel shell; calls go via bind_tools
        def bind_tools(self, tools: Any, **kw: Any) -> Any:
            bound = [(n, m.bind_tools(tools, **kw)) for n, m in tiers]

            def call(messages: Any) -> Any:
                errors = []
                for n, m in bound:
                    try:
                        reply = m.invoke(messages)
                    except Exception as exc:  # any vendor error: fall through
                        errors.append(f"{n}: {type(exc).__name__}")
                        continue
                    served.append(n)
                    return reply
                raise ProviderError("model-chain: every tier failed: " + "; ".join(errors))

            return RunnableLambda(call)

    return model_chain.CHAIN_ID, ChainChat(messages=iter([])), served


def _build_tiers(order: list[str]) -> list[tuple[str, Any]]:
    """The (model id, chat model) pair for each chain entry whose credential is present."""
    import os

    from autotester.providers import ollama_cloud

    tiers: list[tuple[str, Any]] = []
    for name in order:
        if ollama_cloud.is_ollama(name) and os.environ.get(ollama_cloud.KEY_ENV):
            from langchain_ollama import ChatOllama

            key = os.environ[ollama_cloud.KEY_ENV]
            tiers.append((name, ChatOllama(
                model=name.split("/", 1)[1], base_url=ollama_cloud.base_url(),
                client_kwargs={"headers": {"Authorization": f"Bearer {key}"}})))
        elif name.startswith("gemini/") and (os.environ.get("GEMINI_API_KEY")
                                              or os.environ.get("GOOGLE_API_KEY")):
            from langchain_google_genai import ChatGoogleGenerativeAI

            key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            tiers.append((name, ChatGoogleGenerativeAI(model=name.split("/", 1)[1],
                                                        google_api_key=key)))
    return tiers
