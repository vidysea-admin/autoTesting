"""Check packet bindings and record the bounded source structural checks."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

root = Path.cwd()
directory = root / 'qa/evidence/provider-vision-integration'
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
receipts = json.loads((directory / 'receipts.json').read_text())
assert len(receipts) == 30
for receipt in receipts:
    assert receipt['exit_code'] == receipt['expected_exit']
    assert receipt['source_before'] == receipt['source_after']
    assert digest(root / receipt['output']) == receipt['sha256']
    assert digest(directory / 'environment.json') == receipt['environment_sha256']
reds = [r for r in receipts if r['label'].endswith('-red')]
assert len(reds) == 13
for receipt in reds:
    mutation = receipt['mutation']
    assert receipt['source_before'][mutation['path']] == mutation['applied_sha256']
    assert 'FAILED ' + mutation['test'].split('[')[0] in (root / receipt['output']).read_text()
    assert mutation['original_sha256'] != mutation['applied_sha256']
source_binding = json.loads((directory / 'source-binding.json').read_text())
assert source_binding['candidate'] == source_binding['restored']
assert all(digest(root / name) == value for name, value in source_binding['candidate'].items())
paths = ['src/autotester/providers/' + name + '.py' for name in
         ('model_chain', 'litellm_provider', 'video_frames')]
paths += ['tests/test_provider_vision_integration.py', 'tests/test_video_frames.py']
structural = []
for name in paths:
    text = (root / name).read_text(encoding='utf-8')
    tree = ast.parse(text)
    oversized = [node.name for node in ast.walk(tree)
                 if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                 and node.end_lineno - node.lineno > 50]
    # Function caps govern production code; tests retain their existing fixture patterns.
    assert len(text.splitlines()) <= 300 and ast.get_docstring(tree)
    if name.startswith('src/'):
        assert not oversized
    structural.append({'path': name, 'sha256': digest(root / name),
                       'lines': len(text.splitlines()), 'module_docstring': True,
                       'functions_over_50': oversized})
new_class_locations = []
for path in (root / 'src').rglob('*.py'):
    if '__pycache__' in path.parts:
        continue
    for node in ast.parse(path.read_text(encoding='utf-8')).body:
        if isinstance(node, ast.ClassDef) and node.name == 'FrameCapabilityUnavailable':
            new_class_locations.append(str(path.relative_to(root)))
assert new_class_locations == ['src\\autotester\\providers\\video_frames.py']
(directory / 'scoped-doctor.json').write_text(json.dumps({
    'scope': 'Changed source/test caps, production function caps, module docstrings and new-concept uniqueness; full doctor deferred.',
    'files': structural, 'new_exception_locations': new_class_locations}, indent=2))
gate = json.loads((directory / 'reuse-gate.json').read_text())
assert gate['environment_compatible']
assert all(row['status'] == 'COMPATIBLE_UNCHANGED_GUARD_ONLY' for row in gate['claims'])
packet = {'status': 'ready-for-check', 'fix_cycle': 1,
          'runtime_candidate': 'e2765afc59bbe00234af20badc3105a79ef103fe',
          'checked_parents': gate['versions'],
          'manifest': 'qa/manifests/provider-vision-integration.md',
          'proof': {'baseline': '30 passed', 'restored': '30 passed',
                    'unique_named_mutations': 13, 'lint_exit': 0, 'preflight_exit': 0},
          'prior_evidence_scope': 'Only exact unchanged guard ASTs with compatible environment/dependencies; whole-candidate commands rejected.',
          'packet_checks': {'phase_count': len(receipts), 'source_outputs_verified': True,
                            'exact_restoration': True, 'source_caps': True},
          'runtime_changes_after_freeze': subprocess.check_output([
              'git', 'diff', '--name-only', 'e2765afc59bbe00234af20badc3105a79ef103fe',
              '--', 'src', 'tests', 'pyproject.toml', 'uv.lock'], text=True).splitlines(),
          'maker_active_seconds': None, 'maker_tokens': None, 'maker_cost': None,
          'checker_ratio': 'unverified',
          'exclusions': ['full integration gates', 'live model/browser', 'credentials',
                         'SDK media/upload/poll', 'capability verifier', 'role defaults/migrations',
                         'narration', 'consumer persistence of failure coverage']}
assert not packet['runtime_changes_after_freeze']
packet['evidence_sha256'] = {str(p.relative_to(directory)): digest(p)
                            for p in directory.rglob('*') if p.is_file()}
(directory / 'packet.json').write_text(json.dumps(packet, indent=2))
(directory / 'finish-packet.py').write_bytes((root / '.work/finish-provider-vision-packet.py').read_bytes())
print('packet verified: 30 phases, 13 named reds, exact restoration, bounded source checks')
