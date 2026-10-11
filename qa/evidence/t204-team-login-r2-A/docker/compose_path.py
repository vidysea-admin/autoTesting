"""Docker path: values compose produces for the app (docker compose config, see ../fuzz/compose) fed to
startup (bind --host 0.0.0.0 --port 8000, entrypoint.sh) and to the real app guard."""
import os, sys
import autotester
print("autotester.__file__", autotester.__file__)
from pathlib import Path
import tempfile
from fastapi.testclient import TestClient
sys.path.insert(0, "D:/autoTesting/.worktrees/t204-team-login/tests")
from autotester.auth.config import AuthConfigError, check_startup
from autotester.ui.app import app

def case(label, public, hosts, origins, browser):
    for k in ("AUTOTESTER_HOSTED","AUTOTESTER_ALLOWED_HOSTS","AUTOTESTER_ALLOWED_ORIGINS","AUTOTESTER_PUBLIC_ORIGIN","UVICORN_HOST","UVICORN_PORT"):
        os.environ.pop(k, None)
    os.environ.update(AUTOTESTER_HOSTED="1", AUTOTESTER_FIRST_ADMIN_EMAIL="boss@at.example",
                      AUTOTESTER_ALLOWED_HOSTS=hosts, AUTOTESTER_ALLOWED_ORIGINS=origins,
                      AUTOTESTER_PUBLIC_ORIGIN=public)
    sys.argv = ["uvicorn", "autotester.ui.app:app", "--host", "0.0.0.0", "--port", "8000"]
    try:
        check_startup(); start = "STARTS"
    except AuthConfigError as e:
        start = "RAISES: " + str(e)[:70]
    scheme, host = browser
    c = TestClient(app, base_url="http://testserver", follow_redirects=False, headers={"host": host})
    g = c.get("/auth/login").status_code
    p = c.post("/auth/login", data={"email": "x@y.z", "password": "p"}, headers={"origin": f"{scheme}://{host}"}).status_code
    print(f"{label:60s} startup={start:60s} browser {scheme}://{host}: GET {g} POST {p}")

D="https://qa.example.com"
case("1 no vars (compose -> https://localhost), lists name domain", "https://localhost", "qa.example.com", D, ("https","qa.example.com"))
case("2 no vars (compose -> https://localhost), lists name WRONG", "https://localhost", "other.example.com", "https://other.example.com", ("https","qa.example.com"))
case("3 no vars, IP interim lists right, PUBLIC unset by op -> localhost", "https://localhost", "192.168.1.20:8000", "http://192.168.1.20:8000", ("http","192.168.1.20:8000"))
case("4 no vars, IP interim lists WRONG ip", "https://localhost", "192.168.1.99:8000", "http://192.168.1.99:8000", ("http","192.168.1.20:8000"))
case("5 DOMAIN only (-> https://qa.example.com), lists name domain", D, "qa.example.com", D, ("https","qa.example.com"))
case("6 DOMAIN only, lists name WRONG domain", D, "other.example.com", "https://other.example.com", ("https","qa.example.com"))
case("7 DOMAIN only, only HOSTS set (no ORIGINS)", D, "qa.example.com", "", ("https","qa.example.com"))
case("8 DOMAIN only, ORIGINS only (host from origin)", D, "", D, ("https","qa.example.com"))
case("9 DOMAIN only, origin has explicit :443", D, "", D+":443", ("https","qa.example.com"))
