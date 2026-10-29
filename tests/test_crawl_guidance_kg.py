"""crawl-guidance Units 2-3 (qa/contracts/crawl-guidance.md G7, G8, G10): graph, pins, prompt.

Every model here is a fake: scripted answers, a spy on the redaction guard, the attempt budget it
was granted, and seconds it "took" on the crawl clock. No network, no credential, no real model.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
from crawl_guidance_support import (
    FakeProvider,
    commit,
    controls,
    guide,
    make_rt,
    reverse,
    screen,
)

from autotester.providers.base import load_skill_prompt
from autotester.schema.crawl import CrawlBounds
from autotester.stages import explore_guidance as eg

graft = eg.graft

SKILLS = Path(eg.__file__).resolve().parents[1] / "skills"


def names(items: list[Any]) -> list[str]:
    return [e.name for e in items]


# -- G7: the knowledge graph is the one home, keyed so a change misses -------------------------

def test_a_ranking_is_kept_on_the_crawl_node_and_nothing_touches_the_persona_file(
        tmp_path: Path) -> None:
    """D-119: during the crawl guidance writes only to the crawl's own node, never the persona."""
    rt, model, node = make_rt(tmp_path), FakeProvider(reverse), screen("node_7")
    guide(model).order(rt, node, controls(4))
    assert node.guidance is not None
    note = node.guidance[0]
    assert (note.source, note.model, note.ranking) == ("model", "fake-1017", [3, 2, 1, 0])
    assert note.reason == "reversed" and note.prompt_version.startswith("1:")
    assert not rt.store.paths.portal_persona.exists(), "the persona build is the only writer"
    assert not list(tmp_path.rglob("crawl_guidance*")), "the KG is the one place, no side cache"


def test_the_persona_build_grafts_the_annotation_onto_the_graph_screen_node(
        tmp_path: Path) -> None:
    rt, node = make_rt(tmp_path), screen("node_7")
    guide(FakeProvider(reverse)).order(rt, node, controls(4))
    stored = commit(rt, node).graph.node("screen:node_7")
    assert stored is not None and stored.guidance == node.guidance
    again = graft(commit(rt, node), [node]).graph.node("screen:node_7")
    assert again is not None and again.guidance == node.guidance, "grafting twice adds nothing"


def test_a_rerun_over_an_unchanged_screen_makes_zero_calls_and_the_same_order(
        tmp_path: Path) -> None:
    rt, cands, node = make_rt(tmp_path), controls(4), screen("node_7")
    first = FakeProvider(reverse)
    order1 = guide(first).order(rt, node, cands)
    commit(rt, node)
    second = FakeProvider(reverse)
    g2 = guide(second)
    order2 = g2.order(make_rt(tmp_path), screen("node_7"), cands)
    assert second.calls == 0 and g2.hits == 1 and names(order1) == names(order2)
    assert g2.crawl_fields()["provider"] == "fake-1017", "a reuse still names the model behind it"


def test_a_changed_control_misses_for_that_screen_only(tmp_path: Path) -> None:
    rt, a, b = make_rt(tmp_path), screen("a"), screen("b")
    guide(FakeProvider(reverse)).order(rt, a, controls(3))
    guide(FakeProvider(reverse)).order(rt, b, controls(3, prefix="B"))
    commit(rt, a, b)
    model = FakeProvider(reverse)
    g = guide(model)
    rt2, changed = make_rt(tmp_path), controls(3)
    changed[1].name = "Renamed"
    g.order(rt2, screen("a"), changed)
    g.order(rt2, screen("b"), controls(3, prefix="B"))
    assert model.calls == 1 and g.hits == 1


def test_a_new_prompt_version_or_a_different_model_tag_misses(tmp_path: Path) -> None:
    rt, cands, node = make_rt(tmp_path), controls(3), screen("a")
    guide(FakeProvider(reverse)).order(rt, node, cands)
    commit(rt, node)
    bumped = tmp_path / "skills"
    shutil.copytree(SKILLS / eg.SKILL, bumped / eg.SKILL)
    skill = bumped / eg.SKILL / "SKILL.md"
    skill.write_text(skill.read_text(encoding="utf-8").replace("version: 1", "version: 2"),
                     encoding="utf-8")
    newer = FakeProvider(reverse)
    guide(newer, skills_dir=bumped).order(make_rt(tmp_path), screen("a"), cands)
    assert newer.calls == 1, "a new prompt version misses"
    other = FakeProvider(reverse, model="other-model")
    guide(other, models=("other-model",)).order(make_rt(tmp_path), screen("a"), cands)
    assert other.calls == 1, "a different model tag misses"


def test_reuse_needs_no_call_budget_and_no_credentials(tmp_path: Path) -> None:
    rt, node = make_rt(tmp_path), screen("a")
    guide(FakeProvider(reverse)).order(rt, node, controls(3))
    commit(rt, node)
    off = FakeProvider(reverse, ready=False)
    spent = CrawlBounds(max_model_calls=1, model_call_timeout_s=20, model_total_s=120)
    g = guide(off)
    out = g.order(make_rt(tmp_path, bounds=spent), screen("a"), controls(3))
    assert off.calls == 0 and g.hits == 1 and names(out) == ["Open 2", "Open 1", "Open 0"]


def test_annotations_fold_newest_five_and_the_graft_adds_only_screens_with_a_ranking(
        tmp_path: Path) -> None:
    rt, node, bare = make_rt(tmp_path), screen("a"), screen("b")
    for i in range(7):
        guide(FakeProvider(reverse, model=f"m{i}"), models=(f"m{i}",)).order(rt, node, controls(3))
    persona = commit(rt, node, bare)
    kept = persona.graph.node("screen:a").guidance
    assert [a.model for a in kept] == [f"m{i}" for i in range(2, 7)]
    assert persona.graph.node("screen:b") is None, "no ranking, no graph node"


# -- G8: the pinned models and the serving label -----------------------------------------------

def test_the_pinned_chain_spec_is_byte_for_byte_and_has_no_gemini() -> None:
    assert eg.GUIDANCE_SPEC == (
        "model-chain:ollama_chat/deepseek-v4.1-flash:1017,ollama_chat/glm-5.3-flash")
    from autotester import providers
    provider_id, options = providers.parse_spec(eg.GUIDANCE_SPEC)
    chain = providers.get(provider_id, **options)
    assert chain.order() == list(eg.GUIDANCE_MODELS), "explicit list: implicit Gemini tier is OFF"
    assert "gemini" not in Path(eg.__file__).read_text(encoding="utf-8").lower().replace(
        "no gemini", "")


def test_the_crawl_records_the_tier_that_actually_served(tmp_path: Path) -> None:
    class Chain(FakeProvider):
        def act(self, prompt: str, schema: Any = None, **kw: Any) -> Any:
            out = super().act(prompt, schema, **kw)
            self._served = "litellm:ollama_chat/glm-5.3-flash"  # tier 1 failed, tier 2 answered
            return out

    g = guide(Chain(reverse), models=("ollama_chat/glm-5.3-flash",))
    g.order(make_rt(tmp_path), screen(), controls(3))
    fields = g.crawl_fields()
    assert fields["provider"] == "ollama_chat/glm-5.3-flash"
    assert fields["guidance"].models_served == ["ollama_chat/glm-5.3-flash"]
    assert fields["guidance"].calls == 1 and fields["guidance"].input_tokens == 10


# -- G10: the prompt is a versioned file --------------------------------------------------------

def test_the_ranking_prompt_is_a_skill_file_that_raises_when_missing(tmp_path: Path) -> None:
    body = load_skill_prompt(eg.SKILL)
    assert "only order" in body and "ranked" in body
    with pytest.raises(FileNotFoundError):
        load_skill_prompt(eg.SKILL, skills_dir=tmp_path)


def test_a_missing_prompt_falls_back_with_a_reason_instead_of_ordering_blind(
        tmp_path: Path) -> None:
    g, cands = guide(FakeProvider(reverse), skills_dir=tmp_path / "none"), controls(3)
    assert g.order(make_rt(tmp_path), screen(), cands) == cands
    assert any("prompt unavailable" in r for r in g.fallbacks)


def test_no_inline_prompt_literal_in_the_guidance_modules() -> None:
    for module in ("explore_guidance.py", "explore_guidance_payload.py"):
        text = (Path(eg.__file__).parent / module).read_text(encoding="utf-8")
        assert "You are" not in text and "ranked the controls" not in text
