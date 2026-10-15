import hashlib,importlib.metadata,json,os,platform,subprocess,sys,time
from pathlib import Path
R=Path.cwd(); E=R/'qa/evidence/acceptance-baselines'; O=E/'checker-cycle1'; O.mkdir(exist_ok=True)
W=R/'.work/baseline-proofs'; H=lambda b:hashlib.sha256(b).hexdigest()
i=json.loads((E/'risk-proofs/identity.json').read_bytes())
env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=os.pathsep.join(str(p) for p in (W/'src',W,W/'tests',W/'scripts')))
assert platform.python_version()==i['python_version']
assert {d.metadata['Name']:d.version for d in importlib.metadata.distributions()}==i['versions']
assert H((W/'_baseline_reports.py').read_bytes())==i['plugin_sha256']
assert H(json.dumps({k:env.get(k) for k in ('PYTHONPATH','PYTHONUTF8','PYTHONDONTWRITEBYTECODE','AUTOTESTER_ROOT','AUTOTESTER_AUTH_DIR','AUTOTESTER_AUTH_DISABLED','AUTOTESTER_TEST_AUTO_LOGIN','AUTOTESTER_ALLOWED_ORIGINS')},sort_keys=True).encode())==i['env_fingerprint']
inv={str(p.relative_to(W)).replace('\\','/'):H(p.read_bytes()) for part in ('src','tests','scripts') for p in (W/part).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
assert inv==json.loads((E/'risk-proofs/inventory.json').read_bytes())
(O/'compatible.json').write_text(json.dumps(dict(compatible=True,source_files=len(inv),candidate='417b3c011ec92308812a1436eb98a47b0bfb489a')))
print('READY: exact Python/dependencies/environment/plugin/complete copy authenticated',flush=True)
if '--audit' in sys.argv:sys.exit()
commands=[]
def run(label,argv):
 t=time.monotonic(); p=subprocess.run(argv,cwd=W,env=env,capture_output=True,timeout=40)
 (O/(label+'.log')).write_bytes(p.stdout+p.stderr)
 commands.append(dict(label=label,argv=argv,exit_code=p.returncode,duration_s=time.monotonic()-t,log_sha256=H(p.stdout+p.stderr)))
 (O/'commands.json').write_text(json.dumps(commands,indent=2)); print(label,p.returncode,flush=True);return p.returncode
helper='C:/Users/product/.agents/skills/checker/scripts/review_budget.py'
assert run('preflight',[sys.executable,helper,'preflight','--root',str(W),'--import-name','autotester','--import-root',str(W/'src'),'--temp-parent',str(W)])==0
nodes=['tests/test_acceptance_baseline.py::test_same_build_scoped_refs_and_input_only_isolation','tests/test_acceptance_baseline.py::test_partial_write_is_visible_and_refuses_reuse','tests/test_acceptance_baseline.py::test_stale_or_existing_plan_refused_without_writes[config]']
def pytest(label, selected):return run(label,[sys.executable,'-m','pytest',*selected,'-p','no:cacheprovider','--basetemp',str(W/('checker-'+label))])
assert pytest('green',nodes)==0
p=W/'src/autotester/stages/acceptance_baseline.py'; original=p.read_bytes(); old=b'if _digest(config) != plan.source_config_sha256:'; assert original.count(old)==1
try:
 p.write_bytes(original.replace(old,b'if False:',1));assert pytest('red',[nodes[-1]])==1
 assert nodes[-1].encode() in (O/'red.log').read_bytes()
finally:p.write_bytes(original)
assert pytest('restored',[nodes[-1]])==0
probe='''import json,subprocess,tempfile,os
from pathlib import Path
from test_acceptance_baseline import baseline
from autotester.stages.acceptance_baseline import prepare_baselines
base=Path(tempfile.mkdtemp(prefix="checker-source-junction-",dir="." )).resolve()
root,inputs,output,plan,store=baseline.__wrapped__(base)
real=base/"outside-project";store.paths.dir.rename(real)
alias=store.paths.dir
p=subprocess.run(["powershell.exe","-NoProfile","-NonInteractive","-Command","New-Item -ItemType Junction -Path $env:CHECK_ALIAS -Target $env:CHECK_TARGET -ErrorAction Stop | Out-Null"],env=dict(os.environ,CHECK_ALIAS=str(alias),CHECK_TARGET=str(real)),capture_output=True,timeout=20)
assert p.returncode==0,p.stderr
assert alias.resolve()==real.resolve() and not real.is_relative_to(root)
try:prepare_baselines(root,inputs,output,plan)
except ValueError as e: print(json.dumps(dict(source_escaped=True,refused=True,error=str(e))))
else: print(json.dumps(dict(source_escaped=True,refused=False,receipt=(output/"baseline-receipt.json").exists())));raise SystemExit(1)
'''
run('source-junction-probe',[sys.executable,'-c',probe])
assert p.read_bytes()==original
print('RUNTIME_COMPLETE',flush=True)
