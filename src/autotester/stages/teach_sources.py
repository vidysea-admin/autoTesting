"""Teach every registered source through one snapshotted, resumable proposal stage."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from autotester.browser.secrets import SecretStore
from autotester.core.ids import content_id
from autotester.core.paths import RepoDocs
from autotester.core.redact import Redactor, mask_pii_obj
from autotester.providers.base import Provider
from autotester.schema.base import Provenance
from autotester.schema.enums import SourceKind
from autotester.schema.flowspec import FlowSpec
from autotester.schema.project import Source
from autotester.schema.teaching_run import (
    TeachingMaterial,
    TeachingOutcome,
    TeachingResult,
    TeachingSnapshot,
)
from autotester.stages.ingest import build_ingest_prompt, ingest_video
from autotester.stages.merge_flowspec import merge_flowspec
from autotester.stages.reconcile import assign_kinds
from autotester.stages.source_material import DECLARED_KINDS, resolve_teaching_material
from autotester.stages.teach_text import teach_text
from autotester.store.filestore import read_json, write_json
from autotester.store.project_store import ProjectStore


class TeachingInputsChanged(RuntimeError):
    """A run cannot silently teach a different registered input set on resume."""


def _guarded_artifact(model, redactor: Redactor):
    payload = mask_pii_obj(redactor.scrub_obj(model.model_dump(mode="json")))
    guarded = type(model).model_validate(payload)
    redactor.assert_clean(guarded.model_dump_json())
    return guarded


def freeze_teaching_inputs(
    store: ProjectStore, run_id: str, sources: list[Source], redactor: Redactor
) -> tuple[TeachingSnapshot, list[TeachingMaterial]]:
    """Resolve and bind all current evidence before a provider is created or called."""
    ordered = sorted(sources, key=lambda source: source.id)
    materials = [resolve_teaching_material(store, source, ordered) for source in ordered]
    snapshot = TeachingSnapshot(
        project=store.paths.slug,
        run_id=run_id,
        inputs=[material.identity for material in materials],
    )
    path = store.paths.run_dir(run_id) / "teaching-inputs.json"
    previous = read_json(path, TeachingSnapshot)
    if previous is not None and (
        previous.project != snapshot.project
        or previous.run_id != run_id
        or previous.fingerprint != snapshot.fingerprint
    ):
        raise TeachingInputsChanged("Teaching inputs changed; start a new run instead of resuming")
    if previous is None:
        write_json(path, _guarded_artifact(snapshot, redactor))
    return previous or snapshot, materials


def _teach_material(
    store: ProjectStore,
    source: Source,
    material: TeachingMaterial,
    provider: Provider,
    redactor: Redactor,
    docs: RepoDocs,
) -> FlowSpec:
    if source.kind is not SourceKind.VIDEO:
        return teach_text(
            source, store.paths.slug, provider, units=material.units, redactor=redactor, docs=docs
        )
    transcript = (
        _guarded_artifact(material.transcript, redactor)
        if material.transcript is not None
        else None
    )
    safe_source = source.model_copy(
        update={"label": mask_pii_obj(redactor.scrub(source.label or ""))}
    )
    redactor.assert_clean(build_ingest_prompt(safe_source, docs, transcript))
    return ingest_video(
        safe_source, store.paths.slug, provider, docs, transcript=transcript, redactor=redactor
    )


def _source_outcome(
    store: ProjectStore,
    source: Source,
    material: TeachingMaterial,
    provider_for: Callable[[SourceKind], Provider],
    redactor: Redactor,
    docs: RepoDocs,
    trace,
) -> TeachingOutcome:
    outcome = TeachingOutcome(
        source_id=source.id,
        input_fingerprint=material.identity.fingerprint,
        status="failed",
        problems=material.problems,
        document=material.document,
    )
    if material.unavailable:
        return outcome
    if source.kind in DECLARED_KINDS:
        return outcome.model_copy(update={"status": "declared"})
    if material.children and not material.problems:
        return outcome.model_copy(update={"status": "container"})
    if not material.units and source.kind is not SourceKind.VIDEO:
        return outcome.model_copy(
            update={"problems": material.problems or ["no extracted content"]}
        )
    try:
        provider = provider_for(source.kind)
        provider.trace = trace
        outcome.provenance = Provenance(
            produced_by="teach_sources", inputs=[source.id], note=f"provider: {provider.label}"
        )
        proposal = _teach_material(store, source, material, provider, redactor, docs)
        proposal = _guarded_artifact(proposal, redactor)
        return outcome.model_copy(
            update={"status": "partial" if material.problems else "learned", "proposal": proposal}
        )
    except Exception as exc:
        return outcome.model_copy(
            update={"problems": [*material.problems, f"teaching failed ({type(exc).__name__})"]}
        )


def _cached_outcome(path: Path, material: TeachingMaterial) -> TeachingOutcome | None:
    cached = read_json(path, TeachingOutcome)
    if cached is not None and (
        cached.source_id != material.identity.source_id
        or cached.input_fingerprint != material.identity.fingerprint
    ):
        raise TeachingInputsChanged(
            "Teaching receipt does not match the frozen input; start a new run"
        )
    if (
        cached is not None
        and cached.status in {"learned", "partial"}
        and (
            cached.proposal is None or material.identity.source_id not in cached.proposal.source_ids
        )
    ):
        raise TeachingInputsChanged("Teaching receipt has no matching proposal; start a new run")
    if cached is not None and cached.status == "running":
        return cached.model_copy(
            update={
                "status": "failed",
                "problems": [
                    "interrupted teaching; provider outcome unknown, start a new run to retry"
                ],
            }
        )
    return cached


def _aggregate_teaching(
    store: ProjectStore,
    run_id: str,
    snapshot: TeachingSnapshot,
    outcomes: list[TeachingOutcome],
    redactor: Redactor,
) -> TeachingResult:
    path = store.paths.run_dir(run_id) / "teaching.json"
    previous = read_json(path, TeachingResult)
    if (
        previous is not None
        and previous.snapshot_fingerprint == snapshot.fingerprint
        and previous.outcomes == outcomes
    ):
        return previous
    proposal = FlowSpec(project=store.paths.slug)
    for outcome in outcomes:
        if outcome.proposal is not None:
            proposal = merge_flowspec(proposal, outcome.proposal, source_id=outcome.source_id)
    flows, _ = assign_kinds(proposal.flows, set())
    proposal = proposal.model_copy(update={"flows": flows})
    result = TeachingResult(
        project=store.paths.slug,
        run_id=run_id,
        snapshot_fingerprint=snapshot.fingerprint,
        outcomes=outcomes,
        proposal=proposal,
    )
    result = _guarded_artifact(result, redactor)
    write_json(store.paths.run_dir(run_id) / "teaching.json", result)
    return result


def teach_registered_sources(
    store: ProjectStore,
    run_id: str,
    provider_for: Callable[[SourceKind], Provider],
    *,
    secrets: SecretStore,
    docs: RepoDocs | None = None,
    trace=None,
) -> TeachingResult:
    """Teach all registered inputs into a run-local DRAFT; reuse completed/failed receipts.
    Interrupted calls require a new run: their uncertain provider outcomes never repeat.
    """
    sources = sorted(store.list_sources(), key=lambda source: source.id)
    redactor, docs = secrets.redactor(), docs or RepoDocs()
    snapshot, materials = freeze_teaching_inputs(store, run_id, sources, redactor)
    outcomes, seen_content = [], {}
    for source, material in zip(sources, materials, strict=True):
        key = material.identity.content_fingerprint
        path = store.paths.run_dir(run_id) / "teaching" / f"{content_id('src', source.id)}.json"
        outcome = _cached_outcome(path, material)
        if outcome is None:
            if key in seen_content:
                prior = seen_content[key]
                outcome = TeachingOutcome(
                    source_id=source.id,
                    input_fingerprint=material.identity.fingerprint,
                    status="duplicate",
                    duplicate_of=prior.source_id,
                    problems=sorted(set([*prior.problems, *material.problems])),
                )
            else:
                write_json(
                    path,
                    _guarded_artifact(
                        TeachingOutcome(
                            source_id=source.id,
                            input_fingerprint=material.identity.fingerprint,
                            status="running",
                        ),
                        redactor,
                    ),
                )
                outcome = _source_outcome(
                    store, source, material, provider_for, redactor, docs, trace
                )
        outcome = _guarded_artifact(outcome, redactor)
        write_json(path, outcome)
        outcomes.append(outcome)
        if material.units or (source.kind is SourceKind.VIDEO and not material.unavailable):
            seen_content.setdefault(key, outcome)
    return _aggregate_teaching(store, run_id, snapshot, outcomes, redactor)
