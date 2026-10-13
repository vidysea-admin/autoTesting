"""Ollama cloud endpoint settings for LiteLLM: the one place that knows them.

Umesh, 2026-10-13: the primary models are GLM 5.3 Flash then DeepSeek 4.1 Flash,
served by the Ollama API (`https://ollama.com`) with `OLLAMA_API_KEY` from the
repo-root `.env`. `OLLAMA_BASE_URL` overrides the endpoint (a local daemon needs no
key). Ids were read from `GET /api/tags` on 2026-10-13.
"""

from __future__ import annotations

import os

OLLAMA_PREFIXES = ("ollama/", "ollama_chat/")
OLLAMA_CLOUD_URL = "https://ollama.com"
KEY_ENV = "OLLAMA_API_KEY"
GLM = "ollama_chat/glm-5.3-flash"
DEEPSEEK = "ollama_chat/deepseek-v4.1-flash"


def is_ollama(model: str) -> bool:
    return model.startswith(OLLAMA_PREFIXES)


def base_url() -> str | None:
    """Explicit `OLLAMA_BASE_URL`, else the cloud URL when a cloud key is set."""
    explicit = os.environ.get("OLLAMA_BASE_URL")
    if explicit:
        return explicit
    return OLLAMA_CLOUD_URL if os.environ.get(KEY_ENV) else None


def endpoint() -> dict[str, str]:
    """`api_base`/`api_key` kwargs for an Ollama model, only the ones set."""
    base, key = base_url(), os.environ.get(KEY_ENV)
    return {**({"api_base": base} if base else {}), **({"api_key": key} if key else {})}
