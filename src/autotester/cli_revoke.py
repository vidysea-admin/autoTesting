"""`autotester revoke`: withdraw a previously granted approval with a signed row."""

from __future__ import annotations

from datetime import UTC, datetime

import typer

from autotester.store.project_store import ProjectStore


def revoke_cmd(
    project: str,
    approval_id: str = typer.Argument(..., help="the approval id, e.g. appr_0123abcd"),
    by: str = typer.Option(..., "--by", help="who is revoking"),
    reason: str = typer.Option(..., "--reason", help="why, in your words"),
) -> None:
    """Revoke an approval. HMAC-signed with the repo-root approval key; fails closed
    without it, and on an id that this project never granted."""
    from autotester.core.ids import SigningKeyMissing
    from autotester.schema.approval import RunApproval
    from autotester.schema.approval_revocation import ApprovalRevocation
    from autotester.store.approval_revocations import add_revocation
    from autotester.store.filestore import read_jsonl

    store_ = ProjectStore(project)
    if store_.load_project() is None:
        typer.secho(f"no project '{project}' yet", fg=typer.colors.RED)
        raise typer.Exit(1)
    granted = {a.id for a in read_jsonl(store_.paths.approvals, RunApproval)}
    if approval_id not in granted:
        typer.secho(f"{project}: no approval {approval_id}", fg=typer.colors.RED)
        raise typer.Exit(1)
    row = ApprovalRevocation(approval_id=approval_id, revoked_by=by, reason=reason,
                             revoked_at=datetime.now(UTC).isoformat())
    try:
        row.sign()
    except SigningKeyMissing as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(1) from None
    add_revocation(store_.paths.approval_revocations, row)
    typer.secho(f"{approval_id}: revoked by {by}", fg=typer.colors.GREEN)
