import pathlib,json,time,subprocess,hashlib,os,ast
r=pathlib.Path.cwd(); e=r/'qa/evidence/smtp-profile-checker';e.mkdir(exist_ok=True); t=time.monotonic()
py=r.parents[1]/'.venv/Scripts/python.exe'; helper='C:/Users/product/.agents/skills/checker/scripts/review_budget.py'
m=json.loads((r.parents[0]/'checker-dispatch/smtp-m1-coordinator.json').read_text());m['reviewers']=[{'id':'readiness','active_s':None,'tokens':None,'cost':None,'budget_debit':{'active_s':30,'tokens':1000}}];m['next_phase']={'active_s':110,'tokens':3500};(e/'runtime-budget.json').write_text(json.dumps(m))
def run(label,args,env=None,cwd=r,expected=0):
 s=time.monotonic();p=subprocess.run(args,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=45);(e/(label+'.log')).write_bytes(p.stdout);receipt={'command':list(args),'exit_code':p.returncode,'duration_s':time.monotonic()-s,'output_sha256':hashlib.sha256(p.stdout).hexdigest()};(e/(label+'.json')).write_text(json.dumps(receipt,indent=2));assert p.returncode==expected,(label,p.stdout[-2000:]);return receipt
run('runtime-gate',[str(py),helper,'assess','--input',str(e/'runtime-budget.json')])
b=json.loads((r/'qa/evidence/smtp-profile/binding.json').read_text()); inventory=json.loads((r/'qa/evidence/smtp-profile/source-inventory.json').read_text());assert hashlib.sha256((r/'uv.lock').read_bytes()).hexdigest()==b['lock_sha256']
copy=r/'.work/smtp-m1-independent';copy.mkdir(exist_ok=True)
for name,digest in inventory.items():
 raw=(r/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==digest;p=copy/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
assert all(hashlib.sha256((copy/name).read_bytes()).hexdigest()==d for name,d in inventory.items())
env=json.loads((r/'qa/evidence/smtp-profile/environment.json').read_text());env.update(PYTHONPATH=str(copy/'src'),TEMP=str(copy),TMP=str(copy))
run('preflight',[str(py),helper,'preflight','--root',str(copy),'--import-name','autotester','--import-root',str(copy/'src'),'--temp-parent',str(copy)],env,copy)
spec=json.loads((r/'qa/evidence/smtp-profile/spec.json').read_text());node=spec['mutations'][3]['node'];nodes=[str(copy/'tests/test_notification_profile.py'),str(copy/'tests/test_ui_auth_accounts.py'),str(copy/'tests/test_routers_list.py')]
invoke=str(r/'qa/evidence/smtp-profile/invoke.py');args=[str(py),invoke,str(copy/'src'),*nodes,'-p','no:cacheprovider','--basetemp',str(copy/'temp-green')];run('green',args,env,copy)
p=copy/spec['mutations'][3]['file'];raw=p.read_bytes();mutation=spec['mutations'][3];changed=raw.replace(mutation['old'].encode(),mutation['new'].encode(),1);assert raw!=changed and raw.count(mutation['old'].encode())==1
probe=[str(py),invoke,str(copy/'src'),str(copy/node),'-p','no:cacheprovider','--basetemp',str(copy/'temp-probe')];frozen=list(probe);p.write_bytes(changed)
try:
 run('own-identity-red',frozen,env,copy,1);assert ('FAILED '+node).encode() in (e/'own-identity-red.log').read_bytes()
finally:p.write_bytes(raw)
assert p.read_bytes()==raw and probe==frozen
run('own-identity-restored',frozen,env,copy)
(e/'mutation.json').write_text(json.dumps({'node':node,'argv':frozen,'original_sha256':hashlib.sha256(raw).hexdigest(),'mutation_sha256':hashlib.sha256(changed).hexdigest(),'restored_sha256':hashlib.sha256(p.read_bytes()).hexdigest()},indent=2))
changedpaths=['src/autotester/store/notification_prefs.py','src/autotester/ui/routes_profile.py','src/autotester/auth/policy.py','src/autotester/ui/routers.py','src/autotester/ui/theme.py','tests/test_notification_profile.py','tests/test_ui_auth_accounts.py']
run('lint',[str(py),'-m','ruff','check','--no-cache',*changedpaths],env,r)
for name in changedpaths:
 tree=ast.parse((r/name).read_bytes());assert ast.get_docstring(tree);assert len((r/name).read_bytes().splitlines())<=300
 for n in ast.walk(tree):
  if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):assert n.end_lineno-n.lineno+1<=50
(e/'completed.json').write_text(json.dumps({'runtime_duration_s':time.monotonic()-t,'copy_inventory_count':len(inventory),'source_unchanged':all(hashlib.sha256((r/n).read_bytes()).hexdigest()==d for n,d in inventory.items()),'runtime_active_s':None,'tokens':None,'cost':None},indent=2));print('INDEPENDENT_CHECKS_COMPLETE')
