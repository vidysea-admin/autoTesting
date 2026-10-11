"""Source.origin probe (MR1-B). usage: drive_origin.py gen OUT.json | load OUT.json SAMPLES.json"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import zipfile
from pathlib import Path

os.environ["AUTOTESTER_ALLOWED_HOSTS"] = "testserver"
os.environ.pop("PYTEST_CURRENT_TEST", None)
sys.path.insert(0, os.path.join(os.getcwd(), "tests"))

import autotester  # noqa: E402
from autotester.schema.project import Project, Source  # noqa: E402
from autotester.store.project_store import ProjectStore  # noqa: E402

mode = sys.argv[1]
out = {"file": autotester.__file__}
TS = re.compile(r"\d{4}-\d{2}-\d{2}T[\d:.]+(?:Z|[+-]\d\d:\d\d)?")


def new_root():
    root = Path(tempfile.mkdtemp(prefix="so-", dir=os.environ["PROBE_TMP"]))
    os.environ["AUTOTESTER_ROOT"] = str(root)
    st = ProjectStore("demo", root)
    st.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test", allowed_domains=["demo.test"]))
    return root, st


if mode == "gen":
    from drive_fakes import FakeDrive
    from fastapi.testclient import TestClient
    from zip_fixtures import video

    from autotester.ui import intake_gate, routes_intake
    from autotester.ui.app import app
    from ui_intake_support import FakeGate

    root, st = new_root()
    intake_gate.set_gate(FakeGate())
    fake = FakeDrive()
    routes_intake.drive_factory = lambda _s: fake
    c = TestClient(app)
    r1 = c.post("/projects/demo/sources/upload", files={"recording": ("clip.mp4", video("up"), "video/mp4")}, follow_redirects=False)
    zp = root / "in.zip"
    with zipfile.ZipFile(zp, "w") as z:
        z.writestr("a/one.mp4", video("z1"))
        z.writestr("b/two.mp4", video("z2"))
    r2 = c.post("/projects/demo/sources/upload", files={"recording": ("bundle.zip", zp.read_bytes(), "application/zip")}, follow_redirects=False)
    fid = fake.add("FILE000001", video("drv"), name="Walk.mp4")
    r3 = c.post("/projects/demo/sources/drive", data={"link": f"https://drive.google.com/file/d/{fid}/view"})
    out["statuses"] = [r1.status_code, r2.status_code, r3.status_code]
    raw = (st.paths.sources_index).read_text(encoding="utf-8")
    out["raw_lines"] = raw.splitlines()
    out["origins"] = [(type(s.origin).__name__, str(s.origin)) for s in st.list_sources()]
    out["normalised"] = [TS.sub("TS", ln) for ln in raw.splitlines()]
    # path values contain the temp root: normalise
    out["normalised"] = [ln.replace(str(root).replace("\\", "\\\\"), "ROOT") for ln in out["normalised"]]

elif mode == "load":
    samples = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
    root, st = new_root()
    rows = {}
    base = json.loads(samples["base_line"])
    for label, origin in samples["origins"].items():
        doc = dict(base)
        if origin == "__ABSENT__":
            doc.pop("origin", None)
        else:
            doc["origin"] = origin
        line = json.dumps(doc, separators=(",", ":"))
        res = {}
        try:
            s = Source.model_validate_json(line)
            res["accepted"] = True
            res["arm"] = type(s.origin).__name__
            res["origin_repr"] = repr(s.origin)
            dumped = s.model_dump_json(exclude_none=True)
            res["resave_origin_json"] = json.loads(dumped).get("origin", "__ABSENT__")
            res["id_unchanged"] = s.id == doc["id"]
            # byte comparison of a whole re-save, against the input compacted the same way
            res["bytes_equal_after_resave"] = (json.dumps(json.loads(dumped), sort_keys=True) == json.dumps(doc, sort_keys=True))
            s2 = Source.model_validate_json(dumped)
            res["load_save_load_equal"] = s2 == s
            # through the real store file
            p = st.paths.sources_index
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(line + "\n", encoding="utf-8")
            listed = st.list_sources()
            res["store_list_len"] = len(listed)
        except Exception as exc:  # noqa: BLE001
            res["accepted"] = False
            res["error"] = type(exc).__name__ + ": " + str(exc).splitlines()[0][:80] + " | " + " ; ".join(
                sorted({e["type"] for e in getattr(exc, "errors", lambda: [])()})) if hasattr(exc, "errors") else str(exc)[:100]
            try:
                p = st.paths.sources_index
                p.write_text(line + "\n", encoding="utf-8")
                res["store_list"] = f"len={len(st.list_sources())}"
            except Exception as exc2:  # noqa: BLE001
                res["store_list"] = type(exc2).__name__
        rows[label] = res
    out["rows"] = rows
    exact = []
    for ln in samples["raw_lines"]:
        exact.append(Source.model_validate_json(ln).model_dump_json(exclude_none=True) == ln)
    out["master_lines_byte_exact_after_resave"] = exact
    # constructing in code
    from autotester.schema.intake import DriveOrigin, UploadOrigin, ZipOrigin
    code = {}
    for label, make in {
        "DriveOrigin(file_id)": lambda: DriveOrigin(file_id="F1"),
        "ZipOrigin(...)": lambda: ZipOrigin(archive_name="a.zip", member_path="x/y.mp4"),
        "UploadOrigin(...)": lambda: UploadOrigin(file_name="c.mp4"),
        "UploadOrigin(kind='zip')": lambda: UploadOrigin(kind="zip", file_name="c.mp4"),
        "DriveOrigin(extra)": lambda: DriveOrigin(file_id="F", file_name="x"),
    }.items():
        try:
            o = make()
            code[label] = f"ok kind={o.kind!r} json={o.model_dump_json()}"
        except Exception as exc:  # noqa: BLE001
            code[label] = type(exc).__name__
    out["code"] = code
    # direct kwarg construction of Source
    from autotester.schema.enums import SourceKind
    for label, orig in {"Source(origin=DriveOrigin)": DriveOrigin(file_id="F1"), "Source(origin='drive')": "drive",
                        "Source(origin=bad 'email')": "email", "Source(origin={'kind':'drive','file_id':'x'})": {"kind": "drive", "file_id": "x"}}.items():
        try:
            s = Source(project="demo", kind=SourceKind.RECORDING, path="p.mp4", sha256="a" * 64, origin=orig)
            code[label] = f"ok {type(s.origin).__name__} id={s.id}"
        except Exception as exc:  # noqa: BLE001
            code[label] = type(exc).__name__
Path(sys.argv[2]).write_text(json.dumps(out, indent=1, sort_keys=True, default=str), encoding="utf-8")
print("done", mode)
