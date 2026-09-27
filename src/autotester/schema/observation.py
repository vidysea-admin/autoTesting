"""A vision model's raw reading of one video — INGEST's input material.

Moved out of `flowspec.py` at D-014 (that file was at its 300-line cap) and
extended with the fields the four Track A outputs need: a screen's url and
purpose, its fields and visible controls, moments worth a screenshot, and the
issues the model itself noticed. `stages/ingest.py` and `stages/analyze_video.py`
turn these into `FlowSpec`/`VideoAnalysis` — this module never touches disk and
never calls a provider.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from autotester.schema.base import Artifact
from autotester.schema.enums import Action, Confidence, IssueCategory, IssueOrigin, Severity


class ObservedStep(BaseModel):
    """One action a vision model saw in a video. Raw material for a `Step` —
    `stages/ingest.py` turns `t_start`/`t_end` into a `SourceRef`."""

    model_config = ConfigDict(extra="forbid")

    order: int
    action: Action
    target: str = Field(description="what was clicked/filled, in plain terms — a role/name/"
                        "label a human would use, never a CSS selector")
    value: str | None = None
    t_start: float = Field(description="seconds into the video when this action starts")
    t_end: float | None = None
    on_screen_text: str | None = Field(default=None, description="visible text near the action")
    narration: str | None = Field(default=None, description="what the presenter said, if any")


class ObservedFlow(BaseModel):
    """One journey a vision model saw across screens."""

    model_config = ConfigDict(extra="forbid")

    name: str
    entry_screen: str = Field(description="the name of the screen this flow starts on")
    exit_screen: str | None = None
    steps: list[ObservedStep] = Field(default_factory=list)


class ObservedScreen(BaseModel):
    """One distinguishable screen a vision model saw."""

    model_config = ConfigDict(extra="forbid")

    name: str
    t_start: float = Field(description="seconds into the video when this screen first appears")
    t_end: float | None = None
    signals: list[str] = Field(default_factory=list, description="visible cues that identify it")
    url: str | None = Field(default=None, description="address bar text, when visible")
    purpose: str | None = None
    fields: list[str] = Field(default_factory=list, description="input field names, in plain terms")
    ui_elements: list[str] = Field(default_factory=list, description="buttons/links/controls seen")
    screenshot_ts: list[float] = Field(
        default_factory=list, description="fully-loaded, stable moments worth a frame"
    )


class ObservedIssue(BaseModel):
    """A problem the vision model itself noticed — spoken, on-screen, or both."""

    model_config = ConfigDict(extra="forbid")

    t_start: float
    t_end: float | None = None
    screen: str = Field(description="the screen name this issue was seen on")
    category: IssueCategory
    severity: Severity = Severity.S2
    confidence: Confidence = Confidence.MEDIUM
    title: str
    what_is_wrong: str
    on_screen_text: str | None = None
    narration: str | None = None
    origin: IssueOrigin = IssueOrigin.MODEL_DETECTED


class VisionOptions(BaseModel):
    """Generation config for a vision call — the settings the proven external
    pipeline benchmarked (fps 2, HIGH media resolution, seed 7)."""

    model_config = ConfigDict(extra="forbid")

    fps: float = 2.0
    seed: int = 7
    max_output_tokens: int = 65536
    media_resolution: Literal["low", "medium", "high"] = Field(
        default="high",
        description="AT-591: constrained to the values google-genai's "
        "`types.MediaResolution` actually accepts (minus the UNSPECIFIED sentinel) "
        "-- an unconstrained str let a typo (e.g. 'ultra') reach the SDK's "
        "f'MEDIA_RESOLUTION_{value.upper()}' construction unvalidated, the same "
        "shape AT-370 fixed for thinking_level one field above.",
    )
    thinking_level: Literal["minimal", "low", "medium", "high"] = Field(
        default="high",
        description="AT-370: constrained to the values google-genai's "
        "`types.ThinkingLevel` actually accepts (minus the UNSPECIFIED sentinel) "
        "-- an unconstrained str let a typo reach the SDK as a silently-accepted "
        "nonsense enum member with only a stderr UserWarning, never an exception "
        "this codebase's own error path would surface.",
    )
    temperature: float | None = None
    system_instruction: str | None = None


class VideoObservation(BaseModel):
    """A vision provider's raw reading of one video (or chunk) — turned into a
    `FlowSpec` by `stages/ingest.py` or into a `VideoAnalysis` by
    `stages/analyze_video.py` (ids minted, provenance attached)."""

    model_config = ConfigDict(extra="forbid")

    screens: list[ObservedScreen] = Field(default_factory=list)
    flows: list[ObservedFlow] = Field(default_factory=list)
    issues: list[ObservedIssue] = Field(default_factory=list)
    summary: str = ""
    open_questions: list[str] = Field(default_factory=list)


class ModelObservation(Artifact):
    """One model's raw answer for one chunk — cached on disk so re-running the
    ensemble never re-spends a provider call (VL3)."""

    source_id: str
    provider_label: str = Field(description="e.g. 'gemini:gemini-3.1-pro-preview'")
    prompt_name: str
    prompt_sha256: str = Field(default="", description="the prompt TEXT this answer came from. "
                               "A name is not a key: editing a prompt file leaves its name alone, "
                               "and the cache would hand back the answer to the old question")
    chunk_index: int
    offset_s: float
    length_s: float
    observation: VideoObservation
    input_tokens: int = 0
    output_tokens: int = 0
