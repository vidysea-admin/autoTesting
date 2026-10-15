import sys, pathlib, importlib.util, subprocess, os, json
from unittest.mock import patch
r=pathlib.Path.cwd(); sys.path[:0]=[str(r/'src'),str(r/'scripts')]
spec=importlib.util.spec_from_file_location('fixture',r/'tests/test_acceptance_baseline.py'); mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
base=r/'.work/checker-config-only'; base.mkdir(); results=[]
for loc in ['ordinary','outside','inside']:
 d=base/loc;d.mkdir();root,inputs,out,plan,store=mod.baseline.__wrapped__(d)
 cfg=store.paths.config
 if loc!='ordinary':
  target=(root if loc=='inside' else d)/'relocated.json';cfg.rename(target)
  try: cfg.symlink_to(target)
  except OSError as e:
   results.append(dict(case=loc,symlink_gap=str(e)));continue
 reads=[]; original=pathlib.Path.read_bytes
 def reading(p):
  if p.resolve()==cfg.resolve():reads.append(str(p))
  return original(p)
 with patch.object(pathlib.Path,'read_bytes',reading):
  try:
   mod.prepare_baselines(root,inputs,out,plan); refused=False
  except ValueError as e:
   assert loc=='outside' and 'source project' in str(e);refused=True
 assert refused==(loc=='outside') and bool(reads)==(loc!='outside') and out.exists()==(loc!='outside')
 results.append(dict(case=loc,refused=refused,reads=len(reads),output=out.exists()))
print(json.dumps(results))
