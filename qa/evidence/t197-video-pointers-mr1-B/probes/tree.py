"""Walk the whole CLI tree; print one JSON: {file, commands:{path: help_text}}"""
import json, os, sys
os.environ["COLUMNS"] = "100"; os.environ["NO_COLOR"] = "1"; os.environ["TERM"] = "dumb"
import autotester
from autotester.cli import app
import typer, click
from typer.testing import CliRunner
print("AT_FILE", autotester.__file__, file=sys.stderr)
cmd = typer.main.get_command(app)
out = {}
runner = CliRunner()
def walk(c, path):
    r = runner.invoke(app, [*path, "--help"], terminal_width=100)
    out[" ".join(path) or "<root>"] = {"exit": r.exit_code, "help": r.output, "group": hasattr(c, "commands")}
    if hasattr(c, "commands"):
        for name in sorted(c.commands):
            walk(c.commands[name], [*path, name])
walk(cmd, [])
json.dump({"file": autotester.__file__, "commands": out}, sys.stdout, indent=1, sort_keys=True)
