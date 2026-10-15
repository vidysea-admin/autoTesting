"""Archive unchanged isolated role proofs while explicitly awaiting deadline dependency."""
import hashlib
import importlib.metadata
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'.work/role-proof-r2'
ARCHIVE = ROOT/'qa/evidence/vision-role-defaults'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
data = json.loads((OUT/'receipts.json').read_bytes())
spec = json.loads((ARCHIVE/'spec.json').read_bytes())
assert len(data['mutations']) == len(spec['mutations']) == 14
assert data['instrument_sha256'] == sha(ARCHIVE/'proof.py')
assert data['spec_sha256'] == sha(ARCHIVE/'spec.json')
assert data['python'] == sys.executable and data['version'] == sys.version
assert all(importlib.metadata.version(n) == v for n,v in data['dependencies'].items())
assert data['preflight_sha256'] == sha(OUT/'preflight.log')
assert data['lint_sha256'] == sha(OUT/'lint.log')
for name,expected in data['files'].items():
    assert sha(ROOT/name) == expected == sha(OUT/'subject'/name), name
old = json.loads((ARCHIVE/'receipts.json').read_bytes())
assert old['mutations'] == data['mutations'][:8]
assert old['bursts'] == data['bursts'][:len(old['bursts'])]
history = ARCHIVE/'receipts-through-8.json'
assert not history.exists()
history.write_bytes((ARCHIVE/'receipts.json').read_bytes())
green = [data['baseline']]+[r['restored'] for r in data['bursts']]
for row in green+data['mutations']:
    phase = row['phase']
    assert row['log_sha256'] == sha(OUT/(phase+'.log'))
    cases = list(ET.parse(OUT/(phase+'.xml')).iter('testcase'))
    failures = [c.attrib['name'] for c in cases if c.find('failure') is not None]
    assert not any(c.find('error') is not None for c in cases), phase
    if row in green:
        assert row['exit'] == 0 and len(cases) == 15 and not failures, phase
    else:
        assert row['exit'] == 1 and failures == row['failures'], phase
        assert {n.split('::')[-1] for n in row['kills']} <= set(failures)
        raw = (ROOT/row['file']).read_bytes()
        before,after = row['old'].encode(),row['new'].encode()
        if raw.count(before) == 0 and b'\r\n' in raw:
            before,after = before.replace(b'\n',b'\r\n'),after.replace(b'\n',b'\r\n')
        assert raw.count(before) == 1
        assert hashlib.sha256(raw).hexdigest() == row['source_sha256']
        assert hashlib.sha256(raw.replace(before,after)).hexdigest() == row['mutated_sha256']
records = json.loads((ROOT/'src/autotester/skills/vision-probe/capabilities.json').read_bytes())['records']
for record in records:
    name = 'primary-model-probes.json' if 'deepseek' in record['result']['model'] else 'gemini-model-probe.json'
    actual = json.loads((ARCHIVE/name).read_bytes())
    results = actual.get('results',[actual])
    assert record['receipt_sha256'] == sha(ARCHIVE/name)
    assert record['source_sha'] == actual['source_sha']
    assert any(row.get('result') == record['result'] for row in results)
for p in OUT.iterdir():
    if p.is_file() and p.suffix in {'.json','.log','.xml'}:
        destination = ARCHIVE/p.name
        if destination.exists() and p.name != 'receipts.json':
            assert destination.read_bytes() == p.read_bytes(), p.name
        destination.write_bytes(p.read_bytes())
pending = {'status':'DEPENDENCY_PENDING','isolation_evidence':'VALID',
           'source_checkpoint':'3a5098268fe54694b133dcb683fb29bb6d7145ff',
           'base':'57a010d5e4f5eebe21c605d704981a10dd2e8a5c',
           'risk_proofs':14,'green_cases_per_boundary':15,
           'source_inventory':'receipts.json files: live/copy bytes unchanged',
           'instrument_sha256':data['instrument_sha256'],'spec_sha256':data['spec_sha256'],
           'receipt_sha256':sha(ARCHIVE/'receipts.json'),
           'actual_probe_bindings':'Both packaged verified results match exact archived actual execution bytes/source SHA.',
           'pending':['independently checked late-success deadline dependency',
                      'focused interaction baseline on exact combined candidate',
                      'final source/evidence/Git checkout fingerprints and checker packet'],
           'actual_maker_usage':{'active_s':None,'tokens':None,'cost':None},
           'limits':'Historical proof is on unchanged parked source; no final readiness/PASS or changed dependency claim. No saved project apply/live call/source edit.'}
(ARCHIVE/'dependency-pending.json').write_bytes(json.dumps(pending,indent=2).encode())
(ARCHIVE/'evidence-archive-instrument.py').write_bytes(Path(__file__).read_bytes())
print('ISOLATION_EVIDENCE_VALID 14 named reds; baseline/allrestored15; DEPENDENCY_PENDING')
