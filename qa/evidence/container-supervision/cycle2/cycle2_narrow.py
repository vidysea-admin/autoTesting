"""Add one unique-context exit guard proof without rewriting historical wide receipts."""
from pathlib import Path
import json

p = Path(__file__).with_name('cycle2_proof.py')
ns = {'__file__': str(p)}
exec(p.read_text().split("assert not OUT.exists()")[0], ns)
ns['TEST'] = 'tests/test_container_supervision.py'
exec(p.read_text().split('def pytest(name, nodes, expected):')[1].split("TEST = 'tests/test_container_supervision.py'",1)[0].join(['def pytest(name, nodes, expected):', '']), ns)
old = ('        while not stopping:\n'
       '            reap_children(children)\n'
       '            if any(child.returncode is not None for child in children):\n'
       '                print("container service exited; restarting stack", file=sys.stderr)\n'
       '                return 1')
new = old[:-1]+'0'
path = 'docker/supervise.py'
frozen = ns['FROZEN']
assert frozen[path].count(old.encode()) == 1
mutation = {'name': 'exit-detection-narrow', 'file': path, 'old': old, 'new': new,
            'anchor_count': 1, 'kills': [ns['TEST']+'::test_any_exit_fails_stack_and_reaps_other_services']}
target = ns['COPY']/path
expected = {**frozen, path: frozen[path].replace(old.encode(), new.encode())}
assert ns['pytest']('exit-detection-narrow-green', mutation['kills'], frozen).returncode == 0
target.write_bytes(expected[path])
ns['save'](ns['OUT']/'exit-detection-narrow.mutation.json', {**mutation,
    'before': ns['digest'](frozen[path]), 'after': ns['digest'](expected[path]), 'only_changed_file': path})
result = ns['pytest']('exit-detection-narrow-red', mutation['kills'], expected)
assert result.returncode == 1
assert 'FAILED '+mutation['kills'][0] in result.stdout.decode(errors='replace')
target.write_bytes(frozen[path])
assert ns['pytest']('exit-detection-narrow-restored', mutation['kills'], frozen).returncode == 0
spec = json.loads((ns['ROOT']/'qa/evidence/container-supervision/mutations.json').read_bytes())
spec['mutations'] = [mutation if item['name'] == 'exit-detection' else item for item in spec['mutations']]
spec['note'] = 'Primary exit guard now has one unique-context application; earlier four-return mutation receipts retained as supplemental historical evidence.'
ns['save'](ns['OUT']/'mutations.json', spec)
print('narrow unique exit guard proof complete')
