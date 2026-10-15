"""Safe physical model-request accounting, without prompts or vendor error payloads."""
from typing import Literal

from pydantic import BaseModel, ConfigDict


class ProviderAttempt(BaseModel):
    """One reserved physical request; missing token measurements remain unknown."""

    model_config = ConfigDict(extra="forbid")
    provider: str
    role: str
    status: Literal["pending", "succeeded", "failed"] = "pending"
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_s: float = 0.0
