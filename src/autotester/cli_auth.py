"""`autotester auth` -- break-glass account administration from the server shell (T-204).

`bootstrap-admin` creates an admin account, or resets an existing account's password,
re-enables it, puts it in Admin/CEO and ends its sessions. The password is read from
stdin or a hidden prompt, never from a command-line argument (shell history, `ps`).
"""

from __future__ import annotations

import sys

import typer

from autotester.auth.accounts import AccountError, bootstrap_admin
from autotester.auth.passwords import WeakPassword

app = typer.Typer(help="Team login accounts (T-204).", no_args_is_help=True)


@app.command("bootstrap-admin")
def bootstrap_admin_cmd(
    email: str = typer.Option(..., "--email", help="the admin account's email"),
    password_stdin: bool = typer.Option(
        False, "--password-stdin", help="read the password from the first stdin line"),
) -> None:
    """Create or reset an admin account."""
    if password_stdin:
        password = sys.stdin.readline().rstrip("\r\n")
    else:
        password = typer.prompt("Password", hide_input=True, confirmation_prompt=True)
    try:
        user, created = bootstrap_admin(email, password)
    except (AccountError, WeakPassword) as exc:
        typer.echo(f"refused: {exc}", err=True)
        raise typer.Exit(2) from exc
    typer.echo(f"{'created' if created else 'reset'} admin {user.email} "
               f"(groups: {', '.join(user.groups)})")
