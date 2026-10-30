"""Prepare fresh input-only acceptance roots without reading credentials or contacting a target."""

from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.parse import urlsplit

from autotester.core.paths import ProjectPaths
from autotester.core.safe_names import safe_slug
from autotester.schema.acceptance_baseline import BaselinePlan, BaselineReceipt
from autotester.schema.base import Provenance
from autotester.schema.project import Project, Source
from autotester.store.filestore import write_bytes, write_json
from autotester.store.filestore_paths import evidence_mkdir, read_bytes_path
from autotester.store.project_store import ProjectStore


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _input_bytes(input_root: Path, plan: BaselinePlan) -> list[bytes]:
    """Validate every file before creating either baseline; never accept an env file."""
    blobs = []
    for row in plan.teaching_inputs:
        relative = Path(row.path)
        path = (input_root / relative).resolve()
        if (relative.is_absolute() or ".." in relative.parts
                or not path.is_relative_to(input_root) or not relative.parts
                or any(part.lower().startswith(".env") for part in path.parts)):
            raise ValueError("teaching input must be a contained non-credential file")
        if not row.approval_ref.strip():
            raise ValueError("teaching input needs an explicit owner approval reference")
        extensions = ({".mp4", ".webm", ".mov", ".mkv"} if row.kind == "video"
                      else {".pdf", ".docx", ".md", ".txt"})
        if path.suffix.lower() not in extensions:
            raise ValueError("teaching input must be a supported video or document file")
        blob = path.read_bytes()
        if _digest(blob) != row.sha256:
            raise ValueError("teaching input changed since the plan was prepared")
        blobs.append(blob)
    if {row.kind for row in plan.teaching_inputs} != {"video", "doc"}:
        raise ValueError("rich teaching baseline needs approved video and document inputs")
    return blobs


def _project(source: Project, plan: BaselinePlan, mode: str) -> Project:
    """Copy declared settings only; historical pointers, schedules and truth stay behind."""
    keys = plan.credential_keys
    selected = [ref.model_copy(deep=True) for ref in source.secrets if ref.key in keys]
    if (not keys or len(set(keys)) != len(keys) or len(selected) != len(keys)
            or any(not ref.domains or any(not source.allows_domain(d) for d in ref.domains)
                   for ref in selected)):
        raise ValueError("credential keys must name distinct existing domain-scoped references")
    target = urlsplit(source.base_url)
    if (target.scheme not in {"http", "https"} or not target.hostname
            or target.username or target.password or target.query or target.fragment
            or not source.allows_domain(target.hostname)):
        raise ValueError("target must be an allowed HTTP URL without embedded credentials")
    return Project(
        slug=f"{plan.baseline_slug}-{mode}", name=f"{source.name} acceptance {mode}",
        base_url=source.base_url, allowed_domains=list(source.allowed_domains),
        production=source.production, write_policy=source.write_policy,
        providers=source.providers.model_copy(deep=True), secrets=selected,
        headed=source.headed, test_id_attributes=list(source.test_id_attributes),
        max_parallel=source.max_parallel,
    )


def prepare_baselines(source_root: Path, input_root: Path, destination: Path,
                      plan: BaselinePlan) -> BaselineReceipt:
    """Create one never-overwritten pair; no historical artifacts or approvals are imported.

    Inputs must already be owner-approved redacted derivatives. This records that external
    approval reference; it does not grant approval, provision credentials, or verify the build.
    A failed filesystem write may leave a partial destination, which deliberately blocks retry.
    """
    source_root, input_root = source_root.resolve(), input_root.resolve()
    destination = destination.absolute()
    if destination.resolve() != destination or destination.exists():
        raise ValueError("baseline destination must be new and have no redirected ancestors")
    source_dir = ProjectPaths(safe_slug(plan.source_slug), source_root).dir.resolve()
    config_path = ProjectPaths(plan.source_slug, source_root).config.resolve()
    if (not source_dir.is_relative_to(source_root)
            or not config_path.is_relative_to(source_root)):
        raise ValueError("source project must remain within the supplied source root")
    if destination.is_relative_to(source_dir) or source_dir.is_relative_to(destination):
        raise ValueError("baseline destination overlaps the source project")
    if not plan.target_build.strip():
        raise ValueError("target build identity must be explicitly declared")
    config = read_bytes_path(config_path)
    if config is None:
        raise FileNotFoundError(config_path)
    if _digest(config) != plan.source_config_sha256:
        raise ValueError("source configuration changed since the plan was prepared")
    source = Project.model_validate_json(config)
    projects = [_project(source, plan, mode) for mode in ("teaching", "url-only")]
    blobs = _input_bytes(input_root, plan)
    destination.mkdir(parents=True, exist_ok=False)
    write_json(destination / "baseline-plan.json", plan)
    ids = _write_pair(destination, projects, plan, blobs)
    receipt = BaselineReceipt(
        plan_sha256=_digest(plan.model_dump_json().encode()),
        source_config_sha256=_digest(config), target_build=plan.target_build,
        teaching_slug=projects[0].slug, url_only_slug=projects[1].slug,
        teaching_source_ids=ids, credential_keys=list(plan.credential_keys),
        next_steps=["Bind the authorized credential environment explicitly; copy no values",
                    "Obtain human-signed production approvals for each new project/run",
                    "Confirm the same target build before serial live acceptance"],
    )
    write_json(destination / "baseline-receipt.json", receipt)
    return receipt


def _write_pair(destination: Path, projects: list[Project], plan: BaselinePlan,
                blobs: list[bytes]) -> list[str]:
    """Persist through the existing project/source APIs, never copying a project directory."""
    ids = []
    for mode, project in zip(("teaching", "url_only"), projects, strict=True):
        root = destination / mode
        store = ProjectStore(project.slug, root)
        store.save_project(project)
        evidence_mkdir(root / "qa" / "evidence" / "t169-real" / mode)
        if mode != "teaching":
            continue
        for index, (row, blob) in enumerate(zip(plan.teaching_inputs, blobs, strict=True)):
            path = store.paths.sources_dir / f"input-{index}{Path(row.path).suffix}"
            relative = path.relative_to(store.paths.dir)
            write_bytes(path, blob)
            source = Source(project=project.slug, kind=row.kind, path=relative.as_posix(),
                            sha256=row.sha256, provenance=Provenance(
                                produced_by="acceptance-baseline", inputs=[row.sha256],
                                note=f"Owner approval reference: {row.approval_ref}"))
            ids.append(store.add_source(source).id)
    return ids
