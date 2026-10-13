"""The list of CLI sub-apps `autotester` registers (T-205/TF5, design rule).

One job: hold `SUBAPPS`, the `(name, typer_app)` pairs `cli.py` adds with `add_typer`, so a new
command group (`schedule`, `tracker`, `video review`, ...) is registered by appending one pair
here, never by editing `cli.py`, which sits at the 300-line cap. A sub-app defined in `cli.py`
itself (`ledger`, `flowspec`, `report`) cannot be listed here without a circular import.
"""

from __future__ import annotations

import typer

from autotester import cli_issues, cli_schedule, cli_video
from autotester.cli_auth import app as auth_app

SUBAPPS: list[tuple[str, typer.Typer]] = [
    ("ingest", cli_video.app),
    ("issues", cli_issues.app),
    ("auth", auth_app),  # T-204 team login
    ("schedule", cli_schedule.app),
]


def register_subapps(app: typer.Typer) -> None:
    """Add every `SUBAPPS` pair to `app`, in order."""
    for name, sub in SUBAPPS:
        app.add_typer(sub, name=name)
