import pathlib,json,hashlib,sys,importlib.metadata,subprocess
r=pathlib.Path.cwd();e=r/'qa/evidence/ollama-frame-vision';out=e/'checker';out.mkdir(exist_ok=True)
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
a=json.loads((e/'receipts.json').read_text());b=json.loads((e/'candidate-source-binding.json').read_text())
assert all(h(r/p)==v==a['files'][p] for p,v in b.items())
for key in ['proof','preflight']: assert h(e/(key+'.py' if key=='proof' else key+'.log'))==a[key+'_sha256']
assert all(importlib.metadata.version(p)==v for p,v in a['dependencies'].items())
for label in ['green','restored']:
 q=a[label]; assert q['exit']==0 and h(e/(label+'.log'))==q['log_sha256']; assert '75 passed' in (e/(label+'.log')).read_text()
for m in a['mutations']:
 assert m['source_sha256']==b[m['source']] and m['exit']==1
 s=(r/m['source']).read_bytes().decode();assert s.count(m['old'])==1
 assert hashlib.sha256(s.replace(m['old'],m['new'],1).encode()).hexdigest()==m['mutated_sha256']
 assert h(e/(m['name']+'.log'))==m['log_sha256']
 assert all(n in (e/(m['name']+'.log')).read_text() for n in m['failures'])
assert len(a['mutations'])==41
(out/'readiness.json').write_text(json.dumps({'candidate':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'cycle':1,'bindings':'14 file hashes,41 mutations,green/restored logs,dependency versions verified'}))
m={'maker':{'active_s':None,'tokens':None,'cost':None},'reviewers':[{'id':'vision-readiness','active_s':None,'tokens':None,'cost':None,'budget_debit':{'active_s':40,'tokens':1500}}],'next_phase':{'active_s':140,'tokens':4500,'cost':None},'bootstrap_scope':'Exact vision candidate readiness plus minimum risks and distinct colors probe','bootstrap':{'active_s':180,'tokens':6000},'escalation':None}
(out/'runtime-budget.json').write_text(json.dumps(m))
print('READINESS VERIFIED')

