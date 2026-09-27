"""`autotester issues` — turn an analysis into the sheet a human tester reads.

AT-220. `stages/issues.py::derive_issues` and `stages/analyze_video.py::analyze`
were both built, checker-PASSed, and had **no caller anywhere under `src/`**. Two
units shipped with no way to run them, and the scorer's refusal message pointed
at `autotester issues derive`, a command that did not exist — so the one message
telling a human how to proceed named a dead end.

Separate from `cli_video.py` because that file is near its line budget and these
commands drive a different stage, which is the same reason `cli_video.py` is
separate from `cli.py`.
"""

from __future__ import annotations

import re
from pathlib import Path

import typer
from fastapi import HTTPException

from autotester.browser.secrets import SecretStore
from autotester.core.paths import ProjectPaths
from autotester.schema.case import Case
from autotester.schema.enums import Action
from autotester.schema.flowspec import ExpectedState, Step
from autotester.schema.issue import Issue
from autotester.schema.project import Project
from autotester.stages.issues import (
    derive_issues,
    export_issues_excel,
    pin_issue_as_case,
    refuse_if_issue_already_pinned,
)
from autotester.store.project_store import PinnedCaseError, ProjectStore
from autotester.ui.helpers import _refuse_unsafe_submission, _require_reachable_navigate_steps

app = typer.Typer(help="Issues derived from a recording — the tester's sheet.")


def _sources_with_analysis(store: ProjectStore) -> list:
    return [s for s in store.list_sources() if store.load_analysis(s.id) is not None]


@app.command("derive")
def derive_cmd(
    project: str = typer.Argument(..., help="project slug"),
    source_id: str = typer.Option(None, "--source",
                                  help="one source; default is every analysed one"),
) -> None:
    """Turn each analysed recording into Issue rows. Idempotent on content."""
    store = ProjectStore(project)
    sources = ([s for s in store.list_sources() if s.id == source_id] if source_id
               else _sources_with_analysis(store))
    if not sources:
        typer.secho(
            f"{project}: no analysed source to derive from. Run `autotester ingest analyze "
            f"{project} <source-id>` first — `autotester ingest list` shows the sources.",
            fg=typer.colors.RED)
        raise typer.Exit(2)

    added = 0
    for source in sources:
        analysis = store.load_analysis(source.id)
        if analysis is None:
            typer.secho(f"  {source.id}: no analysis — skipped", fg=typer.colors.YELLOW)
            continue
        for issue in derive_issues(analysis, source, project):
            before = len(store.list_issues())
            store.add_issue(issue)
            added += len(store.list_issues()) - before

    typer.secho(f"{project}: {added} new issue(s); {len(store.list_issues())} total",
                fg=typer.colors.GREEN)


@app.command("list")
def list_issues_cmd(project: str = typer.Argument(..., help="project slug")) -> None:
    """Every issue derived for this project."""
    issues = ProjectStore(project).list_issues()
    if not issues:
        typer.secho(f"{project}: no issues yet — try `autotester issues derive {project}`.",
                    fg=typer.colors.YELLOW)
        raise typer.Exit(0)
    for issue in sorted(issues, key=lambda i: (i.recording_label, i.at_s)):
        minutes, seconds = divmod(round(issue.at_s), 60)
        typer.echo(f"  {issue.severity.value}  {minutes:02d}:{seconds:02d}  "
                   f"{issue.recording_label[:28]:28s}  {issue.title[:70]}")


_URL_FIELD_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://[^/:]*(?::\d+)?[^:]*")
"""Matches a whole `scheme://host[:port]/path` field: the scheme, `://`, a
host with no `:` or `/` in it, an OPTIONAL `:port`, then a path that runs up
to whatever `:` comes next. AT-597 cycle 2's `(?!//)` lookahead protected
only the scheme's own colon -- "navigate:http://localhost:8069/signup" still
split at the PORT colon, into target='http://localhost', value='8069/signup'
(cycle 2's checker FAIL, one character further along than cycle 1's). This
regex consumes the port colon as part of the same field, so nothing after
`_take_step_field` ever sees it as a separator."""


def _take_step_field(remainder: str) -> tuple[str, str | None]:
    """One field of `_parse_step`'s raw `--step` string, plus whatever still
    follows its separating `:` (`None` once nothing does). A field matching
    `_URL_FIELD_RE` -- a URL, scheme onward -- is taken whole, port and all;
    every other field still splits at its first remaining `:`, exactly like
    the original `str.split(":", 1)` always did."""
    match = _URL_FIELD_RE.match(remainder)
    if match:
        field = match.group(0)
        rest = remainder[len(field):]
        return field, (rest[1:] if rest.startswith(":") else None)
    if ":" in remainder:
        field, rest = remainder.split(":", 1)
        return field, rest
    return remainder, None


def _split_step_fields(remainder: str) -> list[str]:
    """Up to 3 `:`-delimited fields (target, value, expect) out of
    `_parse_step`'s raw string, via `_take_step_field` -- so a URL field's own
    colons (scheme, port) never count as a field separator, wherever in the
    step that URL sits."""
    fields: list[str] = []
    rest: str | None = remainder
    for _ in range(3):
        if rest is None:
            break
        field, rest = _take_step_field(rest)
        fields.append(field)
    return fields


def _parse_step(order: int, raw: str) -> Step:
    """`action:target[:value[:expect]]` — the CLI's compact form of one confirmed
    repro step. Never a guess: the caller types exactly what they just verified
    reproduces the bug, same discipline `pin_issue_as_case` documents for its
    `steps` argument.

    AT-597 cycle 4: every action, NAVIGATE included, tokenizes the remainder
    the same way, field by field via `_split_step_fields` -- which keeps a
    `scheme://host[:port]/path` field whole (via `_take_step_field`'s
    `_URL_FIELD_RE` match) no matter which field position it lands in, so a
    navigate target's own port survives exactly like a fill's URL value does.
    Cycle 3 gave NAVIGATE the whole remainder as its target with no split at
    all, on the reasoning that navigate has no value -- but a navigate DOES
    have a live `expect` (T-184's `Step.expected`, settled and checked post-
    navigate by `execute.py`, E1), and that bypass swallowed a trailing
    `::expect` into the URL instead (cycle 3's checker FAIL, 1133e8b).
    NAVIGATE now takes the same `[target[:value[:expect]]]` tail as every
    other action, but refuses a non-empty value -- a navigate step has
    nowhere to put one -- so `navigate:<url>::<expect>` keeps the expect and
    `navigate:<url>:<anything>:<expect>` is refused with a clear error
    instead of silently corrupting the target.
    """
    action_raw, sep, remainder = raw.partition(":")
    if not sep:
        raise ValueError(
            f"--step '{raw}' must look like 'action:target[:value[:expect]]'"
        )
    try:
        action = Action(action_raw)
    except ValueError as exc:
        known = ", ".join(a.value for a in Action)
        raise ValueError(f"--step '{raw}': '{action_raw}' is not one of {known}") from exc

    fields = _split_step_fields(remainder)
    target = fields[0] if fields else ""
    value = (fields[1].strip() or None) if len(fields) > 1 else None
    expect = fields[2].strip() if len(fields) > 2 else ""
    if action is Action.NAVIGATE and value:
        raise ValueError(
            f"--step '{raw}': navigate has no value field -- write "
            "'navigate:<url>' or 'navigate:<url>::<expect>' for an expect"
        )
    if action is Action.NAVIGATE:
        value = None
    expected = ExpectedState(visible_text=[expect]) if expect else ExpectedState()
    return Step(order=order, action=action, target=target.strip(), value=value, expected=expected)


def _guard_pin_steps(steps: list[Step], project: Project, secrets: SecretStore) -> None:
    """C5: the same two guards the UI pin route runs on a submitted case --
    a raw credential in any target/value/expect box (`ui.helpers.
    _refuse_unsafe_submission`), and a navigate step that could never reach an
    allowed domain (`ui.helpers._require_reachable_navigate_steps`) -- so the
    CLI cannot write what the UI would refuse with a 400."""
    texts: list[tuple[str, str]] = []
    for s in steps:
        texts.append((f"step {s.order} target", s.target))
        if s.value:
            texts.append((f"step {s.order} value", s.value))
        texts.extend((f"step {s.order} expect", line) for line in s.expected.visible_text)
    _refuse_unsafe_submission(texts, project, secrets)
    _require_reachable_navigate_steps(steps, project)


@app.command("pin")
def pin_cmd(
    project: str = typer.Argument(..., help="project slug"),
    issue_id: str = typer.Argument(..., help="issue id (see `issues list`)"),
    step: list[str] = typer.Option(
        None, "--step",
        help="one confirmed repro step, 'action:target[:value[:expect]]'. A navigate "
             "target must be a full URL inside the project's allowed domains. Repeat "
             "in order -- e.g. --step navigate:https://app.example.com/signup "
             "--step click:#submit",
    ),
) -> None:
    """AT-597: pin a confirmed issue as a regression case (T-184/AT-585) — the
    CLI's entry point to `stages/issues.py::pin_issue_as_case`, alongside the
    issues page's 'Pin as regression case' action. Steps are never guessed:
    pass exactly the reproduction steps you confirmed yourself. Runs the same
    credential, reachable-navigate and one-pin-per-issue (AT-604) guards the
    UI route does, so the CLI can never write what the UI would refuse."""
    store = ProjectStore(project)
    proj = store.load_project()
    if proj is None:
        typer.secho(f"no project '{project}' yet", fg=typer.colors.RED)
        raise typer.Exit(2)
    issue = next((i for i in store.list_issues() if i.id == issue_id), None)
    if issue is None:
        typer.secho(f"{project}: no issue '{issue_id}' -- try `autotester issues list {project}`.",
                    fg=typer.colors.RED)
        raise typer.Exit(2)
    if not step:
        typer.secho(
            f"{project}: pinning needs at least one confirmed --step "
            "('action:target[:value[:expect]]') -- steps are never guessed.",
            fg=typer.colors.RED)
        raise typer.Exit(2)
    try:
        steps = [_parse_step(i + 1, raw) for i, raw in enumerate(step)]
        secrets = SecretStore.load(proj, ProjectPaths(project).env_file, strict=False)
        _guard_pin_steps(steps, proj, secrets)
        case = pin_issue_as_case(issue, flow_id="manual", steps=steps, project=project)
        refuse_if_issue_already_pinned(store, issue.id, case.id)
    except (ValueError, HTTPException, PinnedCaseError) as exc:
        message = exc.detail if isinstance(exc, HTTPException) else str(exc)
        typer.secho(f"{project}: {message}", fg=typer.colors.RED)
        raise typer.Exit(2) from exc
    _finish_pin(store, project, issue, case)


def _finish_pin(store: ProjectStore, project: str, issue: Issue, case: Case) -> None:
    """Idempotent tail of `pin_cmd`: a case identical to one already on file
    is a no-op success (`add_case`'s own idempotence), never a second write."""
    if store.has_case(case.id):
        typer.secho(f"{project}: already pinned as case {case.id} -- nothing to do.",
                    fg=typer.colors.YELLOW)
        raise typer.Exit(0)
    store.add_case(case)
    typer.secho(f"{project}: pinned '{issue.title}' as regression case {case.id}",
                fg=typer.colors.GREEN)


@app.command("export")
def export_cmd(
    project: str = typer.Argument(..., help="project slug"),
    out: Path = typer.Option(None, "--out", help="where to write the workbook"),
) -> None:
    """Write the issues as the 13-column workbook a tester can open beside theirs."""
    store = ProjectStore(project)
    issues = store.list_issues()
    if not issues:
        typer.secho(f"{project}: nothing to export — try `autotester issues derive {project}`.",
                    fg=typer.colors.RED)
        raise typer.Exit(2)
    target = out or (store.paths.dir / "issues.xlsx")
    export_issues_excel(issues, target)
    typer.secho(f"{project}: {len(issues)} issue(s) -> {target}", fg=typer.colors.GREEN)
