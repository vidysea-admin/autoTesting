"""Before reusing GREEN, verify original runtime/source/copy/environment remain identical."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys

root = Path.cwd()
e = root/'qa/evidence/account-generation/cycle2'
load = lambda name: json.loads((e/name).read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
digest = lambda value: hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
binding, inventory = load('binding.json'), load('source-inventory.json')
copy = Path(binding['copy_root'])
assert all(sha(root/name) == value and sha(copy/name) == value
           for name, value in inventory.items())
assert digest(inventory) == binding['inventory_sha256']
assert sha(e/'proof.py') == binding['harness_sha256']
assert sha(e/'invoke.py') == binding['invoke_sha256']
assert sha(e/'control.py') == binding['control_sha256']
assert sha(e/'spec.json') == binding['spec_sha256']
assert sys.executable == binding['python'] and sys.version == binding['version']
assert sha(Path(sys.executable)) == binding['python_sha256']
deps = sorted((d.metadata.get('Name', ''), d.version) for d in importlib.metadata.distributions())
assert digest(deps) == binding['dependencies_sha256']
environment = {key: os.environ[key] for key in ('SYSTEMROOT','WINDIR','PATH','PATHEXT',
                'COMSPEC','USERPROFILE','APPDATA','LOCALAPPDATA') if key in os.environ}
environment.update(PYTHONPATH=str(copy/'src'), PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1',
                   PYTHONHASHSEED='0', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', OMP_THREAD_LIMIT='1',
                   TEMP=str(copy), TMP=str(copy))
assert load('environment.json') == environment
assert digest(environment) == binding['environment_sha256']
assert load('green.json')['exit_code'] == load('control.json')['exit_code'] == 0
result = dict(status='MAKER_GREEN_REUSE_VALIDATED', source=binding['source'],
              harness_sha256=sha(e/'reuse.py'), inventory_count=len(inventory))
(e/'reuse.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result))
