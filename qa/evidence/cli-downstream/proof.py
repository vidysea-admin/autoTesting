"""Maker-only, serial-burst fresh green/red/exact-restored proofs over a frozen copied tree."""
import hashlib,importlib.metadata,json,os,pathlib,shutil,subprocess,sys,time
R=pathlib.Path.cwd();E=R/"qa/evidence/cli-downstream";T=R/".work/cli-downstream-proof-tree"
sha=lambda b:hashlib.sha256(b).hexdigest()
h=lambda p:sha(p.read_bytes())
digest=lambda obj:sha(json.dumps(obj,sort_keys=True).encode())
read=lambda p:json.loads(p.read_text(encoding="utf-8"))
def dump(p,obj):p.write_text(json.dumps(obj,sort_keys=True,indent=2),encoding="utf-8",newline="\n")
def git(*args):return subprocess.check_output(["git",*args],cwd=R,text=True).strip()
def deps():return sorted((d.metadata.get("Name", ""),d.version) for d in importlib.metadata.distributions())
def inventory(root):
 entries={}
 for name in ("src","tests","scripts"):
  for p in sorted((root/name).rglob("*")):
   if p.is_file() and "__pycache__" not in p.parts and p.suffix!=".pyc" and ".pytest_cache" not in p.parts:
    entries[p.relative_to(root).as_posix()]=h(p)
 for name in ("pyproject.toml","uv.lock"):entries[name]=h(root/name)
 return entries

def mutation(raw,m):
 eol=b"\r\n" if b"\r\n" in raw else b"\n"
 assert eol==b"\n" or b"\n" not in raw.replace(b"\r\n",b"")
 old=m["old"].encode().replace(b"\n",eol);new=m["new"].encode().replace(b"\n",eol)
 assert raw.count(old)==1
 changed=raw.replace(old,new,1);assert changed!=raw
 return changed,sha(old)

spec_path=E/"mutations.json"
spec=read(spec_path)
mode=sys.argv[1]
if mode=="init":
 assert not T.exists(),"Never overwrite proof trees"
 source=git("rev-parse","HEAD")
 assert source=="2f1e30c1c1b2b4071bd9e2f093a8bbea03561775"
 assert subprocess.run(["git","diff","--quiet",source,"--","src","tests","scripts","pyproject.toml","uv.lock"],cwd=R).returncode==0
 for name in ("src","tests","scripts"):
  shutil.copytree(R/name,T/name,ignore=shutil.ignore_patterns("__pycache__","*.pyc",".pytest_cache"))
 for name in ("pyproject.toml","uv.lock"):shutil.copyfile(R/name,T/name)
 original=inventory(R);assert inventory(T)==original
 dump(E/"source-inventory.json",original)
 D=deps();dump(E/"dependencies.json",D)
 env={k:os.environ[k] for k in ("SYSTEMROOT","WINDIR","PATH","PATHEXT","COMSPEC","USERPROFILE","APPDATA","LOCALAPPDATA") if k in os.environ}
 env.update(PYTHONPATH=str(T/"src"),PYTHONDONTWRITEBYTECODE="1",PYTHONUTF8="1",PYTHONHASHSEED="0",PYTEST_ADDOPTS="",PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",OMP_THREAD_LIMIT="1",TEMP=str(T),TMP=str(T))
 dump(E/"environment.json",env)
 common={"source_candidate":source,"source_parent":git("rev-parse",source+"^"),"base_candidate":"00c9e13ded3cba6cfe57bd9d0c422f5154ed6e09","proof_checkout":source,"proof_checkout_root":str(R),"copy_root":str(T),"python":sys.executable,"python_version":sys.version,"python_sha256":h(pathlib.Path(sys.executable)),"dependencies_sha256":digest(D),"dependencies_file_sha256":h(E/"dependencies.json"),"lock_sha256":h(T/"uv.lock"),"environment_sha256":digest(env),"environment_file_sha256":h(E/"environment.json"),"harness_sha256":h(E/"proof.py"),"invoke_sha256":h(E/"invoke.py"),"spec_path":str(spec_path.relative_to(R)),"spec_sha256":h(spec_path),"inventory_sha256":digest(original),"inventory_file_sha256":h(E/"source-inventory.json"),"source_inventory_count":len(original),"role":"maker","maker_active_s":None,"maker_tokens":None,"maker_cost":None}
 dump(E/"run-binding.json",common)
 dump(E/"mutation-ledger.json",[])
else:
 common=read(E/"run-binding.json");original=read(E/"source-inventory.json");env=read(E/"environment.json");D=read(E/"dependencies.json")
 assert common["harness_sha256"]==h(E/"proof.py") and common["invoke_sha256"]==h(E/"invoke.py")
 assert common["spec_sha256"]==h(spec_path)
 assert digest(deps())==common["dependencies_sha256"]
 assert inventory(R)==inventory(T)==original

def run(label,nodes,expected):
 assert inventory(R)==original and inventory(T)==expected
 assert digest(deps())==common["dependencies_sha256"]
 args=[sys.executable,"-B",str(E/"invoke.py"),str(T/"src"),*nodes,"--basetemp",str(T/f".proof-temp-{label}"),"-p","no:cacheprovider","-o","addopts="]
 receipt=dict(common,label=label,command=args,command_sha256=digest(args),cwd=str(T),nodes=nodes,source_inventory_sha256=digest(expected),file_overrides={k:v for k,v in expected.items() if v!=original.get(k)},started_at=time.time(),started_monotonic=time.monotonic(),status="running")
 dump(E/f"{label}-before.json",receipt)
 with (E/f"{label}.log").open("wb") as stream:
  result=subprocess.run(args,cwd=T,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=90)
 receipt.update(status="finished",exit_code=result.returncode,finished_at=time.time(),finished_monotonic=time.monotonic(),output_sha256=h(E/f"{label}.log"))
 receipt["duration_s"]=receipt["finished_monotonic"]-receipt["started_monotonic"]
 after=inventory(T);assert after==expected and inventory(R)==original
 assert digest(deps())==common["dependencies_sha256"]
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

known={}
for testfile in spec["tests"]:
 for line in (T/testfile).read_text().splitlines():
  if line.startswith("def test_"):
   name=line.split("def ")[1].split("(")[0];assert name not in known;known[name]=f"{testfile}::{name}"
if mode=="init":
 nodes=list(known.values())+spec["consumers"]
 green,_=run("shared-green",nodes,original)
 assert green["exit_code"]==0
 print(f"Shared GREEN sealed: {len(nodes)} nodes",flush=True)
elif mode=="run":
 ledger=read(E/"mutation-ledger.json")
 start,count=int(sys.argv[2]),int(sys.argv[3])
 assert start==len(ledger)+1
 for i in range(start,min(start+count,len(spec["mutations"])+1)):
  m=spec["mutations"][i-1];p=T/m["file"];raw=p.read_bytes()
  changed,anchor_sha=mutation(raw,m)
  p.write_bytes(changed);expected=dict(original);expected[m["file"]]=sha(changed)
  nodes=[known[name] for name in m["kills"]]
  try:
   red,log=run(f"m{i:02}-red",nodes,expected)
   assert red["exit_code"]==1
   failures=[node for node in nodes if f"FAILED {node}" in log];assert failures==nodes
  finally:
   p.write_bytes(raw);assert p.read_bytes()==raw
  assert inventory(T)==original
  restored,_=run(f"m{i:02}-restored",nodes,original);assert restored["exit_code"]==0
  row={"index":i,"name":m["name"],"source_file":m["file"],"original_sha256":sha(raw),"mutated_sha256":sha(changed),"restored_sha256":h(p),"anchor_count":1,"anchor_old_sha256":anchor_sha,"defenders":nodes,"attributed_failures":failures,"green_receipt":"shared-green.json","red_receipt":f"m{i:02}-red.json","restored_receipt":f"m{i:02}-restored.json"}
  for phase in ("green","red","restored"):row[phase+"_binding_sha256"]=h(E/row[phase+"_receipt"])
  ledger.append(row);dump(E/"mutation-ledger.json",ledger)
  print(f"{i}/{len(spec['mutations'])} triples sealed: {m['name']}",flush=True)
elif mode=="finish":
 ledger=read(E/"mutation-ledger.json");assert len(ledger)==len(spec["mutations"])
 dump(E/"completed.json",{"binding_sha256":h(E/"run-binding.json"),"ledger_sha256":h(E/"mutation-ledger.json"),"triples":len(ledger),"all_restored":True,"maker_active_s":None,"maker_tokens":None,"maker_cost":None,"finished_at":time.time()})
