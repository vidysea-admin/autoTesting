"""Run only a coordinator-granted deadline risk group on the sealed proof copy."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('operation', choices=('prepare', 'group'))
parser.add_argument('--candidate', required=True)
parser.add_argument('--group', choices=('A', 'B', 'C'))
args = parser.parse_args()
root = Path.cwd()
evidence = root / 'qa/evidence/provider-deadline-finalization/final'
proof = root / '.work/deadline-final-proof'
spec_path = evidence / 'spec.json'
harness_path = evidence / 'proof.py'
spec = json.loads(spec_path.read_text())
digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
source = ['src/autotester/providers/' + name + '.py' for name in
          ('attempts', 'litellm_provider', 'gemini', 'gemini_files', 'vision_probe',
           'video_frames', 'model_chain', 'availability', 'base')]
source += ['tests/test_provider_deadlines.py', 'tests/test_provider_deadline_consumers.py',
           'tests/test_provider_attempts.py', 'tests/test_text_availability.py']
fixtures = ['tests/conftest.py', 'tests/litellm_fake.py', 'tests/auth_login_fixture.py',
            'tests/test_video_frames.py', 'tests/test_vision_probe.py',
            'tests/test_gemini_media_guard.py', 'tests/tests_mutation_fixtures.py',
            'scripts/regression_proof.py', 'pyproject.toml', 'uv.lock']
def inventory(base, names):
    return {name: digest(base / name) for name in names}
env = dict(os.environ, PYTHONPATH=str(proof / 'src'), PYTHONDONTWRITEBYTECODE='1')
if args.operation == 'prepare':
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip() == args.candidate
    proof.mkdir()
    for name in ('src', 'tests', 'scripts'):
        shutil.copytree(root / name, proof / name,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.pytest_cache'))
    for name in ('pyproject.toml', 'uv.lock'):
        shutil.copy2(root / name, proof / name)
    (proof / '.work').mkdir()
    assert (proof / 'tests/tests_mutation_fixtures.py').is_file()
    assert not list(proof.rglob('__pycache__'))
    assert inventory(proof, source) == inventory(root, source)
    assert inventory(proof, fixtures) == inventory(root, fixtures)
    environment = {'sealed_candidate': args.candidate, 'source_test': spec['source_test_candidate'],
                   'production': spec['production_candidate'], 'python': sys.executable,
                   'version': sys.version,
                   'dependencies': sorted((d.metadata['Name'], d.version)
                                          for d in importlib.metadata.distributions()),
                   'source': inventory(proof, source), 'fixtures_lock': inventory(proof, fixtures),
                   'spec_sha256': digest(spec_path), 'harness_sha256': digest(harness_path),
                   'copy': 'complete src/tests/scripts incl tests_mutation_fixtures.py; no caches',
                   'maker_active_seconds': None, 'maker_tokens': None, 'maker_cost': None}
    (evidence / 'environment.json').write_text(json.dumps(environment, indent=2))
    command = [sys.executable, 'C:/Users/product/.agents/skills/checker/scripts/review_budget.py',
        'preflight', '--root', str(proof), '--import-name', 'autotester',
        '--import-root', str(proof / 'src'), '--temp-parent', str(proof / '.work')]
    result = subprocess.run(command, cwd=proof, env=env, capture_output=True, text=True)
    output = evidence / 'preflight.log'
    output.write_text(result.stdout + result.stderr)
    assert result.returncode == 0
    (evidence / 'readiness.json').write_text(json.dumps({'sealed_candidate': args.candidate,
        'command': command, 'exit_code': result.returncode, 'output_sha256': digest(output),
        'environment_sha256': digest(evidence / 'environment.json'), 'tests_started': False}, indent=2))
    print('complete copy, sealed source/spec/harness and own-import preflight ready; no tests started')
    raise SystemExit(0)
assert args.group
environment = json.loads((evidence / 'environment.json').read_text())
assert environment['sealed_candidate'] == args.candidate
assert digest(spec_path) == environment['spec_sha256']
assert digest(harness_path) == environment['harness_sha256']
baseline = environment['source']
assert inventory(root, source) == inventory(proof, source) == baseline
assert inventory(proof, fixtures) == environment['fixtures_lock']
group = spec['groups'][args.group]
receipts = []
receipt_path = evidence / ('group-' + args.group + '-receipts.json')
assert not receipt_path.exists(), 'Preserve completed evidence; never overwrite a group'
def run(label, selectors, expected=0, mutation=None, *, lint=False):
    before = inventory(proof, source)
    command = ([sys.executable, '-m', 'ruff', 'check', *selectors] if lint else
               [sys.executable, '-B', '-m', 'pytest', '-p', 'no:cacheprovider',
                '--basetemp=.work/pytest-group-' + args.group, *selectors])
    started = time.monotonic()
    result = subprocess.run(command, cwd=proof, env=env, capture_output=True, text=True)
    elapsed = time.monotonic() - started
    output = result.stdout + result.stderr
    path = evidence / (args.group + '-' + label + '.log')
    path.write_text(output)
    assert before == inventory(proof, source)
    assert inventory(proof, fixtures) == environment['fixtures_lock']
    assert digest(spec_path) == environment['spec_sha256']
    assert digest(harness_path) == environment['harness_sha256']
    receipts.append({'label': label, 'group': args.group, 'command': command, 'cwd': str(proof),
                     'exit_code': result.returncode, 'expected_exit': expected,
                     'command_elapsed_s': elapsed, 'source_before': before,
                     'source_after': inventory(proof, source),
                     'fixtures_lock': inventory(proof, fixtures),
                     'environment_sha256': digest(evidence / 'environment.json'),
                     'spec_sha256': digest(spec_path), 'harness_sha256': digest(harness_path),
                     'sealed_candidate': args.candidate, 'output': str(path.relative_to(root)),
                     'output_sha256': digest(path), 'mutation': mutation})
    receipt_path.write_text(json.dumps(receipts, indent=2))
    print(args.group, label, result.returncode, flush=True)
    assert result.returncode == expected, 'Unexpected result; inspect content-safe retained output'
    return output
run('baseline', group['controls'])
for row in group['mutations']:
    path = proof / row['path']
    original = path.read_bytes()
    old, new = row['old'].encode(), row['new'].encode()
    if b'\r\n' in original:
        old, new = old.replace(b'\n', b'\r\n'), new.replace(b'\n', b'\r\n')
    assert original.count(old) == 1, (row['id'], 'unique anchor required')
    applied = original.replace(old, new, 1)
    path.write_bytes(applied)
    assert [name for name, value in inventory(proof, source).items()
            if value != baseline[name]] == [row['path']]
    mutation = dict(row, original_sha256=hashlib.sha256(original).hexdigest(),
                    applied_sha256=hashlib.sha256(applied).hexdigest(), occurrences=1)
    try:
        output = run(row['id'] + '-red', [row['node']], 1, mutation)
        assert 'FAILED ' + row['node'].split('[')[0] in output, 'Named defending failure absent'
    finally:
        path.write_bytes(original)
    assert inventory(proof, source) == baseline
    run(row['id'] + '-restored', [row['node']])
run('controls-restored', group['controls'])
if args.group == 'C':
    run('scoped-lint', [source[index] for index in (0, 1, 2, 4, 9, 10, 11, 12)], lint=True)
assert inventory(proof, source) == inventory(root, source) == baseline
(evidence / ('group-' + args.group + '-binding.json')).write_text(json.dumps({
    'sealed_candidate': args.candidate, 'candidate': inventory(root, source),
    'restored': inventory(proof, source), 'exact_raw_restoration': True}, indent=2))
print('group ' + args.group + ' complete; release serial CPU lease', flush=True)
