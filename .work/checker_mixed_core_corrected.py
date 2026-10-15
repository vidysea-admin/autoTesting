from pathlib import Path
import subprocess,json,hashlib,shutil,os,time,sys,xml.etree.ElementTree as E
r=Path.cwd(); e=r/'.work/checker-mixed-core-corrected'; e.mkdir(exist_ok=True); c=e/'copy'; start=time.monotonic(); h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for d in ['src','tests','scripts']: shutil.copytree(r/d,c/d,ignore=shutil.ignore_patterns('__pycache__','*.pyc','.pytest_cache'),dirs_exist_ok=True)
for p in ['pyproject.toml','uv.lock']: shutil.copyfile(r/p,c/p)
inv={str(p.relative_to(r)):h(p) for d in ['src','tests','scripts'] for p in (r/d).rglob('*') if p.is_file() and '__pycache__' not in p.parts and '.pytest_cache' not in p.parts and p.suffix!='.pyc'}; assert all(h(c/p)==v for p,v in inv.items()); (e/'inventory.json').write_text(json.dumps(inv)); env={**os.environ,'PYTHONPATH':str(c/'src'),'PYTHONDONTWRITEBYTECODE':'1'}
def run(name,args):
 t=time.monotonic(); before={p:h(c/p) for p in inv}; (e/(name+'-argv.json')).write_text(json.dumps(args)); q=subprocess.run(args,cwd=c,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=40); (e/(name+'.log')).write_bytes(q.stdout); out={'exit':q.returncode,'argv':args,'duration_s':time.monotonic()-t,'python':sys.executable,'lock':h(c/'uv.lock'),'before':before,'after':{p:h(c/p) for p in inv},'log':h(e/(name+'.log'))}; (e/(name+'.json')).write_text(json.dumps(out)); print(name,q.returncode,flush=True); assert before==out['after']; return q
q=run('preflight',[sys.executable,'C:/Users/product/.agents/skills/checker/scripts/review_budget.py','preflight','--root',str(c),'--import-name','autotester','--import-root',str(c/'src'),'--temp-parent',str(e)]); assert q.returncode==0,q.stdout
node='tests/test_teaching_inputs.py::test_changed_actual_input_requires_new_run_before_model[set]'
def test(name): return run(name,[sys.executable,'-m','pytest',node,'-p','no:cacheprovider','--basetemp',str(e/(name+'-temp')),'--junitxml',str(e/(name+'.xml'))])
assert test('green').returncode==0
p=c/'src/autotester/stages/teach_sources.py';raw=p.read_bytes();a=b'        or previous.fingerprint != snapshot.fingerprint\n';assert raw.count(a)==1
try:
 p.write_bytes(raw.replace(a,b''));assert test('red').returncode==1;cases=list(E.parse(e/'red.xml').iter('testcase'));assert any(x.attrib['name'].endswith('[set]') and x.find('failure') is not None for x in cases)
finally:p.write_bytes(raw)
assert p.read_bytes()==raw;assert test('restored-green').returncode==0
(e/'summary.json').write_text(json.dumps({'status':'PASS','duration_s':time.monotonic()-start,'source_restored':h(p)==h(r/'src/autotester/stages/teach_sources.py'),'tokens':None}));print('CORRECTED PASS',flush=True)
