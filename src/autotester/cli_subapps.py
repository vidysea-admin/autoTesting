"""Register the existing five CLI sub-apps through one extensible hook."""

import typer

from autotester import cli_issues, cli_video
from autotester.cli_auth import app as auth_app

ledger_app = typer.Typer(help="The feature ledger (docs/FEATURES.jsonl) — the only write path.")
flowspec_app = typer.Typer(help="The FlowSpec review gate — nothing expands an unreviewed spec.")
report_app = typer.Typer(help="Export a run as a portable tester report (Excel + HTML).")
SUBAPPS: list[tuple[str, typer.Typer]] = [
    ("ledger", ledger_app), ("flowspec", flowspec_app), ("report", report_app),
    ("ingest", cli_video.app), ("issues", cli_issues.app),
    ("auth", auth_app),
]


def register_subapps(app: typer.Typer) -> None:
    for name, subapp in SUBAPPS:
        app.add_typer(subapp, name=name)
