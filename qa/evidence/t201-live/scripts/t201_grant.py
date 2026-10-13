import os, pathlib
root=pathlib.Path(".work/t201-root").resolve(); os.environ["AUTOTESTER_ROOT"]=str(root)
for l in (root/".env").read_text().splitlines():
    k,_,v=l.partition("="); os.environ[k]=v
from autotester.schema.approval import RunApproval
from autotester.schema.enums import ApprovalKind
from autotester.store.project_store import ProjectStore
s=ProjectStore("livefix",root); t=s.load_project().base_url
a=RunApproval(project="livefix",run_kind=ApprovalKind.LIVE_CASE,target=t,scope="local fixture site only",max_actions=10000,max_probes=0,wall_clock_s=100000.0,granted_by="t201-live-fixture",granted_at="2026-10-13",expires_at="2099-01-01"); a.sign(); s.add_approval(a); print("granted",t)
