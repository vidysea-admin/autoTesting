"""`GeminiProvider._config`'s model-version detection and the 3.x-only
settings it gates. Contract: qa/contracts/ingest.md (provider seam), C8.

Split from test_gemini_schema.py (already scoped to the response-schema
sanitiser, AT-230) — this is a different seam: which generation-config
fields a given model string gets, not how a response schema is rendered.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from autotester.providers.gemini import GeminiProvider, _is_gemini_3
from autotester.schema.observation import VisionOptions

# -- AT-127: the SDK's fully-qualified `models/gemini-3.x` form -------------

def test_is_gemini_3_recognises_the_bare_form() -> None:
    assert _is_gemini_3("gemini-3.6-flash") is True


def test_is_gemini_3_recognises_the_fully_qualified_sdk_form() -> None:
    """AT-127: `client.models.list()` and the SDK's own examples return/accept
    `models/gemini-3.x` — a bare `startswith` silently lost `media_resolution`
    for a provider configured this (entirely legitimate) way."""
    assert _is_gemini_3("models/gemini-3.6-flash") is True


def test_is_gemini_3_rejects_an_older_model_either_way() -> None:
    assert _is_gemini_3("gemini-2.0-flash") is False
    assert _is_gemini_3("models/gemini-2.0-flash") is False


def test_config_applies_media_resolution_for_the_fully_qualified_form() -> None:
    provider = GeminiProvider(api_key="fake-key", model="models/gemini-3.6-flash")
    config = provider._config(None, VisionOptions(media_resolution="high"))
    assert config.media_resolution == "MEDIA_RESOLUTION_HIGH"


def test_config_falls_back_to_temperature_for_an_older_model() -> None:
    provider = GeminiProvider(api_key="fake-key", model="gemini-2.0-flash")
    config = provider._config(None, VisionOptions(temperature=0.2))
    assert config.temperature == 0.2
    assert config.media_resolution is None


# -- AT-126: thinking_level was documented but never applied -----------------

def test_config_applies_thinking_level_for_a_3x_model() -> None:
    """The docstring already promised this ('3.x models take media_resolution
    and a thinking level'); `thinking_config` was never built."""
    provider = GeminiProvider(api_key="fake-key", model="gemini-3.6-flash")
    config = provider._config(None, VisionOptions(thinking_level="high"))
    assert config.thinking_config.thinking_level == "HIGH"


def test_config_thinking_level_follows_the_declared_option() -> None:
    provider = GeminiProvider(api_key="fake-key", model="gemini-3.6-flash")
    config = provider._config(None, VisionOptions(thinking_level="low"))
    assert config.thinking_config.thinking_level == "LOW"


def test_config_does_not_set_thinking_config_for_an_older_model() -> None:
    provider = GeminiProvider(api_key="fake-key", model="gemini-2.0-flash")
    config = provider._config(None, VisionOptions())
    assert config.thinking_config is None


# -- AT-367: temperature used to be dropped (unreachable `elif`) on every ----
# -- 3.x model, including DEFAULT_MODEL -------------------------------------

def test_config_honours_temperature_on_the_default_gemini_3_model() -> None:
    """DEFAULT_MODEL ('gemini-3.6-flash') satisfies `_is_gemini_3`, so the old
    `elif opts.temperature is not None` branch could never fire for it -- a
    caller-set temperature was silently dropped with nothing failing."""
    provider = GeminiProvider(api_key="fake-key")  # DEFAULT_MODEL
    config = provider._config(None, VisionOptions(temperature=0.4))
    assert config.temperature == 0.4


def test_config_honours_temperature_alongside_thinking_config() -> None:
    """temperature is an independent GenerateContentConfig field the SDK
    accepts on every model -- it does not conflict with thinking_config, so
    both are set together on a 3.x model."""
    provider = GeminiProvider(api_key="fake-key", model="gemini-3.6-flash")
    config = provider._config(None, VisionOptions(temperature=0.7, thinking_level="low"))
    assert config.temperature == 0.7
    assert config.thinking_config.thinking_level == "LOW"


def test_config_omits_temperature_when_caller_does_not_set_it() -> None:
    """No regression: an unset temperature still isn't sent for a 3.x model."""
    provider = GeminiProvider(api_key="fake-key", model="gemini-3.6-flash")
    config = provider._config(None, VisionOptions())
    assert config.temperature is None


# -- AT-370: thinking_level was an unvalidated bare str ----------------------

def test_visionoptions_rejects_an_invalid_thinking_level() -> None:
    """A typo used to reach the SDK as a silently-accepted nonsense enum
    member (only a stderr UserWarning, nothing raised through this repo's own
    error path). It must now fail at construction time instead."""
    with pytest.raises(ValidationError):
        VisionOptions(thinking_level="banana")


@pytest.mark.parametrize("level", ["minimal", "low", "medium", "high"])
def test_visionoptions_accepts_every_sdk_thinking_level(level: str) -> None:
    assert VisionOptions(thinking_level=level).thinking_level == level


# -- AT-591: media_resolution was an unvalidated bare str, same shape --------
# -- as AT-370's thinking_level ----------------------------------------------

def test_visionoptions_rejects_an_invalid_media_resolution() -> None:
    """A typo (e.g. 'ultra') used to reach the SDK unvalidated -- gemini.py's
    f'MEDIA_RESOLUTION_{value.upper()}' would build a nonsense enum name the
    SDK does not define. It must now fail at construction time instead."""
    with pytest.raises(ValidationError):
        VisionOptions(media_resolution="ultra")


@pytest.mark.parametrize("resolution", ["low", "medium", "high"])
def test_visionoptions_accepts_every_sdk_media_resolution(resolution: str) -> None:
    assert VisionOptions(media_resolution=resolution).media_resolution == resolution
