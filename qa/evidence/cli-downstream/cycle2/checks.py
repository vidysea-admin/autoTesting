"""Bind final scoped Ruff and source-shape checks to frozen source and actual tool outputs."""
import hashlib,importlib.metadata,json,pathlib,subprocess,sys,time
R=pathlib.Path.cwd();E=R/"qa/evidence/cli-downstream/cycle2"
read=lambda p:json.loads(p.read_text(encoding="utf-8"))
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
digest=lambda o:hashlib.sha256(json.dumps(o,sort_keys=True).encode()).hexdigest()
def dump(p,o):p.write_text(json.dumps(o,sort_keys=True,indent=2),encoding="utf-8",newline="\n")
binding=read(E/"run-binding.json");inventory=read(E/"source-inventory.json")
T=pathlib.Path(binding["copy_root"]);env=read(E/"environment.json")
paths=["src/autotester/browser/profiles.py","src/autotester/core/paths.py","src/autotester/schema/run_state.py","src/autotester/stages/expand.py","src/autotester/stages/orchestrate_downstream.py","src/autotester/stages/orchestrate_execute.py","src/autotester/stages/report_export.py","src/autotester/stages/run_case_pipeline.py","src/autotester/ui/run_execution.py","tests/downstream_fixture.py","tests/test_orchestrate_downstream.py","tests/test_run_case_pipeline.py","tests/test_orchestrate_downstream_privacy.py"]
def intact():
 assert all(h(R/p)==v and h(T/p)==v for p,v in inventory.items())
 assert h(E/"run-binding.json")==binding_sha
 assert digest(sorted((d.metadata.get("Name", ""),d.version) for d in importlib.metadata.distributions()))==binding["dependencies_sha256"]
binding_sha=h(E/"run-binding.json")
for tool in ("ruff","shape"):
 intact()
 args=[sys.executable,"-B",str(E/"check_tool.py"),str(T/"src"),tool,*paths]
 receipt={**binding,"check_harness_sha256":h(E/"checks.py"),"check_tool_sha256":h(E/"check_tool.py"),"command":args,"command_sha256":digest(args),"cwd":str(T),"tool":tool,"paths":paths,"status":"running","started_at":time.time(),"started_monotonic":time.monotonic()}
 dump(E/(tool+"-before.json"),receipt)
 with (E/(tool+".log")).open("wb") as stream:
  outcome=subprocess.run(args,cwd=T,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=60)
 receipt.update(status="finished",exit_code=outcome.returncode,finished_at=time.time(),finished_monotonic=time.monotonic(),output_sha256=h(E/(tool+".log")))
 receipt["duration_s"]=receipt["finished_monotonic"]-receipt["started_monotonic"]
 intact()
 receipt["after_source_inventory_sha256"]=digest(inventory)
 lines=(E/(tool+".log")).read_text(encoding="utf-8",errors="replace").splitlines()
 runtime=[line for line in lines if line.startswith("__RUNTIME__")];assert len(runtime)==1
 receipt["runtime_identity"]=json.loads(runtime[0].removeprefix("__RUNTIME__"))
 assert receipt["runtime_identity"]["python"]==binding["python"]
 assert receipt["runtime_identity"]["dependencies_sha256"]==binding["dependencies_sha256"]
 assert pathlib.Path(receipt["runtime_identity"]["import_file"]).is_relative_to(T/"src")
 dump(E/(tool+".json"),receipt)
 assert outcome.returncode==0,(tool,str(E/(tool+".log")))
 print(f"Scoped {tool} passed",flush=True)
