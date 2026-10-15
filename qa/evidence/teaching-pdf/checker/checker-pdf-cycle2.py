import hashlib,json,subprocess,sys,time,importlib.metadata
from pathlib import Path
start=time.monotonic();r=Path.cwd();e=r/'qa/evidence/teaching-pdf-cycle2';out=r/'.work/checker-pdf-cycle2.json'
h=lambda b:hashlib.sha256(b).hexdigest()
load=lambda n:json.loads((e/n).read_text())
sha='0f48beaea6abc9c3a0ce9c238c6cf09abe03d118';assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==sha
assert not subprocess.check_output(['git','diff','c1f67d93b9ae1c9cab0c0cdbffdb5adadf68fcee',sha,'--','src','tests','scripts','pyproject.toml','uv.lock'])
seal=load('seal.json');assert len(seal)==55
for name,digest in seal.items():assert h((e/name).read_bytes())==digest,name
c=load('context.json');m=c['source_manifest'];tree=lambda d:h(json.dumps(d,sort_keys=True).encode());assert tree(m)==c['source_tree_sha256']
for path,digest in m.items():assert h((r/path).read_bytes())==digest,path
assert h(Path(sys.executable).read_bytes())==c['python_sha256']
for name,version in c['dependencies'].items():assert importlib.metadata.version(name)==version
for tool in c['tools'].values():assert h(Path(tool['path']).read_bytes())==tool['sha256']
rows=load('results.json');assert len(rows)==21
for n in ['00-green.receipt.json','99-restored-green.receipt.json']:
 q=load(n);assert q['exit_code']==0 and q['before_tree_sha256']==q['after_tree_sha256']==tree(m);assert h((e/q['output']).read_bytes())==q['output_sha256'];assert '12 passed' in (e/q['output']).read_text()
for row in rows:
 original=(r/row['file']).read_bytes();assert original.decode().count(row['old'])==1
 altered=original.decode().replace(row['old'],row['new'],1).encode();assert altered!=original and h(altered)==row['mutated_sha256'];assert row['before_sha256']==row['restored_sha256']==m[row['file']]
 q=load(row['command_receipt']);assert q['before_tree_sha256']==q['after_tree_sha256']==tree({**m,row['file']:h(altered)});assert q['exit_code']==row['exit']==1 and row['killed'] and row['anchor_matches']==1
 assert set(row['expected'])<=set(q['failed_nodeids']) and set(row['expected'])<=set(row['actual_failed']);assert q['command'][0]==sys.executable and q['elapsed_s']>0
 raw=(e/q['output']).read_bytes();assert h(raw)==q['output_sha256'];assert all(node.split('::')[-1] in raw.decode() for node in row['expected']);assert row['restored_tree_sha256']==tree(m)
bad=dict(seal);first=next(iter(bad));bad[first]='0'*64;assert h((e/first).read_bytes())!=bad[first]
assert load('completion.json')['all_killed'] and load('completion.json')['bound_worktree_unchanged']
result={'status':'PASS','candidate':sha,'cycle':2,'sealed_artifacts':55,'bound_proofs':21,'source_manifest_entries':len(m),'source_unchanged':True,'corrupted_seal_rejected':True,'elapsed_s':time.monotonic()-start,'tokens':None,'cost':None};out.write_text(json.dumps(result,indent=2));print(json.dumps(result))
