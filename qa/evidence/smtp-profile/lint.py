"""Seal touched-path lint against the same complete source and controlled runtime."""
import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

root = Path.cwd()
e = root / 'qa/evidence/smtp-profile'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
digest = lambda value: hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
load = lambda name: json.loads((e/name).read_text())
source, binding, environment = load('source-inventory.json'), load('binding.json'), load('environment.json')
assert all(sha(root/path) == value for path, value in source.items())
deps = sorted((dist.metadata.get('Name', ''), dist.version) for dist in importlib.metadata.distributions())
assert digest(deps) == binding['dependencies_sha256']
files = ['src/autotester/store/notification_prefs.py', 'src/autotester/ui/routes_profile.py', 'src/autotester/auth/policy.py', 'src/autotester/ui/routers.py', 'src/autotester/ui/theme.py', 'tests/test_notification_profile.py', 'tests/test_ui_auth_accounts.py']
command = [sys.executable, '-m', 'ruff', 'check', *files, '--no-cache']
receipt = dict(binding, command=command, command_sha256=digest(command), harness_sha256=sha(e/'lint.py'), cwd=str(root), runtime_ruff_module=importlib.util.find_spec('ruff').origin, started_at=time.time(), status='running')
(e/'lint-before.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
with (e/'lint.log').open('wb') as output:
    result = subprocess.run(command, cwd=root, env=environment, stdout=output, stderr=subprocess.STDOUT)
assert all(sha(root/path) == value for path, value in source.items())
receipt.update(status='finished', exit_code=result.returncode, output_sha256=sha(e/'lint.log'), finished_at=time.time(), after_source_inventory_sha256=digest(source))
(e/'lint.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
assert result.returncode == 0, (e/'lint.log').read_text()
print('sealed touched-path lint green')
