from pathlib import Path
import hashlib,json,subprocess,sys,os
root=Path(r'C:/Users/product/Desktop/autoTesting/.work/account-generation');e=root/'qa/evidence/account-generation/cycle2';os.chdir(root)
s=(e/'readiness.py').read_text();s=s[:s.index("(E/'readiness.json').write_text")];exec(compile(s,'raw-receipt-readback','exec'))
assert sha(root/'uv.lock')==binding['lock_sha256']
assert all(sha(Path(binding['copy_root'])/p)==v for p,v in source.items())
paths=set()
for folder in ('src','tests','scripts'):
 paths.update(p.relative_to(root).as_posix() for p in (root/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
paths.update(('uv.lock','pyproject.toml'));assert paths==set(source)
assert subprocess.run(['git','diff','--quiet',binding['source'],'--','src','tests','scripts','uv.lock','pyproject.toml'],cwd=root).returncode==0
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()=='f1b345aa02f8e6673c3fc589239944ebb24f638e'
print(json.dumps(dict(status='CHECKER_AUTHENTICATED_READY',inventory=len(paths),receipts=8,triples=3,logs='raw-sha256',source_mapping='git-clean-to-source-and-raw-root-copy-inventory',lock=True)))
