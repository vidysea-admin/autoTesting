from pathlib import Path
import subprocess,json,hashlib,shutil,os,time,sys,xml.etree.ElementTree as E
r=Path.cwd(); e=r/'.work/checker-mixed-core-escalated'; e.mkdir(exist_ok=True); c=e/'copy'; start=time.monotonic(); h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for d in ['src','tests','scripts']: shutil.copytree(r/d,c/d,ignore=shutil.ignore_patterns('__pycache__','*.pyc','.pytest_cache'),dirs_exist_ok=True)
for p in ['pyproject.toml','uv.lock']: shutil.copyfile(r/p,c/p)
inv={str(p.relative_to(r)):h(p) for d in ['src','tests','scripts'] for p in (r/d).rglob('*') if p.is_file() and '__pycache__' not in p.parts and '.pytest_cache' not in p.parts and p.suffix!='.pyc'}; assert all(h(c/p)==v for p,v in inv.items()); (e/'inventory.json').write_text(json.dumps(inv)); env={**os.environ,'PYTHONPATH':str(c/'src'),'PYTHONDONTWRITEBYTECODE':'1'}
def run(name,args):
 t=time.monotonic(); before={p:h(c/p) for p in inv}; (e/(name+'-argv.json')).write_text(json.dumps(args)); q=subprocess.run(args,cwd=c,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=40); (e/(name+'.log')).write_bytes(q.stdout); out={'exit':q.returncode,'argv':args,'duration_s':time.monotonic()-t,'python':sys.executable,'lock':h(c/'uv.lock'),'before':before,'after':{p:h(c/p) for p in inv},'log':h(e/(name+'.log'))}; (e/(name+'.json')).write_text(json.dumps(out)); print(name,q.returncode,flush=True); assert before==out['after']; return q
q=run('preflight',[sys.executable,'C:/Users/product/.agents/skills/checker/scripts/review_budget.py','preflight','--root',str(c),'--import-name','autotester','--import-root',str(c/'src'),'--temp-parent',str(e)]); assert q.returncode==0,q.stdout
T='tests/test_teach_sources.py::'; F='tests/test_teaching_inputs.py::'; nodes=[T+'test_every_registered_type_is_consumed_with_citations_and_resume_cache',F+'test_changed_actual_input_requires_new_run_before_model[bytes]',F+'test_stale_or_misattributed_content_never_reaches_provider[project]','tests/test_teaching_privacy.py::test_video_prompt_and_returned_artifact_cross_privacy_guard[input]',T+'test_failed_provider_is_redacted_and_cached_without_repeat',T+'test_invalid_or_interrupted_receipt_never_repeats_a_model_call[running]',T+'test_aggregate_never_rewrites_approved_canonical_bytes',T+'test_teaching_artifacts_do_not_enter_case_results']
def pytest(name,selected): return run(name,[sys.executable,'-m','pytest',*selected,'-p','no:cacheprovider','--basetemp',str(e/(name+'-temp')),'--junitxml',str(e/(name+'.xml'))])
assert pytest('green',nodes).returncode==0
p=c/'src/autotester/stages/teach_sources.py'; raw=p.read_bytes(); anchor=b'        or previous.fingerprint != snapshot.fingerprint\n'; assert raw.count(anchor)==1
try:
 p.write_bytes(raw.replace(anchor,b'')); assert pytest('independent-red',[nodes[1]]).returncode==1; cases=list(E.parse(e/'independent-red.xml').iter('testcase')); assert any(x.attrib['name']=='test_changed_actual_input_requires_new_run_before_model[bytes]' and x.find('failure') is not None for x in cases)
finally: p.write_bytes(raw)
assert p.read_bytes()==raw; assert pytest('restored-green',[nodes[1]]).returncode==0
summary={'status':'PASS','focused_instances':8,'active_runtime_s':time.monotonic()-start,'inventory_files':len(inv),'tokens':None}; (e/'summary.json').write_text(json.dumps(summary)); print(json.dumps(summary))

