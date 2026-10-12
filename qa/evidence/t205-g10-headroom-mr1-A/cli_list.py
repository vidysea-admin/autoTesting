import json, sys, click, typer
from autotester import cli
g = typer.main.get_command(cli.app); ctx = click.Context(g)
json.dump([[n, g.commands[n].get_short_help_str(1000)] for n in g.list_commands(ctx)], open(sys.argv[1], "w", encoding="utf-8"), indent=1, ensure_ascii=True)
