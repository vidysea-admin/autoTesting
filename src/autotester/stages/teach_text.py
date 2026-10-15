"""Turn guarded extracted teaching sections into a locator-cited DRAFT proposal."""

from __future__ import annotations

import json

from autotester.core.ids import content_id
from autotester.core.paths import RepoDocs
from autotester.core.redact import Redactor, mask_pii_obj
from autotester.providers.base import Provider
from autotester.schema.base import Provenance
from autotester.schema.enums import SourceKind
from autotester.schema.flowspec import Flow, FlowSpec, Screen, SourceRef, Step
from autotester.schema.project import Source
from autotester.schema.teaching import TeachingUnit, TextObservation
from autotester.stages.ingest import project_redactor

PROMPT_FILE = "teach_text_v1.md"


class InvalidTextTeaching(ValueError):
    """The evidence or model reading cannot support a provenance-safe proposal."""


def _guard_teaching_payload(payload: object, redactor: Redactor) -> object:
    cleaned = mask_pii_obj(redactor.scrub_obj(payload))
    redactor.assert_clean(json.dumps(cleaned, ensure_ascii=False))
    return cleaned


def _validate_text_reading(reading: TextObservation, units: list[TeachingUnit]) -> None:
    locators = {unit.locator for unit in units}
    names = {screen.name for screen in reading.screens}
    if len(names) != len(reading.screens):
        raise InvalidTextTeaching("duplicate screen names")
    if any(screen.locator not in locators for screen in reading.screens):
        raise InvalidTextTeaching("screen cites an unknown teaching locator")
    for flow in reading.flows:
        if flow.entry_screen not in names or (flow.exit_screen and flow.exit_screen not in names):
            raise InvalidTextTeaching("flow cites an unknown screen")
        orders = [step.order for step in flow.steps]
        if orders != sorted(set(orders)):
            raise InvalidTextTeaching("flow step orders must be distinct and increasing")
        if any(step.locator not in locators or step.screen not in names for step in flow.steps):
            raise InvalidTextTeaching("step cites an unknown teaching locator or screen")


def _text_proposal(reading: TextObservation, source: Source, project_slug: str) -> FlowSpec:
    screens = [Screen(
        id=content_id("screen", {"name": s.name, "signals": s.signals}), name=s.name,
        url_pattern=s.url_pattern, signals=s.signals, fields=s.fields,
        source_ref=SourceRef(source_id=source.id, locator=s.locator)) for s in reading.screens]
    ids = {screen.name: screen.id for screen in screens}
    flows = []
    for flow in reading.flows:
        steps = [Step(order=s.order, action=s.action, target=s.target, value=s.value,
                      expected=s.expected, screen_id=ids[s.screen],
                      source_ref=SourceRef(source_id=source.id, locator=s.locator))
                 for s in flow.steps]
        flows.append(Flow(
            id=content_id("flow", {"source": source.id, "flow": flow.model_dump(mode="json")}),
            name=flow.name, entry_screen=ids[flow.entry_screen],
            exit_screen=ids[flow.exit_screen] if flow.exit_screen else None, steps=steps))
    return FlowSpec(project=project_slug, screens=screens, flows=flows, source_ids=[source.id],
                    app_overview=reading.summary,
                    provenance=Provenance(produced_by="teach_text", inputs=[source.id]))


def teach_text(
    source: Source, project_slug: str, provider: Provider, *, units: list[TeachingUnit],
    redactor: Redactor | None = None, docs: RepoDocs | None = None,
) -> FlowSpec:
    """Propose text knowledge through Provider.act; never persist or approve truth.

    Units must come from registered extracted content, not file/folder metadata.
    The caller retains extraction errors and chooses the configured text-role provider.
    This stage validates citation membership and references, not semantic truth.
    """
    if source.project != project_slug or source.kind is SourceKind.VIDEO:
        raise InvalidTextTeaching("text teaching requires a same-project non-video source")
    if not units or len(units) > 500 or sum(len(u.text) for u in units) > 500_000:
        raise InvalidTextTeaching("teaching requires 1..500 units within 500000 characters")
    if len({u.locator for u in units}) != len(units):
        raise InvalidTextTeaching("teaching locators must be unique")
    redactor = redactor if redactor is not None else project_redactor(project_slug)
    cleaned = _guard_teaching_payload([u.model_dump() for u in units], redactor)
    template = ((docs or RepoDocs()).prompts_dir / PROMPT_FILE).read_text(encoding="utf-8")
    prompt = template.replace("{{UNITS}}", json.dumps(cleaned, ensure_ascii=False))
    redactor.assert_clean(prompt)
    raw = provider.act(prompt, TextObservation, prompt_file=PROMPT_FILE, fed_id=source.id)
    reading = TextObservation.model_validate(raw)
    cleaned_reading = _guard_teaching_payload(reading.model_dump(), redactor)
    reading = TextObservation.model_validate(cleaned_reading)
    _validate_text_reading(reading, units)
    return _text_proposal(reading, source, project_slug)

