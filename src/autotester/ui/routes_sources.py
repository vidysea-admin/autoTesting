"""The operator-facing recording registry.

This is the UI door to the same content-addressed ``Source`` ledger used by
``autotester ingest register``. It never creates a second upload registry or a
UI-only representation. Planned owner: Track A5.2 in ``plan.md``.
"""

from __future__ import annotations

import shutil
from html import escape
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse

from autotester import providers
from autotester.browser.secrets import SecretStore
from autotester.core.ids import file_sha256
from autotester.core.paths import ProjectPaths, RepoDocs, work_dir
from autotester.providers.base import ProviderError
from autotester.schema.enums import ReviewStatus, SourceKind
from autotester.schema.observation import VisionOptions
from autotester.schema.project import Source
from autotester.stages.analyze_video import DuplicateProviders, NoObservations, analyze
from autotester.stages.ingest import (
    NotARecording,
    register_source,
    require_recording_suffix,
)
from autotester.stages.issues import derive_issues, sync_source_issues
from autotester.stages.media_prep import SourceNotPrepared, UnreadableRecording, require_prepared
from autotester.stages.product_map import attach_screenshots, build_screen_map
from autotester.ui import theme
from autotester.ui.helpers import (
    _load_project_or_404,
    _refuse_unsafe_submission,
    _require_safe_id,
    _reserved_temp_path,
)

router = APIRouter()


def _link(href: str, text: str) -> str:
    return f"<a class='btn' href='{escape(href)}'>{escape(text)}</a>"


def _refusal(slug: str, message: str, *, title: str = "Recording not found") -> HTMLResponse:
    body = theme.card(
        f"<p>{escape(message)}</p><p style='margin-top:14px'>"
        f"{_link(f'/projects/{slug}/sources', 'Try another path')}</p>",
        title=title,
    )
    return HTMLResponse(
        theme.page(title, body, active_slug=slug), status_code=400)


def _source_rows(store, slug: str) -> str:
    def _row(source: Source) -> str:
        reference = source.path or source.url or source.text or "—"
        action = (
            f"<form method='post' action='/projects/{escape(slug)}/sources/"
            f"{escape(source.id)}/analyze'><button type='submit'>Analyze</button></form>"
            if source.kind is SourceKind.VIDEO else "<span class='meta'>Declared</span>"
        )
        return (
        f"<tr><td><code>{escape(source.id)}</code></td>"
        f"<td>{escape(source.label or '—')}</td>"
        f"<td>{escape(source.kind.value)}</td><td><code>{escape(reference)}</code></td>"
        f"<td>{action}</td></tr>"
        )

    return "".join(_row(source) for source in store.list_sources()) or (
        "<tr><td colspan='5'>No sources registered yet.</td></tr>"
    )


def parse_intake_sources(
    slug: str, evals: str, conditions: str, use_cases: str,
    kinds: list[str], values: list[str], labels: list[str],
) -> list[Source]:
    """Turn the unified form into canonical, content-addressed Source artifacts."""
    sources: list[Source] = []
    statement_groups = (
        (SourceKind.EVAL, evals), (SourceKind.CONDITION, conditions),
        (SourceKind.USE_CASE, use_cases),
    )
    for kind, block in statement_groups:
        for statement in dict.fromkeys(line.strip() for line in block.splitlines() if line.strip()):
            sources.append(Source(project=slug, kind=kind, text=statement, label=kind.value))
    if len({len(kinds), len(values), len(labels)}) != 1:
        raise HTTPException(400, "source rows are incomplete")
    allowed = {SourceKind.VIDEO, SourceKind.DOC, SourceKind.TEXT, SourceKind.URL}
    for raw_kind, raw_value, raw_label in zip(kinds, values, labels, strict=True):
        if not any(item.strip() for item in (raw_kind, raw_value, raw_label)):
            continue
        try:
            kind = SourceKind(raw_kind)
        except ValueError as exc:
            raise HTTPException(400, "that is not an offered source type") from exc
        if kind not in allowed or not raw_value.strip():
            raise HTTPException(400, "each source needs an offered type and reference")
        value = raw_value.strip()
        payload = ({"url": value} if kind is SourceKind.URL else
                   {"text": value} if kind is SourceKind.TEXT else {"path": value})
        sources.append(Source(
            project=slug, kind=kind, label=raw_label.strip() or None, **payload,
        ))
    return sources


@router.get("/projects/{slug}/sources", response_class=HTMLResponse)
def sources_page(slug: str) -> str:
    """List registered sources and offer a server-local path registration form."""
    store, project = _load_project_or_404(slug)
    name = escape(project.name)
    crumbs = theme.breadcrumb(("Projects", "/"), (name, f"/projects/{slug}"),
                              ("Sources", None))
    rows = _source_rows(store, slug)
    form = f"""
      <form method="post" action="/projects/{escape(slug)}/sources">
        <div class="field"><label for="path">Recording path on this machine</label>
          <input id="path" name="path" required placeholder="path to the recording file">
          <span class="hint">The file stays where it is; AutoTester records its content hash.</span>
        </div>
        <div class="field"><label for="label">What this recording shows</label>
          <input id="label" name="label" placeholder="Trainer onboarding — happy path">
        </div>
        <button class="btn btn-primary" type="submit">Add recording</button>
      </form>"""
    upload = f"""
      <form method="post" enctype="multipart/form-data"
            action="/projects/{escape(slug)}/sources/upload">
        <div class="field"><label for="recording">Upload a recording</label>
          <input id="recording" type="file" name="recording" required accept="video/*">
        </div>
        <div class="field"><label for="upload-label">What this recording shows</label>
          <input id="upload-label" name="label" placeholder="Trainer onboarding — edge cases">
        </div>
        <button class="btn btn-primary" type="submit">Upload recording</button>
      </form>"""
    body = (crumbs + theme.card(form, title="Register a recording already on this host")
            + theme.card(upload, title="Upload a recording") + theme.card(
        "<table><thead><tr><th>Source</th><th>Label</th><th>Kind</th>"
        "<th>Reference</th><th></th></tr></thead>"
        f"<tbody>{rows}</tbody></table>",
        title=f"{name} recordings",
    ))
    return theme.page(f"{name} · Sources", body, active_slug=slug)


@router.post("/projects/{slug}/sources")
def add_source(slug: str, path: str = Form(""), label: str = Form("")):
    """Register a real local file through the canonical ingest-stage function."""
    store, project = _load_project_or_404(slug)
    secrets = SecretStore.load(project, ProjectPaths(slug).env_file, strict=False)
    _refuse_unsafe_submission([("recording path", path), ("label", label)], project, secrets)
    try:
        register_source(store, Path(path.strip()), label=label.strip() or None)
    except NotARecording as exc:
        return _refusal(slug, str(exc), title="Not a recording")
    except (FileNotFoundError, OSError):
        return _refusal(slug, "Recording not found")
    return RedirectResponse(f"/projects/{slug}/sources", status_code=303)


@router.post("/projects/{slug}/sources/upload")
def upload_source(slug: str, recording: Annotated[UploadFile, File()], label: str = Form("")):
    """Copy an uploaded recording into its content-addressed project directory."""
    store, project = _load_project_or_404(slug)
    secrets = SecretStore.load(project, ProjectPaths(slug).env_file, strict=False)
    _refuse_unsafe_submission([("label", label)], project, secrets)
    try:
        suffix = require_recording_suffix(recording.filename or "")
    except NotARecording as exc:
        return _refusal(slug, str(exc), title="Not a recording")
    temp = _reserved_temp_path(
        suffix,
        directory=work_dir(store.paths.root),
    )
    target: Path | None = None
    try:
        with temp.open("wb") as handle:
            shutil.copyfileobj(recording.file, handle)
        digest = file_sha256(temp)
        existing = next((source for source in store.list_sources()
                         if source.sha256 == digest), None)
        if existing is not None:
            return RedirectResponse(f"/projects/{slug}/sources", status_code=303)
        draft = Source(project=slug, kind=SourceKind.VIDEO, sha256=digest,
                       label=label.strip() or None)
        target = store.paths.source_dir(draft.id) / f"recording{suffix}"
        target.parent.mkdir(parents=True, exist_ok=True)
        temp.replace(target)
        store.add_source(draft.model_copy(update={"path": str(target.resolve())}))
    except OSError:
        if target is not None:
            target.unlink(missing_ok=True)
        return _refusal(slug, "The uploaded recording could not be stored.",
                        title="Upload failed")
    finally:
        temp.unlink(missing_ok=True)
    return RedirectResponse(f"/projects/{slug}/sources", status_code=303)


def _save_analysis_outputs(store, source, analysis) -> None:
    sync_source_issues(
        store,
        source.id,
        derive_issues(analysis, source, store.paths.slug),
        remove_missing=analysis.is_complete,
    )
    screen_map = build_screen_map(store)
    store.save_screen_map(screen_map)
    spec = store.load_flowspec()
    if spec is not None and spec.review.status is not ReviewStatus.APPROVED:
        store.save_flowspec(attach_screenshots(spec, screen_map))


@router.post("/projects/{slug}/sources/{source_id}/analyze")
def analyze_source(slug: str, source_id: str):
    """Run the configured vision provider, then refresh issues and product map."""
    store, project = _load_project_or_404(slug)
    _require_safe_id(source_id, "source_id")
    source = next((item for item in store.list_sources() if item.id == source_id), None)
    if source is None:
        raise HTTPException(404, "source not found")
    try:
        require_prepared(store, source.id)
    except SourceNotPrepared as exc:
        return _refusal(slug, str(exc), title="Prepare this recording first")
    try:
        # AT-542: the ensemble is every configured vision provider, not always
        # exactly one — `vision_ensemble()` splits the comma-separated config.
        # A provider with no credential is skipped (the ensemble degrades,
        # never dies); analyze itself refuses only when EVERY call fails.
        # AT-550: skipping it here used to be silent — `ready` alone decided
        # `expected`, so a 2-provider config missing one credential persisted
        # an analysis that read as a complete 2-model reading. `requested_
        # providers` carries the full configured ensemble through so the
        # saved artifact can show the shrink even though only `ready` is ever
        # called. An EMPTY config is a separate silent case — `vision_ensemble()`
        # substitutes `DEFAULT_VISION_PROVIDER` rather than refusing;
        # `vision_config_defaulted` records that the substitution happened.
        ensemble = [providers.get(name) for name in project.providers.vision_ensemble()]
        ready = [p for p in ensemble if p.available()]
        if not ready:
            raise ProviderError(
                "no configured vision provider has a credential — "
                f"checked: {[p.id for p in ensemble]}")
        analysis = analyze(
            store, source, ready, docs=RepoDocs(), options=VisionOptions(),
            requested_providers=[p.label for p in ensemble],
            vision_config_defaulted=project.providers.vision_ensemble_defaulted())
    except (ProviderError, SourceNotPrepared, UnreadableRecording,
            NoObservations, DuplicateProviders) as exc:
        return _refusal(slug, str(exc), title="Analysis could not finish")
    _save_analysis_outputs(store, source, analysis)
    return RedirectResponse(f"/projects/{slug}/product-map", status_code=303)
