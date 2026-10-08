"""The five legacy CLI groups retain exact help, plus the authorized T204 group (TF5)."""

import typer
from typer.main import get_command
from typer.testing import CliRunner

from autotester.cli import app
from autotester.cli_subapps import SUBAPPS, register_subapps

# Captured independently from base 167f7576, before the registration refactor.
LEGACY_HELP = {
    "doctor": "Check the repo against the design rules...",
    "providers": "Show which model providers have...",
    "map": "Regenerate docs/MAP.md — directory map +...",
    "snapshot": "Regenerate docs/SNAPSHOT.md — the digest...",
    "expand": "Generate this project's test cases from...",
    "login": "Open a real browser for a human to log in...",
    "loop-status": "Report gaps in `qa/.last-tick` — was the...",
    "explore": "Bounded BFS crawl of a project, refusing...",
    "approve": "Grant a human's approval for one kind of...",
    "orchestrate": "Run (or resume) the pipeline for...",
    "ledger": "The feature ledger (docs/FEATURES.jsonl) —...",
    "ledger add": "Append one feature event.",
    "ledger weight": "Re-weight a feature after shipping.",
    "ledger check": "L3: every closed high-value goal task has...",
    "ledger relitigation": "Gate check before a unit is built: is this...",
    "flowspec": "The FlowSpec review gate — nothing expands...",
    "flowspec status": "Show a project's FlowSpec review status.",
    "flowspec approve": "A human approves the project's FlowSpec...",
    "flowspec request-edit": "A human found something wrong — back to...",
    "report": "Export a run as a portable tester report...",
    "report excel": "One row per case: outcome, verdict,...",
    "report html": "Screen-by-screen report with embedded...",
    "report crawl": "Summary, screens, edges, refusals, issues...",
    "ingest": "Learn a product's screens and flows from a...",
    "ingest register": "Record a video as a Source.",
    "ingest list": "Every source registered for this project.",
    "ingest prep": "Probe, chunk and transcribe a recording.",
    "ingest frames": "Extract the stills the vision pass named.",
    "ingest run": "Watch one source and write the FlowSpec it...",
    "ingest analyze": "Run the ensemble over a prepared recording...",
    "ingest map": "Fold every persisted video analysis into...",
    "issues": "Issues derived from a recording — the...",
    "issues derive": "Turn each analysed recording into Issue rows.",
    "issues list": "Every issue derived for this project.",
    "issues pin": "AT-597: pin a confirmed issue as a...",
    "issues export": "Write the issues as the 13-column workbook...",
}


def _help_projection(command, prefix: tuple[str, ...] = ()) -> dict[str, str]:
    result = {}
    for name, child in command.commands.items():
        if not prefix and name == "auth":
            continue
        path = (*prefix, name)
        result[" ".join(path)] = child.get_short_help_str()
        if hasattr(child, "commands"):
            result.update(_help_projection(child, path))
    return result


def test_legacy_cli_groups_and_help_are_unchanged() -> None:
    expected = (
        ("ledger", "The feature ledger (docs/FEATURES.jsonl) — the only write path."),
        ("flowspec", "The FlowSpec review gate — nothing expands an unreviewed spec."),
        ("report", "Export a run as a portable tester report (Excel + HTML)."),
        ("ingest", "Learn a product's screens and flows from a screen recording."),
        ("issues", "Issues derived from a recording — the tester's sheet."),
    )
    command = get_command(app)
    assert _help_projection(command) == LEGACY_HELP
    assert tuple((name, command.commands[name].help) for name, _ in expected) == expected
    assert [name for name, _ in SUBAPPS[:5]] == ["ledger", "flowspec", "report", "ingest",
                                              "issues"]
    assert SUBAPPS[5][0] == "auth"
    assert "bootstrap-admin" in command.commands["auth"].commands


def test_appending_a_subapp_makes_it_reachable_without_cli_edits(monkeypatch) -> None:
    extra = typer.Typer(help="Fixture extension")

    @extra.command()
    def fixture() -> None:
        """Fixture command."""

    monkeypatch.setattr("autotester.cli_subapps.SUBAPPS", [*SUBAPPS, ("fixture", extra)])
    probe = typer.Typer()
    register_subapps(probe)
    result = CliRunner().invoke(probe, ["fixture", "--help"])
    assert result.exit_code == 0 and "Fixture extension" in result.output
