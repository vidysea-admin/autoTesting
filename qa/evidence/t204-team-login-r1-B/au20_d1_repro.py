import os, sys
sys.path.insert(0, r"D:/autoTesting/.worktrees/t204-team-login/src")
from autotester.auth import config
from autotester.ui.helpers import _host_allowed
def run(argv, hosts="", origins=""):
    sys.argv = ["uvicorn", "autotester.ui.app:app", *argv]
    for k, v in (("AUTOTESTER_HOSTED", "1"), ("AUTOTESTER_ALLOWED_HOSTS", hosts), ("AUTOTESTER_ALLOWED_ORIGINS", origins)):
        os.environ[k] = v
    try:
        config.check_startup(); return "startup ok"
    except config.AuthConfigError as e:
        return "RAISES: " + str(e)[:70]
for argv, h, o in [(["--host","10.0.0.5","--port","8443"],"10.0.0.5",""),
                   (["--host","10.0.0.5","--port","8443"],"","https://10.0.0.5"),
                   (["--host","10.0.0.5","--port","8443"],"10.0.0.5:8443",""),
                   (["--host","10.0.0.5"],"10.0.0.5",""),
                   (["--host","10.0.0.5","--port","80"],"10.0.0.5","")]:
    res = run(argv, h, o)
    port = argv[argv.index("--port")+1] if "--port" in argv else "8000"
    os.environ["AUTOTESTER_ALLOWED_HOSTS"] = h; os.environ["AUTOTESTER_ALLOWED_ORIGINS"] = o
    print(argv[1:], "H=%r O=%r" % (h, o), "->", res, "| real Host header 10.0.0.5:%s allowed=%s" % (port, _host_allowed("10.0.0.5:"+port)), "| bare Host allowed=%s" % _host_allowed("10.0.0.5"))
