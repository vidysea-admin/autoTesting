"""Crawl commands — `autotester explore` and `autotester report crawl`.

Split out of `cli.py` at its 300-line cap (C2); the commands are mounted onto
the same typer apps there, so the CLI surface a user sees is unchanged.
"""

from __future__ import annotations

import math
from datetime import UTC, date, datetime, time
from pathlib import Path
from typing import Any

import typer

from autotester.store.project_store import ProjectStore


def _preflight_consent(proj: Any, store_: ProjectStore, bounds: Any) -> None:
    """D-018, checked before ANY directory is created and before the browser starts --
    `run_crawl` checks again at the seam. AT-111: checking only there left
    `crawl/<id>/shots/` and a Chromium profile behind, so a refused run left a trace."""
    from autotester.core.consent import ApprovalRequired
    from autotester.schema.crawl import SafetyPolicy
    from autotester.stages import explore_consent

    try:
        explore_consent.require_consent(
            proj, store_, bounds, policy=SafetyPolicy(write_policy=proj.write_policy))
    except ApprovalRequired as exc:
        typer.secho(str(exc), fg=typer.colors.YELLOW)
        raise typer.Exit(2) from None


def _resolve_crawl_target(project: str, login_case: str | None) -> tuple[ProjectStore, Any, Any]:
    """The project and (optional) login case, or a clean CLI exit naming which
    one is missing — never a traceback at a user."""
    store_ = ProjectStore(project)
    proj = store_.load_project()
    if proj is None:
        typer.secho(f"no project '{project}' yet", fg=typer.colors.RED)
        raise typer.Exit(1)
    # X17: the project's declared login case, which `--login-case` may override for one run.
    case_id = login_case or proj.login_case_id
    case = store_.get_case(case_id) if case_id else None
    if case_id and case is None:
        typer.secho(f"no case '{case_id}' in {project}", fg=typer.colors.RED)
        raise typer.Exit(1)
    return store_, proj, case


def explore_cmd(
    project: str,
    max_screens: int = typer.Option(30, "--max-screens"),
    max_actions: int = typer.Option(200, "--max-actions"),
    wall_clock: float = typer.Option(600.0, "--wall-clock", help="seconds"),
    max_depth: int = typer.Option(6, "--max-depth"),
    login_case: str | None = typer.Option(None, "--login-case", help="case id to log in with"),
    merge: bool = typer.Option(
        False, "--merge", help="fold the crawled screens into the FlowSpec (resets it to DRAFT)"
    ),
) -> None:
    """Bounded BFS crawl of a project, refusing anything its write_policy denies.
    Contract: qa/contracts/explore.md. Only the login case is typed; nothing destructive."""
    from autotester.browser.observe import PageObserver
    from autotester.browser.secrets import SecretStore
    from autotester.browser.session import BrowserSession
    from autotester.core.consent import ApprovalRequired
    from autotester.core.ids import run_id
    from autotester.core.paths import ProjectPaths
    from autotester.schema.crawl import CrawlBounds
    from autotester.stages import explore as explore_stage

    store_, proj, case = _resolve_crawl_target(project, login_case)
    bounds = CrawlBounds(max_screens=max_screens, max_actions=max_actions,
                         wall_clock_s=wall_clock, max_depth=max_depth)
    _preflight_consent(proj, store_, bounds)
    paths = ProjectPaths(project)
    paths.ensure()
    secrets = SecretStore.load(proj, paths.env_file, strict=False)
    observer = PageObserver()
    crawl_id = run_id("crawl")
    try:
        with BrowserSession(proj, secrets, paths.crawl_shots_dir(crawl_id),
                            paths, observer=observer) as session:
            crawl = explore_stage.run_crawl(proj, session, store_, observer=observer,
                                            bounds=bounds, login_case=case, crawl_id=crawl_id)
    except ApprovalRequired as exc:
        typer.secho(str(exc), fg=typer.colors.YELLOW)
        raise typer.Exit(2) from None
    echo_crawl_summary(crawl)
    if merge:
        _merge_into_flowspec(store_, project, crawl.id)
    typer.echo(str(paths.crawl_dir(crawl.id)))


def echo_crawl_summary(crawl: Any) -> None:
    """The CI report, keeping crawler failures apart from product issues (AT-122)."""
    from autotester.stages.explore_status import (
        displayed_reason,
        displayed_status,
        is_success,
        skip_note,
    )

    typer.secho(
        f"{crawl.id}: {displayed_status(crawl).value} ({displayed_reason(crawl)}) — "
        f"{crawl.screens} screens, {crawl.edges} edges, {crawl.actions} actions, "
        f"{crawl.denied} denied, {crawl.issues} issues, "
        f"{crawl.tool_failures} tool failures{skip_note(crawl)}",  # CR5
        fg=typer.colors.GREEN if is_success(crawl) else typer.colors.YELLOW,  # X18(c)
    )


def _merge_into_flowspec(store_: ProjectStore, project: str, crawl_id: str) -> None:
    """Fold the crawl into the FlowSpec and say what it cost the review status (back to DRAFT)."""
    from autotester.stages.explore_merge import merge_stored_crawl

    before = store_.load_flowspec()
    spec = merge_stored_crawl(store_, before, project, crawl_id)
    store_.save_flowspec(spec)
    old_screens, old_flows = (len(before.screens), len(before.flows)) if before else (0, 0)
    typer.secho(
        f"merged {len(spec.screens) - old_screens} new screen(s) and "
        f"{len(spec.flows) - old_flows} flow proposal(s) into flowspec "
        f"v{spec.version} (review: {spec.review.status.value})",
        fg=typer.colors.GREEN,
    )


def _local_now() -> datetime:
    """The operator's current local moment, offset-aware — the seam a test pins (CN4)."""
    return datetime.now().astimezone()


def _end_of_day(day: date) -> datetime:
    """The last local second of `day`, never naive: a NEW grant's `expires_at` (CN4, D-048)."""
    return datetime.combine(day, time(23, 59, 59), tzinfo=_local_now().tzinfo)


def _validate_grant(expires: str, target: str, proj: Any) -> None:
    """Refuse a grant that can never cover anything, flag a likely typo (AT-145)."""
    try:
        expiry = date.fromisoformat(expires)
    except ValueError:
        typer.secho(f"--expires must be YYYY-MM-DD, not {expires!r}", fg=typer.colors.RED)
        raise typer.Exit(1) from None
    today = _local_now().date()
    if expiry < today:
        # CN4 (D-048): a date means THROUGH THE END of that day for new grants.
        # AT-150/AT-151: name a usable date on every arm -- TODAY.
        usable = today.isoformat()
        typer.secho(
            f"--expires {expires} is already in the past; this grant would "
            f"refuse every run it was asked about — use --expires {usable} or later",
            fg=typer.colors.RED)
        raise typer.Exit(1)
    _warn_on_target_mismatch(target, proj)


def _caps_or_refuse(actions: int, wall_clock: float, expires_at: str | None, kind: Any) -> None:
    """The shared grant caps (consent.validate_grant_bounds); exit 1 over one."""
    from autotester.core.consent import validate_grant_bounds

    try:
        validate_grant_bounds(actions, wall_clock, None if expires_at is None
                              else datetime.fromisoformat(expires_at), kind=kind)
    except ValueError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(1) from None


def _resolved_bounds(store_: ProjectStore, kind: Any, *typed: Any) -> tuple[Any, ...]:
    """The grant's three bounds, omitted ones derived (D-112), saying so before signing."""
    from autotester.stages.run_gates import resolve_grant_bounds
    *bounds, note = resolve_grant_bounds(store_, kind, *typed)
    if note:
        typer.secho(note, fg=typer.colors.CYAN)
    return tuple(bounds)


def _grant_expiry(expires: str | None, standing: bool, target: str, proj: Any) -> str | None:
    """A NEW grant's `expires_at`: end-of-day (CN4) or None for `--standing` (D-111); one of two."""
    if standing == (expires is not None):
        typer.secho("give either --expires YYYY-MM-DD or --standing (valid until revoked), "
                    "not both and not neither", fg=typer.colors.RED)
        raise typer.Exit(1)
    if expires is None:
        _warn_on_target_mismatch(target, proj)
        return None
    _validate_grant(expires, target, proj)
    return _end_of_day(date.fromisoformat(expires)).isoformat()


def _is_under(path: str, base: str) -> bool:
    """Is `path` the same as, or genuinely beneath, `base`? (AT-149) A bare
    `startswith` accepts `/apple` under `/app`; a prefix must end at a separator."""
    if ".." in path.split("/"):
        # AT-152: `/app/../evil` reads as contained but resolves to `/evil`.
        return False
    stem = base.rstrip("/")
    return path in (stem, base) or path.startswith(stem + "/")


def _warn_on_target_mismatch(target: str, proj: Any) -> None:
    """Flag (not refuse) a target this project will never ask about (AT-145): CN5 matches
    exactly at consent time, so say it at grant time. AT-148: host equality first, then
    the path prefix -- a naive `startswith` reads `demo.test.evil.com` as a match."""
    from urllib.parse import urlparse

    if proj is None or not proj.base_url or "://" not in target:   # a provider id is no URL
        return
    base, want = urlparse(target), urlparse(proj.base_url)
    same_host = (base.scheme, base.netloc) == (want.scheme, want.netloc)
    if same_host and _is_under(base.path, want.path):
        return
    typer.secho(
        f"note: {target} does not match this project's base_url "
        f"({proj.base_url}) — a crawl of it will not match this approval",
        fg=typer.colors.YELLOW)


def _signed_or_refuse(candidate: Any) -> None:
    """AT-110: sign in place, or refuse the grant naming the missing key."""
    from autotester.core.ids import SigningKeyMissing

    try:
        candidate.sign()
    except SigningKeyMissing as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(1) from None


def approve_cmd(
    project: str,
    kind: str = typer.Option(..., "--kind", help="read|crawl|adversarial|live_case|video_review"),
    target: str = typer.Option(..., "--target", help="the exact base_url or endpoint"),
    scope: str = typer.Option(..., "--scope", help="what this run may touch, in your words"),
    granted_by: str = typer.Option(..., "--granted-by"),
    expires: str | None = typer.Option(None, "--expires", help="YYYY-MM-DD, through that day"),
    standing: bool = typer.Option(False, "--standing", help="until revoked (autotester revoke)"),
    max_actions: int | None = typer.Option(None, "--max-actions", min=1, help="default 200"),
    max_probes: int | None = typer.Option(None, "--max-probes", min=1, help="default 200"),
    wall_clock: float | None = typer.Option(None, "--wall-clock", min=0.001, help="default 600s"),
    production: bool = typer.Option(False, "--production", help="adversarial run on production"),
) -> None:
    """Grant a human's approval for one kind of run against one target (D-018).
    HMAC-signed (AT-110). `--kind live_case`: any bound left out is derived (D-112)."""
    from autotester.schema.approval import RunApproval
    from autotester.schema.enums import ApprovalKind

    if any(v is not None and (not math.isfinite(v) or v <= 0)
           for v in (max_actions, max_probes, wall_clock)):
        typer.secho("grant bounds must be positive and finite", fg=typer.colors.RED)
        raise typer.Exit(1)
    store_ = ProjectStore(project)
    if store_.load_project() is None:
        typer.secho(f"no project '{project}' yet", fg=typer.colors.RED)
        raise typer.Exit(1)
    try:
        run_kind = ApprovalKind(kind)
    except ValueError:
        allowed = ", ".join(k.value for k in ApprovalKind)
        typer.secho(f"--kind must be one of: {allowed}", fg=typer.colors.RED)
        raise typer.Exit(1) from None
    max_actions, max_probes, wall_clock = _resolved_bounds(
        store_, run_kind, max_actions, max_probes, wall_clock)
    # CN4: only NEW rows get an offset-aware end-of-day expiry (D-048); D-111: or none.
    expires_at = _grant_expiry(expires, standing, target, store_.load_project())
    _caps_or_refuse(max_actions, wall_clock, expires_at, run_kind)
    candidate = RunApproval(
        project=project, run_kind=run_kind, target=target, scope=scope,
        max_actions=max_actions, max_probes=max_probes, wall_clock_s=wall_clock,
        production=production, granted_by=granted_by,
        granted_at=datetime.now(UTC).isoformat(), expires_at=expires_at, standing=standing,
    )
    _signed_or_refuse(candidate)
    approval = store_.add_approval(candidate)
    typer.secho(
        f"{approval.id}: {run_kind.value} on {target} "
        f"{'STANDING, until revoked' if standing else f'until {expires_at}'} "
        f"(actions<={max_actions}, probes<={max_probes})",
        fg=typer.colors.GREEN,
    )


def report_crawl(
    project: str,
    crawl_id: str = typer.Argument(..., help="crawl id, e.g. crawl_01J…"),
    out: str = typer.Option(..., "--out", help="output .xlsx path"),
) -> None:
    """Summary, screens, edges, refusals, issues and third-party noise."""
    from autotester.stages.crawl_report import export_crawl_excel

    try:
        path = export_crawl_excel(project, crawl_id, Path(out))
    except ValueError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(1) from exc
    typer.secho(f"wrote {path}", fg=typer.colors.GREEN)
