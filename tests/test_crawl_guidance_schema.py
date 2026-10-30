"""crawl-guidance Unit 1 (qa/contracts/crawl-guidance.md G5, G7, G8, G11): schema only.

Every new field is additive: a default that reproduces today's serialized form, `extra="forbid"`
everywhere, an old approval row still verifies, an old `crawl.json` still loads.
"""

from __future__ import annotations

import re
from pathlib import Path

import crawl_guidance_support as support
import pytest
from pydantic import ValidationError

from autotester.schema.approval import RunApproval
from autotester.schema.crawl import Crawl, CrawlBounds
from autotester.schema.crawl_guidance import (
    CrawlGuidance,
    GuidanceAnnotation,
    GuidanceFallback,
    GuidanceOptIn,
    NextActionRanking,
)
from autotester.schema.portal_persona import GraphNode, KnowledgeGraph, PortalPersona
from autotester.schema.project import Project
from autotester.schema.screen_graph import ScreenNode
from autotester.store.filestore import read_json, write_json


def test_default_bounds_serialise_exactly_as_before() -> None:
    """G5: a default CrawlBounds on disk has none of the three new keys (None is omitted)."""
    dumped = CrawlBounds().model_dump(exclude_none=True)
    assert not {"max_model_calls", "model_call_timeout_s", "model_total_s"} & dumped.keys()


def test_new_bounds_default_to_off_and_reject_negatives() -> None:
    bounds = CrawlBounds()
    assert not bounds.max_model_calls and not bounds.model_call_timeout_s
    assert not bounds.model_total_s
    with pytest.raises(ValidationError):
        CrawlBounds(max_model_calls=-1)
    with pytest.raises(ValidationError):
        CrawlBounds(model_total_s=-0.5)


def test_a_pre_change_signed_approval_row_still_verifies() -> None:
    """G5/AT-110: the signature binds actions and wall clock, never the new model bounds."""
    row = (support.BASELINE_DIR / "pre_change_approval.jsonl").read_text(encoding="utf-8")
    approval = RunApproval.model_validate_json(row)
    assert approval.is_signed_and_verified


def test_an_old_crawl_json_still_loads_and_has_no_guidance() -> None:
    text = support.baseline("crawl.json").replace("\r\n", "\n")
    text = re.sub(r'"created_at":"T"', '"created_at": "2026-10-29T05:05:03.445295Z"', text)
    crawl = Crawl.model_validate_json(text)
    assert crawl.guidance is None and crawl.provider is None
    assert "guidance" not in crawl.model_dump(exclude_none=True)


def test_old_project_and_persona_json_load_without_the_new_fields(tmp_path: Path) -> None:
    project = Project(slug="demo", name="Demo", base_url="https://app.test/")
    assert project.crawl_guidance is None
    assert "crawl_guidance" not in project.model_dump(exclude_none=True)
    persona = PortalPersona(project="demo")
    persona.graph.add_node(GraphNode.make("screen", "node_1", "Home"))
    path = tmp_path / "persona.json"
    write_json(path, persona)
    assert '"guidance"' not in path.read_text(encoding="utf-8")


def test_a_screen_node_carries_annotations_only_when_set() -> None:
    """D-119: the crawl's own node holds the ranking; unset it serialises exactly as before."""
    node = support.screen("node_1")
    assert node.guidance is None and "guidance" not in node.model_dump(exclude_none=True)
    note = GuidanceAnnotation(candidate_hash="h", prompt_version="1:x", model="m", ranking=[1, 0])
    node.guidance = [note]
    loaded = ScreenNode.model_validate_json(node.model_dump_json(exclude_none=True))
    assert loaded.guidance == [note]


def test_extra_forbid_holds_on_every_new_model() -> None:
    bad = {"unknown": 1}
    for model, good in [
        (GuidanceOptIn, {}), (NextActionRanking, {"ranked": [0]}),
        (GuidanceFallback, {"reason": "x"}), (CrawlGuidance, {"mode": "guided"}),
        (GuidanceAnnotation, {"candidate_hash": "h", "prompt_version": "1", "model": "m",
                              "ranking": [0]}),
    ]:
        model(**good)
        with pytest.raises(ValidationError):
            model(**good, **bad)
    with pytest.raises(ValidationError):
        GraphNode(id="screen:a", kind="screen", surprise=True)  # type: ignore[call-arg]


def test_annotation_survives_a_persona_round_trip(tmp_path: Path) -> None:
    """G7: the home is `PortalPersona.graph`; it round-trips and stays marked `source: model`."""
    note = GuidanceAnnotation(candidate_hash="abc", prompt_version="1:ff", model="m:1017",
                              ranking=[2, 0, 1], reason="prefer nav")
    node = GraphNode.make("screen", "node_9", "Home")
    node.guidance = [note]
    persona = PortalPersona(project="demo", graph=KnowledgeGraph(nodes=[node]))
    path = tmp_path / "portal_persona.json"
    write_json(path, persona)
    loaded = read_json(path, PortalPersona)
    assert loaded is not None
    stored = loaded.graph.node("screen:node_9")
    assert stored is not None and stored.guidance == [note]
    assert stored.guidance[0].source == "model"


def test_ranking_reason_is_capped_not_rejected() -> None:
    ranking = NextActionRanking(ranked=[1, 0], reason="x" * 5000)
    assert len(ranking.reason) == 200


def test_project_opt_in_is_off_unless_set() -> None:
    off = Project(slug="demo", name="D", base_url="https://app.test/")
    assert off.crawl_guidance is None
    on = Project(slug="demo", name="D", base_url="https://app.test/",
                 crawl_guidance=GuidanceOptIn(enabled=True))
    assert on.crawl_guidance is not None and on.crawl_guidance.enabled
    assert GuidanceOptIn().enabled is False
