import ast, hashlib, importlib.metadata, json, os, subprocess, sys, time
from pathlib import Path
from datetime import datetime, timezone
from types import SimpleNamespace

root = Path(__file__).resolve().parents[1]
out = root/'qa/evidence/vision-role-defaults/checker-cycle2-native'
out.mkdir(exist_ok=True)
start = time.monotonic()
records = []
def run(name, cmd):
    t = time.monotonic()
    p = subprocess.run(cmd, cwd=root, capture_output=True)
    (out/(name+'.stdout')).write_bytes(p.stdout)
    (out/(name+'.stderr')).write_bytes(p.stderr)
    records.append(dict(name=name, command=cmd, exit=p.returncode, duration_s=time.monotonic()-t))
    return p
helper='C:/Users/product/.agents/skills/checker/scripts/review_budget.py'
prior=Path('C:/Users/product/Desktop/autoTesting/.work/measured-vision-completion/checker/finalization-exception-admission.json')
metrics=json.loads(prior.read_text(encoding='utf-8-sig'))
metrics['native_cycle2_exception']={'authority':'Human finite focused review authorization relayed in exact parent dispatch', 'scope':'one vision-role-defaults cycle2 parser delta; no policy change', 'max_wall_s':180, 'actual_total_tokens':None, 'token_metric':'actual_total'}
(out/'phase-input.json').write_text(json.dumps(metrics,indent=2))
run('validate',[sys.executable,helper,'validate','--input',str(out/'phase-input.json')])
run('assess',[sys.executable,helper,'assess','--input',str(out/'phase-input.json')])
# Refusals are retained, not represented as admission. Explicit finite human exception governs.
candidate='46f6a8089f0730c201ebe8a6dde201868ddebec4'
assert run('head',['git','rev-parse','HEAD']).stdout.decode().strip()==candidate
packet=json.loads((root/'qa/evidence/vision-role-defaults/completion-cycle2/checker-packet.json').read_bytes())
for path,digest in packet['fingerprints'].items():
    assert hashlib.sha256((root/path).read_bytes()).hexdigest()==digest,path
recon=json.loads((root/'qa/evidence/vision-role-defaults/completion-cycle2/six-file-reconciliation.json').read_bytes())
for row in recon['rows']:
    old=run('old-'+str(len(records)),['git','show',recon['historical_sha']+':'+row['path']]).stdout
    dep=run('dep-'+str(len(records)),['git','show',recon['accepted_dependency_sha']+':'+row['path']]).stdout
    new=run('new-'+str(len(records)),['git','show',candidate+':'+row['path']]).stdout
    assert hashlib.sha256(old).hexdigest()==row['old_git_blob_sha256']
    historical=old.replace(b'\n',b'\r\n') if row['historical_inventory_reconstruction']=='CRLF_checkout' else old
    assert hashlib.sha256(historical).hexdigest()==row['historical_inventory_sha256']
    assert dep==new and hashlib.sha256(dep).hexdigest()==row['accepted_dependency_git_blob_sha256']
    assert hashlib.sha256((root/row['path']).read_bytes()).hexdigest()==row['current_raw_sha256']
import autotester.providers as p
from autotester.schema.project import ProviderConfig
from autotester.schema.enums import SourceKind
assert Path(p.__file__).resolve()==root/'src/autotester/providers/__init__.py'
for dep,version in {'pydantic':'2.13.5','pytest':'9.1.1','Pillow':'12.3.0','litellm':'1.104.0','python-dotenv':'1.2.3','ruff':'0.16.5'}.items():
    assert importlib.metadata.version(dep)==version
source=(root/'src/autotester/providers/__init__.py').read_bytes()
tree=ast.parse(source)
fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='for_teaching_group')
good='\n'.join(source.decode().splitlines()[fn.lineno-1:fn.end_lineno])
ns=dict(vars(p)); ns['Project']=object; ns['get']=lambda name,**opts:(name,opts)
project=SimpleNamespace(providers=ProviderConfig(vision='litellm:vendor/a:tag,litellm:vendor/b:tag,litellm:vendor/a:tag,vision-chain',vision_allow_gemini_fallback=False))
expected=[('litellm',{'model':'vendor/a:tag'}),('litellm',{'model':'vendor/b:tag'}),('vision-chain',{'allow_gemini_fallback':False})]
exec(good,ns)
assert ns['for_teaching_group'](project,SourceKind.VIDEO)==expected
for bad in ('litellm:','unknown:x','litellm:https://invalid.test','litellm:user@host','mock,,anthropic'):
    try: ns['for_teaching_group'](project,SourceKind.VIDEO,override=bad)
    except p.ProviderError: pass
    else: raise AssertionError('invalid member accepted')
anchor='    for member in dict.fromkeys(part.strip() for part in spec.split(",")):\n        name, member_options = parse_spec(member)'
assert good.count(anchor)==1
bad=good.replace(anchor,'    provider_id, options = parse_spec(spec)\n    for name in dict.fromkeys(part.strip() for part in provider_id.split(",")):\n        member_options = dict(options)')
assert bad!=good
exec(bad,ns)
try: assert ns['for_teaching_group'](project,SourceKind.VIDEO)==expected,'member model tags/order lost'
except AssertionError as error: red=str(error)
else: raise AssertionError('mutation survived')
exec(good,ns)
assert ns['for_teaching_group'](project,SourceKind.VIDEO)==expected
assert (root/'src/autotester/providers/__init__.py').read_bytes()==source
assert run('ruff',[sys.executable,'-m','ruff','check','src/autotester/providers/__init__.py','tests/test_vision_roles.py']).returncode==0
result={'status':'INDEPENDENT_PROBE_GREEN','candidate':candidate,'cycle':2,'reconciliation_rows':6,'green':True,'red_named_reason':red,'restored':True,'isolation':'in-memory actual function with fake constructor; production bytes unchanged','python':sys.executable,'version':sys.version,'commands':records,'duration_s':time.monotonic()-start,'ended_at':datetime.now(timezone.utc).isoformat(),'actual_total_tokens':None,'active_s':None,'wait_s':None,'token_metric':'actual_total'}
(out/'checks.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
