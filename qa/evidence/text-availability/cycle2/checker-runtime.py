"""Independent bounded offline tests and one isolated refusal-guard sabotage."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

start = time.monotonic()
root = Path.cwd()
ev = root / 'qa/evidence/text-availability/cycle2'
scratch = root / '.work/checker-text-cycle2'
scratch.mkdir(exist_ok=True)
for name in ('src', 'tests', 'scripts'):
    shutil.copytree(root / name, scratch / name, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.pytest_cache'))
for name in ('pyproject.toml', 'uv.lock'):
    shutil.copy2(root / name, scratch / name)
(scratch / '.work').mkdir(exist_ok=True)
env = dict(os.environ, PYTHONPATH=str(scratch / 'src'), PYTHONDONTWRITEBYTECODE='1')
receipts = []
def run(label, args, expected):
    begun = time.monotonic()
    result = subprocess.run([sys.executable, *args], cwd=scratch, env=env,
                            capture_output=True, text=True, timeout=60)
    output = result.stdout + result.stderr
    (ev / (label + '.log')).write_text(output, encoding='utf-8')
    receipts.append({'label': label, 'command': [sys.executable, *args],
                     'cwd': str(scratch), 'exit': result.returncode,
                     'monotonic_start': begun, 'monotonic_end': time.monotonic(),
                     'output_sha256': hashlib.sha256((ev / (label + '.log')).read_bytes()).hexdigest()})
    (ev / 'checker-runtime-receipts.json').write_text(json.dumps(receipts, indent=2))
    print(label, result.returncode, flush=True)
    assert result.returncode == expected, output[-1800:]
    return output
run('checker-preflight', ['C:/Users/product/.agents/skills/checker/scripts/review_budget.py',
    'preflight', '--root', str(scratch), '--import-name', 'autotester',
    '--import-root', str(scratch / 'src'), '--temp-parent', str(scratch / '.work')], 0)
args = ['-m', 'pytest', '-p', 'no:cacheprovider', '--basetemp=.work/checker-pytest']
run('checker-boundaries', args + ['tests/test_text_availability.py',
    'tests/test_model_chain.py::test_cli_provider_defaults_resolve_through_the_chain'], 0)
path = scratch / 'src/autotester/providers/availability.py'
original = path.read_bytes()
text = original.decode().replace('    return None\n', '    return "service"\n')
assert text != original.decode()
path.write_bytes(text.encode())
try:
    output = run('checker-refusal-red', args + [
        'tests/test_text_availability.py::test_ambiguous_and_policy_failures_stop'], 1)
    assert 'FAILED tests/test_text_availability.py::test_ambiguous_and_policy_failures_stop' in output
finally:
    path.write_bytes(original)
assert path.read_bytes() == original
run('checker-refusal-restored', args + [
    'tests/test_text_availability.py::test_ambiguous_and_policy_failures_stop'], 0)
run('checker-lint', ['-m', 'ruff', 'check', 'src/autotester/providers/availability.py',
    'src/autotester/providers/model_chain.py', 'src/autotester/providers/litellm_provider.py',
    'tests/test_text_availability.py', 'tests/test_model_chain.py', 'tests/test_provider_attempts.py'], 0)
(ev / 'checker-runtime-duration.json').write_text(json.dumps(
    {'start_monotonic': start, 'end_monotonic': time.monotonic(), 'waits': [], 'tokens': None, 'cost': None}))
