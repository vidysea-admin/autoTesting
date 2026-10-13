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
