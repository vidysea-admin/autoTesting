import json, sys
spec = json.loads(sys.stdin.read())
sys.argv = ["uvicorn", "autotester.ui.app:app", *spec["args"]]
import autotester
from fastapi.testclient import TestClient
from autotester.ui.app import app
out = []
for scheme, host in spec["probes"]:
    c = TestClient(app, base_url=f"{scheme}://testserver", follow_redirects=False, headers={"host": host})
    g = c.get("/auth/login")
    p = c.post("/auth/login", data={"email": "admin@at.example", "password": "scratch-pass-12345"},
               headers={"origin": f"{scheme}://{host}"})
    out.append({"scheme": scheme, "host": host, "GET": g.status_code, "POST": p.status_code,
                "served": g.status_code == 200 and p.status_code == 303})
print(json.dumps(out))
