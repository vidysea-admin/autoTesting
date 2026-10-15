import importlib.util,json,os,time
from pathlib import Path
spec=importlib.util.spec_from_file_location("proof", "scripts/mutation_check.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
original=m._run_pytest
out=Path(".work/narration-proof");out.mkdir(exist_ok=True)
n=0
def run(cwd,tests,*args,**kwargs):
 global n
 n+=1
 old=os.environ.get("PYTHONPATH")
 os.environ["PYTHONPATH"]=str(cwd/"src")
 try:
  code,log=original(cwd,tests,*args,**kwargs)
  (out/f"{n:02}.log").write_text(log,encoding="utf-8")
  return code,log
 finally:
  if old is None:os.environ.pop("PYTHONPATH",None)
  else:os.environ["PYTHONPATH"]=old
m._run_pytest=run
started=time.time()
results=m.check(json.loads(Path("qa/evidence/narration-policy/mutations.json").read_text()),Path.cwd())
(out/"results.json").write_text(json.dumps(dict(elapsed_s=time.time()-started,results=results),indent=2))
raise SystemExit(m.report(results))
