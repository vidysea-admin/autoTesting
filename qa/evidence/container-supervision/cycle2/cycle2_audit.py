"""Self-audit every primary proof phase against candidate bytes before checker dispatch."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'qa/evidence/container-supervision/cycle2'
def digest(value):
    return hashlib.sha256(value).hexdigest()
def load(name):
    return json.loads((OUT/name).read_bytes())
identity = load('identity.json')
frozen = {p: (ROOT/p).read_bytes() for p in identity['frozen_source']}
assert {p: digest(v) for p,v in frozen.items()} == identity['frozen_source']
spec = load('mutations.json')
baseline = load('green-baseline.before.json')
phases = {'preflight': (frozen, 0, []), 'green-baseline': (frozen, 0, []),
          'green-final': (frozen, 0, []),
          'exit-detection-narrow-green': (frozen, 0, [])}
for item in spec['mutations']:
    name, path = item['name'], item['file']
    old, new = item['old'].encode(), item['new'].encode()
    assert frozen[path].count(old) == 1
    expected = {**frozen, path: frozen[path].replace(old,new)}
    declaration = load(name+'.mutation.json')
    assert declaration['before'] == digest(frozen[path])
    assert declaration['after'] == digest(expected[path])
    phases[name+'-red'] = (expected, 1, item['kills'])
    phases[name+'-restored'] = (frozen, 0, [])
audit = {}
for name, (expected, code, kills) in phases.items():
    before, after = load(name+'.before.json'), load(name+'.after.json')
    expected_sha = {p: digest(v) for p,v in expected.items()}
    for record in (before,after):
        assert record['source'] == expected_sha, name
        assert record['candidate_source'] == identity['frozen_source'], name
        for field in ['python', 'python_version', 'dependencies', 'lock_sha', 'environment']:
            assert record[field] == baseline[field], (name,field)
    assert after['exit'] == code
    log = (OUT/(name+'.log')).read_bytes()
    assert digest(log) == after['log_sha']
    text = log.decode(errors='replace')
    for node in kills:
        assert 'FAILED '+node in text
        assert node in before['command']
    if kills:
        assert 'ERROR collecting' not in text and 'INTERNALERROR' not in text
    audit[name] = {'exit': code, 'log_sha': digest(log), 'source_exact': True,
                   'environment_exact': True, 'named_failure_nodes': kills,
                   'duration_s': after['duration_s']}
for name in ['cycle2_proof.py', 'cycle2_narrow.py', 'cycle2_audit.py']:
    shutil.copy2(Path(__file__).with_name(name), OUT/name)
result = {'status': 'READY', 'fix_cycle': 2, 'source_candidate': identity['candidate'],
          'primary_mutations': 14, 'all_primary_anchor_counts': 1,
          'phase_count': len(audit), 'phases': audit,
          'historical_extra': 'exit-detection four-return cycle2 proof is retained but not a primary unique guard proof',
          'maker_usage': {'active_s': None, 'tokens': None, 'cost': None},
          'artifact_hashes': {p.name:digest(p.read_bytes()) for p in OUT.iterdir()
                             if p.is_file() and p.name != 'self-audit.json'}}
(OUT/'self-audit.json').write_bytes(json.dumps(result,indent=2).encode())
print('READY: 14 unique primary mutations;', len(audit), 'phases independently revalidated')
