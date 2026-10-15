"""Validate fresh proof triples and all immutable narration evidence bindings before dispatch."""
import hashlib,importlib.metadata,json,pathlib,subprocess,sys
R=pathlib.Path.cwd();E=R/"qa/evidence/narration-policy/cycle2"
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
digest=lambda o:hashlib.sha256(json.dumps(o,sort_keys=True).encode()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding="utf-8"))
binding=read(E/"run-binding.json");inventory=read(E/"source-inventory.json")
assert binding["source_candidate"]=="a16c2a53e3ba5ff09533210aacd29ddf56d5ac56"
assert binding["base_candidate"]=="40f5b4b20e91d3806ee313fb8e67af109b62b0ae"
assert binding["proof_checkout"]=="e30a5ab8b6ffe36e68a96c115c42d228a59b7f13"
assert binding["harness_sha256"]==h(E/"proof.py") and binding["invoke_sha256"]==h(E/"invoke.py")
assert binding["spec_sha256"]==h(R/binding["spec_path"])
assert binding["inventory_sha256"]==digest(inventory)
assert binding["inventory_file_sha256"]==h(E/"source-inventory.json")
assert all(h(R/k)==v for k,v in inventory.items())
assert binding["lock_sha256"]==h(R/"uv.lock")
assert binding["python_sha256"]==h(pathlib.Path(sys.executable))
assert binding["python_version"]==sys.version and binding["python"]==sys.executable
for name in ("dependencies","environment"):
 data=read(E/(name+".json"))
 assert binding[name+"_sha256"]==digest(data)
 assert binding[name+"_file_sha256"]==h(E/(name+".json"))
assert read(E/"dependencies.json")==[list(x) for x in sorted((d.metadata.get("Name", ""),d.version) for d in importlib.metadata.distributions())]
env=read(E/"environment.json")
assert env["PYTHONDONTWRITEBYTECODE"]=="1" and env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"]=="1"
assert set(env)<={"SYSTEMROOT","WINDIR","PATH","PATHEXT","COMSPEC","USERPROFILE","APPDATA","LOCALAPPDATA","PYTHONPATH","PYTHONDONTWRITEBYTECODE","PYTHONUTF8","PYTHONHASHSEED","PYTEST_ADDOPTS","PYTEST_DISABLE_PLUGIN_AUTOLOAD","OMP_THREAD_LIMIT","TEMP","TMP"}
assert subprocess.run(["git","diff","--quiet",binding["source_candidate"],"--","src","tests","scripts","pyproject.toml","uv.lock"],cwd=R).returncode==0
spec=read(R/binding["spec_path"]);ledger=read(E/"mutation-ledger.json");completed=read(E/"completed.json")
assert len(spec["mutations"])==len(ledger)==completed["triples"]==15
assert completed["binding_sha256"]==h(E/"run-binding.json") and completed["ledger_sha256"]==h(E/"mutation-ledger.json")
assert completed["all_restored"] is True
validated=[]
def receipt(name,expected_inventory,exit_code):
 post=read(E/name);label=post["label"];before=read(E/(label+"-before.json"));logfile=E/(label+".log")
 assert before["status"]=="running" and post["status"]=="finished"
 assert all(post[k]==v for k,v in before.items() if k!="status")
 assert all(post[k]==v for k,v in binding.items())
 assert post["command_sha256"]==digest(post["command"])
 assert post["source_inventory_sha256"]==post["after_source_inventory_sha256"]==digest(expected_inventory)
 assert post["file_overrides"]=={k:v for k,v in expected_inventory.items() if inventory[k]!=v}
 assert post["exit_code"]==exit_code and post["output_sha256"]==h(logfile)
 assert post["finished_at"]>=post["started_at"] and post["finished_monotonic"]>=post["started_monotonic"]
 assert post["duration_s"]==post["finished_monotonic"]-post["started_monotonic"]
 actual=post["runtime_identity"]
 assert actual["python"]==binding["python"] and actual["version"]==binding["python_version"]
 assert actual["dependencies_sha256"]==binding["dependencies_sha256"]
 assert pathlib.Path(actual["import_file"]).is_relative_to(pathlib.Path(binding["copy_root"])/"src")
 lines=logfile.read_text(encoding="utf-8",errors="replace").splitlines()
 runtime=[line for line in lines if line.startswith("__RUNTIME__")]
 assert len(runtime)==1 and json.loads(runtime[0].removeprefix("__RUNTIME__"))==actual
 validated.append(name)
 return post,"\n".join(lines)
green,glog=receipt("shared-green.json",inventory,0);assert "17 passed" in glog
for m,row in zip(spec["mutations"],ledger,strict=True):
 raw=(R/m["file"]).read_bytes();text=raw.decode("utf-8");assert text.count(m["old"])==row["anchor_count"]==1
 changed=text.replace(m["old"],m["new"],1).encode("utf-8");assert changed!=raw
 assert row["source_file"]==m["file"] and row["original_sha256"]==row["restored_sha256"]==h(R/m["file"])
 assert row["mutated_sha256"]==hashlib.sha256(changed).hexdigest()
 mutated=dict(inventory);mutated[m["file"]]=row["mutated_sha256"]
 red,rlog=receipt(row["red_receipt"],mutated,1)
 restored,slog=receipt(row["restored_receipt"],inventory,0)
 assert red["nodes"]==restored["nodes"]==row["defenders"]==row["attributed_failures"]
 assert set(row["defenders"])<=set(green["nodes"])
 assert all("FAILED "+node in rlog for node in row["defenders"])
 assert "passed" in slog and "FAILED " not in slog
 for kind in ("green","red","restored"):
  assert row[kind+"_binding_sha256"]==h(E/row[kind+"_receipt"])
assert all(h(R/k)==v for k,v in inventory.items())
result={"status":"MAKER_READINESS_VALIDATED","not_independent_verification":True,"source_candidate":binding["source_candidate"],"proof_checkout":binding["proof_checkout"],"current_wrapper_candidate":subprocess.check_output(["git","rev-parse","HEAD"],cwd=R,text=True).strip(),"triples":15,"receipts":len(set(validated)),"runtime_dependencies_lock_source_harness_spec_outputs":"validated","inventory_entries":len(inventory),"maker_active_s":None,"maker_tokens":None,"maker_cost":None}
output=pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else E/"readiness.json"
output.write_text(json.dumps(result,sort_keys=True,indent=2),encoding="utf-8",newline="\n")
print(json.dumps(result))
