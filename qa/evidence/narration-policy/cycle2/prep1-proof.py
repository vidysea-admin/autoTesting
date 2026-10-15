"""Fresh maker-only, contemporaneously sealed green/red/restored narration proof triples."""
import hashlib,importlib.metadata,json,os,pathlib,shutil,subprocess,sys,time
R=pathlib.Path.cwd(); E=R/"qa/evidence/narration-policy/cycle2"; T=R/".work/narration-cycle2-tree"
SOURCE="a16c2a53e3ba5ff09533210aacd29ddf56d5ac56";BASE="40f5b4b20e91d3806ee313fb8e67af109b62b0ae"
sha=lambda b:hashlib.sha256(b).hexdigest()
def dump(p,o):
 p.write_text(json.dumps(o,sort_keys=True,indent=2),encoding="utf-8",newline="\n")
def h(p):return sha(p.read_bytes())
def inventory(root):
 entries={}
 for name in ("src","tests","scripts"):
  for p in sorted((root/name).rglob("*")):
   if p.is_file() and "__pycache__" not in p.parts and p.suffix!=".pyc" and ".pytest_cache" not in p.parts:
    entries[p.relative_to(root).as_posix()]=h(p)
 for name in ("pyproject.toml","uv.lock"):
  entries[name]=h(root/name)
 return entries
def digest(obj):return sha(json.dumps(obj,sort_keys=True).encode())
def deps():return sorted((d.metadata.get("Name", ""),d.version) for d in importlib.metadata.distributions())
def git(*args):return subprocess.check_output(["git",*args],cwd=R,text=True).strip()
assert subprocess.run(["git","diff","--quiet",SOURCE,"--","src","tests","scripts","pyproject.toml","uv.lock"],cwd=R).returncode==0
assert not T.exists(), "Proof tree must be fresh; never overwrite a previous copy"
for name in ("src","tests","scripts"):
 shutil.copytree(R/name,T/name,ignore=shutil.ignore_patterns("__pycache__","*.pyc",".pytest_cache"))
for name in ("pyproject.toml","uv.lock"):shutil.copyfile(R/name,T/name)
original=inventory(R); assert inventory(T)==original
old=json.loads((R/"qa/evidence/narration-policy/final/fingerprint.json").read_text())
assert all(original[k]==v for k,v in old["source_hashes"].items())
dump(E/"source-inventory.json",original)
spec_path=R/"qa/evidence/narration-policy/mutations-final.json";spec=json.loads(spec_path.read_text());assert len(spec["mutations"])==15
known={}
for testfile in spec["tests"]:
 for line in (T/testfile).read_text().splitlines():
  if line.startswith("def test_"):
   name=line.split("def ")[1].split("(")[0];assert name not in known;known[name]=f"{testfile}::{name}"
D=deps();dump(E/"dependencies.json",D)
env={k:os.environ[k] for k in ("SYSTEMROOT","WINDIR","PATH","PATHEXT","COMSPEC","USERPROFILE","APPDATA","LOCALAPPDATA") if k in os.environ}
env.update(PYTHONPATH=str(T/"src"),PYTHONDONTWRITEBYTECODE="1",PYTHONUTF8="1",PYTHONHASHSEED="0",PYTEST_ADDOPTS="",PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",OMP_THREAD_LIMIT="1",TEMP=str(T),TMP=str(T))
dump(E/"environment.json",env)
common={"source_candidate":SOURCE,"base_candidate":BASE,"proof_checkout":git("rev-parse","HEAD"),"proof_checkout_root":str(R),"copy_root":str(T),"python":sys.executable,"python_version":sys.version,"python_sha256":h(pathlib.Path(sys.executable)),"dependencies_sha256":digest(D),"dependencies_file_sha256":h(E/"dependencies.json"),"lock_sha256":h(T/"uv.lock"),"environment_sha256":digest(env),"environment_file_sha256":h(E/"environment.json"),"harness_sha256":h(E/"proof.py"),"invoke_sha256":h(E/"invoke.py"),"spec_path":str(spec_path.relative_to(R)),"spec_sha256":h(spec_path),"inventory_sha256":digest(original),"inventory_file_sha256":h(E/"source-inventory.json"),"source_inventory_count":len(original),"role":"maker","maker_active_s":None,"maker_tokens":None,"maker_cost":None}
dump(E/"run-binding.json",common)
def run(label,nodes,expected_inventory):
 assert inventory(R)==original,"Live candidate source changed"
 before=inventory(T);assert before==expected_inventory
 assert deps()==D
 args=[sys.executable,"-B",str(E/"invoke.py"),str(T/"src"),*nodes,"--basetemp",str(T/f".proof-temp-{label}"),"-p","no:cacheprovider"]
 # Override repository addopts through controlled empty PYTEST_ADDOPTS is insufficient;
 # explicit -o keeps a single -q and preserves pytest summary for these proof-only runs.
 args.extend(["-o","addopts="])
 receipt=dict(common,label=label,command=args,command_sha256=digest(args),cwd=str(T),nodes=nodes,source_inventory_sha256=digest(before),file_overrides={k:v for k,v in before.items() if v!=original.get(k)},started_at=time.time(),started_monotonic=time.monotonic(),status="running")
 dump(E/f"{label}-before.json",receipt)
 with (E/f"{label}.log").open("wb") as stream:
  result=subprocess.run(args,cwd=T,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=60)
 receipt.update(status="finished",exit_code=result.returncode,finished_at=time.time(),finished_monotonic=time.monotonic(),output_sha256=h(E/f"{label}.log"))
 receipt["duration_s"]=receipt["finished_monotonic"]-receipt["started_monotonic"]
 after=inventory(T);assert after==before,"Check mutated its source inventory";assert inventory(R)==original;assert deps()==D
 receipt["after_source_inventory_sha256"]=digest(after)
 log=(E/f"{label}.log").read_text(encoding="utf-8",errors="replace")
 runtime=[x for x in log.splitlines() if x.startswith("__RUNTIME__")];assert len(runtime)==1
 identity=json.loads(runtime[0].removeprefix("__RUNTIME__"))
 assert pathlib.Path(identity["import_file"]).is_relative_to(T/"src")
 assert identity["dependencies_sha256"]==common["dependencies_sha256"]
 assert identity["python"]==sys.executable and identity["version"]==sys.version
 receipt["runtime_identity"]=identity
 dump(E/f"{label}.json",receipt)
 return receipt,log
allnodes=list(known.values())
green,_=run("shared-green",allnodes,original);assert green["exit_code"]==0
ledger=[]
for i,m in enumerate(spec["mutations"],1):
 p=T/m["file"];raw=p.read_bytes();text=raw.decode("utf-8");assert text.count(m["old"])==1
 changed=text.replace(m["old"],m["new"],1).encode("utf-8");assert changed!=raw
 p.write_bytes(changed);assert p.read_bytes()==changed
 changed_inventory=dict(original);changed_inventory[m["file"]]=sha(changed)
 nodes=[known[x] for x in m["kills"]]
 try:
  red,log=run(f"m{i:02}-red",nodes,changed_inventory)
  assert red["exit_code"]==1
  failures=[node for node in nodes if f"FAILED {node}" in log];assert failures==nodes
 finally:
  p.write_bytes(raw);assert p.read_bytes()==raw
 assert inventory(T)==original
 restored,_=run(f"m{i:02}-restored",nodes,original);assert restored["exit_code"]==0
 row={"index":i,"name":m["name"],"source_file":m["file"],"original_sha256":sha(raw),"mutated_sha256":sha(changed),"restored_sha256":h(p),"anchor_count":1,"defenders":nodes,"attributed_failures":failures,"green_receipt":"shared-green.json","red_receipt":f"m{i:02}-red.json","restored_receipt":f"m{i:02}-restored.json","green_binding_sha256":h(E/"shared-green.json"),"red_binding_sha256":h(E/f"m{i:02}-red.json"),"restored_binding_sha256":h(E/f"m{i:02}-restored.json")}
 ledger.append(row);dump(E/"mutation-ledger.json",ledger);print(f"{i}/15 triples sealed: {m['name']}",flush=True)
assert len(ledger)==15 and inventory(R)==original and inventory(T)==original
dump(E/"completed.json",{"binding_sha256":h(E/"run-binding.json"),"ledger_sha256":h(E/"mutation-ledger.json"),"triples":15,"all_restored":True,"maker_active_s":None,"maker_tokens":None,"maker_cost":None,"finished_at":time.time()})
