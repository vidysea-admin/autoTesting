"""TF5 (team-foundation.md): a CLI sub-app list lets new command groups register without editing
`cli.py`. The golden is the command names and one-line help `autotester --help` lists."""

from __future__ import annotations

import json
from pathlib import Path

import click
import typer
from typer.testing import CliRunner

from autotester import cli, cli_subapps

GOLDEN = Path(__file__).parent / "golden" / "cli_commands.json"
CLI_PY = Path(cli.__file__)


def command_listing(app: typer.Typer) -> list[list[str]]:
    group = typer.main.get_command(app)
    ctx = click.Context(group)
    return [[name, group.commands[name].get_short_help_str(1000)]
            for name in group.list_commands(ctx)]


def test_help_lists_exactly_the_commands_it_listed_before() -> None:
    assert command_listing(cli.app) == json.loads(GOLDEN.read_text(encoding="utf-8"))


def test_registered_groups_come_from_the_list() -> None:
    names = {name for name, _ in cli_subapps.SUBAPPS}
    assert names == {"ingest", "issues", "schedule"}
    assert names <= {row[0] for row in command_listing(cli.app)}


def test_a_throwaway_subapp_registers_without_editing_cli_py(monkeypatch) -> None:
    sub = typer.Typer(help="throwaway group")

    @sub.command("ping")
    def ping() -> None:
        typer.echo("pong")

    monkeypatch.setattr(cli_subapps, "SUBAPPS", [*cli_subapps.SUBAPPS, ("throwaway-t205", sub)])
    fresh = typer.Typer()
    cli_subapps.register_subapps(fresh)
    result = CliRunner().invoke(fresh, ["throwaway-t205", "--help"])
    assert result.exit_code == 0 and "throwaway group" in result.output
    assert CliRunner().invoke(fresh, ["throwaway-t205", "ping"]).output.strip() == "pong"


def test_cli_py_stays_under_the_cap() -> None:
    assert len(CLI_PY.read_text(encoding="utf-8").splitlines()) <= 300
