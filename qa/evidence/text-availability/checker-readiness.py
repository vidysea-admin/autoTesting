"""Independent pre-test check of mutation receipt source bindings."""
import hashlib
import json
import subprocess
import time
from pathlib import Path

start = time.monotonic()
root = Path.cwd()
out = root / 'qa/evidence/text-availability'
candidate = 'db143be1181721b27dc72e70a7e09ab982ee9e69'
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
assert head == candidate
manifest = (root / 'qa/manifests/text-availability.md').read_text()
assert 'Status: ready-for-check' in manifest and 'Fix cycle: 1' in manifest
receipts = json.loads((out / 'receipts.json').read_text())
by_label = {r['label']: r for r in receipts}
missing = []
for label, source, before, after, node in json.loads((out / 'mutations.json').read_text()):
    for suffix, expected in [('red', 1), ('restored', 0)]:
        r = by_label[label + '-' + suffix]
        assert r['exit'] == expected
        assert hashlib.sha256((root / r['output']).read_bytes()).hexdigest() == r['sha256']
        if source not in r['source']:
            missing.append({'label': r['label'], 'unbound_mutated_source': source})
result = {'candidate': head, 'cycle': 1, 'verdict': 'HOLD' if missing else 'READY',
          'missing_contemporaneous_source_bindings': missing,
          'pytest_executed': False, 'phase_start_monotonic': start,
          'phase_end_monotonic': time.monotonic()}
(out / 'checker-readiness.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result))
