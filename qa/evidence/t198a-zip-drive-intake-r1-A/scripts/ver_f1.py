import sys, zipfile, tempfile, shutil, traceback
from pathlib import Path
tree=Path(sys.argv[1]); work=Path(sys.argv[2])
sys.path[:0]=[str(tree/"src"),str(tree/"tests")]
import autotester; assert str(tree) in autotester.__file__
from zip_fixtures import add_member, make_store, video
from autotester.sources.zip_intake import expand_zip
for which in (0,1,2):
  for ver in (63,64,99,255):
    d=Path(tempfile.mkdtemp(dir=work)); a=d/"in.zip"
    with zipfile.ZipFile(a,"w") as z:
        for i,t in enumerate("abc"):
            info=zipfile.ZipInfo(f"{t}.mp4"); 
            if i==which: info.extract_version=ver
            z.writestr(info, video(t))
    # raw stdlib behaviour
    try: zipfile.ZipFile(a).close(); std="stdlib-ok"
    except Exception as e: std=f"stdlib {type(e).__name__}: {e}"
    store=make_store(d)
    try:
        rep=expand_zip(store,a,max_file_bytes=1<<20)
        out=(rep.status.value,rep.exit_code,[(m.member,m.outcome.value,(m.reason or "")[:50]) for m in rep.members],[s.label for s in store.list_sources()])
    except BaseException as e: out=("CRASH",type(e).__name__,str(e))
    print(f"member#{which} ver={ver/10}: {std} | intake={out}")
    shutil.rmtree(d,ignore_errors=True)
