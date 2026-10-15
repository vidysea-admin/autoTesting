"""Resolve the visual role from checked model-specific neutral-probe receipts."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from autotester.providers.base import ProviderError, load_skill_prompt
from autotester.providers.model_chain import ModelChainProvider
from autotester.providers.ollama_cloud import DEEPSEEK
from autotester.schema.video_frames import VisionCapability
from autotester.schema.vision_capabilities import VisionCapabilitySet

VISION_POLICY_ID = "vision-chain"
GEMINI_VISION_MODEL = "gemini/gemini-3.6-flash"
_RECEIPTS = Path(__file__).resolve().parents[1]/"skills/vision-probe/capabilities.json"


def checked_capabilities() -> dict[str, VisionCapability]:
    """Validate persisted live answers/bindings; never manufacture a passed receipt."""
    try:
        records = VisionCapabilitySet.model_validate_json(_RECEIPTS.read_bytes()).records
        prompt_hash = hashlib.sha256(load_skill_prompt("vision-probe").encode()).hexdigest()
        capabilities = {}
        for record in records:
            result = record.result
            cap = result.capability
            valid = (result.status == "verified" and result.reason == "matched"
                     and result.expected is not None and result.expected == result.observed
                     and cap is not None and cap.passed and cap.model == result.model
                     and cap.endpoint_sha256 == result.endpoint_sha256
                     and cap.probe_protocol == "sanitized-layout-pair-v1"
                     and cap.prompt_sha256 == prompt_hash
                     and cap.output_sha256 == hashlib.sha256(
                         result.observed.model_dump_json().encode()).hexdigest()
                     and bool(result.attempts) and result.attempts[-1].status == "succeeded"
                     and all(a.provider == f"litellm:{result.model}" for a in result.attempts))
            if not valid or result.model in capabilities:
                raise ValueError("invalid_live_capability_binding")
            capabilities[result.model] = cap
        return capabilities
    except (OSError, ValueError, AttributeError):
        raise ProviderError("checked visual capability receipts unavailable or invalid") from None


class VisionChainProvider(ModelChainProvider):
    """DeepSeek visual primary; verified Gemini only on eligible bounded fallback."""

    def __init__(self, **options: Any) -> None:
        if options.pop("model", None) is not None or "vision_capabilities" in options:
            raise ProviderError("vision-chain order is receipt-bound; use an explicit provider")
        allow = options.pop("allow_gemini_fallback", True)
        if type(allow) is not bool:
            raise ProviderError("visual Gemini fallback flag must be a boolean")
        models = [DEEPSEEK] + ([GEMINI_VISION_MODEL] if allow else [])
        super().__init__(**options, model=",".join(models),
                         vision_capabilities=checked_capabilities())
        self.options.pop("model", None)  # the policy id round-trips; its order is not a user model

    @property
    def id(self) -> str:
        return self.served or VISION_POLICY_ID
