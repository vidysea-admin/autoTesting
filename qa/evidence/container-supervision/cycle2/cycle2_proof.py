"""Byte-preserving cycle2 proofs; reject any unaccounted source or environment drift."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'qa/evidence/container-supervision/cycle2'
COPY = ROOT/'.work/container-supervision/cycle2-copy'
TEMP = ROOT/'.work/container-supervision/CONTemp/cycle2'
FILES = ['Dockerfile', 'docker/entrypoint.sh', 'docker/supervise.py', 'docker/DEPLOY.md',
         'tests/test_container_supervision.py', 'uv.lock', 'pyproject.toml', '.gitattributes',
         'docker/compose.prod.yml']
CANDIDATE = '326bf0a7ffa5296a81bcbe0bc5a112903bb68787'
DEPS = ['pytest', 'ruff', 'pydantic', 'PyYAML', 'fastapi']
ENV = dict(os.environ, PYTHONPATH=str(ROOT/'src'), PYTHONDONTWRITEBYTECODE='1',
           TMP=str(TEMP), TEMP=str(TEMP))
FROZEN = {p: (ROOT/p).read_bytes() for p in FILES}
def digest(value):
    return hashlib.sha256(value).hexdigest()
def save(path, value):
    path.write_bytes(json.dumps(value, indent=2).encode())
def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()
def snapshot(cwd, expected):
    actual = {p: (cwd/p).read_bytes() for p in FILES}
    assert actual == expected, [p for p in FILES if actual[p] != expected[p]]
    assert {p: (ROOT/p).read_bytes() for p in FILES} == FROZEN
    return {'source': {p: digest(v) for p, v in actual.items()},
            'candidate_source': {p: digest(v) for p, v in FROZEN.items()},
            'python': sys.executable, 'python_version': sys.version,
            'dependencies': {p: importlib.metadata.version(p) for p in DEPS},
            'lock_sha': digest(FROZEN['uv.lock']),
            'environment': {p: ENV[p] for p in ['PYTHONPATH', 'PYTHONDONTWRITEBYTECODE', 'TMP', 'TEMP']},
            'candidate_sha': CANDIDATE, 'cwd': str(cwd)}
def run(name, cwd, expected, args, timeout=30):
    before = snapshot(cwd, expected)
    before.update(command=args, started_utc=time.time(), started_monotonic=time.monotonic())
    save(OUT/f'{name}.before.json', before)
    result = subprocess.run(args, cwd=cwd, env=ENV, capture_output=True, timeout=timeout)
    log = result.stdout + result.stderr
    (OUT/f'{name}.log').write_bytes(log)
    after = snapshot(cwd, expected)
    for field in ['source', 'python', 'python_version', 'dependencies', 'lock_sha', 'environment']:
        assert after[field] == before[field]
    after.update(command=args, exit=result.returncode, log_sha=digest(log),
                 ended_utc=time.time(), duration_s=time.monotonic()-before['started_monotonic'])
    save(OUT/f'{name}.after.json', after)
    print(name, result.returncode, flush=True)
    return result

assert not OUT.exists(), 'never overwrite prior cycle2 receipts'
OUT.mkdir(parents=True)
COPY.mkdir(parents=True, exist_ok=True)
TEMP.mkdir(parents=True, exist_ok=True)
baseline = json.loads((ROOT/'qa/evidence/container-supervision/baseline.before.json').read_bytes())
assert all(digest(FROZEN[p]) == v for p, v in baseline['source'].items())
blobs = {p: git('rev-parse', f'{CANDIDATE}:{p}') for p in FILES}
assert {p: git('hash-object', p) for p in FILES} == blobs
for path, value in FROZEN.items():
    target = COPY/path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(value)
assert not list(COPY.rglob('__pycache__'))
save(OUT/'identity.json', {'candidate': CANDIDATE, 'current_head': git('rev-parse', 'HEAD'),
    'git_blobs': blobs, 'frozen_source': {p: digest(v) for p,v in FROZEN.items()},
    'newline_drift_proof': {p: digest(FROZEN[p].replace(b'\n', b'\r\n'))
        for p in ['docker/supervise.py', 'docker/entrypoint.sh']},
    'prior_evidence': 'cycle1 retained but not reused as mutation provenance',
    'maker_usage': {'active_s': None, 'tokens': None, 'cost': None}})
preflight = run('preflight', ROOT, FROZEN, [sys.executable,
    'C:/Users/product/.agents/skills/checker/scripts/review_budget.py', 'preflight',
    '--root', str(ROOT), '--import-name', 'autotester', '--import-root', str(ROOT/'src'),
    '--temp-parent', str(TEMP)])
assert preflight.returncode == 0
def pytest(name, nodes, expected):
    return run(name, COPY, expected, [sys.executable, '-m', 'pytest', '-p', 'no:cacheprovider',
               '--basetemp', str(TEMP/name), *nodes])
TEST = 'tests/test_container_supervision.py'
assert pytest('green-baseline', [TEST], FROZEN).returncode == 0
spec = json.loads((ROOT/'qa/evidence/container-supervision/mutations.json').read_bytes())
for mutation in spec['mutations']:
    name, path = mutation['name'], mutation['file']
    old, new = mutation['old'].encode(), mutation['new'].encode()
    assert FROZEN[path].count(old) == mutation['anchor_count']
    changed = FROZEN[path].replace(old, new)
    assert changed != FROZEN[path]
    expected = {**FROZEN, path: changed}
    (COPY/path).write_bytes(changed)
    save(OUT/f'{name}.mutation.json', {**mutation, 'before': digest(FROZEN[path]),
                                      'after': digest(changed), 'only_changed_file': path})
    result = pytest(name+'-red', mutation['kills'], expected)
    assert result.returncode == 1
    text = result.stdout.decode(errors='replace')
    assert 'ERROR collecting' not in text and 'INTERNALERROR' not in text
    for node in mutation['kills']:
        assert 'FAILED '+node in text, (name, node, text)
    (COPY/path).write_bytes(FROZEN[path])
    assert pytest(name+'-restored', mutation['kills'], FROZEN).returncode == 0
assert pytest('green-final', [TEST], FROZEN).returncode == 0
save(OUT/'readiness.json', {'status': 'READY', 'fix_cycle': 2, 'source_candidate': CANDIDATE,
    'mutation_count': len(spec['mutations']), 'baseline_green': True, 'final_green': True,
    'all_red_only_declared_bytes': True, 'all_restored_exact_bytes': True,
    'all_environments_stable': True, 'every_named_failure_attributed': True,
    'receipts': {p.name: digest(p.read_bytes()) for p in OUT.iterdir() if p.is_file()}})
print('READY cycle2; all14 exact-byte chains audited', flush=True)
