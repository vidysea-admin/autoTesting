import sys, json, os, subprocess
import typer
from typer.main import get_command
import autotester
from autotester.cli import app
print(autotester.__file__, file=sys.stderr)
# walk the click tree; run --help for each group/command in subprocess-free CliRunner
from typer.testing import CliRunner
r = CliRunner()
out = {}
def walk(cmd, path):
    res = r.invoke(app, path + ["--help"], terminal_width=100) if path else r.invoke(app, ["--help"], terminal_width=100)
    out[" ".join(path) or "(root)"] = [res.exit_code, res.output]
    if hasattr(cmd, "commands"):
        for n, sub in sorted(cmd.commands.items()):
            walk(sub, path + [n])
walk(get_command(app), [])
gp = os.path.join(os.getcwd(), "tests/golden/cli_commands.json"); golden = json.load(open(gp, encoding="utf-8")) if os.path.exists(gp) else None
cmd = get_command(app)
import click
ctx = click.Context(cmd)
live = [[n, cmd.commands[n].get_short_help_str(1000)] for n in cmd.list_commands(ctx)]
out["__golden_equals_live"] = live == golden
json.dump({"help": out, "live_listing": live, "golden_len": len(golden or [])}, open(sys.argv[1], "w"), indent=1, sort_keys=True)
print(len(out), "help pages")
