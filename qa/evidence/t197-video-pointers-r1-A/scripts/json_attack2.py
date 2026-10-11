import os, sys, subprocess, shutil, json
from pathlib import Path
W = Path(r"D:/autoTesting/.worktrees/t197-video-pointers")
sys.path[:0] = [str(W/"src"), str(W/"tests")]
import autotester
from typer.testing import CliRunner
from video_review_fakes import RecordingProvider, item, reply_of
from autotester import providers
from autotester.cli import app
from autotester.schema.enums import ApprovalKind
from autotester.schema.project import Project
from autotester.stages.ingest import register_source
from autotester.store.project_store import ProjectStore
from run_approval_fixture import grant_live_case_approval
T = Path(sys.argv[1]); shutil.rmtree(T, ignore_errors=True); T.mkdir(parents=True)
os.environ["AUTOTESTER_ROOT"] = str(T); os.environ["AUTOTESTER_APPROVAL_KEY"] = "checker-r1a-throwaway-key-0123456789abcdef"
vid = T/"rec.mp4"
subprocess.run(["ffmpeg","-y","-f","lavfi","-i","color=c=blue:s=64x48:r=1:d=130","-c:v","libx264","-preset","veryfast",str(vid)],check=True,capture_output=True)
store = ProjectStore("demo", T)
store.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test", allowed_domains=["demo.test"]))
src = register_source(store, vid, label="rec")
grant_live_case_approval(store, project="demo", target="fake", max_actions=500, run_kind=ApprovalKind.VIDEO_REVIEW)
class Boom(RecordingProvider):
    def __init__(s, exc): super().__init__(); s.exc = exc
    def judge(s,*a,**k): raise s.exc
cur = {"p": RecordingProvider([reply_of([item(source_id=src.id, time_s=70)])]*20)}
providers.get = lambda _id, **kw: cur["p"]
runner = CliRunner()
def run(*args, prov=None):
    if prov is not None: cur["p"] = prov
    r = runner.invoke(app, ["ingest","review","demo",src.id,"--output","json",*args], catch_exceptions=True)
    try: json.loads(r.stdout); ok = "one-doc"
    except Exception: ok = f"NO-DOC stdout={r.stdout[:60]!r}"
    exc = f" exc={type(r.exception).__name__}" if r.exception and not isinstance(r.exception, SystemExit) else ""
    print(f"{' '.join(args)[:50]:52} exit={r.exit_code} {ok}{exc}")

def go(label, prov, *args):
    cur["p"] = prov
    r = runner.invoke(app, ["ingest","review","demo",src.id,"--output","json","--refresh",*args], catch_exceptions=True)
    try: json.loads(r.stdout); ok="one-doc"
    except Exception: ok=f"NO-DOC stdout={r.stdout[:40]!r}"
    print(f"{label:30} exit={r.exit_code} {ok} exc={type(r.exception).__name__ if r.exception else None} stderr={r.stderr[-80:]!r}")
go("provider RuntimeError", Boom(RuntimeError("provider blew up")))
go("provider OSError", Boom(OSError("disk")))
go("provider KeyboardInterrupt", Boom(KeyboardInterrupt()))
from autotester.providers.base import ProviderError
go("provider ProviderError", Boom(ProviderError("bad")))
go("redact+RuntimeError", Boom(RuntimeError("x")), "--redact","1:00-1:10")
