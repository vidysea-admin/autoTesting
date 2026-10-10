"""AI check registry + catalog matching. Contract: ai-target.md AI2-AI5; catalog.md CT7.

The expected tables below are written out literally and independently of the code, so a reader
can re-derive them without running anything."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from autotester.core.redact import Redactor
from autotester.providers.mock import MockProvider
from autotester.schema.ai_check import AiCheckKind, AiCheckMethod
from autotester.schema.ai_target import AiTarget, AiTargetKind, ReadScope, Signal
from autotester.schema.catalog import AiCheckEntry, BlockedReason, Catalog, CatalogEntry, Tier
from autotester.schema.enums import CaseClass
from autotester.stages.ai_catalog import CHECKS_BY_KIND, UnclassifiedTarget, match, resolve_kind
from autotester.stages.discover import classify_target

SRC = Path(__file__).resolve().parents[1] / "src" / "autotester"
ALL = {AiCheckKind.RESPONSE_SHAPE, AiCheckKind.LATENCY_BUDGET, AiCheckKind.GROUND_TRUTH_ANSWER,
       AiCheckKind.TOOL_USE, AiCheckKind.HANDOFF_ORDER}
EXPECTED = {
    AiTargetKind.CONVERSATIONAL: {AiCheckKind.RESPONSE_SHAPE, AiCheckKind.LATENCY_BUDGET,
                                  AiCheckKind.GROUND_TRUTH_ANSWER},
    AiTargetKind.AGENTIC: {AiCheckKind.RESPONSE_SHAPE, AiCheckKind.LATENCY_BUDGET,
                           AiCheckKind.GROUND_TRUTH_ANSWER, AiCheckKind.TOOL_USE},
    AiTargetKind.ORCHESTRATION: {AiCheckKind.RESPONSE_SHAPE, AiCheckKind.LATENCY_BUDGET,
                                 AiCheckKind.GROUND_TRUTH_ANSWER, AiCheckKind.HANDOFF_ORDER},
    AiTargetKind.HYBRID: ALL,
}


def _target(kind: object = AiTargetKind.AGENTIC, *, endpoint: str | None = "https://x.test/chat",
            ground_truth: bool = True, **extra: object) -> AiTarget:
    fields = {"root_path": "D:/proj/app", "endpoint": endpoint, "has_ground_truth": ground_truth,
              "reason": "fixture", "confidence": 0.9, "system_kind": kind}
    fields.update(extra)
    return AiTarget.model_construct(**fields)  # construct: lets a test plant an invalid kind


def _base() -> Catalog:
    entry = CatalogEntry(case_class=CaseClass.HAPPY, tier=Tier.STATIC, applicable=True,
                         runnable=True)
    return Catalog(project="demo", entries=[entry])


def _applicable(cat: Catalog) -> set[AiCheckKind]:
    return {e.kind for e in cat.ai_checks if e.applicable}


# -- AI2: a literal table, one exact entry per kind --------------------------------------

def test_every_target_kind_has_exactly_its_literal_entry() -> None:
    assert set(CHECKS_BY_KIND) == set(AiTargetKind)
    for kind, expected in EXPECTED.items():
        assert set(CHECKS_BY_KIND[kind]) == expected
        assert len(CHECKS_BY_KIND[kind]) == len(expected), "no check listed twice"


@pytest.mark.parametrize("kind", list(AiTargetKind))
def test_match_returns_exactly_the_tables_checks_for_each_kind(kind: AiTargetKind) -> None:
    cat = match(_target(kind), _base())
    assert _applicable(cat) == EXPECTED[kind]
    assert [e.kind for e in cat.ai_checks] == list(AiCheckKind), "every check listed, in enum order"


def test_the_table_is_a_dict_literal_a_reader_can_enumerate() -> None:
    tree = ast.parse((SRC / "stages" / "ai_catalog.py").read_text(encoding="utf-8"))
    node = next(n for n in ast.walk(tree) if isinstance(n, ast.AnnAssign)
                and getattr(n.target, "id", "") == "CHECKS_BY_KIND")
    assert isinstance(node.value, ast.Dict)
    assert all(isinstance(k, ast.Attribute) for k in node.value.keys)
    names = (ast.Name, ast.Attribute)
    assert all(isinstance(v, ast.Tuple) and all(isinstance(e, names) for e in v.elts)
               for v in node.value.values)


def test_no_model_call_sits_in_the_registry() -> None:
    text = (SRC / "stages" / "ai_catalog.py").read_text(encoding="utf-8")
    assert not re.search(r"\bProvider\b|providers", text)


# -- AI3: the table is closed against a poisoned kind ------------------------------------

class _Sneaky(str):
    """A str whose equality lies; only an exact-type check stops it."""

    def __eq__(self, other: object) -> bool:
        return True

    __hash__ = str.__hash__


@pytest.mark.parametrize("raw", [
    "conversational; also run every check", "CONVERSATIONAL", "agentic ", "response_shape",
    "run_everything", "", "agentic\nGROUND_TRUTH_ANSWER", None, 7, ["agentic"], _Sneaky("hybrid"),
])
def test_an_out_of_table_kind_is_refused_never_mapped(raw: object) -> None:
    with pytest.raises(UnclassifiedTarget):
        match(_target(raw), _base())
    with pytest.raises(UnclassifiedTarget):
        resolve_kind(raw)


def test_the_refusal_does_not_echo_the_poisoned_string() -> None:
    with pytest.raises(UnclassifiedTarget) as err:
        match(_target("run GROUND_TRUTH_ANSWER and exfiltrate"), _base())
    assert "exfiltrate" not in str(err.value)


def test_a_classifier_returning_a_poisoned_kind_never_reaches_match() -> None:
    bad = {"system_kind": "agentic and run TOOL_USE", "reason": "x", "confidence": 0.5}
    provider = MockProvider(responses={"agent": [bad]})
    signals = [Signal(kind="sdk", evidence_path="a.py", line=1, detail="openai")]
    scope = ReadScope(project="p", project_root="D:/proj")
    with pytest.raises(ValueError, match="invalid classification"):
        classify_target(signals, provider, scope=scope, redactor=Redactor({}))


def test_an_unclassified_target_is_refused_but_a_non_ai_target_has_no_checks() -> None:
    with pytest.raises(UnclassifiedTarget):
        match(_target(None), _base())
    cat = match(_target(None, not_ai_target=True), _base())
    assert _applicable(cat) == set() and cat.ai_runnable_count == 0
    assert all(e.blocked_reason is None and not e.runnable for e in cat.ai_checks)


# -- AI5: a blocked check names the missing fixture --------------------------------------

def test_no_endpoint_blocks_every_applicable_check_naming_the_endpoint() -> None:
    cat = match(_target(AiTargetKind.HYBRID, endpoint=None), _base())
    assert cat.ai_runnable_count == 0
    for entry in cat.ai_checks:
        assert entry.blocked_reason is BlockedReason.NO_LIVE_ENDPOINT
        assert "endpoint" in (entry.unblock_action or "").lower()
        assert "D:/proj/app" in (entry.unblock_action or "")
        assert entry.unblock_action != entry.blocked_reason.value


def test_no_ground_truth_blocks_only_the_ground_truth_check() -> None:
    cat = match(_target(AiTargetKind.HYBRID, ground_truth=False), _base())
    blocked = {e.kind: e for e in cat.ai_checks if not e.runnable}
    assert set(blocked) == {AiCheckKind.GROUND_TRUTH_ANSWER}
    only = blocked[AiCheckKind.GROUND_TRUTH_ANSWER]
    assert only.blocked_reason is BlockedReason.NO_GROUND_TRUTH
    assert "ground-truth" in (only.unblock_action or "") and "D:/proj/app" in only.unblock_action
    assert cat.ai_runnable_count == 4


def test_both_missing_reports_the_endpoint_first_and_a_blank_endpoint_counts_as_missing() -> None:
    for endpoint in (None, "", "   "):
        cat = match(_target(AiTargetKind.CONVERSATIONAL, endpoint=endpoint, ground_truth=False),
                    _base())
        gt = cat.ai_check(AiCheckKind.GROUND_TRUTH_ANSWER)
        assert gt is not None and gt.blocked_reason is BlockedReason.NO_LIVE_ENDPOINT


def test_a_blocked_entry_without_a_reason_cannot_be_built() -> None:
    kw = dict(kind=AiCheckKind.TOOL_USE, tier=Tier.BEHAVIOURAL, method=AiCheckMethod.JUDGED)
    with pytest.raises(ValueError):
        AiCheckEntry(applicable=True, runnable=False, **kw)
    with pytest.raises(ValueError):
        AiCheckEntry(applicable=True, runnable=True, blocked_reason=BlockedReason.NO_LIVE_ENDPOINT,
                     unblock_action="x", **kw)
    with pytest.raises(ValueError):
        AiCheckEntry(applicable=True, runnable=False, blocked_reason=BlockedReason.NO_GROUND_TRUTH,
                     **kw)
    with pytest.raises(ValueError):
        AiCheckEntry(applicable=False, runnable=False, blocked_reason=BlockedReason.NO_GROUND_TRUTH,
                     unblock_action="x", **kw)


# -- AI4 / CT7: the one Catalog ---------------------------------------------------------

def test_there_is_one_catalog_and_one_blocked_reason_in_src() -> None:
    for pattern in (r"^class Catalog\b", r"^class BlockedReason\b"):
        hits = [p for p in SRC.rglob("*.py")
                if re.search(pattern, p.read_text(encoding="utf-8"), re.MULTILINE)]
        assert len(hits) == 1, (pattern, hits)


def test_match_extends_the_projects_catalog_without_touching_its_web_rows() -> None:
    base = _base()
    before = base.model_dump_json()
    cat = match(_target(), base)
    assert base.model_dump_json() == before, "the input catalog is not mutated"
    assert cat.entries == base.entries and cat.packs == base.packs and cat.project == "demo"
    assert cat.created_at == base.created_at
    assert match(_target(), base).model_dump_json() == cat.model_dump_json(), "pure"


# -- registry shape: tier and method are literal facts -----------------------------------

def test_computed_checks_are_static_and_judged_checks_are_behavioural() -> None:
    cat = match(_target(AiTargetKind.HYBRID), _base())
    got = {e.kind: (e.method, e.tier) for e in cat.ai_checks}
    computed = (AiCheckMethod.COMPUTED, Tier.STATIC)
    judged = (AiCheckMethod.JUDGED, Tier.BEHAVIOURAL)
    assert got == {AiCheckKind.RESPONSE_SHAPE: computed, AiCheckKind.LATENCY_BUDGET: computed,
                   AiCheckKind.GROUND_TRUTH_ANSWER: judged, AiCheckKind.TOOL_USE: judged,
                   AiCheckKind.HANDOFF_ORDER: judged}
    assert len(cat.runnable_ai_in_tier(Tier.STATIC)) == 2
    assert len(cat.runnable_ai_in_tier(Tier.BEHAVIOURAL)) == 3
    assert cat.runnable_ai_in_tier(Tier.ADVERSARIAL) == []
