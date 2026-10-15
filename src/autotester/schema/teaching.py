"""Structured, locator-cited teaching material and its model reading."""

from pydantic import BaseModel, ConfigDict, Field

from autotester.schema.enums import Action
from autotester.schema.flowspec import ExpectedState, InputField


class TeachingUnit(BaseModel):
    """One extracted section/page/transcript segment, without invented video time."""

    model_config = ConfigDict(extra="forbid")
    locator: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=100_000)


class TextScreen(BaseModel):
    """A screen explicitly described by one supplied teaching unit."""

    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1)
    locator: str
    url_pattern: str | None = None
    signals: list[str] = Field(default_factory=list)
    fields: list[InputField] = Field(default_factory=list)


class TextStep(BaseModel):
    """A described action citing a supplied locator, never a synthetic timestamp."""

    model_config = ConfigDict(extra="forbid")
    order: int = Field(ge=1)
    action: Action
    target: str = Field(min_length=1)
    value: str | None = None
    locator: str
    screen: str
    expected: ExpectedState = Field(default_factory=ExpectedState)


class TextFlow(BaseModel):
    """An ordered task supported by the teaching material."""

    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1)
    entry_screen: str
    exit_screen: str | None = None
    steps: list[TextStep] = Field(min_length=1)


class TextObservation(BaseModel):
    """The bounded text-role response; reconciliation remains a later stage."""

    model_config = ConfigDict(extra="forbid")
    screens: list[TextScreen] = Field(default_factory=list, max_length=200)
    flows: list[TextFlow] = Field(default_factory=list, max_length=200)
    summary: str | None = None
