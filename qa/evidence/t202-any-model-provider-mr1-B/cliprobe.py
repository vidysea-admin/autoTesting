import os, sys
os.environ.pop("AUTOTESTER_MODEL", None)
from typer.testing import CliRunner
from autotester.cli import app
import autotester
print("autotester at", autotester.__file__)
r = CliRunner()
for args in (["ledger","relitigation","some unit","--provider","litellm"],
             ["ledger","relitigation","some unit","--provider","litellm:ollama/llama3"]):
    res = r.invoke(app, args)
    print(args[-1], "exit", res.exit_code, "|", (res.output or "").strip()[:200].replace("\n"," "), "| exc:", type(res.exception).__name__ if res.exception else None, str(res.exception)[:120] if res.exception else "")
res = r.invoke(app, ["providers"]); print("providers:", res.output.strip())
os.environ["AUTOTESTER_MODEL"]="ollama/llama3"; os.environ["OLLAMA_BASE_URL"]="http://127.0.0.1:9"
res = r.invoke(app, ["providers"]); print("providers with model+base:", res.output.strip())
