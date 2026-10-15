"""Check packaging-only checkout preservation without rerunning runtime tests."""
import hashlib
import json
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
archive = root/'qa/evidence/vision-capability-probe'
out = root/'.work/probe-packaging-r2'
out.mkdir()
sha = lambda b: hashlib.sha256(b).hexdigest()
def git(*args):
    return subprocess.run(['git',*args],cwd=root,capture_output=True,check=True).stdout
before = git('show','5587d30e:.gitattributes')
paths = git('diff','--name-only','00c9e13ded3cba6cfe57bd9d0c422f5154ed6e09').decode().splitlines()
paths += git('diff','--cached','--name-only').decode().splitlines()
paths = sorted(set(paths))
git('checkout-index','--prefix='+out.as_posix()+'/', '--',*paths)
observed = {}
for name in paths:
    actual = (root/name).read_bytes()
    assert (out/name).read_bytes() == actual, name
    observed[name] = sha(actual)
receipts = json.loads((archive/'receipts.json').read_bytes())
for name,expected in receipts['files'].items():
    assert sha((root/name).read_bytes()) == expected, name
config = {'.gitattributes':{'before_committed_blob_sha256':sha(before),
                          'before_worktree_sha256':None,
                          'after_worktree_sha256':sha((root/'.gitattributes').read_bytes()),
                          'after_index_blob_sha256':sha(git('show',':.gitattributes'))},
          'qa/evidence/vision-capability-probe/.gitattributes':{
              'before':'absent','after_worktree_sha256':observed['qa/evidence/vision-capability-probe/.gitattributes']}}
result = {'status':'PACKAGING_CHECKOUT_BYTES_MATCH','source_candidate_before_packaging':'5587d30e',
          'changed_config':config,'checkout_fingerprints':observed,
          'receipt_sha256':sha((archive/'receipts.json').read_bytes()),
          'limits':'Packaging metadata added after runtime proof. No runtime tests rerun; prior receipts bind original source/environment, not new attributes. Raw working source and proof bytes unchanged. Before-worktree config hash was not measured; committed before-blob hash is explicit.'}
(archive/'packaging.json').write_bytes(json.dumps(result,indent=2).encode())
(archive/'packaging-instrument.py').write_bytes(Path(__file__).read_bytes())
print('PACKAGING_CHECKOUT_BYTES_MATCH',len(observed),'paths; original source inventory unchanged')
