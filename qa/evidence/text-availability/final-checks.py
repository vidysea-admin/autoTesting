"""Bind focused consumer checks and supplemental refusal proof to candidate content."""
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

root = Path.cwd()
evidence = root / 'qa/evidence/text-availability'
source_files = ['src/autotester/providers/' + n + '.py' for n in
                ('availability', 'model_chain', 'litellm_provider')]
source_files += ['tests/test_text_availability.py', 'tests/test_model_chain.py',
                 'tests/test_provider_attempts.py']
hashfile = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
def source_identity():
    return {n: hashfile(root / n) for n in source_files + ['pyproject.toml', 'uv.lock']}
env = dict(os.environ, PYTHONPATH=str(root / 'src'), PYTHONDONTWRITEBYTECODE='1')
checks = []
def run(name, command):
    result = subprocess.run([sys.executable, *command], cwd=root, env=env,
                            capture_output=True, text=True)
    output = evidence / (name + '.log')
    output.write_text(result.stdout + result.stderr, encoding='utf-8')
    checks.append({'name': name, 'command': [sys.executable, *command],
                   'cwd': str(root), 'exit': result.returncode,
                   'output': str(output.relative_to(root)), 'sha256': hashfile(output),
                   'source': source_identity()})
    print(name, result.returncode, flush=True)
    return result.returncode
run('consumers', ['-m', 'pytest', '-p', 'no:cacheprovider', '--basetemp=.work/pytest-consumers',
                 'tests/test_text_availability.py', 'tests/test_model_chain.py',
                 'tests/test_provider_attempts.py', 'tests/test_litellm_provider.py',
                 'tests/test_litellm_guard.py', 'tests/test_provider_factory.py'])
run('lint', ['-m', 'ruff', 'check', *source_files])
run('doctor', ['-m', 'autotester', 'doctor'])
run('preflight-candidate', ['C:/Users/product/.agents/skills/checker/scripts/review_budget.py',
    'preflight', '--root', str(root), '--import-name', 'autotester',
    '--import-root', str(root / 'src'), '--temp-parent', str(root / '.work')])
# The scratch writer translated LF to CRLF on Windows. Verify the exact semantic
# and canonical git-text identity rather than concealing the raw-byte difference.
bindings = {}
for name in source_files:
    candidate, restored = root / name, root / '.work/proof-copy' / name
    a, b = candidate.read_text(encoding='utf-8'), restored.read_text(encoding='utf-8')
    bindings[name] = {'candidate_raw': hashfile(candidate), 'restored_raw': hashfile(restored),
                      'canonical_text_equal': a == b,
                      'ast_equal': ast.dump(ast.parse(a)) == ast.dump(ast.parse(b))}
assert all(v['canonical_text_equal'] and v['ast_equal'] for v in bindings.values())
(evidence / 'canonical-source-binding.json').write_text(json.dumps(bindings, indent=2))
(evidence / 'checks.json').write_text(json.dumps(checks, indent=2))
for name in ('run-proof.py', 'final-checks.py'):
    shutil.copyfile(root / '.work' / name, evidence / name)
