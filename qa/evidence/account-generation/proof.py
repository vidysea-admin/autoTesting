"""Seal maker-only SMTP M1 green/red/restored proof from a complete disposable copy."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path.cwd()
EVIDENCE = ROOT / 'qa/evidence/account-generation'
COPY = ROOT / '.work/account-generation-proof'
BASE = 'ac1efde173d4dc1d5fe8259f30888655a0072f08'
SOURCE = 'eb506b81a3c17ff2b7f69aaffd3148ff0c95316d'
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
def dump(name, value):
    (EVIDENCE / name).write_text(json.dumps(value, sort_keys=True, indent=2), encoding='utf-8')
def inventory(root):
    rows = {}
    for folder in ('src', 'tests', 'scripts'):
        for path in sorted((root / folder).rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
                rows[path.relative_to(root).as_posix()] = sha(path)
    for name in ('uv.lock', 'pyproject.toml'):
        rows[name] = sha(root / name)
    return rows
mode = sys.argv[1]
assert mode in ('baseline', 'mutations')
if mode == 'baseline':
    assert not COPY.exists()
assert subprocess.run(['git', 'diff', '--quiet', SOURCE, '--', 'src', 'tests', 'scripts', 'uv.lock', 'pyproject.toml']).returncode == 0
if mode == 'baseline':
    for folder in ('src', 'tests', 'scripts'):
        shutil.copytree(ROOT / folder, COPY / folder, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    for name in ('uv.lock', 'pyproject.toml'):
        shutil.copyfile(ROOT / name, COPY / name)
original = inventory(ROOT)
assert inventory(COPY) == original
dependencies = sorted((dist.metadata.get('Name', ''), dist.version) for dist in importlib.metadata.distributions())
environment = {key: os.environ[key] for key in ('SYSTEMROOT', 'WINDIR', 'PATH', 'PATHEXT', 'COMSPEC', 'USERPROFILE', 'APPDATA', 'LOCALAPPDATA') if key in os.environ}
environment.update(PYTHONPATH=str(COPY / 'src'), PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1', PYTHONHASHSEED='0', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', OMP_THREAD_LIMIT='1', TEMP=str(COPY), TMP=str(COPY))
spec = json.loads((EVIDENCE / 'spec.json').read_text())
dump('source-inventory.json', original)
dump('dependencies.json', dependencies)
dump('environment.json', environment)
common = dict(base=BASE, source=SOURCE, python=sys.executable, python_sha256=sha(Path(sys.executable)), version=sys.version, dependencies_sha256=digest(dependencies), environment_sha256=digest(environment), lock_sha256=sha(COPY / 'uv.lock'), harness_sha256=sha(EVIDENCE / 'proof.py'), invoke_sha256=sha(EVIDENCE / 'invoke.py'), spec_sha256=sha(EVIDENCE / 'spec.json'), copy_root=str(COPY), inventory_sha256=digest(original), maker_active_s=None, maker_tokens=None, maker_cost=None)
common['control_sha256'] = sha(EVIDENCE / 'control.py')
dump('binding.json', common)
def run(label, nodes, expected, code):
    assert inventory(ROOT) == original and inventory(COPY) == expected
    command = ([sys.executable, '-B', str(EVIDENCE / 'control.py'), str(COPY / 'src'), *nodes]
               if label == 'control' else
               [sys.executable, '-B', str(EVIDENCE / 'invoke.py'), str(COPY / 'src'), *nodes,
                '--basetemp', str(COPY / ('.temp-' + label)), '-p', 'no:cacheprovider', '-o', 'addopts='])
    before = dict(common, label=label, command=command, command_sha256=digest(command), nodes=nodes, source_inventory_sha256=digest(expected), overrides={key: value for key, value in expected.items() if original[key] != value}, started_at=time.time(), started_monotonic=time.monotonic(), status='running')
    dump(label + '-before.json', before)
    with (EVIDENCE / (label + '.log')).open('wb') as output:
        result = subprocess.run(command, cwd=COPY, env=environment, stdout=output, stderr=subprocess.STDOUT, timeout=100)
    after = dict(before, status='finished', exit_code=result.returncode, finished_at=time.time(), finished_monotonic=time.monotonic(), output_sha256=sha(EVIDENCE / (label + '.log')))
    after['duration_s'] = after['finished_monotonic'] - before['started_monotonic']
    assert inventory(COPY) == expected and inventory(ROOT) == original
    after['after_source_inventory_sha256'] = digest(inventory(COPY))
    log = (EVIDENCE / (label + '.log')).read_text(encoding='utf-8', errors='replace')
    runtime = [line for line in log.splitlines() if line.startswith('__RUNTIME__')]
    assert len(runtime) == 1
    identity = json.loads(runtime[0].removeprefix('__RUNTIME__'))
    assert identity['dependencies_sha256'] == common['dependencies_sha256']
    assert Path(identity['import_file']).is_relative_to(COPY / 'src')
    after['runtime_identity'] = identity
    dump(label + '.json', after)
    assert result.returncode == code, log
    return log
if mode == 'baseline':
    run('control', spec['files'], original, 0)
    run('green', spec['tests'], original, 0)
    raise SystemExit(0)
ledger = []
for index, item in enumerate(spec['mutations'], 1):
    path = COPY / item['file']
    raw = path.read_bytes()
    anchor = item['old'].encode()
    assert raw.count(anchor) == 1
    changed = raw.replace(anchor, item['new'].encode(), 1)
    assert raw != changed
    path.write_bytes(changed)
    assert path.read_bytes() == changed
    expected = dict(original)
    expected[item['file']] = sha(path)
    label = f'm{index:02}'
    try:
        red = run(label + '-red', [item['node']], expected, 1)
        assert 'FAILED ' + item['node'] in red
    finally:
        path.write_bytes(raw)
        assert path.read_bytes() == raw
    restored = run(label + '-restored', [item['node']], original, 0)
    assert 'passed' in restored
    ledger.append(dict(name=item['name'], file=item['file'], anchor_count=1, original_sha256=hashlib.sha256(raw).hexdigest(), mutated_sha256=hashlib.sha256(changed).hexdigest(), restored_sha256=sha(path), node=item['node'], red_receipt=label+'-red.json', restored_receipt=label+'-restored.json'))
    dump('mutation-ledger.json', ledger)
    print('sealed', index, item['name'], flush=True)
dump('completed.json', dict(binding_sha256=sha(EVIDENCE/'binding.json'), ledger_sha256=sha(EVIDENCE/'mutation-ledger.json'), all_restored=inventory(COPY)==original, triples=len(ledger)))
