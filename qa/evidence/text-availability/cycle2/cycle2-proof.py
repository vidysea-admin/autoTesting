"""Replace only unauthenticated count/deadline proof with contemporaneous bindings."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

root = Path.cwd()
frozen = 'ec882aa8fb99165afa116a70cd8941c3bbdaf8a2'
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip() == frozen
proof = root / '.work/text-availability-cycle2'
evidence = root / 'qa/evidence/text-availability/cycle2'
proof.mkdir()
evidence.mkdir()
for name in ('src', 'tests', 'scripts'):
    shutil.copytree(root / name, proof / name,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.pytest_cache'))
for name in ('pyproject.toml', 'uv.lock'):
    shutil.copy2(root / name, proof / name)
(proof / '.work').mkdir()
assert (proof / 'tests/tests_mutation_fixtures.py').is_file()
assert not list(proof.rglob('__pycache__'))
source = ['src/autotester/providers/' + name + '.py' for name in
          ('availability', 'model_chain', 'litellm_provider', 'attempts')]
source += ['tests/test_text_availability.py', 'tests/test_model_chain.py',
           'tests/test_provider_attempts.py']
fixtures = ['tests/conftest.py', 'tests/litellm_fake.py', 'tests/tests_mutation_fixtures.py',
            'tests/auth_login_fixture.py', 'scripts/regression_proof.py',
            'pyproject.toml', 'uv.lock']
digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
def inventory(base, names):
    return {name: digest(base / name) for name in names}
baseline = inventory(proof, source)
assert baseline == inventory(root, source)
environment = {'frozen_head': frozen, 'python': sys.executable, 'version': sys.version,
               'dependencies': sorted((d.metadata['Name'], d.version)
                                      for d in importlib.metadata.distributions()),
               'source': baseline, 'fixture_config_lock': inventory(proof, fixtures),
               'candidate_fixture_config_lock': inventory(root, fixtures),
               'copy': 'complete src/tests/scripts including tests_mutation_fixtures.py',
               'excluded': ['__pycache__', '*.pyc', '.pytest_cache'],
               'maker_active_seconds': None, 'maker_tokens': None, 'maker_cost': None}
assert environment['fixture_config_lock'] == environment['candidate_fixture_config_lock']
(evidence / 'environment.json').write_text(json.dumps(environment, indent=2))
env = dict(os.environ, PYTHONPATH=str(proof / 'src'), PYTHONDONTWRITEBYTECODE='1')
receipts = []
def run(label, arguments, expected, mutation=None):
    before = inventory(proof, source)
    fixture_before = inventory(proof, fixtures)
    started = time.monotonic()
    command = [sys.executable, *arguments]
    result = subprocess.run(command, cwd=proof, env=env, capture_output=True, text=True)
    ended = time.monotonic()
    output = result.stdout + result.stderr
    path = evidence / (label + '.log')
    path.write_text(output, encoding='utf-8')
    after = inventory(proof, source)
    assert before == after, (label, 'source changed during command')
    assert fixture_before == inventory(proof, fixtures)
    receipts.append({'label': label, 'command': command, 'cwd': str(proof),
                     'exit_code': result.returncode, 'expected_exit': expected,
                     'source_before': before, 'source_after': after,
                     'fixture_config_lock': fixture_before,
                     'environment_sha256': digest(evidence / 'environment.json'),
                     'output': str(path.relative_to(root)), 'output_sha256': digest(path),
                     'frozen_head': frozen, 'mutation': mutation,
                     'command_elapsed_s': ended - started})
    (evidence / 'receipts.json').write_text(json.dumps(receipts, indent=2))
    print(label, result.returncode, flush=True)
    assert result.returncode == expected, output[-3000:]
    return output
run('preflight', ['C:/Users/product/.agents/skills/checker/scripts/review_budget.py',
    'preflight', '--root', str(proof), '--import-name', 'autotester',
    '--import-root', str(proof / 'src'), '--temp-parent', str(proof / '.work')], 0)
nodes = ['tests/test_text_availability.py::test_enclosing_budget_never_falls_through[2-30]',
         'tests/test_text_availability.py::test_enclosing_budget_never_falls_through[6-0]']
arguments = ['-m', 'pytest', '-p', 'no:cacheprovider', '--basetemp=.work/pytest']
run('baseline', arguments + nodes, 0)
target = proof / 'src/autotester/providers/attempts.py'
original = target.read_bytes()
mutations = [
    ('global_count', b'if scope.used >= scope.max_calls:', b'if False:', nodes[0]),
    ('global_deadline', b'if scope.deadline is not None:', b'if False:', nodes[1]),
]
for label, old, new, node in mutations:
    assert target.read_bytes() == original
    assert original.count(old) == 1
    applied = original.replace(old, new, 1)
    target.write_bytes(applied)
    assert target.read_bytes() == applied
    changed = [name for name, value in inventory(proof, source).items()
               if value != baseline[name]]
    assert changed == ['src/autotester/providers/attempts.py']
    mutation = {'path': changed[0], 'before': old.decode(), 'after': new.decode(),
                'occurrences': 1, 'original_sha256': hashlib.sha256(original).hexdigest(),
                'applied_sha256': hashlib.sha256(applied).hexdigest(), 'node': node}
    try:
        output = run(label + '-red', arguments + [node], 1, mutation)
        assert 'FAILED ' + node in output, (label, 'named failure absent')
    finally:
        target.write_bytes(original)
    assert inventory(proof, source) == baseline
    run(label + '-restored', arguments + [node], 0)
assert inventory(proof, source) == inventory(root, source) == baseline
(evidence / 'source-binding.json').write_text(json.dumps({
    'frozen_head': frozen, 'candidate': inventory(root, source),
    'restored': inventory(proof, source), 'raw_bytes_equal': True}, indent=2))
shutil.copyfile(root / '.work/cycle2-proof.py', evidence / 'cycle2-proof.py')
print('cycle2: baseline 2 green; two unique named reds; exact-byte restoration green', flush=True)
