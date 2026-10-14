"""Read and append the sibling `approval_revocations.jsonl` of a project."""

from __future__ import annotations

from pathlib import Path

from autotester.core.paths import ProjectPaths
from autotester.schema.approval import RunApproval
from autotester.schema.approval_revocation import ApprovalRevocation, drop_revoked
from autotester.store.filestore import append_jsonl, read_jsonl


def list_revocations(path: Path) -> list[ApprovalRevocation]:
    return read_jsonl(path, ApprovalRevocation)


def add_revocation(path: Path, revocation: ApprovalRevocation) -> ApprovalRevocation:
    append_jsonl(path, revocation)
    return revocation


def load_unrevoked(paths: ProjectPaths) -> list[RunApproval]:
    """The project's approvals minus any with a valid signed revocation."""
    rows = read_jsonl(paths.approvals, RunApproval)
    return drop_revoked(rows, list_revocations(paths.approval_revocations))
