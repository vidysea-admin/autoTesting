"""Guard and account structured text/frame requests, refusing overdue logical results."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from autotester.core.env import ENV_FILE, PUBLIC_ENV_KEYS, read_dotenv, redaction_values
from autotester.core.paths import repo_root
from autotester.core.redact import assert_no_raw_secrets
from autotester.providers import ollama_cloud
from autotester.providers.attempts import check_deadline, reserve_attempt
from autotester.providers.availability import AvailabilityFailure, availability_reason
from autotester.providers.base import Provider, ProviderError
from autotester.providers.images import image_url_parts
from autotester.providers.litellm_schema import (
    json_mode_instruction,
    parse_answer,
    request_options,
)
from autotester.schema.observation import VisionOptions

ModelT = TypeVar("ModelT", bound=BaseModel)

MODEL_ENV = "AUTOTESTER_MODEL"
_TIMEOUT_S = 120
_PROVIDER_KEY_ENV = ("GEMINI_API_KEY", "GOOGLE_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY",
                     "LITELLM_API_KEY", ollama_cloud.KEY_ENV)
"""Vendor-key variables read from the PROCESS environment too: an exported key never
passes through `.env`, so the `.env` scan alone would not know it (LL5)."""
_CONFIG_KEYS = frozenset({MODEL_ENV, "LITELLM_API_BASE", "OLLAMA_BASE_URL", "OLLAMA_MODEL",
                          "AUTOTESTER_MODEL_ORDER", "AUTOTESTER_TEXT_FALLBACK_MODEL"})
"""`.env` keys that are settings, not secrets: a model name or an endpoint URL in a
prompt must not be refused as a leaked credential."""


def _load_litellm() -> Any:
    """Import the SDK lazily, so an unused or absent LiteLLM costs nothing. Two
    flags are set first: PRODUCTION mode stops LiteLLM running `load_dotenv()` on
    whatever `.env` it finds walking up from the cwd (a different file than the
    repo-root one `core/env.py` loads, and it would bypass that loader's
    test-process refusal); the local cost map stops an import-time fetch from
    GitHub. Neither is a credential."""
    os.environ.setdefault("LITELLM_MODE", "PRODUCTION")
    os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
    import litellm

    litellm.telemetry = False   # LL10: 1.104.0 has no such switch (checked in its source); a no-op
    return litellm


def _env_secret_values() -> list[str]:
    """Every non-empty value in the repo-root `.env` that is not a setting: the
    same "anything in .env is a secret" rule `SecretStore` applies at the stage."""
    path = repo_root() / ENV_FILE
    skip = _CONFIG_KEYS | PUBLIC_ENV_KEYS
    values = read_dotenv(path) if path.exists() else {}
    stored = list(redaction_values({}).values())  # credentials held in the store (U11); none off
    return [v for k, v in values.items() if k and v and k not in skip] + stored


def _texts(messages: list[dict[str, Any]]) -> list[str]:
    """Every text a request will carry (plain content and text parts alike)."""
    out: list[str] = []
    for message in messages:
        content = message["content"]
        if isinstance(content, str):
            out.append(content)
        else:
            out.extend(p["text"] for p in content if p.get("type") == "text")
    return out


def _why(exc: ValueError) -> str:
    """A short, content-free reason: pydantic's field paths and messages (never the
    offending input value), or a plain 'not valid JSON'."""
    if isinstance(exc, ValidationError):
        return "; ".join(f"{'.'.join(str(p) for p in e['loc']) or 'answer'}: {e['msg']}"
                         for e in exc.errors())
    return "not valid JSON"


class LiteLLMProvider(Provider):
    """One explicit model, any vendor. `options`: `model` (else `AUTOTESTER_MODEL`),
    and `secrets` (extra values the prompt guard must refuse, on top of `.env`)."""

    id = "litellm"

    def __init__(self, **options: Any) -> None:
        super().__init__(**options)
        self._model = str(options.get("model") or os.environ.get(MODEL_ENV) or "").strip()
        if self._model:
            self.options["model"] = self._model  # so `label` reads `litellm:<model>`
        self._extra_secrets: list[str] = [str(v) for v in options.get("secrets") or []]

    # -- availability ------------------------------------------------------
    def _endpoint(self) -> dict[str, str]:
        """`api_base`/`api_key` kwargs from the environment, only the ones set."""
        if ollama_cloud.is_ollama(self._model):
            return ollama_cloud.endpoint()
        base = os.environ.get("LITELLM_API_BASE")
        key = os.environ.get("LITELLM_API_KEY")
        return {**({"api_base": base} if base else {}), **({"api_key": key} if key else {})}

    def _missing_keys(self) -> list[str]:
        """Names of the credentials this model still needs ([] when none). An
        explicit endpoint (self-hosted / OpenAI-compatible / Ollama) needs no key."""
        endpoint = self._endpoint()
        if "api_base" in endpoint:
            return []
        try:
            env = _load_litellm().validate_environment(
                model=self._model, api_key=endpoint.get("api_key"))
        except Exception:
            return ["an API key for this model"]
        if env.get("keys_in_environment"):
            return []
        return list(env.get("missing_keys") or ["an API key"])

    def unavailable_reason(self) -> str | None:
        """Why this provider cannot serve a call right now, naming the model and the
        one thing to set (never a key, a prompt or an endpoint value); None when ready.
        The website's refusal pages show it (LL11)."""
        if not self._model:
            return (f"litellm has no model configured: set {MODEL_ENV} in .env (for example "
                    "gemini/gemini-2.5-pro or ollama/llama3), or name it in the project as "
                    "`litellm:<model>`")
        missing = self._missing_keys()
        if missing:
            return (f"{self.label} is missing credentials: set {', '.join(missing)} in .env "
                    "(or LITELLM_API_KEY / LITELLM_API_BASE for an OpenAI-compatible endpoint)")
        return None

    def available(self) -> bool:
        return self.unavailable_reason() is None

    def _require_ready(self) -> None:
        reason = self.unavailable_reason()
        if reason:
            raise ProviderError(reason)

    # -- roles -------------------------------------------------------------
    def see_video(self, path: Path, prompt: str, schema: type[ModelT],
                  options: VisionOptions | None = None, *,
                  prompt_file: str | None = None, fed_id: str | None = None) -> ModelT:
        from autotester.providers.video_frames import see_video

        return see_video(self, path, prompt, schema, options,
                         prompt_file=prompt_file, fed_id=fed_id)

    def act(self, prompt: str, schema: type[ModelT] | None = None, *,
            prompt_file: str | None = None, fed_id: str | None = None) -> Any:
        return self._structured(prompt, schema, role="agent",
                                prompt_file=prompt_file, fed_id=fed_id)

    def judge(
        self, prompt: str, schema: type[ModelT], images: list[Path] | None = None, *,
        prompt_file: str | None = None, fed_id: str | None = None,
    ) -> ModelT:
        return self._structured(prompt, schema, role="judge", images=images,
                                prompt_file=prompt_file, fed_id=fed_id)

    # -- the call ----------------------------------------------------------
    def _strategy(self) -> str:
        """By capability, never by vendor name: response schema, else a forced tool,
        else JSON mode with a repair retry."""
        if ollama_cloud.is_ollama(self._model):
            return "json"
        lit = _load_litellm()
        for name, probe in (("schema", lit.supports_response_schema),
                            ("tool", lit.supports_function_calling)):
            try:
                if probe(self._model):
                    return name
            except Exception:
                continue
        return "json"

    def _secret_values(self) -> list[str]:
        """The ONE secret-value set: `.env` values, exported vendor keys and the
        `secrets` option. The prompt guard refuses these going out and `_failure`
        withholds them coming back (LL5, LL8)."""
        exported = [os.environ[k] for k in _PROVIDER_KEY_ENV if os.environ.get(k)]
        return [*_env_secret_values(), *exported, *self._extra_secrets]

    def guard_text(self, text: str) -> None:
        """The redaction gate for one prompt text; raises `ProviderError`, never echoing a value."""
        try:
            assert_no_raw_secrets(text, self._secret_values())
        except ValueError:
            raise ProviderError(
                f"{self.label}: prompt withheld, a credential value reached it") from None

    def _guard(self, messages: list[dict[str, Any]]) -> None:
        self.guard_text("\n".join(_texts(messages)))

    def _failure(self, role: str, exc: Exception, messages: list[dict[str, Any]]) -> str:
        """A vendor failure, with the exception text kept only when it provably
        echoes none of the prompt, the endpoint or any secret value (LL8)."""
        text = str(exc)
        echoed = any(t[:30] in text for t in _texts(messages) if t)
        hidden = [v for v in (*self._endpoint().values(), *self._secret_values()) if v]
        if echoed or any(v in text for v in hidden) or len(text) > 300:
            text = "(details withheld)"
        return f"{self.label} {role} call failed: {type(exc).__name__}: {text}"

    def _complete(self, messages: list[dict[str, Any]], schema: type[BaseModel], strategy: str,
                  role: str, *, prompt_file: str | None, fed_id: str | None,
                  retries: int = 0,
                  generation_options: dict[str, Any] | None = None) -> tuple[Any, float]:
        """ONE physical `litellm.completion` call: guarded first, recorded after."""
        self._guard(messages)
        output_options = ({} if ollama_cloud.is_ollama(self._model)
                          else request_options(strategy, self._model, schema))
        kwargs: dict[str, Any] = {
            "model": self._model, "messages": messages, "num_retries": 0,
            "timeout": _TIMEOUT_S, "drop_params": True, **self._endpoint(),
            **output_options}
        kwargs.update(generation_options or {})
        if role == "judge":
            kwargs["temperature"] = 0
        receipt, kwargs["timeout"] = reserve_attempt(self.label, role, _TIMEOUT_S)
        deadline = time.monotonic() + kwargs["timeout"]
        started = time.perf_counter()
        try:
            response = _load_litellm().completion(**kwargs)
        except Exception as exc:
            receipt.status = "failed"
            receipt.latency_s = time.perf_counter() - started
            self.record(role, None, None, failed=True, prompt_file=prompt_file,
                        fed_id=fed_id, latency_s=receipt.latency_s, retries=retries)
            check_deadline(deadline)
            reason = availability_reason(exc)
            if reason is not None:
                raise AvailabilityFailure(reason) from None
            raise ProviderError(self._failure(role, exc, messages)) from None
        usage = getattr(response, "usage", None)
        receipt.status = "succeeded"
        receipt.input_tokens = getattr(usage, "prompt_tokens", None)
        receipt.output_tokens = getattr(usage, "completion_tokens", None)
        receipt.latency_s = time.perf_counter() - started
        self.record(
            role, input_tokens=receipt.input_tokens, output_tokens=receipt.output_tokens,
            prompt_file=prompt_file, fed_id=fed_id,
            latency_s=time.perf_counter() - started, retries=retries)
        check_deadline(deadline)
        try:
            return response.choices[0].message, deadline
        except (AttributeError, IndexError, TypeError):
            raise ProviderError(f"{self.label} {role} call returned no message") from None
    def _structured(
        self, prompt: str, schema: type[ModelT] | None, *, role: str,
        images: list[Path] | None = None,
        content_parts: list[dict[str, Any]] | None = None,
        generation_options: dict[str, Any] | None = None,
        prompt_file: str | None = None, fed_id: str | None = None,
    ) -> ModelT:
        if schema is None:
            raise ProviderError(
                f"{self.label} requires a schema for structured output (role={role})")
        self._require_ready()
        strategy = self._strategy()
        text = prompt + (json_mode_instruction(schema) if strategy == "json" else "")
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": ([{"type": "text", "text": text}, *content_parts]
                                         if content_parts else image_url_parts(text, images))}]
        meta = {"prompt_file": prompt_file, "fed_id": fed_id}
        if generation_options:
            meta["generation_options"] = generation_options
        message, deadline = self._complete(messages, schema, strategy, role, **meta)
        try:
            answer = parse_answer(message, strategy, schema,
                                strict=ollama_cloud.is_ollama(self._model)
                                or self.options.get("strict", False))
            check_deadline(deadline)
            return answer
        except ValueError as exc:
            problem = _why(exc)
            if strategy != "json":
                raise ProviderError(self._unparsable(role, problem)) from None
        messages += [
            {"role": "assistant", "content": getattr(message, "content", None) or ""},
            {"role": "user", "content": "That reply was not valid. Reply with ONE JSON object "
                                        f"only, matching the schema. Problem: {problem}"}]
        message, deadline = self._complete(messages, schema, strategy, role, retries=1, **meta)
        try:
            answer = parse_answer(message, strategy, schema,
                                strict=ollama_cloud.is_ollama(self._model)
                                or self.options.get("strict", False))
            check_deadline(deadline)
            return answer
        except ValueError as exc:
            raise ProviderError(self._unparsable(role, _why(exc))) from None
    def _unparsable(self, role: str, problem: str) -> str:
        return f"{self.label} {role} answer did not match the schema ({problem})"
