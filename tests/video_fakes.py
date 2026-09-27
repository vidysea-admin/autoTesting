"""Spies and a prepared source, shared by the two analyze test files.

Split out when `test_analyze_video.py` crossed the 300-line cap: the cost tests
(does a re-run spend money?) and the behaviour tests (does it read the right
narration?) are separate responsibilities, but they need the same fake ensemble
and the same prepared recording. One definition, imported twice — duplicating
it would let the two files drift and quietly test different things.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from autotester.providers.base import Provider, ProviderError
from autotester.schema.enums import IssueCategory, Severity, SourceKind
from autotester.schema.media import MediaChunk, MediaPrep
from autotester.schema.observation import (
    ModelObservation,
    ObservedIssue,
    ObservedScreen,
    VideoObservation,
)
from autotester.schema.project import Project, Source
from autotester.store.project_store import ProjectStore


class SpyProvider(Provider):
    """Counts calls and records the prompts it was handed."""

    def __init__(self, label: str, *, fail: bool = False) -> None:
        super().__init__(model=label)
        self.id = "spy"
        self._label = label
        self.calls: list[tuple[str, str]] = []   # (video path, prompt)
        self.fail = fail

    @property
    def label(self) -> str:
        return self._label

    def available(self) -> bool:
        return True

    def see_video(self, path, prompt, schema, options=None, *,
                  prompt_file=None, fed_id=None):
        self.calls.append((str(path), prompt))
        if self.fail:
            raise ProviderError("no credentials")
        return VideoObservation(
            screens=[ObservedScreen(name="Trainers", t_start=1.0, t_end=9.0)],
            issues=[ObservedIssue(t_start=5.0, screen="Trainers",
                                  category=IssueCategory.FEATURE_GAP,
                                  title="t", what_is_wrong="w")],
            summary="a trainer tool",
        )



@pytest.fixture
def prepared(tmp_path: Path) -> tuple[ProjectStore, Source]:
    store = ProjectStore("erp", tmp_path)
    store.save_project(Project(slug="erp", name="ERP", base_url="https://demo.test",
                               allowed_domains=["demo.test"]))
    video = tmp_path / "erp1.mp4"
    video.write_bytes(b"fake")
    source = store.add_source(Source(project="erp", kind=SourceKind.VIDEO,
                                     path=str(video), sha256="d", label="erp1.mp4"))
    store.save_media_prep(MediaPrep(source_id=source.id, duration_s=400.0, chunks=[
        MediaChunk(index=0, path=str(video), offset_s=0.0, length_s=180.0),
        MediaChunk(index=1, path=str(video), offset_s=165.0, length_s=180.0),
    ]))
    return store, source


PRO = "gemini:gemini-3.1-pro-preview"
FLASH = "gemini:gemini-3.8-flash"


def obs(label: str, *, chunk: int = 0, offset: float = 0.0,
        screens: list[ObservedScreen] | None = None,
        issues: list[ObservedIssue] | None = None,
        prompt: str = "video_issues_v1",
        summary: str = "") -> ModelObservation:
    """One cached answer.

    `prompt` is a parameter because it did not used to be: every fixture in
    this file hardcoded one prompt name, the sort key omitted `prompt_name`,
    and so the ONE tie the production shape actually produces — a model's two
    prompts on one chunk — was the one shape no test could construct."""
    return ModelObservation(
        source_id="src_1", provider_label=label, prompt_name=prompt,
        chunk_index=chunk, offset_s=offset, length_s=180.0,
        observation=VideoObservation(screens=screens or [], issues=issues or [],
                                     summary=summary),
    )


def screen(name: str, t_start: float, t_end: float | None = None, **kw) -> ObservedScreen:
    return ObservedScreen(name=name, t_start=t_start, t_end=t_end, **kw)


def issue(screen_name: str, t_start: float, *, category: IssueCategory = IssueCategory.OTHER,
          severity: Severity = Severity.S2, **kw) -> ObservedIssue:
    return ObservedIssue(screen=screen_name, t_start=t_start, category=category,
                         severity=severity, title=kw.pop("title", "t"),
                         what_is_wrong=kw.pop("what_is_wrong", "w"), **kw)
