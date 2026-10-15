"""Validate exact source, harness and named green/red/restored SMTP M1 receipts."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path.cwd()
E = ROOT / 'qa/evidence/smtp-profile'
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
def load(name):
    return json.loads((E / name).read_text())
binding = load('binding.json')
source = load('source-inventory.json')
assert digest(source) == binding['inventory_sha256']
assert all(sha(ROOT / path) == value for path, value in source.items())
for field, path in [('harness_sha256', 'proof.py'), ('invoke_sha256', 'invoke.py'), ('spec_sha256', 'spec.json')]:
    assert sha(E / path) == binding[field]
assert sha(Path(sys.executable)) == binding['python_sha256']
assert digest(load('dependencies.json')) == binding['dependencies_sha256']
assert digest(load('environment.json')) == binding['environment_sha256']
def receipt(label, expected, code):
    before, after = load(label+'-before.json'), load(label+'.json')
    assert before['status'] == 'running' and after['status'] == 'finished'
    assert all(after[key] == value for key, value in before.items() if key != 'status')
    assert all(after[key] == value for key, value in binding.items())
    assert after['exit_code'] == code
    assert after['output_sha256'] == sha(E / (label+'.log'))
    assert after['source_inventory_sha256'] == after['after_source_inventory_sha256'] == digest(expected)
    assert after['command_sha256'] == digest(after['command'])
    assert after['finished_monotonic'] >= after['started_monotonic']
    identity = after['runtime_identity']
    assert identity['python'] == binding['python'] and identity['version'] == binding['version']
    assert identity['dependencies_sha256'] == binding['dependencies_sha256']
    assert Path(identity['import_file']).is_relative_to(Path(binding['copy_root']) / 'src')
    log = (E / (label+'.log')).read_text(encoding='utf-8')
    assert '__RUNTIME__'+json.dumps(identity, sort_keys=True) in log
    return after, log
green, log = receipt('green', source, 0)
assert '23 passed' in log
ledger, spec = load('mutation-ledger.json'), load('spec.json')
assert len(ledger) == len(spec['mutations']) == 11
for index, (row, mutation) in enumerate(zip(ledger, spec['mutations'], strict=True), 1):
    raw = (ROOT / row['file']).read_bytes()
    assert raw.count(mutation['old'].encode()) == row['anchor_count'] == 1
    changed = raw.replace(mutation['old'].encode(), mutation['new'].encode(), 1)
    assert raw != changed
    assert hashlib.sha256(raw).hexdigest() == row['original_sha256'] == row['restored_sha256']
    assert hashlib.sha256(changed).hexdigest() == row['mutated_sha256']
    expected = dict(source)
    expected[row['file']] = row['mutated_sha256']
    red, rlog = receipt(f'm{index:02}-red', expected, 1)
    restored, slog = receipt(f'm{index:02}-restored', source, 0)
    assert red['nodes'] == restored['nodes'] == [mutation['node']] == [row['node']]
    assert 'FAILED '+row['node'] in rlog and '1 passed' in slog
done = load('completed.json')
assert done['all_restored'] and done['triples'] == 11
assert done['binding_sha256'] == sha(E/'binding.json')
assert done['ledger_sha256'] == sha(E/'mutation-ledger.json')
result = dict(status='MAKER_READINESS_VALIDATED', source=binding['source'], triples=11, receipts=23, inventory_count=len(source), maker_active_s=None, maker_tokens=None, maker_cost=None, checker_ratios='unverified')
(E/'readiness.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result))
