"""Maker readiness validation of all source/runtime/argv/output identities and restored triples."""
import hashlib,importlib.metadata,json,pathlib,subprocess,sys
R=pathlib.Path.cwd();E=R/"qa/evidence/cli-downstream/cycle2"
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
digest=lambda o:hashlib.sha256(json.dumps(o,sort_keys=True).encode()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding="utf-8"))
binding=read(E/"run-binding.json");inventory=read(E/"source-inventory.json")
assert binding["source_candidate"]=="030560cf033782f50fb54c5c034b4f0fb3e0bb93"
assert binding["source_parent"]=="1babc7feb33c91657c28077304b2403809d7a8a1"
assert binding["base_candidate"]=="00c9e13ded3cba6cfe57bd9d0c422f5154ed6e09"
assert binding["proof_checkout"]==binding["source_candidate"]
assert binding["harness_sha256"]==h(E/"proof.py") and binding["invoke_sha256"]==h(E/"invoke.py")
assert binding["spec_sha256"]==h(R/binding["spec_path"])
selection=read(R/binding["selection_path"])
assert binding["selection_sha256"]==h(R/binding["selection_path"])
assert binding["selected_original_indices"]==selection["selected_original_indices"]
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
deps=sorted((d.metadata.get("Name", ""),d.version) for d in importlib.metadata.distributions())
assert digest(deps)==binding["dependencies_sha256"]
env=read(E/"environment.json")
assert env["PYTHONDONTWRITEBYTECODE"]=="1" and env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"]=="1"
assert set(env)<={"SYSTEMROOT","WINDIR","PATH","PATHEXT","COMSPEC","USERPROFILE","APPDATA","LOCALAPPDATA","PYTHONPATH","PYTHONDONTWRITEBYTECODE","PYTHONUTF8","PYTHONHASHSEED","PYTEST_ADDOPTS","PYTEST_DISABLE_PLUGIN_AUTOLOAD","OMP_THREAD_LIMIT","TEMP","TMP"}
assert subprocess.run(["git","diff","--quiet",binding["source_candidate"],"--","src","tests","scripts","pyproject.toml","uv.lock"],cwd=R).returncode==0
spec=read(R/binding["spec_path"]);ledger=read(E/"mutation-ledger.json");completed=read(E/"completed.json")
assert len(spec["mutations"])==selection["full_spec_count"]==15
assert len(selection["selected_original_indices"])==len(ledger)==completed["triples"]==11
selected=[spec["mutations"][i-1] for i in selection["selected_original_indices"]]
assert sorted(selection["selected_original_indices"]+[row["original_index"] for row in selection["not_executed"]])==list(range(1,16))
assert completed["binding_sha256"]==h(E/"run-binding.json") and completed["ledger_sha256"]==h(E/"mutation-ledger.json")
assert completed["all_restored"] is True
validated=[]
baseline=read(E/"baseline.json");baseline_before=read(E/"baseline-before.json")
assert baseline_before["status"]=="running" and baseline["status"]=="finished"
assert all(baseline[k]==v for k,v in baseline_before.items() if k!="status")
assert baseline["source_candidate"]==binding["base_candidate"] and baseline["exit_code"]==1
assert baseline["harness_sha256"]==h(E/"baseline.py") and baseline["invoke_sha256"]==h(E/"invoke.py")
assert baseline["command_sha256"]==digest(baseline["command"])
assert baseline["output_sha256"]==h(E/"baseline.log")
assert baseline["source_inventory_sha256"]==baseline["after_source_inventory_sha256"]
assert baseline["source_inventory_sha256"]==digest(read(E/"baseline-source-inventory.json"))
assert baseline["source_inventory_file_sha256"]==h(E/"baseline-source-inventory.json")
assert baseline["python_sha256"]==binding["python_sha256"] and baseline["python"]==binding["python"]
assert baseline["dependencies_sha256"]==binding["dependencies_sha256"]
base_lock=pathlib.Path(baseline["copy_root"])/"uv.lock"
assert h(base_lock)==baseline["lock_sha256"]==read(E/"baseline-source-inventory.json")["uv.lock"]
assert base_lock.read_bytes().replace(b"\r\n",b"\n")== (R/"uv.lock").read_bytes().replace(b"\r\n",b"\n")
for kind in ("dependencies","environment"):
 assert baseline[kind+"_sha256"]==digest(read(E/("baseline-"+kind+".json")))
 assert baseline[kind+"_file_sha256"]==h(E/("baseline-"+kind+".json"))
assert baseline["runtime_identity"]["dependencies_sha256"]==binding["dependencies_sha256"]
assert pathlib.Path(baseline["runtime_identity"]["import_file"]).is_relative_to(pathlib.Path(baseline["copy_root"])/"src")
assert "FAILED "+baseline["nodes"][0] in (E/"baseline.log").read_text(encoding="utf-8",errors="replace")
for tool in ("ruff","shape"):
 post=read(E/(tool+".json"));before=read(E/(tool+"-before.json"))
 assert all(post[k]==v for k,v in before.items() if k!="status")
 assert before["status"]=="running" and post["status"]=="finished" and post["exit_code"]==0
 assert all(post[k]==v for k,v in binding.items())
 assert post["after_source_inventory_sha256"]==binding["inventory_sha256"]
 assert post["check_harness_sha256"]==h(E/"checks.py") and post["check_tool_sha256"]==h(E/"check_tool.py")
 assert post["command_sha256"]==digest(post["command"])
 assert post["output_sha256"]==h(E/(tool+".log"))
 assert post["runtime_identity"]["python"]==binding["python"]
 assert post["runtime_identity"]["dependencies_sha256"]==binding["dependencies_sha256"]
 assert pathlib.Path(post["runtime_identity"]["import_file"]).is_relative_to(pathlib.Path(binding["copy_root"])/"src")

def receipt(name,expected,exit_code):
 post=read(E/name);label=post["label"];before=read(E/(label+"-before.json"));logfile=E/(label+".log")
 assert before["status"]=="running" and post["status"]=="finished"
 assert all(post[k]==v for k,v in before.items() if k!="status")
 assert all(post[k]==v for k,v in binding.items())
 assert post["command_sha256"]==digest(post["command"])
 assert post["source_inventory_sha256"]==post["after_source_inventory_sha256"]==digest(expected)
 assert post["file_overrides"]=={k:v for k,v in expected.items() if inventory[k]!=v}
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

green,glog=receipt("shared-green.json",inventory,0);assert "21 passed" in glog
assert set(spec["consumers"])<=set(green["nodes"])
assert all(any(node.endswith("::"+row["positive_test"]) for node in green["nodes"])
           for row in selection["not_executed"])
for m,row,original_index in zip(selected,ledger,selection["selected_original_indices"],strict=True):
 assert row["original_spec_index"]==original_index
 raw=(R/m["file"]).read_bytes();eol=b"\r\n" if b"\r\n" in raw else b"\n"
 assert eol==b"\n" or b"\n" not in raw.replace(b"\r\n",b"")
 old=m["old"].encode().replace(b"\n",eol);new=m["new"].encode().replace(b"\n",eol)
 assert raw.count(old)==row["anchor_count"]==1 and hashlib.sha256(old).hexdigest()==row["anchor_old_sha256"]
 changed=raw.replace(old,new,1);assert changed!=raw
 assert row["source_file"]==m["file"] and row["original_sha256"]==row["restored_sha256"]==h(R/m["file"])
 assert row["mutated_sha256"]==hashlib.sha256(changed).hexdigest()
 mutated=dict(inventory);mutated[m["file"]]=row["mutated_sha256"]
 red,rlog=receipt(row["red_receipt"],mutated,1)
 restored,slog=receipt(row["restored_receipt"],inventory,0)
 assert red["nodes"]==restored["nodes"]==row["defenders"]==row["attributed_failures"]
 assert set(row["defenders"])<=set(green["nodes"])
 assert all("FAILED "+node in rlog for node in row["defenders"])
 assert "passed" in slog and "FAILED " not in slog
 for kind in ("green","red","restored"):assert row[kind+"_binding_sha256"]==h(E/row[kind+"_receipt"])
assert all(h(R/k)==v for k,v in inventory.items())
result={"status":"MAKER_READINESS_VALIDATED","not_independent_verification":True,"source_candidate":binding["source_candidate"],"proof_checkout":binding["proof_checkout"],"current_wrapper_candidate":subprocess.check_output(["git","rev-parse","HEAD"],cwd=R,text=True).strip(),"triples":len(ledger),"receipts":len(set(validated)),"runtime_dependencies_lock_source_harness_spec_outputs":"validated","inventory_entries":len(inventory),"maker_active_s":None,"maker_tokens":None,"maker_cost":None}
output=pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else E/"readiness.json"
output.write_text(json.dumps(result,sort_keys=True,indent=2),encoding="utf-8",newline="\n")
print(json.dumps(result))
