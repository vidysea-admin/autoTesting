"""Bind a single existing privacy/rubric consumer check to the exact checked base revision."""
import hashlib,importlib.metadata,io,json,os,pathlib,subprocess,sys,tarfile,time
R=pathlib.Path.cwd();E=R/"qa/evidence/cli-downstream";T=R/".work/baseline-consumer-tree"
BASE="00c9e13ded3cba6cfe57bd9d0c422f5154ed6e09"
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
digest=lambda o:hashlib.sha256(json.dumps(o,sort_keys=True).encode()).hexdigest()
def dump(p,o):p.write_text(json.dumps(o,sort_keys=True,indent=2),encoding="utf-8",newline="\n")
assert not T.exists()
payload=subprocess.check_output(["git","archive","--format=tar",BASE,"src","tests","scripts","pyproject.toml","uv.lock"],cwd=R)
T.mkdir(parents=True)
with tarfile.open(fileobj=io.BytesIO(payload),mode="r:") as archive:
 for member in archive.getmembers():
  assert (T/member.name).resolve().is_relative_to(T.resolve()) and not member.issym() and not member.islnk()
 archive.extractall(T)
inventory={p.relative_to(T).as_posix():h(p) for p in sorted(T.rglob("*")) if p.is_file()}
dump(E/"baseline-source-inventory.json",inventory)
deps=sorted((d.metadata.get("Name", ""),d.version) for d in importlib.metadata.distributions())
env={k:os.environ[k] for k in ("SYSTEMROOT","WINDIR","PATH","PATHEXT","COMSPEC","USERPROFILE","APPDATA","LOCALAPPDATA") if k in os.environ}
env.update(PYTHONPATH=str(T/"src"),PYTHONDONTWRITEBYTECODE="1",PYTHONUTF8="1",PYTHONHASHSEED="0",PYTEST_ADDOPTS="",PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",OMP_THREAD_LIMIT="1",TEMP=str(T),TMP=str(T))
dump(E/"baseline-environment.json",env);dump(E/"baseline-dependencies.json",deps)
nodes=["tests/test_run_case_pipeline.py::test_run_and_grade_case_builds_and_persists_a_default_rubric_when_none_exists"]
args=[sys.executable,"-B",str(E/"invoke.py"),str(T/"src"),*nodes,"--basetemp",str(T/".test-temp"),"-p","no:cacheprovider","-o","addopts="]
receipt={"role":"maker","source_candidate":BASE,"copy_root":str(T),"source_inventory_sha256":digest(inventory),"source_inventory_file_sha256":h(E/"baseline-source-inventory.json"),"archive_sha256":hashlib.sha256(payload).hexdigest(),"command":args,"command_sha256":digest(args),"cwd":str(T),"nodes":nodes,"python":sys.executable,"python_version":sys.version,"python_sha256":h(pathlib.Path(sys.executable)),"dependencies_sha256":digest(deps),"dependencies_file_sha256":h(E/"baseline-dependencies.json"),"environment_sha256":digest(env),"environment_file_sha256":h(E/"baseline-environment.json"),"lock_sha256":h(T/"uv.lock"),"harness_sha256":h(E/"baseline.py"),"invoke_sha256":h(E/"invoke.py"),"started_at":time.time(),"started_monotonic":time.monotonic(),"status":"running","maker_active_s":None,"maker_tokens":None,"maker_cost":None}
dump(E/"baseline-before.json",receipt)
with (E/"baseline.log").open("wb") as stream:
 result=subprocess.run(args,cwd=T,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=60)
receipt.update(status="finished",exit_code=result.returncode,finished_at=time.time(),finished_monotonic=time.monotonic(),output_sha256=h(E/"baseline.log"))
receipt["duration_s"]=receipt["finished_monotonic"]-receipt["started_monotonic"]
assert all(h(T/k)==v for k,v in inventory.items())
receipt["after_source_inventory_sha256"]=digest(inventory)
runtime=[x for x in (E/"baseline.log").read_text(encoding="utf-8",errors="replace").splitlines() if x.startswith("__RUNTIME__")]
assert len(runtime)==1
receipt["runtime_identity"]=json.loads(runtime[0].removeprefix("__RUNTIME__"))
assert pathlib.Path(receipt["runtime_identity"]["import_file"]).is_relative_to(T/"src")
assert receipt["runtime_identity"]["dependencies_sha256"]==receipt["dependencies_sha256"]
dump(E/"baseline.json",receipt)
print(json.dumps({"exit_code":receipt["exit_code"],"duration_s":receipt["duration_s"],"log":str(E/"baseline.log")}))
