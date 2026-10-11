import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from zipcraft import build, entry, video
from zip_fixtures import make_store
from autotester.core.paths import ENV_ROOT
from autotester.schema.project import Project
import os
d = Path(tempfile.mkdtemp()); os.environ[ENV_ROOT] = str(d)
st = make_store(d); st.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test", allowed_domains=["demo.test"]))
from autotester.ui.app import app
es = [entry(b"zz.mp4", video("a"), flag=0x800), entry("ok.mp4", video("k"))]
data = bytearray(build(es)); i = data.find(b"zz.mp4"); data[i:i+6] = b"\xffz.mp4"
r = TestClient(app, raise_server_exceptions=False, base_url="http://127.0.0.1").post("/projects/demo/sources/upload", files={"recording": ("h.zip", bytes(data), "application/zip")}, data={"label": "x"})
print(r.status_code, "Partial" in r.text, "corrupt member" in r.text, len(st.list_sources()), [p for p in (d/".work").rglob("*") if p.is_file()])
