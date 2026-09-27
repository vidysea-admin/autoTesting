"""Every command this codebase tells an operator to run must actually exist.

AT-163 → AT-172 → AT-176. Three fix cycles of T-132 went on one message naming
`autotester media prep`, a command the CLI does not expose. Then the same dead
end appeared one command over (`ingest analyze`). Then — after this guard was
built to end the class — a checker pointed `PREP_COMMAND` back at the dead name
and **this test returned zero failures**, because the backtick and the command
name lived in different AST nodes.

So the collector no longer scans string literals. `tests/advice_scan.py` renders
each string the way Python will, substituting module constants, and reads
commands out of the result whether or not they are backticked. That took the
visible surface from 5 sites to 9 — including `ingest prep`, the message the
whole class exists for, which the literal scanner could not see.

Two oracles, because they answer different questions:

* **does it resolve** — registered, and takes the arity implied.
* **does it work** — the causal one: trigger the refusal, run the command it
  names, assert the refusal stops firing. That was designed by a checker after
  I argued no such oracle could exist without encoding the answer in the test
  (AT-174). I was wrong; my premise held only for *static* oracles.

Contract: qa/contracts/video-learning.md VL1d, generalised.
"""

from __future__ import annotations

import shlex
from pathlib import Path

import pytest
from advice_scan import (
    advice_in,
    advice_in_source,
    unresolved_in,
    unresolved_in_source,
)
from typer.testing import CliRunner

from autotester.cli import app
from autotester.schema.enums import SourceKind
from autotester.schema.project import Project, Source
from autotester.stages import media_prep
from autotester.store.project_store import ProjectStore

SRC = Path(__file__).resolve().parents[1] / "src" / "autotester"
runner = CliRunner()


def advice() -> list[tuple[Path, str]]:
    return advice_in_source(SRC)


def _unprepared_source(tmp_path: Path) -> tuple[ProjectStore, Source]:
    store = ProjectStore("demo", tmp_path)
    store.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test",
                               allowed_domains=["demo.test"]))
    video = tmp_path / "erp1.mp4"
    video.write_bytes(b"fake-mp4")
    source = store.add_source(Source(project="demo", kind=SourceKind.VIDEO,
                                     path=str(video), sha256="deadbeef"))
    return store, source


def test_the_collector_sees_the_COMPOSED_site_not_just_the_constant() -> None:
    """AT-176, pinned by LINE — and AT-206, which is why it has to be.

    The old assertion was `"ingest prep" in commands`, and it **passed with the
    renderer deleted**: `PREP_COMMAND = "autotester ingest prep"` is a plain
    string constant that yields the command on its own, results were deduped to
    `(file, command)`, and so the guard could not tell the message it exists for
    from the ingredient it is built from.

    Both sites are real advice and both must be seen, so this asserts on both
    lines: the constant's own definition, and the f-string that interpolates it
    — which no literal scanner can produce."""
    prep = [a for a in advice()
            if a.command == "ingest prep" and a.where == Path("stages") / "media_prep.py"]
    lines = {a.line for a in prep}
    source = (SRC / "stages" / "media_prep.py").read_text(encoding="utf-8").splitlines()

    assert prep, "no `ingest prep` site in stages/media_prep.py at all"
    assert len(lines) >= 2, (
        f"only one `ingest prep` site found ({prep}) — the composed message and "
        f"the constant it interpolates are different lines, and seeing only one "
        f"of them is how AT-206 hid")
    composed = [n for n in lines if "PREP_COMMAND" in source[n - 1]
                and not source[n - 1].startswith("PREP_COMMAND")]
    assert composed, (
        f"no site INTERPOLATES PREP_COMMAND was collected; lines seen: {sorted(lines)}. "
        f"That is the AT-176 shape, and the renderer is the only thing that can see it")


def test_a_constant_imported_from_another_module_still_resolves() -> None:
    """AT-192. Resolution stopped at the file boundary, so AT-176's exact shape
    written one `import` away rendered nothing at all — and an empty result is
    indistinguishable from a file that gives no advice."""
    src = (
        'PREP_COMMAND = "autotester ingest prep"\n'
        'def f(slug):\n'
        '    raise ValueError(f"run `{PREP_COMMAND} {slug}` first")\n')
    imported_src = (
        'from autotester.stages.media_prep import PREP_COMMAND\n'
        'def f(slug):\n'
        '    raise ValueError(f"run `{PREP_COMMAND} {slug}` first")\n')

    same_file = advice_in(src)
    imported = advice_in(imported_src, {"PREP_COMMAND": "autotester ingest prep"})

    assert [c for _, c in same_file] == ["ingest prep", "ingest prep"], (
        "the same-file case should see BOTH the constant and the message")
    assert [c for _, c in imported] == ["ingest prep"], (
        "a constant one import away rendered nothing at all")


def test_documentation_written_as_an_f_string_is_not_read_as_advice() -> None:
    """AT-193. `_is_documentation` matched `Expr(Constant)` only, while the
    renderer had already learned `JoinedStr` and `BinOp` — so this codebase's
    own variable-docstring convention, written either way, was scanned as live
    advice about a command that is dead."""
    joined = advice_in('X = 1\nf"""the old name was autotester media prep and it is dead"""\n')
    concat = advice_in('X = 1\n"the old name was " + "autotester media prep" + " and it is dead"\n')

    assert joined == []
    assert concat == []


def test_the_hole_report_actually_reports_a_hole() -> None:
    """The half that makes the check below mean something.

    Sabotaging `unresolved_in` to return `[]` unconditionally failed NOTHING at
    first — the repo has no holes today, so a detector that can never report is
    indistinguishable from one that finds nothing. That is the same shape as
    AT-206, arriving inside the fix for AT-206. So this hands it a source with a
    known hole: a command-shaped constant imported from outside the tree, whose
    value cannot be known statically. `{slug}` on the same line stays unreported
    — a detector that flags every runtime value is one nobody reads."""
    hole = (
        'from somewhere.unknown import PREP_COMMAND\n'
        'def f(slug):\n'
        '    raise ValueError(f"run `{PREP_COMMAND} {slug}` first")\n')
    assert unresolved_in(hole) == [3]


def test_the_collector_reports_what_it_could_not_resolve() -> None:
    """A hole that returns an empty list looks exactly like a clean scan, which
    is how AT-176 and AT-192 each survived a guard written to catch them. If
    this ever fails, the answer is to resolve the name — not to widen the
    filter until the report is empty again."""
    assert unresolved_in_source(SRC) == []


def test_every_site_is_reported_with_a_line_a_human_can_open() -> None:
    for entry in advice():
        assert entry.line >= 1, entry


EXPECTED_SITES = {
    ("cli.py", "providers"),
    ("cli_orchestrate.py", "ingest register"),
    ("cli_issues.py", "ingest analyze"),
    ("cli_issues.py", "ingest list"),
    ("cli_issues.py", "issues derive"),
    ("cli_issues.py", "issues list"),
    ("cli_video.py", "ingest register"),
    ("cli_video.py", "ingest list"),
    ("core/consent.py", "approve"),
    ("doctor.py", "map"),
    ("doctor.py", "snapshot"),
    ("ledger/render.py", "snapshot"),
    ("stages/analyze_video.py", "providers"),
    ("stages/ingest.py", "ingest register"),
    ("stages/media_prep.py", "ingest prep"),
    ("stages/review.py", "flowspec approve"),
}
"""Every place this codebase tells a human to run something, frozen.

AT-210: without this, the suite could not notice a site DISAPPEARING. The
resolve check below is parametrized over whatever the collector returns, so
deleting a site removes a **case**, not a test — deleting `core/consent.py`'s
advice, the very site AT-178 exists for, dropped the run from 26 tests to 25
and failed nothing. Nine of the eleven sites were freely deletable. The
`len(commands) >= 6` bound this replaced was crude, but it did bite at six;
removing it without putting this in its place was a net loss.

Two sites in `media_prep.py` share a command (the constant and the message that
interpolates it), so this set has ten entries for eleven sites; the count is
asserted separately. AT-110 added a second `core/consent.py` "approve" site
(re-grant an unsigned approval), so that command now has two sites as well."""

EXPECTED_SITE_COUNT = 19


def test_no_advice_site_can_vanish_unnoticed() -> None:
    """The guard AT-210 says was missing. A new site is a deliberate act and
    should be added here; a site that disappears should be a decision, not a
    silently shorter test run."""
    found = {(str(a.where).replace(chr(92), "/"), a.command) for a in advice()}

    assert found == EXPECTED_SITES, (
        f"advice sites changed.{chr(10)}"
        f"gone: {sorted(EXPECTED_SITES - found)}{chr(10)}new: {sorted(found - EXPECTED_SITES)}")
    assert len(advice()) == EXPECTED_SITE_COUNT, [tuple(a) for a in advice()]


@pytest.mark.parametrize("entry", advice(),
                         ids=lambda a: f"{a.where}:{a.line}:{a.command}".replace("\\", "_"))
def test_every_command_the_code_names_is_one_the_cli_exposes(entry) -> None:
    """click prints its `Usage:` banner for an unregistered command, an
    unregistered subcommand and the wrong arity alike, so its absence is one
    oracle covering all three. Measured, not assumed (AT-171)."""
    where, command = entry.where, entry.command
    result = runner.invoke(app, [*shlex.split(command), "--help"])

    assert "Usage:" not in result.output or "--help" in result.output, (
        f"{where}:{entry.line} tells an operator to run `autotester {command}`, "
        f"which the CLI does not expose: {' '.join(result.output.split())[:140]!r}")
    assert "No such command" not in result.output, (
        f"{where}:{entry.line} names a command that does not exist: `autotester {command}`")


def test_the_refusal_names_a_command_that_actually_stops_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AT-174 — the causal oracle, and it is a checker's design, not mine.

    I argued no oracle could tell a correct command from a plausible sibling
    without encoding the answer in the test. True of *static* oracles only.
    This tests the message's PROMISE: it says "run X and this stops", so run X
    and check that it stops."""
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    store, source = _unprepared_source(tmp_path)
    monkeypatch.setattr(media_prep.probe_mod, "ffmpeg_available", lambda: False)

    with pytest.raises(media_prep.SourceNotPrepared) as caught:
        media_prep.require_prepared(store, source.id)
    message = str(caught.value)
    assert "`" in message, f"the refusal named no command: {message}"

    named = message.split("`")[1]
    argv = shlex.split(named)[1:]          # drop the leading "autotester"
    result = runner.invoke(app, argv)

    assert result.exit_code == 0, f"the command the refusal named failed: {result.output}"
    media_prep.require_prepared(store, source.id)   # must no longer raise


def test_a_sibling_command_would_not_satisfy_that_promise(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The half that proves the oracle discriminates. `ingest frames` is
    registered and takes the same two arguments, so every static check passes
    it — and it leaves the refusal firing, which is the whole point."""
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    store, source = _unprepared_source(tmp_path)

    runner.invoke(app, ["ingest", "frames", "demo", source.id])

    with pytest.raises(media_prep.SourceNotPrepared):
        media_prep.require_prepared(store, source.id)
