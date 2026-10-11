from common import *
root = setup("famB3")
import re
from urllib.parse import urlencode
from fastapi.testclient import TestClient
from autotester.ui.app import app
c = TestClient(app, follow_redirects=False, raise_server_exceptions=False)
for mb in (1, 2, 4, 8, 16, 32):
    body = urlencode({"email": "x@team.test", "password": "a" * (mb * 1000 * 1000)}).encode()
    r = c.post("/auth/login", content=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
    p(f"urlencoded password {mb:2d} MB -> {r.status_code} {re.sub(chr(10),' ',r.text[:90])!r}")
for mb in (0.5, 1, 2):
    body = (f'--b\r\nContent-Disposition: form-data; name="password"\r\n\r\n' + "a" * int(mb * 1e6) + '\r\n--b--\r\n').encode()
    r = c.post("/auth/login", content=body, headers={"Content-Type": "multipart/form-data; boundary=b"})
    p(f"multipart password part {mb} MB -> {r.status_code} {r.text[:90]!r}")
for n in (1000, 1001, 5000):
    body = urlencode({f"f{i}": "v" for i in range(n)}).encode()
    r = c.post("/auth/login", content=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
    p(f"{n} urlencoded fields -> {r.status_code}")
import starlette, inspect
p("starlette", starlette.__version__)
