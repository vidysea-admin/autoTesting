"""`autotester ingest review`: a pointer-guided review of one recording (T-197, CLI half).

One job: turn the command line into a `stages.video_review.run_review` call and its typed outcome
into an exit code plus text or ONE JSON document on stdout; notes and errors go to stderr.
Exit codes (contract "CLI contract"): 0 ok or partial, 1 usage error, unexpected error or a
failed review, 2 pointer errors (the whole list, Provider never called), 3 approval or permission
missing (zero Provider calls), 4 source unreadable, 130 interrupted. In json mode every exit,
click usage errors included, writes one document with `exit_code`. The stage owns every safety
property; this module composes the gate. Registered on the `ingest` app in `cli_video.py`.
"""

from __future__ import annotations

import json
import math
from collections.abc import Callable
from functools import partial
from itertools import pairwise
from pathlib import Path
from typing import Annotated

import typer
from typer.core import TyperCommand
from typer.exceptions import TyperException

from autotester import providers
from autotester.browser.secrets import SecretStore
from autotester.core.consent import ApprovalRequired, require_approval
from autotester.core.redact import Redactor
from autotester.media.probe import probe
from autotester.providers.base import Provider, ProviderError
from autotester.schema.enums import ApprovalKind
from autotester.schema.project import Source
from autotester.schema.video_review import RedactionWindow, ReviewPlan, VideoReview
from autotester.stages.analyze_video import load_transcript
from autotester.stages.video_pointers import MAX_POINTER_FILE_BYTES, oversize_parse, parse_pointers
from autotester.stages.video_review import (
    DEFAULT_MAX_COST_USD,
    PointerErrors,
    ReviewGate,
    ReviewRefused,
    preview_review,
    run_review,
    unreadable_reason,
)
from autotester.stages.video_review_render import render_markdown
from autotester.store.project_store import ProjectStore

EXIT_USAGE, EXIT_POINTERS, EXIT_REFUSED, EXIT_UNREADABLE, EXIT_INTERRUPTED = 1, 2, 3, 4, 130


class CliFail(Exception):
    """A usage error, refusal or failure with its exit code; `_fail` turns it into the stderr
    note plus, in json mode, ONE document (status, reason, exit_code) on stdout."""

    def __init__(self, reason: str, code: int = EXIT_USAGE, status: str | None = None) -> None:
        super().__init__(reason)
        self.reason, self.code = reason, code
        self.status = status or ("refused" if code == EXIT_REFUSED else "usage_error")


def local_operator_permission() -> None:
    """The CLI runs as the machine's own operator (holds the repo-root `.env` and approval key).
    The hosted route checks `video.upload` via `authorize()` (T-204): wire that check here."""


def build_gate(store: ProjectStore, project: str, provider: Provider,
               plan_fn: Callable[[], ReviewPlan], permission: Callable[[], None]) -> ReviewGate:
    """TV7.1 + TV7.2 as the stage's `gate`: permission, then a signed, unexpired per-use approval
    for exactly (project, provider) wide enough for this plan's calls. Any shortfall raises
    `ReviewRefused` and the stage has made zero Provider calls."""
    def gate() -> None:
        permission()
        plan = plan_fn()
        try:
            require_approval(store.list_approvals(), project=project,
                             kind=ApprovalKind.VIDEO_REVIEW, target=provider.id,
                             actions=plan.call_count)
        except ApprovalRequired as exc:
            raise ReviewRefused(str(exc)) from exc
    return gate


def parse_windows(specs: list[str], duration_s: float) -> list[RedactionWindow]:
    """`--redact 12:30-14:00` (repeatable). Anything that is not a plain START-END window is
    refused whole: a redaction a human meant must never be silently dropped or approximated."""
    if not specs:
        return []
    parse = parse_pointers("\n".join(specs), duration_s)
    wins = [p for p in parse.parsed if p.kind == "window" and not p.approx]
    if parse.errors or len(wins) != len(specs):
        raise ValueError("--redact takes START-END windows inside the recording, like 12:30-14:00")
    return [RedactionWindow(start_s=p.start_s or 0.0, end_s=p.end_s or 0.0) for p in wins]


def _say(text: str, *, colour: str | None = None) -> None:
    typer.secho(text, fg=colour, err=True)


def _doc(payload: object) -> None:
    typer.echo(json.dumps(payload, indent=2, ensure_ascii=False))


def _fail(exc: CliFail, as_json: bool) -> int:
    _say(exc.reason, colour=typer.colors.RED)
    if as_json:
        _doc({"status": exc.status, "reason": exc.reason, "exit_code": exc.code})
    return exc.code


def _wants_json(args: list[str]) -> bool:
    """`--output json` / `--output=json` in argv. A bare `--output` names no format: stays text."""
    return "--output=json" in args or any(
        a == "--output" and nxt == "json" for a, nxt in pairwise(args))


class ReviewCommand(TyperCommand):
    """Click rejects a bad flag (`--max-cost abc`, unknown option, missing argument) before
    `review_cmd` runs with exit 2 (pointer errors here) and no stdout. Make it exit 1 plus,
    in json mode, the same document `_fail` writes."""

    def parse_args(self, ctx: typer.Context, args: list[str]) -> list[str]:
        argv = list(args)                              # the parser consumes `args` in place
        try:
            return super().parse_args(ctx, args)
        except TyperException as exc:                  # typer's click: usage errors
            exc.show()                                 # usage line + message, to stderr
            if _wants_json(argv):
                _doc({"status": "usage_error", "reason": exc.format_message(),
                      "exit_code": EXIT_USAGE})
            ctx.exit(EXIT_USAGE)


def _pointer_errors(exc: PointerErrors, as_json: bool) -> int:
    errors = exc.parse.errors
    _say(f"pointer file refused: {len(errors)} line(s), nothing was sent to a model",
         colour=typer.colors.RED)
    for e in errors:
        _say(f"  line {e.line_no}: {e.reason}", colour=typer.colors.RED)
    if as_json:
        _doc({"status": "pointer_errors", "exit_code": EXIT_POINTERS,
              "errors": [e.model_dump() for e in errors]})
    return EXIT_POINTERS


def _finish(review: VideoReview, as_json: bool) -> int:
    """The json document is the stored review plus `exit_code` (an envelope key, never stored)."""
    code = {"unreadable": EXIT_UNREADABLE, "failed": EXIT_USAGE}.get(review.status, 0)
    if as_json:
        _doc({**review.model_dump(mode="json"), "exit_code": code})
    else:
        typer.echo(render_markdown(review))
    return code


def _find_source(store: ProjectStore, project: str, source_id: str) -> Source:
    if store.load_project() is None:
        raise CliFail(f"no project '{project}' yet")
    source = next((s for s in store.list_sources() if s.id == source_id), None)
    if source is None or not source.path:
        raise CliFail(f"{project} has no recording {source_id} — try `autotester ingest list`.")
    return source


def _read_pointers(path: str | None, as_json: bool) -> str:
    """The pointer file's text; a file over the size limit is refused unread (P5, exit 2)."""
    if not path:
        return ""
    try:
        size = Path(path).stat().st_size
        if size > MAX_POINTER_FILE_BYTES:
            raise typer.Exit(_pointer_errors(PointerErrors(oversize_parse(size)), as_json))
        return Path(path).read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise CliFail(f"cannot read the pointer file ({type(exc).__name__})") from None


def _provider(name: str, model: str | None) -> Provider:
    try:
        prov = providers.get(name, **({"model": model} if model else {}))
    except ProviderError as exc:
        raise CliFail(str(exc)) from None
    if not prov.available():
        raise CliFail(f"provider '{name}' is not available here (no credentials or binary)")
    return prov


def review_cmd(
    project: str = typer.Argument(..., help="project slug"),
    source_id: str = typer.Argument(..., help="a source id from `ingest list`"),
    pointers: str = typer.Option(None, "--pointers", help="file: one pointer per line "
                                 "(12:30, ~12:30, 12:30-14:00, optional '| note'; up to 3 free)"),
    redact: Annotated[list[str] | None, typer.Option(
        "--redact", help="START-END window to black out and mute before a model sees it")] = None,
    provider: str = typer.Option("gemini", "--provider", help="the model frames go to"),
    model: str = typer.Option(None, "--model", help="override the provider's default model"),
    max_cost: float = typer.Option(DEFAULT_MAX_COST_USD, "--max-cost",
                                   help="spend cap in USD; the review stops there, as partial"),
    dry_run: bool = typer.Option(False, "--dry-run", help="print the plan; zero model calls"),
    refresh: bool = typer.Option(False, "--refresh", help="re-run even if a review is stored"),
    output: str = typer.Option("text", "--output", help="text | json (JSON on stdout only)"),
) -> None:
    """Review one recording: a flow summary and a short confirm-list citing exact seconds.
    Pointers raise attention; they never hide the rest. Exit 0 ok, 2 pointer errors, 3 approval
    missing, 4 source unreadable; --output json writes one JSON document on every exit."""
    if output not in ("text", "json"):
        _say("--output must be text or json", colour=typer.colors.RED)
        raise typer.Exit(EXIT_USAGE)
    as_json = output == "json"
    try:
        _review(project, source_id, pointers, redact or [], provider, model, max_cost,
                dry_run, refresh, as_json)
    except CliFail as exc:
        raise typer.Exit(_fail(exc, as_json)) from None
    except (typer.Exit, typer.Abort, TyperException):
        raise
    except KeyboardInterrupt:
        fail = CliFail("interrupted; nothing stored", EXIT_INTERRUPTED, "interrupted")
        raise typer.Exit(_fail(fail, as_json)) from None
    except Exception as exc:
        reason = _failure_reason(exc, project, source_id)
        raise typer.Exit(_fail(CliFail(reason, EXIT_USAGE, "internal_error"), as_json)) from None


def _failure_reason(exc: Exception, project: str, source_id: str) -> str:
    """An unexpected error as one safe line: class name plus message through the Redactor (the
    project's secrets), the recording's path masked. Never raises; no secrets, no message."""
    name = type(exc).__name__
    try:
        store = ProjectStore(project)
        text = Redactor(_secret_values(store)).scrub(str(exc))
        path = next((s.path for s in store.list_sources() if s.id == source_id and s.path), "")
        for hidden in (path, Path(path).as_posix(), Path(path).name) if path else ():
            text = text.replace(hidden, "<recording>")
        text = " ".join(text.split())[:300]
    except Exception:                                          # last-resort path
        text = ""
    return f"unexpected {name} during the review" + (f": {text}" if text else "; nothing stored")


def _review(project: str, source_id: str, pointers: str | None, redact: list[str],
            provider: str, model: str | None, max_cost: float, dry_run: bool, refresh: bool,
            as_json: bool) -> None:
    if not math.isfinite(max_cost) or max_cost < 0:    # NaN or inf would silently remove the cap
        raise CliFail("--max-cost must be a finite number of dollars, 0 or more")
    store = ProjectStore(project)
    source = _find_source(store, project, source_id)
    video = Path(source.path or "")
    _require_readable(source, video, as_json)
    prov, text = _provider(provider, model), _read_pointers(pointers, as_json)
    windows = _windows(redact, video)
    plan_fn = partial(preview_review, video, text, windows, provider_label=prov.label)
    try:
        if dry_run:
            return _print_plan(plan_fn(), as_json)
        gate = build_gate(store, project, prov, plan_fn, local_operator_permission)
        _say(f"reviewing {source_id} with {prov.id} (cap ${max_cost:g})")
        review = run_review(
            store.paths, source, video, prov, load_transcript(store, source), gate=gate,
            secrets=_secret_values(store), pointer_text=text, windows=windows,
            max_cost_usd=max_cost, refresh=refresh)
    except PointerErrors as exc:
        raise typer.Exit(_pointer_errors(exc, as_json)) from None
    except ReviewRefused as exc:
        raise CliFail(str(exc), EXIT_REFUSED) from None
    if code := _finish(review, as_json):
        raise typer.Exit(code)


def _require_readable(source: Source, video: Path, as_json: bool) -> None:
    """TV3: a missing, empty, corrupt or audio-only file is exit 4, before any approval check
    (nothing is spent) and never a review that looks verified."""
    if why := unreadable_reason(video):
        _say(f"{source.id}: {why}", colour=typer.colors.RED)
        if as_json:
            _doc({"status": "unreadable", "source_id": source.id, "reason": why,
                  "exit_code": EXIT_UNREADABLE})
        raise typer.Exit(EXIT_UNREADABLE)


def _windows(specs: list[str], video: Path) -> list[RedactionWindow]:
    try:
        return parse_windows(specs, probe(video)[0])
    except ValueError as exc:
        raise CliFail(str(exc)) from None


def _secret_values(store: ProjectStore) -> dict[str, str]:
    proj = store.load_project()
    return SecretStore.load(proj, store.paths.env_file, strict=False).scrub_values()


def _print_plan(plan: ReviewPlan, as_json: bool) -> None:
    if as_json:
        _doc({**plan.model_dump(mode="json"), "exit_code": 0})
        return
    wins = ", ".join(f"{w.start_s:g}s-{w.end_s:g}s" for w in plan.windows) or "none"
    typer.echo(f"plan: {plan.frame_count} frame(s) in {plan.call_count} call(s), "
               f"{plan.redacted_frame_count} held back by redaction (windows: {wins}), "
               f"estimated cost ${plan.est_cost_usd:.4f}; no model was called")
