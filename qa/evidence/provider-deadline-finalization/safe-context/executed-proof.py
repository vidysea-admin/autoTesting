"""Prepare source-bound deadline proof copy, then run only the coordinator-granted baseline."""
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
frozen = '10abf59e03e8459064508d309072f1bf05a1e4be'
proof = root / '.work/deadline-safe-context'
evidence = root / 'qa/evidence/provider-deadline-finalization/safe-context'
source = ['src/autotester/providers/' + name + '.py' for name in
          ('attempts', 'litellm_provider', 'gemini', 'gemini_files', 'vision_probe',
           'video_frames', 'model_chain', 'availability', 'base')]
source += ['tests/test_provider_deadlines.py', 'tests/test_provider_deadline_consumers.py',
           'tests/test_provider_attempts.py', 'tests/test_text_availability.py']
fixtures = ['tests/conftest.py', 'tests/litellm_fake.py', 'tests/auth_login_fixture.py',
            'tests/test_video_frames.py', 'tests/test_vision_probe.py',
            'tests/test_gemini_media_guard.py', 'tests/tests_mutation_fixtures.py',
            'scripts/regression_proof.py', 'pyproject.toml', 'uv.lock']
digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
def inventory(base, names):
    return {name: digest(base / name) for name in names}
selectors = ['tests/test_provider_deadlines.py::test_expired_vendor_failure_suppresses_canary_traceback', 'tests/test_provider_deadlines.py::test_late_chain_response_preserves_usage_and_never_falls_back', 'tests/test_provider_deadlines.py::test_direct_transport_deadline_is_anchored_before_response', 'tests/test_provider_deadlines.py::test_final_allowed_call_succeeds_before_deadline', 'tests/test_provider_deadline_consumers.py::test_gemini_sdk_response_checks_enclosing_deadline', 'tests/test_provider_deadline_consumers.py::test_gemini_validated_media_is_checked_before_return', 'tests/test_provider_deadline_consumers.py::test_probe_completion_clears_capability_if_evaluation_runs_late']
env = dict(os.environ, PYTHONPATH=str(proof / 'src'), PYTHONDONTWRITEBYTECODE='1')
if sys.argv[1] == 'prepare':
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip() == frozen
    proof.mkdir()
    evidence.mkdir(parents=True)
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
    environment = {'frozen_head': frozen, 'python': sys.executable, 'version': sys.version,
                   'dependencies': sorted((d.metadata['Name'], d.version)
                                          for d in importlib.metadata.distributions()),
                   'source': inventory(proof, source), 'fixtures_lock': inventory(proof, fixtures),
                   'copy': 'complete src/tests/scripts including tests_mutation_fixtures.py; no caches',
                   'maker_active_seconds': None, 'maker_tokens': None, 'maker_cost': None}
    (evidence / 'environment.json').write_text(json.dumps(environment, indent=2))
    command = [sys.executable, 'C:/Users/product/.agents/skills/checker/scripts/review_budget.py',
        'preflight', '--root', str(proof), '--import-name', 'autotester',
        '--import-root', str(proof / 'src'), '--temp-parent', str(proof / '.work')]
    result = subprocess.run(command, cwd=proof, env=env, capture_output=True, text=True)
    (evidence / 'preflight.log').write_text(result.stdout + result.stderr)
    assert result.returncode == 0
    (evidence / 'readiness.json').write_text(json.dumps({'frozen_head': frozen,
        'command': command, 'preflight_exit': result.returncode,
        'preflight_sha256': digest(evidence / 'preflight.log'),
        'environment_sha256': digest(evidence / 'environment.json'), 'selectors': selectors,
        'tests_started': False}, indent=2))
    print('complete cache-free copy and retained own-source preflight ready; tests not started')
elif sys.argv[1] == 'run':
    environment = json.loads((evidence / 'environment.json').read_text())
    assert inventory(proof, source) == inventory(root, source) == environment['source']
    before = inventory(proof, source)
    command = [sys.executable, '-B', '-m', 'pytest', '-p', 'no:cacheprovider',
               '--basetemp=.work/pytest-initial', *selectors]
    started = time.monotonic()
    result = subprocess.run(command, cwd=proof, env=env, capture_output=True, text=True)
    elapsed = time.monotonic() - started
    output = evidence / 'initial.log'
    output.write_text(result.stdout + result.stderr)
    assert before == inventory(proof, source)
    receipt = {'frozen_head': frozen, 'command': command, 'cwd': str(proof),
               'exit_code': result.returncode, 'command_elapsed_s': elapsed,
               'source_before': before, 'source_after': inventory(proof, source),
               'fixtures_lock': inventory(proof, fixtures),
               'environment_sha256': digest(evidence / 'environment.json'),
               'output': str(output.relative_to(root)), 'sha256': digest(output)}
    (evidence / 'initial-receipt.json').write_text(json.dumps(receipt, indent=2))
    print(result.stdout[-3000:] + result.stderr[-1000:])
    print('pytest_exit=' + str(result.returncode))
    shutil.copyfile(root / '.work/deadline-safe-context.py', evidence / 'initial-proof.py')
else:
    raise ValueError('prepare or run only')
