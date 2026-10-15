"""Reconstruct receipt bindings without executing tests."""
import ast
import hashlib
import json
import subprocess
import time
from pathlib import Path

start = time.monotonic()
root = Path.cwd()
ev = root / 'qa/evidence/text-availability'
out = ev / 'cycle2'
h = lambda b: hashlib.sha256(b).hexdigest()
load = lambda p: json.loads(p.read_text())
candidate = '035011aeb3c7cf868ba5ca41246c71c0627b3c7e'
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip() == candidate
assert 'Fix cycle: 2' in (root / 'qa/manifests/text-availability.md').read_text()
changed = subprocess.check_output(['git', 'diff', '--name-only', 'ec882aa8', candidate], text=True).splitlines()
assert all(p.startswith(('qa/manifests/', 'qa/evidence/')) for p in changed)
for name, digest in load(out / 'delta-packet.json')['evidence_sha256'].items():
    assert h((out / name).read_bytes()) == digest, name
original = {p: (root / p).read_bytes() for p in load(out / 'source-binding.json')['candidate']}
for r in load(out / 'receipts.json'):
    assert r['source_before'] == r['source_after']
    assert h((root / r['output']).read_bytes()) == r['output_sha256']
    assert h((out / 'environment.json').read_bytes()) == r['environment_sha256']
    assert r['exit_code'] == r['expected_exit']
    for p, digest in r['fixture_config_lock'].items():
        assert h((root / p).read_bytes()) == digest, p
    for p, digest in r['source_before'].items():
        if not r['label'].endswith('-red'):
            assert h(original[p]) == digest, (r['label'], p)
    if r['label'].endswith('-red'):
        assert r['source_before']['src/autotester/providers/attempts.py'] != h(original['src/autotester/providers/attempts.py'])
        assert 'FAILED tests/test_text_availability.py::test_enclosing_budget_never_falls_through' in (root / r['output']).read_text()
receipts = {r['label']: r for r in load(ev / 'receipts.json')}
issues = []
for label, path, before, after, node in load(ev / 'mutations.json'):
    if label in ('global_count', 'global_deadline'):
        continue
    red, restored = receipts[label + '-red'], receipts[label + '-restored']
    base = (root / path).read_text(encoding='utf-8')
    for r in (red, restored):
        assert h((root / r['output']).read_bytes()) == r['sha256']
    assert h(base.replace(before, after).encode().replace(b'\n', b'\r\n')) == red['source'][path], label
    assert h(base.encode().replace(b'\n', b'\r\n')) == restored['source'][path], label
    assert red['exit'] == 1 and restored['exit'] == 0
    assert 'FAILED ' + node.split('[')[0] in (root / red['output']).read_text()
result = {'candidate': candidate, 'cycle': 2, 'two_repaired_chains': 'bound',
          'original16_mutated_source_reconstruction': 'matched', 'tests_executed': False,
          'monotonic_start': start, 'monotonic_end': time.monotonic()}
(out / 'checker-readiness.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result))
