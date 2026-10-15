"""Gemini provider: the `vision` role (video understanding), plus `agent`/`judge`
via the same structured-output mechanism.

Uses the `google-genai` SDK directly (not LangChain) because video upload is a
vision-specific operation `providers.base.Provider.see_video` needs regardless
of which text model ends up judging/acting — this provider exists primarily to
serve ingest.py's need to watch a video, not to compete with
`LangChainFallbackProvider` for the judge/agent roles (though it can serve
those too, standalone, like `AnthropicProvider` can).
"""

from __future__ import annotations

import io
import json
import math
import os
import time
import wave
from pathlib import Path
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from autotester.providers.attempts import attempt_budget, check_deadline
from autotester.providers.base import Provider, ProviderError
from autotester.providers.gemini_files import GeminiDeadlineTransport, upload_and_wait
from autotester.providers.gemini_schema import gemini_schema
from autotester.providers.litellm_provider import LiteLLMProvider
from autotester.schema.observation import VisionOptions
from autotester.schema.transcription import AudioTransportCapability, GeminiTranscription

ModelT = TypeVar("ModelT", bound=BaseModel)

DEFAULT_MODEL = "gemini-3.6-flash"


def _is_gemini_3(model: str) -> bool:
    """AT-127: the SDK's own fully-qualified form (`models/gemini-3.x`) must
    still be recognised — a bare `startswith` silently lost `media_resolution`
    (and now `thinking_config`) for a model configured that way, with nothing
    failing to say so."""
    return model.removeprefix("models/").startswith("gemini-3")


class GeminiProvider(Provider):
    """Wraps `google.genai.Client`. Never receives a raw secret — callers pass
    prompts containing `{{SECRET:KEY}}` placeholders only, per the base contract."""

    id = "gemini"
    # HTTPX cannot promise hard cancellation of an in-progress socket read.
    audio_transport_capability = AudioTransportCapability(
        physical_attempt_accounting=True, audio_only=True, shared_deadline=True)

    def __init__(self, **options: Any) -> None:
        super().__init__(**options)
        self._api_key = (
            options.get("api_key")
            or os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
        )
        self._model = options.get("model", DEFAULT_MODEL)

    def available(self) -> bool:
        return bool(self._api_key)

    def see_video(self, path: Path, prompt: str, schema: type[ModelT],
                  options: VisionOptions | None = None, *,
                  prompt_file: str | None = None, fed_id: str | None = None) -> ModelT:
        return self._structured(prompt, schema, role="vision", video_path=path,
                                options=options, prompt_file=prompt_file, fed_id=fed_id)

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

    def _config(self, schema: type[BaseModel] | None, options: VisionOptions | None) -> Any:
        """Build the generation config. 3.x models additionally take
        `media_resolution` and a thinking level; `temperature` is an independent
        sampling knob the SDK accepts on every model (AT-367: it does NOT
        conflict with `thinking_config`, which governs reasoning effort, not
        sampling) so it is applied whenever the caller sets it, regardless of
        model. Seed and token ceiling are set for ALL calls, because without
        them a re-run of the same chunk is a different answer and the on-disk
        observation cache means nothing."""
        from google.genai import types

        opts = options or VisionOptions()
        kwargs: dict[str, Any] = {
            "response_mime_type": "application/json",
            "seed": opts.seed,
            "max_output_tokens": opts.max_output_tokens,
        }
        if schema is not None:
            # AT-230: NOT the Pydantic class. google-genai renders it with
            # `additionalProperties` (from this codebase's own C1 `extra="forbid"`)
            # and `$defs`, both of which Gemini's dialect rejects -- every real
            # call 400'd while the fake client in the tests accepted anything.
            kwargs["response_schema"] = gemini_schema(schema)
        if options is not None:
            if _is_gemini_3(self._model):
                kwargs["media_resolution"] = f"MEDIA_RESOLUTION_{opts.media_resolution.upper()}"
                # AT-126: the docstring already promised this; it was never applied.
                kwargs["thinking_config"] = types.ThinkingConfig(
                    thinking_level=opts.thinking_level.upper()
                )
            # AT-367: temperature used to be gated behind `elif`, so a caller-set
            # value was silently dropped for every 3.x model (including
            # DEFAULT_MODEL) with nothing failing. It is an independent
            # GenerateContentConfig field the SDK accepts alongside
            # thinking_config, so it is honoured for every model.
            if opts.temperature is not None:
                kwargs["temperature"] = opts.temperature
            if opts.system_instruction:
                kwargs["system_instruction"] = opts.system_instruction
        return types.GenerateContentConfig(**kwargs)

    def _contents(self, client: Any, prompt: str, video_path: Path | None,
                  images: list[Path] | None, deadline: float) -> list[Any]:
        contents: list[Any] = []
        if video_path is not None and video_path.suffix.lower() == ".wav":
            from google.genai import types

            with video_path.open("rb") as audio_file:
                data = audio_file.read(16 * 1024 * 1024 + 1)
            if len(data) > 16 * 1024 * 1024:
                raise ProviderError("Gemini audio exceeds the 16 MiB inline limit")
            with wave.open(io.BytesIO(data), "rb") as audio:
                if audio.getcomptype() != "NONE":
                    raise ProviderError("Gemini narration requires PCM WAV audio")
            contents.append(types.Part.from_bytes(data=data, mime_type="audio/wav"))
        elif video_path is not None:
            contents.append(upload_and_wait(client, video_path,
                                            cache_path=Path(".work/gemini_uploads.json"),
                                            deadline=deadline))
        for path in images or []:
            if path.exists():
                contents.append(upload_and_wait(client, path, deadline=deadline))
        contents.append(prompt)
        return contents

    def _structured(
        self, prompt: str, schema: type[ModelT] | None, *, role: str,
        video_path: Path | None = None, images: list[Path] | None = None,
        options: VisionOptions | None = None,
        prompt_file: str | None = None, fed_id: str | None = None,
    ) -> ModelT:
        if not self.available():
            raise ProviderError("GEMINI_API_KEY/GOOGLE_API_KEY is not set")
        if schema is None:
            raise ProviderError(f"{self.id} requires a schema for structured output (role={role})")

        timeout = float(self.options.get("timeout_s", 120))
        if not math.isfinite(timeout) or not 0 < timeout <= 120:
            raise ProviderError("Gemini timeout_s must be finite and within 120 seconds")
        if schema is GeminiTranscription and (video_path is None or
                                              video_path.suffix.lower() != ".wav"):
            raise ProviderError("Gemini narration requires bounded extracted WAV audio")
        guard = LiteLLMProvider(secrets=[self._api_key, *(self.options.get("secrets") or [])])
        guard.guard_text(prompt)
        if options and options.system_instruction:
            guard.guard_text(options.system_instruction)
        with attempt_budget(32, timeout):
            return self._bounded_call(prompt, schema, role, video_path, images, options, timeout,
                                      prompt_file, fed_id)

    def _bounded_call(self, prompt: str, schema: type[ModelT], role: str,
                      video_path: Path | None, images: list[Path] | None,
                      options: VisionOptions | None, timeout: float,
                      prompt_file: str | None, fed_id: str | None) -> ModelT:
        from google import genai
        from google.genai import types

        deadline = time.monotonic() + timeout
        transport = GeminiDeadlineTransport(deadline, self, role,
                                            prompt_file=prompt_file, fed_id=fed_id)
        with httpx.Client(transport=transport, follow_redirects=False) as http_client:
            client = genai.Client(api_key=self._api_key, http_options=types.HttpOptions(
                timeout=max(1, int(timeout * 1000)), httpx_client=http_client,
                retry_options=types.HttpRetryOptions(attempts=1)))
            try:
                contents = self._contents(client, prompt, video_path, images, deadline)
                for _ in range(2):
                    transport.remaining()
                    response = client.models.generate_content(
                        model=self._model, contents=contents, config=self._config(schema, options))
                    transport.remaining()
                    check_deadline(deadline)
                    candidates = getattr(response, "candidates", None) or []
                    if any(str(getattr(getattr(c, "finish_reason", None), "name", ""))
                           == "MAX_TOKENS" for c in candidates):
                        raise ProviderError(self._unparsed_reason(response, role))
                    try:
                        parsed = getattr(response, "parsed", None)
                        if isinstance(parsed, BaseModel):
                            parsed = parsed.model_dump(mode="json")
                        if parsed is None:
                            result = schema.model_validate_json(response.text, strict=True)
                        else:
                            result = schema.model_validate_json(json.dumps(parsed), strict=True)
                        check_deadline(deadline)
                        return result
                    except (ValidationError, ValueError, TypeError, AttributeError):
                        continue  # One bounded regeneration, without echoing rejected content.
                raise ProviderError("Gemini returned JSON that does not fit the required schema")
            except ProviderError:
                raise
            except Exception as exc:
                check_deadline(deadline)
                raise ProviderError(f"Gemini {role} request failed: {type(exc).__name__}") from None
            finally:
                close = getattr(type(client), "close", None)
                if close is not None:
                    close(client)

    def _unparsed_reason(self, response: Any, role: str) -> str:
        """Say WHY nothing parsed. A truncated answer is not a malformed one.

        Hitting the output ceiling on a long video is the common failure here,
        and "structured output did not parse" sends the reader looking at their
        schema instead of at the chunk length that actually caused it."""
        finish = ""
        for candidate in getattr(response, "candidates", None) or []:
            reason = getattr(candidate, "finish_reason", None)
            finish = str(getattr(reason, "name", reason) or "")
            break
        if finish == "MAX_TOKENS":
            return (f"{self.label}: the answer hit max_output_tokens and was truncated "
                    f"(role={role}) — shorten the chunk or raise the ceiling")
        suffix = f", finish_reason={finish}" if finish else ""
        return f"{self.label}: structured output did not parse (role={role}{suffix})"
