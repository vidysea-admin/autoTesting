import sys, os
from pathlib import Path
SRC=sys.argv[1]; ARC=Path(sys.argv[2]); WORK=Path(sys.argv[3])
sys.path.insert(0,SRC); sys.path.insert(0,"D:/autoTesting/.worktrees/t198a-zip-drive-intake/tests")
from asgi_helpers import post_stream, multipart_head, multipart_tail, chunked
from autotester.core.paths import ENV_ROOT
from autotester.schema.project import Project
from autotester.store.project_store import ProjectStore
os.environ[ENV_ROOT]=str(WORK)
st=ProjectStore("demo",WORK); st.save_project(Project(slug="demo",name="Demo",base_url="https://demo.test",allowed_domains=["demo.test"]))
data=ARC.read_bytes()
try:
    status,page,_=post_stream("/projects/demo/sources/upload",[multipart_head("bad.zip"),*chunked(data),multipart_tail()],host="localhost")
    print("HTTP status",status, page[:80])
except BaseException as e:
    print("ROUTE RAISED", type(e).__name__, str(e)[:100])
left=[str(p) for p in (WORK/".work").rglob("*") if p.is_file()] if (WORK/".work").exists() else []
print("rows",len(st.list_sources()),"leftover files",left)
