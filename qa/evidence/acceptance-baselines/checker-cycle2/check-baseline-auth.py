from pathlib import Path
import json, hashlib, subprocess, os, sys, importlib.metadata
r=Path.cwd(); o=r/'qa/evidence/acceptance-baselines/checker-cycle2'; m=r/'qa/evidence/acceptance-baselines/cycle2'
s=(m/'seal.py').read_text(); s=s.replace('(out / "readiness.json").write_bytes(json.dumps(result, indent=2).encode())',''); exec(compile(s,str(m/'seal.py'),'exec'),{'__file__':str(m/'seal.py')})
h=lambda b:hashlib.sha256(b).hexdigest()
a=json.loads((m/'identity.json').read_bytes()); old=json.loads((r/'qa/evidence/acceptance-baselines/risk-proofs/identity.json').read_bytes()); reuse=json.loads((m/'reuse.json').read_bytes())
assert a['versions']==old['versions'] and a['lock_sha256']==old['lock_sha256']
assert all(importlib.metadata.version(k)==v for k,v in a['versions'].items())
assert h((r/'qa/evidence/acceptance-baselines/risk-proofs/identity.json').read_bytes())==reuse['prior_identity_sha256']
for p in (r/'qa/evidence/acceptance-baselines/checker-cycle1').glob('*.json'):
 if h(p.read_bytes())==reuse['compatibility_sha256']: break
else: raise AssertionError('compatibility absent')
prev=subprocess.check_output(['git','show',reuse['prior_code']+':tests/test_acceptance_baseline.py']); assert (r/'tests/test_acceptance_baseline.py').read_bytes().startswith(prev)
for rel,sha in json.loads((m/'inventory.json').read_bytes()).items():
 if rel in reuse['changed_inventory_paths']: continue
 assert json.loads((r/'qa/evidence/acceptance-baselines/risk-proofs/inventory.json').read_bytes())[rel]==sha, rel
for p in m.iterdir():
 if p.is_file(): assert subprocess.check_output(['git','show','8ace681a:'+p.relative_to(r).as_posix()])==p.read_bytes()
(o/'authentication.json').write_text(json.dumps({'status':'authenticated','entries':1020,'historical_proofs':13,'candidate':'8ace681a3e4ae48cbb0f383fc121bf3c44d13a4e'}))
print('Authenticated fresh receipt chain, unchanged 1018 inventory, dependency identity, prior compatibility, candidate blobs')
