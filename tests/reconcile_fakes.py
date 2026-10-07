"""Builders for the reconcile tests (qa/contracts/reconcile.md). Offline only:
the frozen fixture, small hand-built FlowSpecs, and a MockProvider judge."""

from __future__ import annotations

import json
from pathlib import Path

from autotester.providers.mock import MockProvider
from autotester.schema.enums import Action
from autotester.schema.flowspec import (
    Flow,
    FlowSpec,
    InputField,
    ReconcileReport,
    Screen,
    ScreenJudgement,
    SourceRef,
    Step,
)
from autotester.schema.media import Transcript, TranscriptSegment
from autotester.schema.observation import VideoObservation
from autotester.schema.screen_graph import ElementRef, ScreenNode
from autotester.stages.ingest import flow_id, flowspec_from_observation
from autotester.stages.screen_identity import structural_signature

FIXTURE = Path(__file__).parent / "fixtures" / "reconcile" / "frozen_sample.json"


def frozen() -> tuple[list[FlowSpec], list[ScreenNode], dict[str, Transcript]]:
    """The frozen sample as reconcile inputs: per-video FlowSpecs, crawl nodes, transcripts."""
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    videos = [flowspec_from_observation(VideoObservation.model_validate(s["observation"]),
                                        s["source_id"], data["project"]) for s in data["sources"]]
    for spec in videos:  # a fixed timestamp: the fixture is frozen, not "now"
        spec.created_at = spec.created_at.replace(2026, 10, 7, 0, 0, 0, 0)
    crawl = [node(n["url_template"], n["title"], [(e["role"], e["name"]) for e in n["elements"]])
             for n in data["crawl"]]
    transcripts = {s["source_id"]: Transcript(source_id=s["source_id"], segments=[
        TranscriptSegment(**seg) for seg in s["transcript"]]) for s in data["sources"]}
    return videos, crawl, transcripts


def node(route: str, title: str, names: list[tuple[str, str]]) -> ScreenNode:
    elements = [ElementRef(role=r, name=n, selector=f"s{i}") for i, (r, n) in enumerate(names)]
    return ScreenNode(crawl_id="crawl_t", project="t", url_template=route,
                      url_example=f"https://app.example.test{route}", title=title,
                      signature=structural_signature(elements), elements=elements)


def screen(sid: str, name: str, route: str | None = None, signals: tuple[str, ...] = (),
           *, source: str = "src_a", t: float = 0.0, fields: tuple[str, ...] = ()) -> Screen:
    return Screen(id=sid, name=name, url_pattern=route, signals=list(signals),
                  fields=[InputField(name=f, label=f) for f in fields],
                  source_ref=SourceRef(source_id=source, t_start=t))


def step(order: int, screen_id: str | None, source: str = "src_a", t: float | None = None, *,
         narration: str | None = None, value: str | None = None) -> Step:
    return Step(order=order, action=Action.CLICK, target=f"control {order}", value=value,
                screen_id=screen_id, narration=narration,
                source_ref=SourceRef(source_id=source, t_start=float(order) if t is None else t))


def flow(name: str, source: str, path: list[str], **step_kw: object) -> Flow:
    """A flow whose step i acts on `path[i]`; entry is path[0], exit path[-1]."""
    return Flow(id=flow_id(name, source), name=name, entry_screen=path[0], exit_screen=path[-1],
                steps=[step(i + 1, sid, source, **step_kw) for i, sid in enumerate(path)])  # type: ignore[arg-type]


def video(source: str, screens: list[Screen], flows: list[Flow]) -> FlowSpec:
    spec = FlowSpec(project="t", screens=screens, flows=flows, source_ids=[source])
    spec.created_at = spec.created_at.replace(2026, 10, 7, 0, 0, 0, 0)
    return spec


def judge_mock(*, same: bool = True, confidence: float = 0.9, n: int = 60) -> MockProvider:
    answers = [ScreenJudgement(same_screen=same, confidence=confidence, reason="r")
               for _ in range(n)]
    return MockProvider(responses={"judge": answers})


def judge_prompts(provider: MockProvider) -> list[str]:
    return [prompt for role, prompt in provider.prompts if role == "judge"]


def dumped(spec: FlowSpec, report: ReconcileReport) -> bytes:
    """The saved shape (store's own exclude_none) of both outputs, for byte comparison."""
    return (spec.model_dump_json(indent=2, exclude_none=True) + "\n"
            + report.model_dump_json(indent=2)).encode("utf-8")
