"""`autotester store`: copy the file-backed state into the one Mongo database, then prove it
(mongo-store U8, M41-M46).

One job: the `migrate` and `verify` commands, their report and their exit codes. The work is in
`store/migrate_state.py`, `auth/migrate_auth.py` and `store/migrate_creds.py`. `migrate` is a dry
run unless `--apply`, and a dry run opens no connection and loads no driver (`--check-remote` is the
explicit opt-in to compare against the target). `--apply` is the human-gated G1 step. The report is
counts, state keys and class names: never a URI, a hash or a credential value (M9, M46), and a
failure prints its exception class name only. Exit: 0 clean, 1 a conflict, refusal or mismatch, 2
refused to start.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from typing import Any

import typer

from autotester.core.env import MONGO_URI_ENV, mongo_uri
from autotester.core.paths import repo_root
from autotester.store import mongo_routes as routes
from autotester.store.filestore import FileBackend
from autotester.store.migrate_state import Tally, migrate_state, scan_tree, verify_approvals

app = typer.Typer(help="Move the file-backed state into the Mongo store (mongo-store U8).",
                  no_args_is_help=True)
COLUMNS = ("to_insert", "unchanged", "conflicting-id", "written", "refused")
WARN_MB = 4
MAX_MB = 12


def _wanted(only: str | None) -> set[str]:
    chosen = {a.strip() for a in only.split(",") if a.strip()} if only else set(routes.AREAS)
    if unknown := chosen - set(routes.AREAS):
        typer.echo(f"refused: unknown part(s) {sorted(unknown)}; use {list(routes.AREAS)}",
                   err=True)
        raise typer.Exit(2)
    return chosen


def _need_uri() -> None:
    if not mongo_uri():
        typer.echo(f"refused: no Mongo URI is configured (set {MONGO_URI_ENV}); nothing was "
                   "written", err=True)
        raise typer.Exit(2)


def _open() -> tuple[Any, Any]:
    """The target backend and blob store, opened only now (the driver loads here, not before)."""
    from autotester.store.blobs import MongoBlobStore
    from autotester.store.mongo_backend import default_backend, default_store

    return default_backend(), MongoBlobStore(default_store())


def _row(name: str, counts: Counter[str]) -> str:
    cells = [f"{c}={counts[c]}" for c in COLUMNS if counts[c] or c in COLUMNS[:3]]
    return f"  {name:<22}" + "  ".join(cells)


def render(t: Tally, extra: dict[str, Counter[str]], mode: str, notes: list[str]) -> None:
    """The report. Counts, bytes and state keys only."""
    out = typer.echo
    out(f"store {mode}")
    out("per collection:")
    for name in sorted(t.counts):
        out(_row(name, t.counts[name]))
    for name, counts in extra.items():
        out(_row(name, counts))
    out("bytes per kind: " + (", ".join(f"{k}={v}" for k, v in sorted(t.kinds.items())) or "none"))
    out(f"largest documents (warn above {WARN_MB} MB, refused above {MAX_MB} MB):")
    for size, key in sorted(t.sizes, reverse=True)[:10]:
        out(f"  {size:>12}  {key}")
    blobs = t.counts.get("gridfs", Counter())
    out(f"GridFS total: {sum(blobs.values())} blobs, {t.kinds['blob']} bytes")
    out(f"keys that failed safe_name: {len(t.unsafe)}")
    for key in t.unsafe[:20]:
        out(f"  {key!r}")
    out("never moved (M25): " + (", ".join(f"{k}={v}" for k, v in sorted(t.skipped.items()))
                                 or "nothing found"))
    out(t.private_line())
    for note in notes:
        out(note)
    written = sum(c["written"] for c in [*t.counts.values(), *extra.values()])
    out(f"written: {written}")


def _auth_part(apply: bool, remote: bool, sessions: bool, notes: list[str]) -> Counter[str]:
    from autotester.auth.migrate_auth import auth_status, import_auth, read_auth

    data = read_auth()
    if data is None:
        notes.append("auth: no SQLite auth file found; nothing to import")
        return Counter()
    notes.append(f"auth sessions: {len(data['sessions'])} in the file, " + (
        "copied (unexpired only)" if sessions else "NOT copied (use --include-sessions)"))
    if apply:
        return import_auth(data, sessions)
    return auth_status(data, remote)


def _creds_part(project: str | None, apply: bool, remote: bool, notes: list[str]) -> Counter[str]:
    from autotester.store.migrate_creds import credential_pairs, import_credentials

    pairs, dropped = credential_pairs(repo_root(), project)
    notes.append(f"credentials: {len(pairs)} declared key(s) found in .env; {dropped} deployment "
                 "secret(s) left out (never stored, never named)")
    return import_credentials(pairs, remote, apply)


def _safely(what: str, body: Callable[[], int]) -> None:
    try:
        code = body()
    except typer.Exit:
        raise
    except Exception as exc:  # the class name only: a driver message may carry the URI (M9)
        typer.echo(f"store {what} failed: {type(exc).__name__}", err=True)
        raise typer.Exit(1) from None
    if code:
        raise typer.Exit(code)


def _migrate(apply: bool, project: str | None, only: str | None, sessions: bool,
             check: bool) -> int:
    wanted, src, t = _wanted(only), FileBackend(repo_root()), Tally()
    if apply:
        _need_uri()
    remote = apply or check
    tgt, blobs = _open() if remote else (None, None)
    found = scan_tree(src, project, t)
    migrate_state(src, found, t, tgt, blobs, apply, wanted)
    extra: dict[str, Counter[str]] = {}
    notes = ["browser sessions are never migrated: role logins are re-established by the human"]
    if "auth" in wanted and not project:
        extra["auth_users"] = _auth_part(apply, remote, sessions, notes)
    if "credentials" in wanted:
        extra["secrets"] = _creds_part(project, apply, remote, notes)
    render(t, extra, "APPLY" if apply else "DRY RUN" + (
        " (target compared)" if remote else " (no connection opened)"), notes)
    return int(t.stuck() > 0 or any(c["conflicting-id"] or c["refused"] for c in extra.values()))


def _verify(project: str | None, only: str | None) -> int:
    wanted, src, t = _wanted(only), FileBackend(repo_root()), Tally()
    _need_uri()
    tgt, blobs = _open()
    found = scan_tree(src, project, t)
    migrate_state(src, found, t, tgt, blobs, False, wanted)
    extra: dict[str, Counter[str]] = {}
    notes: list[str] = []
    bad = t.bad()
    if "approvals" in wanted:
        signed = verify_approvals(tgt, found[0])
        notes.append("approvals: " + ", ".join(f"{k}={v}" for k, v in sorted(signed.items())))
        bad += signed["not_intact"] + signed["signature_failed"] + signed["unreadable"]
    if "auth" in wanted and not project:
        extra["auth_users"] = _auth_part(False, True, False, notes)
    if "credentials" in wanted:
        extra["secrets"] = _creds_part(project, False, True, notes)
    bad += sum(c["to_insert"] + c["conflicting-id"] for c in extra.values())
    render(t, extra, "VERIFY", notes)
    typer.echo(f"mismatches: {bad}")
    return int(bad > 0)


@app.command("migrate")
def migrate_cmd(
    apply: bool = typer.Option(False, "--apply", help="write to Mongo (G1: Umesh runs this)"),
    project: str | None = typer.Option(None, "--project", help="only this project's state"),
    only: str | None = typer.Option(None, "--only", help="comma list of areas, default all"),
    include_sessions: bool = typer.Option(False, "--include-sessions",
                                          help="also copy unexpired login sessions"),
    check_remote: bool = typer.Option(False, "--check-remote",
                                      help="dry run that connects, to fill unchanged/conflicts"),
) -> None:
    """Dry run by default: report what would move. Never edits or deletes a source file."""
    _safely("migrate", lambda: _migrate(apply, project, only, include_sessions, check_remote))


@app.command("verify")
def verify_cmd(
    project: str | None = typer.Option(None, "--project", help="only this project's state"),
    only: str | None = typer.Option(None, "--only", help="comma list of areas, default all"),
) -> None:
    """Compare the files with Mongo (hash, sha256, counts); exit 1 on any mismatch."""
    _safely("verify", lambda: _verify(project, only))
