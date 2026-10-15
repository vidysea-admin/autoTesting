"""Persist exact parent segments/hunks and conservative per-guard reuse decisions."""
import ast
import difflib
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys

root = Path.cwd()
directory = root / 'qa/evidence/provider-vision-integration'
compared = directory / 'compared'
compared.mkdir()
versions = {'text': '5233ffb187cf8ccd4b804c4573d5ac261b125668',
            'vision': '921a4ac5e8c8b8f77b1752bb285c82034ae2db26',
            'combined': 'e2765afc59bbe00234af20badc3105a79ef103fe'}
digest = lambda data: hashlib.sha256(data).hexdigest()
def read(version, path):
    result = subprocess.run(['git', 'show', versions[version] + ':' + path],
                            capture_output=True)
    return result.stdout.decode('utf-8') if result.returncode == 0 else None
def symbols(text):
    found = {}
    for node in ast.parse(text).body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            found[node.name] = node
        if isinstance(node, ast.ClassDef):
            for method in node.body:
                if isinstance(method, ast.FunctionDef):
                    found[node.name + '.' + method.name] = method
    return {name: {'line': node.lineno, 'end_line': node.end_lineno,
                   'ast_sha256': digest(ast.dump(node).encode()),
                   'source': ast.get_source_segment(text, node)} for name, node in found.items()}
paths = ['src/autotester/providers/' + name + '.py' for name in
         ('model_chain', 'litellm_provider', 'video_frames', 'attempts', 'availability')]
records = {}
for path in paths:
    versions_for_path = {}
    for version in versions:
        content = read(version, path)
        versions_for_path[version] = None if content is None else {
            'canonical_file_sha256': digest(content.encode()), 'symbols': symbols(content)}
        if content is not None:
            name = version + '-' + Path(path).name + '.txt'
            (compared / name).write_bytes(content.encode())
    for parent in ('text', 'vision'):
        before, after = read(parent, path), read('combined', path)
        patch = ''.join(difflib.unified_diff((before or '').splitlines(keepends=True),
                                            (after or '').splitlines(keepends=True),
                                            fromfile=parent + '/' + path,
                                            tofile='combined/' + path))
        (compared / (parent + '-to-combined-' + Path(path).name + '.diff')).write_bytes(patch.encode())
    records[path] = versions_for_path
(directory / 'compared-segments.json').write_text(json.dumps(records, indent=2))
text_env = json.loads((root / 'qa/evidence/text-availability/cycle2/environment.json').read_text())
vision_env = json.loads((root / 'qa/evidence/ollama-frame-vision/receipts.json').read_text())
new_env = json.loads((directory / 'environment.json').read_text())
same_text_deps = text_env['dependencies'] == new_env['dependencies']
same_vision_deps = all(importlib.metadata.version(name) == version
                       for name, version in vision_env['dependencies'].items())
same_python = text_env['python'] == vision_env['python'] == sys.executable
same_version = text_env['version'] == vision_env['version'] == sys.version
lock = digest((root / 'uv.lock').read_bytes())
same_lock = (text_env['fixture_config_lock']['uv.lock'] == vision_env['files']['uv.lock'] == lock)
same_config = (text_env['fixture_config_lock']['pyproject.toml'] ==
               vision_env['files']['pyproject.toml'] == digest((root / 'pyproject.toml').read_bytes()))
environment_ok = all((same_text_deps, same_vision_deps, same_python, same_version,
                      same_lock, same_config))
claims = [
 ('text', paths[3], ['reserve_attempt', 'attempt_budget', 'AttemptBudget.__init__'],
  'Physical cap/deadline implementation only; changed chain/transport callers proved anew.'),
 ('text', paths[4], ['availability_reason', 'AvailabilityFailure.__init__'],
  'Payload-free taxonomy implementation only; changed transport caller proved anew.'),
 ('vision', paths[2], ['_parts', '_generation', '_png_bytes', '_sample_times',
                      'endpoint_fingerprint', 'FrameVisionError.__init__'],
  'Unchanged frame sanitation/options/limits implementations; new capability subtype and caller interactions proved anew.'),
 ('vision', paths[1], ['LiteLLMProvider.see_video', 'LiteLLMProvider.guard_text'],
  'Unchanged delegation/redaction bodies only; structured and completion methods are not reused.'),
]
rows = []
for parent, path, names, limitation in claims:
    for name in names:
        old, new = records[path][parent]['symbols'][name], records[path]['combined']['symbols'][name]
        rows.append({'parent': parent, 'path': path, 'symbol': name,
                     'exact_ast_equal': old['ast_sha256'] == new['ast_sha256'],
                     'environment_compatible': environment_ok,
                     'status': ('COMPATIBLE_UNCHANGED_GUARD_ONLY' if environment_ok and
                                old['ast_sha256'] == new['ast_sha256'] else 'DO_NOT_REUSE'),
                     'limitation': limitation})
dependencies = []
for parent, names in [('vision', ['src/autotester/core/image_privacy.py',
        'src/autotester/media/frames.py', 'src/autotester/media/probe.py',
        'src/autotester/schema/video_frames.py', 'src/autotester/schema/observation.py',
        'src/autotester/skills/frame-vision/SKILL.md', 'tests/litellm_fake.py',
        'tests/conftest.py', 'tests/tests_mutation_fixtures.py']),
        ('text', ['src/autotester/providers/base.py', 'src/autotester/providers/litellm_schema.py',
                  'tests/test_text_availability.py', 'tests/litellm_fake.py',
                  'tests/conftest.py', 'tests/tests_mutation_fixtures.py'])]:
    for path in names:
        old, new = read(parent, path), read('combined', path)
        dependencies.append({'parent': parent, 'path': path,
                              'canonical_content_equal': old is not None and old == new})
assert environment_ok and all(row['exact_ast_equal'] for row in rows)
assert all(row['canonical_content_equal'] for row in dependencies)
gate = {'versions': versions, 'environment_compatible': environment_ok,
        'environment': {'python': same_python, 'version': same_version,
                        'text_dependencies': same_text_deps, 'vision_dependencies': same_vision_deps,
                        'lock': same_lock, 'project_config': same_config},
        'claims': rows, 'unchanged_dependency_bindings': dependencies,
        'whole_candidate_commands': 'DO_NOT_REUSE: candidate/import root and changed functions differ.',
        'new_proof_required': ['ModelChainProvider.__init__', 'ModelChainProvider._run',
                               'ModelChainProvider._try_tiers', 'LiteLLMProvider._complete',
                               'LiteLLMProvider._structured', 'video_frames.see_video',
                               'FrameCapabilityUnavailable'],
        'historical_scope': 'No prior100/75-test run or whole-parent PASS is claimed for this candidate.',
        'maker_active_seconds': None, 'maker_tokens': None, 'maker_cost': None}
(directory / 'reuse-gate.json').write_text(json.dumps(gate, indent=2))
shutil_needed = root / '.work/compare-provider-parents.py'
(directory / 'compare-provider-parents.py').write_bytes(shutil_needed.read_bytes())
print('exact parent segments/hunks saved; environment and narrow unchanged-guard gate validated')
