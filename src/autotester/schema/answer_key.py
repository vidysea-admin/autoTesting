"""An answer-key fixture derived from product docs, and where it came from (MP24, MPI2, MPI6).

One job: `AnswerKey` -- the items to answer in a product's scored flow, the score the product's own
documentation says all-correct answers earn (`documented_score` out of `max_score`), and the
`source` the key was written from. The key is refused when it cannot be shown to come from product
documentation: no source, or a source that cites a benchmark finding, the known-bugs list or an
issue (a fixture written from a specific finding is not blind, and its matches could not count as
recall). The key is also refused when it disagrees with itself: the item points must add up to the
documented score. Answers are `<verb> <target>` actions; no answer text or personal data is held.
"""

from __future__ import annotations

import re
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from autotester.schema.leak_evidence import contains_personal_shape, validate_url_template
from autotester.schema.multi_role_finding import parse_repro_step
from autotester.schema.platform import PLATFORM_ID_PATTERN
from autotester.schema.role_account import ROLE_ACCOUNT_ID_PATTERN

KEY_ID_PATTERN = r"^[a-z][a-z0-9_-]{0,31}$"
MAX_ITEMS = 40
# A source naming one of these is a finding, a benchmark list or a tracker row, not product docs.
_FINDING_CITATION = re.compile(
    r"benchmark|ceo[\s_-]*(list|finding|bug)|known[\s_-]*bugs|\bfindings?\b|atomic|"
    r"bug[\s_-]*events|\bAT-\d+|\bMP\d+|acceptance[\s_-]*comparison|\.work[/\\]", re.IGNORECASE)


class AnswerSourceKind(StrEnum):
    """Where a key may come from. Only product documentation is accepted."""

    PRODUCT_DOC = "product_doc"


class AnswerKeySource(BaseModel):
    """Where the key was written from: a product document, by reference."""

    model_config = ConfigDict(extra="forbid")

    kind: AnswerSourceKind
    ref: str = Field(min_length=3, max_length=300, description="doc path or URL, no ids")
    title: str = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def _is_not_a_finding(self) -> AnswerKeySource:
        for text in (self.ref, self.title):
            if _FINDING_CITATION.search(text):
                raise ValueError("an answer key may not cite a benchmark finding or an issue")
            if contains_personal_shape(text):
                raise ValueError("a source reference looks like personal data")
        return self


class AnswerItem(BaseModel):
    """One answer to give. `is_correct=False` is a deliberately wrong answer (score less)."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=KEY_ID_PATTERN)
    answer_action: str = Field(min_length=3, max_length=200)
    points: int = Field(ge=1, le=1000, strict=True)
    is_correct: bool = True

    @model_validator(mode="after")
    def _action_is_replayable(self) -> AnswerItem:
        parse_repro_step(self.answer_action)
        if contains_personal_shape(self.answer_action):
            raise ValueError("an answer action looks like personal data")
        return self


class AnswerKey(BaseModel):
    """The items, the documented all-correct score, and the source."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=KEY_ID_PATTERN)
    platform_id: str = Field(pattern=PLATFORM_ID_PATTERN)
    role_id: str = Field(pattern=ROLE_ACCOUNT_ID_PATTERN, description="who takes the quiz")
    url_template: str
    source: AnswerKeySource
    open_action: str | None = Field(default=None, min_length=3, max_length=200)
    items: list[AnswerItem] = Field(min_length=1, max_length=MAX_ITEMS)
    submit_action: str = Field(min_length=3, max_length=200)
    score_selector: str = Field(min_length=1, max_length=200)
    documented_score: int = Field(ge=0, strict=True, description="score for all-correct answers")
    max_score: int = Field(ge=1, strict=True)

    @model_validator(mode="after")
    def _self_consistent(self) -> AnswerKey:
        validate_url_template(self.url_template)
        for action in (self.open_action, self.submit_action):
            if action is not None:
                parse_repro_step(action)
        ids = [i.id for i in self.items]
        if len(set(ids)) != len(ids):
            raise ValueError("an item is listed twice")
        if sum(i.points for i in self.items) != self.documented_score:
            raise ValueError("item points must add up to the documented all-correct score")
        if self.documented_score > self.max_score:
            raise ValueError("the documented score cannot exceed the maximum")
        return self

    def expected_score(self) -> int:
        """The score the product should show for the answers this key gives."""
        return sum(i.points for i in self.items if i.is_correct)
