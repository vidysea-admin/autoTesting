"""Walking the shipped CLI surface — a helper, not a test module.

Extracted from `test_cli_surface.py` so both that file and
`test_cli_harness_safety.py` can import it without one test module importing
another (the checker called that acceptable-but-a-smell, and it was only there
because the two files were split at a line cap). Same pattern as
`tests/crawl_fake.py`: pytest does not collect it.

`invocation_for` is itself the subject of a harness-safety test — AT-184 was a
bug in this function, not in a command — which is why it lives somewhere both
can reach.
"""

from __future__ import annotations

from pathlib import Path

import click
from typer.main import get_command

from autotester.cli import app


def shipped_commands() -> list[str]:
    """Walk click's own tree — so a command added tomorrow is covered without
    anyone remembering to add it here. A hand-written list would drift out of
    date silently, which is the failure this file is about."""
    root = get_command(app)
    ctx = click.Context(root)

    def walk(cmd: click.Command, prefix: tuple[str, ...] = ()) -> list[str]:
        subs = getattr(cmd, "commands", None)
        if subs is None and hasattr(cmd, "list_commands"):
            subs = {n: cmd.get_command(ctx, n) for n in cmd.list_commands(ctx)}
        if subs:
            out: list[str] = []
            for name, sub in sorted(subs.items()):
                out += walk(sub, (*prefix, name))
            return out
        return [" ".join(prefix)]

    return walk(root)


def invocation_for(command: str, root: Path | None = None) -> list[str]:
    """The command plus one placeholder per REQUIRED parameter, from click.

    AT-180: the first matrix passed `nonexistent-project nonexistent-id` to
    everything, so 18 of 22 commands got the wrong ARITY and stopped at click's
    `Usage:` banner — the assertion was about click's parser, not about
    autotester. Seeding a project did not help, because the problem was never
    state.

    Arity is a property click already knows, so it is asked rather than
    guessed. Placeholders are deliberately nonexistent: the property under test
    is still "answer a bad invocation cleanly", now from INSIDE the command."""
    root_cmd = get_command(app)
    ctx = click.Context(root_cmd)
    cmd: click.Command = root_cmd
    for part in command.split():
        cmd = cmd.get_command(ctx, part)  # type: ignore[union-attr]

    # AT-184: a placeholder is not always an INPUT. `report excel` takes an
    # output path, so a bare "nonexistent" made the matrix write a file called
    # `nonexistent` into the repo root -- AT-181's shape again, produced by
    # AT-181's own fix. Placeholders are absolute paths inside the temp root, so
    # a command that treats one as a destination cannot reach the repository.
    placeholder = str(root / "nonexistent") if root is not None else "nonexistent"

    argv = command.split()
    if command == "mcp":
        # A valid zero-arity server call cannot be a bounded bad-invocation smoke.
        return [*argv, placeholder]
    for param in cmd.params:
        if not param.required:
            continue
        # A positional's `opts[0]` is its NAME, not a flag. Testing
        # `isinstance(param, click.Argument)` silently failed for typer's
        # parameters, so every positional was passed as "<name> nonexistent"
        # -- doubling the arity and putting the command right back at the
        # `Usage:` banner this helper exists to get past.
        # AT-185: a closed vocabulary rejects a free-text placeholder, so ask
        # click for a value it will accept rather than leaving the command
        # stranded at the parser. The temp root makes the write safe.
        value = placeholder
        choices = getattr(param.type, "choices", None)
        if choices:
            value = str(next(iter(choices)))

        flag = param.opts[0]
        if flag.startswith("-"):
            argv += [flag, value]
        else:
            argv.append(value)
    return argv
