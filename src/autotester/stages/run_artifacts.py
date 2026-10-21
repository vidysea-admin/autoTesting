"""Assemble post-run failure evidence and validate links without changing functional records."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from autotester.browser.secrets import SecretStore
from autotester.core.image_privacy import sanitized_images
from autotester.core.trace import TraceParseError, read_spans
from autotester.schema.enums import EvidenceKind, Result
from autotester.schema.failure_bundle import BundleAssembly, BundleIndex, BundleSource
from autotester.schema.run import Run
from autotester.stages.failure_bundle import build_failure_bundle, load_bundle
from autotester.store.filestore import read_json, write_json
from autotester.store.project_store import ProjectStore

_LOG = logging.getLogger(__name__)


def _inside(path: Path, root: Path) -> Path:
    """Resolve before every evidence read; symlinks cannot import another run's bytes."""
    resolved = path.resolve()
    if resolved != path.absolute() or not resolved.is_relative_to(root.resolve()):
        raise ValueError("artifact_outside_run")
    return resolved


def _assemble_case(store, run, case, result, verdict, redactor,
                   mask_limit: float | None = None) -> BundleAssembly:
    run_dir = store.paths.run_dir(run.id)
    shots = [e for e in result.evidence if e.kind is EvidenceKind.SCREENSHOT]
    sources, included, reasons = [], 0, []
    text_unavailable = False
    # One context per image preserves its step identity even when an earlier image is withheld.
    from contextlib import ExitStack

    with ExitStack() as stack:
        for shot in shots:
            try:
                original = _inside(run_dir / shot.path, run_dir)
            except ValueError:
                reasons.append("artifact_outside_run")
                continue
            if not shot.masked or shot.step_order is None:
                reasons.append("unmasked_or_unattributed_image")
                continue
            safe = stack.enter_context(sanitized_images([original], mask_limit=mask_limit))
            reasons.extend(safe.reasons)
            text_unavailable = text_unavailable or safe.text_unavailable
            if safe.paths:
                sources.append(BundleSource(run_id=run.id, path=safe.paths[0],
                                            step_order=shot.step_order, masked=True))
        spans = read_spans(_inside(store.paths.run_trace(run.id), run_dir))
        spans = [s for s in spans if not hasattr(s, "fed_id") or s.fed_id == case.id]
        for existing in store.paths.bundles_dir(run.id).glob("*"):
            _inside(existing, run_dir)
        bundle = build_failure_bundle(out_dir=store.paths.bundles_dir(run.id), run_id=run.id,
                                      case=case, result=result, verdict=verdict, sources=sources,
                                      spans=spans, redactor=redactor)
        manifest = load_bundle(bundle)
        included = sum(f.kind.value == "screenshot" for f in manifest.files)
    missing = included < len(shots)
    return BundleAssembly(case_id=case.id, bundle_id=bundle.name, status="complete",
                          images_requested=len(shots), images_included=included,
                          images_withheld=len(shots) - included, image_reasons=reasons,
                          image_text_unavailable=text_unavailable or missing,
                          diagnostic=("image_text_unavailable"
                                      if text_unavailable or missing else None))


def assemble_run_bundles(store: ProjectStore, run: Run) -> None:
    """Best effort after durable results/verdicts; even a storage failure cannot lose the run."""
    try:
        run_dir = _inside(store.paths.run_dir(run.id), store.paths.dir)
        _inside(store.paths.bundles_dir(run.id), run_dir)
        project = store.load_project()
        if project is None:
            raise ValueError("project_unavailable")
        redactor = SecretStore.load(project, store.paths.env_file, strict=False).redactor()
        cases = {c.id: c for c in store.list_cases() if c.project == run.project}
        results = {r.case_id: r for r in store.load_results(run.id)}
        index = BundleIndex(run_id=run.id)
        for verdict in store.load_verdicts(run.id):
            if verdict.result not in (Result.FAIL, Result.INCONCLUSIVE, Result.BLOCKED):
                continue
            try:
                if verdict.case_id not in run.case_ids:
                    raise ValueError("case_outside_run")
                entry = _assemble_case(store, run, cases[verdict.case_id],
                                       results[verdict.case_id], verdict, redactor,
                                       project.image_mask_limit)
            except Exception as exc:
                # AT-1304 C3: a corrupt trace line says which file and line; never its content.
                reason = str(exc) if isinstance(exc, TraceParseError) else None
                _LOG.warning("failure_bundle_assembly_failed %s", reason or type(exc).__name__)
                entry = BundleAssembly(case_id=verdict.case_id, status="unavailable",
                                       diagnostic="assembly_failed", reason=reason)
            index.cases.append(entry)
        write_json(_inside(store.paths.bundles_dir(run.id) / "index.json", run_dir), index)
    except Exception:
        _LOG.warning("failure_bundle_index_unavailable")  # fixed diagnostic, never exception text


def bundle_report_detail(store: ProjectStore, run_id: str, case_id: str,
                         relative_to: Path | None = None) -> tuple[str | None, str]:
    """Only a complete, hash-validated, same-case/run bundle gets a report link."""
    try:
        run_dir = _inside(store.paths.run_dir(run_id), store.paths.dir)
        index_path = _inside(store.paths.bundles_dir(run_id) / "index.json", run_dir)
        index = read_json(index_path, BundleIndex)
        if index is None:
            return None, "Failure bundle not recorded"
        if index.run_id != run_id:
            raise ValueError("wrong_run_index")
        entry = next(e for e in index.cases if e.case_id == case_id)
        if entry.status != "complete" or entry.bundle_id is None:
            raise ValueError("bundle_unavailable")
        bundle = _inside(store.paths.bundles_dir(run_id) / entry.bundle_id, run_dir)
        manifest = load_bundle(bundle)
        if (manifest.run_id, manifest.case_id, manifest.bundle_id) != (
                run_id, case_id, entry.bundle_id):
            raise ValueError("wrong_bundle_lineage")
        href = Path(os.path.relpath(bundle / "manifest.json", relative_to or run_dir)).as_posix()
        note = ("Failure bundle; image/text evidence unavailable"
                if entry.image_text_unavailable else "Failure bundle")
        return href, note
    except Exception:
        return None, "Failure bundle unavailable"
