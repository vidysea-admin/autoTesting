import sys, json, hashlib, pathlib, autotester
mode, root = sys.argv[1], pathlib.Path(sys.argv[2])
print("autotester at", autotester.__file__)
from autotester.store.project_store import ProjectStore
from autotester.schema.project import Source, Project
from autotester.schema.enums import SourceKind
import shutil
if mode == "write":
    shutil.rmtree(root, ignore_errors=True)
    st = ProjectStore("demo", root)
    st.save_project(Project(slug="demo", name="Demo", base_url="https://x.test", allowed_domains=["x.test"]))
    srcs=[Source(project="demo", kind=SourceKind.TEXT, text="hello"),
          Source(project="demo", kind=SourceKind.URL if hasattr(SourceKind,"URL") else list(SourceKind)[0], url="https://x.test/v", label="l", notes="n", recorded_on="2026-01-01", duration_s=3.5)]
    for s in srcs: st.add_source(s)
    print("ids", [s.id for s in st.list_sources()])
elif mode == "rewrite":
    # read with this code, re-write everything through the store, compare bytes
    st = ProjectStore("demo", root)
    p = st.paths
    before = {f: hashlib.sha256(f.read_bytes()).hexdigest() for f in (p.sources_index, p.config)}
    ids = [s.id for s in st.list_sources()]
    # rewrite sources into a second root via add_source, and project via save_project
    r2 = root.parent / (root.name + "-rw")
    shutil.rmtree(r2, ignore_errors=True)
    st2 = ProjectStore("demo", r2)
    st2.save_project(st.load_project())
    for s in st.list_sources(): st2.add_source(s)
    after = {f: hashlib.sha256(f.read_bytes()).hexdigest() for f in (st2.paths.sources_index, st2.paths.config)}
    print("ids-unchanged", ids == [s.id for s in st2.list_sources()], ids)
    print("sources bytes identical", before[p.sources_index]==after[st2.paths.sources_index])
    print("project bytes identical", before[p.config]==after[st2.paths.config])
    print("sources line:", p.sources_index.read_text().splitlines()[0][:300])
elif mode == "prov":
    from datetime import datetime, timezone
    shutil.rmtree(root, ignore_errors=True)
    st = ProjectStore("demo", root)
    st.save_project(Project(slug="demo", name="Demo", base_url="https://x.test", allowed_domains=["x.test"]))
    plain = Source(project="demo", kind=SourceKind.TEXT, text="hello")
    prov = Source(project="demo", kind=SourceKind.TEXT, text="hello", uploaded_by="u1", uploaded_at=datetime(2026,10,11,tzinfo=timezone.utc), origin="upload")
    print("id plain==prov", plain.id==prov.id, plain.id)
    st.add_source(prov)
    print("line:", st.paths.sources_index.read_text().strip())
    # re-ingest idempotent: add plain again => no dup
    st.add_source(plain); print("count after re-add plain", len(st.list_sources()))
elif mode == "readprov":
    st = ProjectStore("demo", root)
    try:
        print("loaded", st.list_sources())
    except Exception as e:
        print("READ-ERROR", type(e).__name__, str(e)[:400])
