"""Crawl commands — `autotester explore` and `autotester report crawl`.

Split out of `cli.py` at its 300-line cap (C2); the commands are mounted onto
the same typer apps there, so the CLI surface a user sees is unchanged.
"""

from __future__ import annotations

from datetime import date, datetime, time
from pathlib import Path
from typing import Any

import typer

from autotester.store.project_store import ProjectStore


def _preflight_consent(proj: Any, store_: ProjectStore, bounds: Any) -> None:
    """D-018, checked before ANY directory is created and before the browser
    starts — `run_crawl` checks again at the seam, so this is additional.

    AT-111: with the check only at the seam, a refused run still left
    `crawl/<id>/shots/` and a populated Chromium profile behind, because
    `BrowserSession.start()` runs inside the `with` that wraps `run_crawl`.
    Even `paths.ensure()` alone leaves an empty profile dir — harmless, but
    "a refused run leaves no trace" has to mean what it says.
    """
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
    """Bounded BFS crawl of a project, refusing anything its write_policy
    denies. Contract: qa/contracts/explore.md. Nothing is typed except the
    optional login case; nothing destructive is clicked."""
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
    """The whole report a headless or CI run gets (AT-122).

    `tool_failures` belongs here for the same reason it belongs in the
    workbook: this line is the only place such a run learns the crawl could
    not record part of what it saw. Dropping it under-reports as dishonestly
    as folding it into `issues` over-reported."""
    from autotester.stages.explore_status import displayed_status, is_success

    typer.secho(
        f"{crawl.id}: {displayed_status(crawl).value} ({crawl.stop_reason}) — "
        f"{crawl.screens} screens, {crawl.edges} edges, {crawl.actions} actions, "
        f"{crawl.denied} denied, {crawl.issues} issues, "
        f"{crawl.tool_failures} tool failures",
        fg=typer.colors.GREEN if is_success(crawl) else typer.colors.YELLOW,  # X18(c)
    )


def _merge_into_flowspec(store_: ProjectStore, project: str, crawl_id: str) -> None:
    """Fold the crawl's screens into the FlowSpec and say what that cost the
    review status — a merge always sends an approved spec back to DRAFT, and a
    user who is not told that will think the spec is still approved."""
    from autotester.stages.explore_merge import merge_screens

    before = store_.load_flowspec()
    spec = merge_screens(before, store_.list_nodes(crawl_id), project, crawl_id=crawl_id)
    store_.save_flowspec(spec)
    added = len(spec.screens) - (len(before.screens) if before else 0)
    typer.secho(
        f"merged {added} new screen(s) into flowspec v{spec.version} "
        f"(review: {spec.review.status.value})",
        fg=typer.colors.GREEN,
    )


def _local_now() -> datetime:
    """The operator's current local moment, offset-aware — the seam a test pins (CN4)."""
    return datetime.now().astimezone()


def _end_of_day(day: date) -> datetime:
    """The last local second of `day` -- a NEW grant's `expires_at` (CN4, at147
    answered C, D-048); never naive, since `is_expired` reads a naive stamp as UTC."""
    return datetime.combine(day, time(23, 59, 59), tzinfo=_local_now().tzinfo)


def _validate_grant(expires: str, target: str, proj: Any) -> None:
    """Refuse a grant that can never cover anything, and flag a likely typo (AT-145).

    The safety property was never in doubt -- `require_consent` refuses an
    expired or unparseable row at run time. What was wrong is what the HUMAN is
    told: `approve --expires 2020-01-01` printed a green "granted" line for a
    consent that will refuse every run it is asked about. A gate that reports
    success for a grant it will never honour trains the operator to stop
    reading it, and the operator here is granting production consent for a
    crawl of a live ERP.
    """
    try:
        expiry = date.fromisoformat(expires)
    except ValueError:
        typer.secho(f"--expires must be YYYY-MM-DD, not {expires!r}", fg=typer.colors.RED)
        raise typer.Exit(1) from None
    today = _local_now().date()
    if expiry < today:
        # CN4 (at147 answered C, D-048): a date means THROUGH THE END of that
        # day for grants minted from 2026-09-26 on; a bare row already on disk
        # keeps its old start-of-day meaning (option B, retroactive widening,
        # was declined). AT-150/AT-151: name a usable date on every arm -- TODAY.
        usable = today.isoformat()
        typer.secho(
            f"--expires {expires} is already in the past; this grant would "
            f"refuse every run it was asked about — use --expires {usable} or later",
            fg=typer.colors.RED)
        raise typer.Exit(1)
    _warn_on_target_mismatch(target, proj)


def _is_under(path: str, base: str) -> bool:
    """Is `path` the same as, or genuinely beneath, `base`? (AT-149)

    A bare `startswith` is the same defect AT-148 fixed in the HOST half, and
    it survived one line below that fix in the PATH half: against a base_url of
    `https://demo.test/app`, both `/apple-secrets` and `/appliance/admin` were
    silently accepted as being under `/app`. A prefix is only a containment if
    it ends at a separator."""
    if ".." in path.split("/"):
        # AT-152: `urlparse` normalises nothing, so `/app/../evil` reads as
        # contained while resolving to `/evil`. Anything that can climb out is
        # not "under" anything -- refuse to vouch for it rather than guess
        # where it lands.
        return False
    stem = base.rstrip("/")
    return path in (stem, base) or path.startswith(stem + "/")


def _warn_on_target_mismatch(target: str, proj: Any) -> None:
    """Flag a target this project will never ask about (AT-145/AT-148).

    Not a refusal: an endpoint under test may legitimately differ from
    `base_url`, and CN5 matches exactly at consent time regardless. But say it
    at grant time rather than leaving the operator to discover it at a refusal.

    AT-148: the first version used `target.startswith(base_url)`, which is
    silent on `https://demo.test.evil.com/` — a naive URL prefix match reads a
    lookalike host as a match. Host equality first, then the path prefix.
    """
    from urllib.parse import urlparse

    if proj is None or not proj.base_url:
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
    kind: str = typer.Option(..., "--kind", help="read | crawl | adversarial | live_case"),
    target: str = typer.Option(..., "--target", help="the exact base_url or endpoint"),
    scope: str = typer.Option(..., "--scope", help="what this run may touch, in your words"),
    granted_by: str = typer.Option(..., "--granted-by"),
    expires: str = typer.Option(..., "--expires", help="YYYY-MM-DD; consent is never open-ended"),
    max_actions: int = typer.Option(0, "--max-actions"),
    max_probes: int = typer.Option(0, "--max-probes"),
    wall_clock: float = typer.Option(0.0, "--wall-clock", help="seconds"),
    production: bool = typer.Option(
        False, "--production", help="required for an adversarial run against production"
    ),
) -> None:
    """Grant a human's approval for one kind of run against one target (D-018).

    Content-addressed AND signed with an HMAC keyed from
    `AUTOTESTER_APPROVAL_KEY` in the repo-root `.env` (AT-110): tamper-proof
    against anyone who does not hold that key — not against an agent that can
    edit the code (`core/consent.py`) which checks it.
    """
    from autotester.schema.approval import RunApproval
    from autotester.schema.enums import ApprovalKind

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
    _validate_grant(expires, target, store_.load_project())
    # CN4 (at147 answered C, D-048): store the END of the day, offset-aware in
    # local time -- never the bare date (shares `_local_now()` with `_validate_grant`).
    expires_at = _end_of_day(date.fromisoformat(expires)).isoformat()
    candidate = RunApproval(
        project=project, run_kind=run_kind, target=target, scope=scope,
        max_actions=max_actions, max_probes=max_probes, wall_clock_s=wall_clock,
        production=production, granted_by=granted_by,
        granted_at=date.today().isoformat(), expires_at=expires_at,
    )
    _signed_or_refuse(candidate)
    approval = store_.add_approval(candidate)
    typer.secho(
        f"{approval.id}: {run_kind.value} on {target} until {expires_at} "
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
