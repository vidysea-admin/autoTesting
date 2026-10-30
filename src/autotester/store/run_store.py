"""Persistence for the advisory UX track: personas and one run's `UXReport` (T-190, PU1/PU2).

Split out because `project_store.py` sits at the 300-line cap (C2); `ProjectStore` inherits
`RunStoreMixin`, so callers still say `store.save_ux_report(...)`. Not a second store (C3).
It also holds the media write-through (mongo-store M24, M25, M51), because `store/blobs.py` is at
the same cap and no new module is approved: `blob_store`, `put_file`, `write_blob_file`,
`local_blob`, `sync_run_blobs`, `store_media`, `place_media`. With the `blobs` area on `file` (the
default) each one reduces to today's file behaviour and no database driver is imported.
The UX report lives at `runs/<run_id>/ux_report.json` -- beside, never inside, a case's result or
verdict file -- and `RUN_AUX_FILES` is how `ProjectStore.load_results` knows to skip it.
"""

from __future__ import annotations

import errno
import hashlib
import mimetypes
import os
import shutil
from pathlib import Path

from autotester.browser.secrets import SecretStore
from autotester.core.ids import ulid
from autotester.core.paths import ProjectPaths, repo_root
from autotester.schema.enums import EvidenceKind
from autotester.schema.release import FlowPlan, ReleaseRecord, ReleaseScope
from autotester.schema.run import RawResult
from autotester.schema.user_persona import UserPersona
from autotester.schema.ux_report import UXReport
from autotester.store.blobs import BlobInfo, BlobNotFound, BlobStore, MongoBlobStore
from autotester.store.filestore import (
    FileBackend,
    read_json,
    read_jsonl,
    upsert_jsonl,
    write_bytes,
    write_json,
)
from autotester.store.mongo_routes import RUN_AUX_FILES, StoreSelectionError, store_selection

__all__ = ["RUN_AUX_FILES", "RunStoreMixin", "blob_store", "local_blob", "place_media",
           "put_file", "store_media", "sync_run_blobs", "write_blob_file"]
_BLOBS: dict[str, BlobStore] = {}
_TYPES = {".png": "image/png", ".webm": "video/webm"}
_MEDIA = {EvidenceKind.SCREENSHOT: "screenshot", EvidenceKind.VIDEO: "video"}


class RunStoreMixin:
    """Requires `self.paths: ProjectPaths` from `ProjectStore.__init__` -- mixed in, never alone."""

    paths: ProjectPaths

    def save_result(self, run_id: str, result: RawResult) -> None:
        """One case's result. M24: its screenshots and kept video are in the blob store BEFORE the
        result that names them is written (moved here from `ProjectStore`, which is at the cap)."""
        sync_run_blobs(self.paths.run_dir(run_id), result)
        write_json(self.paths.run_dir(run_id) / f"{result.case_id}.json", result)

    # -- advisory personas (one jsonl row per persona, id-keyed) ---------------
    def save_user_persona(self, persona: UserPersona, secrets: SecretStore | None = None) -> None:
        """Upsert one persona. With `secrets`, the whole row is guarded first (C5): a raw
        credential value in any persona field raises `ValueError` and nothing is written."""
        if persona.project != self.paths.slug:
            raise ValueError(f"persona '{persona.id}' belongs to '{persona.project}'")
        if secrets is not None:
            secrets.guard_prompt(persona.model_dump_json())
        upsert_jsonl(self.paths.user_personas, persona, UserPersona)

    def list_user_personas(self) -> list[UserPersona]:
        return read_jsonl(self.paths.user_personas, UserPersona)

    def get_user_persona(self, persona_id: str) -> UserPersona | None:
        return next((p for p in self.list_user_personas() if p.id == persona_id), None)

    # -- the advisory report (one file per run) --------------------------------
    def save_ux_report(self, report: UXReport) -> None:
        write_json(self.paths.run_ux_report(report.run_id), report)

    def load_ux_report(self, run_id: str) -> UXReport | None:
        """`None` only when the run never had a UX pass. A file that exists but does not
        validate raises `ValueError` naming the path -- never read as "no findings"."""
        return read_json(self.paths.run_ux_report(run_id), UXReport)

    # -- release regression: per-flow plans, a frozen scope, one durable record (T-167) --------
    def save_flow_plan(self, plan: FlowPlan) -> None:
        """Upsert one flow's persisted validation plan (a flow has exactly one)."""
        if plan.project != self.paths.slug:
            raise ValueError(f"flow plan '{plan.flow_id}' belongs to '{plan.project}'")
        upsert_jsonl(self.paths.flow_plans, plan, FlowPlan, key="flow_id")

    def list_flow_plans(self) -> list[FlowPlan]:
        return read_jsonl(self.paths.flow_plans, FlowPlan)

    def save_release_scope(self, scope: ReleaseScope) -> None:
        """Write the scope once; a different scope for the same run is refused (frozen)."""
        previous = self.load_release_scope(scope.run_id)
        if previous is not None and previous.fingerprint != scope.fingerprint:
            raise ValueError("release scope is frozen for this run")
        if previous is None:
            write_json(self.paths.run_release_scope(scope.run_id), scope)

    def load_release_scope(self, run_id: str) -> ReleaseScope | None:
        return read_json(self.paths.run_release_scope(run_id), ReleaseScope)

    def save_release_record(self, record: ReleaseRecord) -> None:
        """The release's ONE record + issues log; its scope must be the frozen one."""
        frozen = self.load_release_scope(record.run_id)
        if frozen is None or frozen.fingerprint != record.scope.fingerprint:
            raise ValueError("release record must match the persisted frozen scope")
        write_json(self.paths.run_release_record(record.run_id), record)

    def load_release_record(self, run_id: str) -> ReleaseRecord | None:
        return read_json(self.paths.run_release_record(run_id), ReleaseRecord)

    def list_release_records(self) -> list[ReleaseRecord]:
        """Every release of this project, oldest first (ties broken by run id)."""
        if not self.paths.runs_dir.exists():
            return []
        found = [self.load_release_record(d.name) for d in self.paths.runs_dir.iterdir()
                 if d.is_dir()]
        return sorted((r for r in found if r is not None),
                      key=lambda r: (r.scope.created_at, r.run_id))


# -- media write-through: files stay on disk; a blob-backed area ALSO holds them (M24, M25, M51) --
def blob_store() -> BlobStore | None:
    """The process's blob store when the `blobs` area is on mongo, else `None` (files only)."""
    if store_selection()["blobs"] != "mongo":
        return None
    if "mongo" not in _BLOBS:
        from autotester.store import mongo_backend, mongo_guard  # lazy: file mode loads no driver
        uri = os.environ.get(mongo_backend.URI_ENV, "").strip()
        if not uri:
            raise StoreSelectionError(f"{mongo_backend.URI_ENV} is not set; blobs=mongo needs it")
        _BLOBS["mongo"] = MongoBlobStore(mongo_guard.GuardedStore(uri))
    return _BLOBS["mongo"]


def _key(path: Path) -> str | None:
    """The blob key of `path` (relative to the data root), `None` outside the data root."""
    try:
        return Path(path).resolve().relative_to(repo_root().resolve()).as_posix()
    except ValueError:
        return None


def put_file(path: Path, data: bytes | None = None, *, kind: str, masked: bool) -> BlobInfo | None:
    """Put `data` (default: the bytes of the file at `path`) under `path`'s key. `None`: the blobs
    area is on file, or `path` is outside the data root. A refusal (M23: an unmasked screenshot,
    M8/M54: a secret value) propagates; nothing is written."""
    store, key = blob_store(), _key(path)
    if store is None or key is None:
        return None
    suffix = Path(path).suffix.lower()
    guess = mimetypes.guess_type(f"x{suffix}")[0]
    ctype = _TYPES.get(suffix) or guess or "application/octet-stream"
    body = Path(path).read_bytes() if data is None else data
    return store.put(key, body, kind=kind, masked=masked, content_type=ctype)


def write_blob_file(dest: Path, data: bytes, *, kind: str, masked: bool) -> None:
    """Blob first (it can refuse), then the local file, atomically, exactly as today: through the
    routed state backend while the blobs area is on file, a plain file once the bytes live in GridFS
    (media never goes into the state database)."""
    if put_file(dest, data, kind=kind, masked=masked) is None:
        write_bytes(dest, data)
    else:
        FileBackend(Path(dest).parent).put(Path(dest).name, data)


def local_blob(path: Path) -> Path:
    """A real local file for a reader (M24): `path` itself while it exists (byte-identical to
    today); with the blobs area on mongo and the file gone, a verified copy in `.work/blob-cache/`;
    else `path` unchanged."""
    path = Path(path)
    store, key = (None, None) if path.is_file() else (blob_store(), _key(path))
    if store is None or key is None:
        return path
    try:
        return store.materialize(key)
    except BlobNotFound:
        return path


def sync_run_blobs(run_dir: Path, result: RawResult) -> int:
    """M24: every screenshot and kept video `result` names is in the blob store BEFORE the result
    is saved. A file already stored is a no-op. Returns the number of files put or confirmed; 0
    when the blobs area is on file. A path that leaves `run_dir` is skipped."""
    root, count = Path(run_dir).resolve(), 0
    for ev in result.evidence:
        path = (Path(run_dir) / ev.path).resolve()
        if ev.kind in _MEDIA and path.is_file() and path.is_relative_to(root):
            count += put_file(path, kind=_MEDIA[ev.kind], masked=ev.masked) is not None
    return count


def store_media(target: Path, data: bytes) -> Path:
    """M51: ingested source bytes at `target`. Blob-backed: GridFS only (nothing under the data
    root); a same-named blob with other content is kept apart by a digest prefix. Returns the
    LOGICAL path in both modes, which is what a `Source` records; a reader that needs the bytes
    passes it through `local_blob` (a no-op in file mode)."""
    store = blob_store()
    if store is not None and (key := _key(target)) is not None:
        sha = hashlib.sha256(data).hexdigest()
        if (held := store.stat(key)) is not None and held.sha256 != sha:
            target = target.with_name(f"{sha[:8]}_{target.name}")
        put_file(target, data, kind="source", masked=False)
        return target
    FileBackend(target.parent).put(target.name, data)
    return target


def place_media(staged: Path, target: Path, digest: str) -> None:
    """M51: move a staged, already-hashed recording to `target`. Blob-backed: GridFS only. File
    mode: create the folder and rename; across volumes copy beside the target, verify, replace."""
    if blob_store() is not None and _key(target) is not None:
        data = Path(staged).read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError("the stored copy does not match its sha256")
        put_file(target, data, kind="source", masked=False)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.replace(staged, target)
    except OSError as exc:
        if exc.errno != errno.EXDEV:
            raise
        temp = target.with_name(f".tmp-{ulid()}{target.suffix}")
        shutil.copyfile(staged, temp)
        with temp.open("rb") as handle:
            same = hashlib.file_digest(handle, "sha256").hexdigest() == digest
        if not same:
            temp.unlink(missing_ok=True)
            raise ValueError("the stored copy does not match its sha256") from None
        os.replace(temp, target)
