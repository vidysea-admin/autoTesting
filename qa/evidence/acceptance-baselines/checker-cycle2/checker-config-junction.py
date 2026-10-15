import sys, pathlib, importlib.util, subprocess, os, json
from unittest.mock import patch
r=pathlib.Path.cwd(); sys.path[:0]=[str(r/'src'),str(r/'scripts')]
spec=importlib.util.spec_from_file_location('fixture',r/'tests/test_acceptance_baseline.py'); mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
base=r/'.work/checker-config-junction'; base.mkdir(); results=[]
for loc in ['junction']:
 d=base/loc;d.mkdir();root,inputs,out,plan,store=mod.baseline.__wrapped__(d)
 cfg=store.paths.config
 cfg.unlink();target=d/'external';target.mkdir()
 subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command','New-Item -ItemType Junction -Path $env:CHECK_ALIAS -Target $env:CHECK_TARGET -ErrorAction Stop | Out-Null'],env=dict(os.environ,CHECK_ALIAS=str(cfg),CHECK_TARGET=str(target)),check=True,capture_output=True,timeout=15)
 assert store.paths.dir.resolve().is_relative_to(root.resolve()) and not cfg.resolve().is_relative_to(root.resolve())
 reads=[]; original=pathlib.Path.read_bytes
 def reading(p):
  if p.resolve()==cfg.resolve():reads.append(str(p))
  return original(p)
 with patch.object(pathlib.Path,'read_bytes',reading):
  try:
   mod.prepare_baselines(root,inputs,out,plan); refused=False
  except ValueError as e:
   assert loc=='junction' and 'source project' in str(e);refused=True
 assert refused==(loc=='junction') and bool(reads)==(loc!='junction') and out.exists()==(loc!='junction')
 results.append(dict(case=loc,refused=refused,reads=len(reads),output=out.exists()))
print(json.dumps(results))
