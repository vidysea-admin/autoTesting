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

import os
import time
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from autotester.providers.base import Provider, ProviderError
from autotester.providers.gemini_files import upload_and_wait
from autotester.providers.gemini_schema import gemini_schema
from autotester.schema.observation import VisionOptions

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
                  images: list[Path] | None) -> list[Any]:
        contents: list[Any] = []
        if video_path is not None:
            contents.append(upload_and_wait(client, video_path,
                                            cache_path=Path(".work/gemini_uploads.json")))
        for path in images or []:
            if path.exists():
                contents.append(upload_and_wait(client, path))
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

        from google import genai

        client = genai.Client(api_key=self._api_key)
        contents = self._contents(client, prompt, video_path, images)
        started = time.perf_counter()
        try:
            response = client.models.generate_content(
                model=self._model, contents=contents,
                config=self._config(schema, options),
            )
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(
                f"{self.label} generate_content failed (role={role}): "
                f"{type(exc).__name__}: {exc}") from exc
        latency_s = time.perf_counter() - started

        if response.parsed is None:
            raise ProviderError(self._unparsed_reason(response, role))
        usage = response.usage_metadata
        self.record(
            role,
            input_tokens=getattr(usage, "prompt_token_count", 0) or 0,
            output_tokens=getattr(usage, "candidates_token_count", 0) or 0,
            prompt_file=prompt_file, fed_id=fed_id, latency_s=latency_s,
        )
        # AT-230: `response_schema` is now a sanitised dict rather than the
        # Pydantic class, so the SDK hands back a plain dict instead of building
        # the model for us. Validate it here -- which is stricter anyway, because
        # `extra="forbid"` is enforced on OUR side where Gemini's dialect cannot
        # express it at all.
        if isinstance(response.parsed, dict):
            try:
                return schema.model_validate(response.parsed)
            except ValidationError as exc:
                raise ProviderError(
                    f"{self.id} returned JSON that does not fit {schema.__name__} "
                    f"(role={role}): {exc}") from None
        return response.parsed

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
