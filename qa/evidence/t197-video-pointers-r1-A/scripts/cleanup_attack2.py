import os, sys, subprocess, shutil, threading, time, tempfile
from pathlib import Path
W = Path(r"D:/autoTesting/.worktrees/t197-video-pointers")
sys.path[:0] = [str(W/"src"), str(W/"tests")]
import autotester
assert str(W).lower().replace("/","\\") in autotester.__file__.lower().replace("/","\\"), autotester.__file__
from video_review_fakes import RecordingProvider, item, reply_of, SRC
from autotester.core.paths import ProjectPaths
from autotester.schema.project import Source
from autotester.schema.enums import SourceKind
from autotester.stages.video_review import run_review, ReviewRefused
from autotester.schema.video_review import RedactionWindow
from autotester.providers.base import ProviderError

T = Path(sys.argv[1]); shutil.rmtree(T, ignore_errors=True); T.mkdir(parents=True)
vid = T/"rec.mp4"
subprocess.run(["ffmpeg","-y","-f","lavfi","-i","color=c=blue:s=64x48:r=1:d=130","-c:v","libx264","-preset","veryfast",str(vid)],check=True,capture_output=True)
src = Source(id=SRC, project="p", kind=SourceKind.VIDEO, path="rec.mp4")
WIN=[RedactionWindow(start_s=60, end_s=70)]
def tree(root):
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*")) if root.exists() else []
def fresh(name):
    root = T/name; return root, ProjectPaths("p", root)
def go(name, provider, wins=WIN, **kw):
    root, paths = fresh(name)
    try:
        r = run_review(paths, src, vid, provider, None, gate=lambda: None, secrets={}, windows=wins, refresh=True, **kw)
        out = f"ok status={r.status}"
    except BaseException as e:
        out = f"raised {type(e).__name__}: {str(e)[:80]}"
    return out, tree(root)

class Boom(RecordingProvider):
    def __init__(s, exc): super().__init__([reply_of([item(source_id=SRC, time_s=30)])]*20); s.exc=exc
    def judge(s,*a,**k):
        raise s.exc
        return super().judge(*a,**k)
for name, p in [("ok", RecordingProvider([reply_of([item(source_id=SRC,time_s=30)])]*50)),
                ("kbint", Boom(KeyboardInterrupt())),
                ("runtime", Boom(RuntimeError("x"))),
                ("provider", Boom(ProviderError("x"))),
                ("sysexit", Boom(SystemExit(3)))]:
    out, t = go(name, p)
    print(name, out, "LEFT:", t)
# no windows -> frames cut from the ORIGINAL
out, t = go("nowin", RecordingProvider([reply_of([item(source_id=SRC,time_s=30)])]*50), wins=[])
print("nowin", out, "LEFT:", t)
