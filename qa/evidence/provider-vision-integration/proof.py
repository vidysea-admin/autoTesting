"""Source-bound focused integration proof, without broad parent-suite repetition."""
import ast
import difflib
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
frozen = 'e2765afc59bbe00234af20badc3105a79ef103fe'
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip() == frozen
directory = root / 'qa/evidence/provider-vision-integration'
directory.mkdir(parents=True)
proof = root / '.work/combined-proof'
proof.mkdir()
for name in ('src', 'tests', 'scripts'):
    shutil.copytree(root / name, proof / name,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.pytest_cache'))
for name in ('pyproject.toml', 'uv.lock'):
    shutil.copy2(root / name, proof / name)
(proof / '.work').mkdir()
assert (proof / 'tests/tests_mutation_fixtures.py').is_file()
assert not list(proof.rglob('__pycache__'))
source = ['src/autotester/providers/' + name + '.py' for name in
          ('model_chain', 'litellm_provider', 'video_frames', 'attempts', 'availability',
           'base', 'litellm_schema', 'images')]
source += ['src/autotester/schema/video_frames.py', 'src/autotester/schema/observation.py',
           'src/autotester/core/image_privacy.py', 'tests/test_provider_vision_integration.py',
           'tests/test_text_availability.py', 'tests/test_video_frames.py',
           'tests/test_provider_attempts.py']
fixtures = ['tests/conftest.py', 'tests/litellm_fake.py', 'tests/auth_login_fixture.py',
            'tests/tests_mutation_fixtures.py', 'scripts/regression_proof.py',
            'src/autotester/skills/frame-vision/SKILL.md', 'pyproject.toml', 'uv.lock']
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
def inventory(base, names):
    return {name: digest(base / name) for name in names}
baseline = inventory(proof, source)
assert baseline == inventory(root, source)
environment = {'frozen_head': frozen, 'python': sys.executable, 'version': sys.version,
               'dependencies': sorted((d.metadata['Name'], d.version)
                                      for d in importlib.metadata.distributions()),
               'source': baseline, 'fixture_config_lock': inventory(proof, fixtures),
               'copy': 'complete src/tests/scripts incl tests_mutation_fixtures.py; no caches',
               'maker_active_seconds': None, 'maker_tokens': None, 'maker_cost': None}
(directory / 'environment.json').write_text(json.dumps(environment, indent=2))
env = dict(os.environ, PYTHONPATH=str(proof / 'src'), PYTHONDONTWRITEBYTECODE='1')
receipts = []
def run(label, arguments, expected=0, mutation=None):
    before = inventory(proof, source)
    fixture_before = inventory(proof, fixtures)
    started = time.monotonic()
    command = [sys.executable, *arguments]
    result = subprocess.run(command, cwd=proof, env=env, capture_output=True, text=True)
    elapsed = time.monotonic() - started
    path = directory / (label + '.log')
    output = result.stdout + result.stderr
    path.write_text(output, encoding='utf-8')
    after = inventory(proof, source)
    assert before == after and fixture_before == inventory(proof, fixtures)
    receipts.append({'label': label, 'command': command, 'cwd': str(proof),
                     'exit_code': result.returncode, 'expected_exit': expected,
                     'source_before': before, 'source_after': after,
                     'fixture_config_lock': fixture_before,
                     'environment_sha256': digest(directory / 'environment.json'),
                     'output': str(path.relative_to(root)), 'sha256': digest(path),
                     'frozen_head': frozen, 'mutation': mutation, 'command_elapsed_s': elapsed})
    (directory / 'receipts.json').write_text(json.dumps(receipts, indent=2))
    print(label, result.returncode, flush=True)
    assert result.returncode == expected, output[-4500:]
    return output
run('preflight', ['C:/Users/product/.agents/skills/checker/scripts/review_budget.py',
    'preflight', '--root', str(proof), '--import-name', 'autotester',
    '--import-root', str(proof / 'src'), '--temp-parent', str(proof / '.work')])
selected = ['tests/test_text_availability.py', 'tests/test_provider_vision_integration.py']
selected += ['tests/test_video_frames.py::' + name for name in (
    'test_real_sanitized_bytes_and_clip_relative_timestamp_payload',
    'test_partial_withholding_retains_original_index_and_time',
    'test_all_withheld_never_sends_text_only_success',
    'test_repair_and_fallback_obey_shared_physical_budget',
    'test_fallback_serves_configured_model_only',
    'test_prompt_secret_guard_precedes_media_processing',
    'test_chain_failure_retains_visual_shortfall',
    'test_budget_refusal_preserves_inclusion_without_claiming_delivery')]
arguments = ['-m', 'pytest', '-p', 'no:cacheprovider', '--basetemp=.work/pytest']
(directory / 'selected-nodes.json').write_text(json.dumps(selected, indent=2))
run('baseline', arguments + selected)
ch, lp, vf = source[:3]
node = lambda name: 'tests/test_provider_vision_integration.py::' + name
mutations = [
 ('strict_constructor', ch, 'secrets=secrets, strict=True,', 'secrets=secrets, strict=False,',
  node('test_non_ollama_chain_output_keeps_strict_validation')),
 ('capability_forwarding', ch, 'vision_capability=capabilities.get(m)', 'vision_capability=None',
  node('test_tier_constructor_and_video_forwarding_preserve_limits_options')),
 ('limits_forwarding', ch, 'if "frame_limits" in options else {}', 'if False else {}',
  node('test_tier_constructor_and_video_forwarding_preserve_limits_options')),
 ('video_implicit_exclusion', ch, 'method == "see_video" or ', '',
  node('test_default_video_never_reaches_implicit_gemini_and_keeps_coverage')),
 ('coverage_propagation', ch, 'coverage = getattr(exc, "coverage", coverage)', 'coverage = None',
  node('test_default_video_never_reaches_implicit_gemini_and_keeps_coverage')),
 ('safe_reason_retention', ch, 'self._call.fallback_reasons.append(errors[-1])', 'pass',
  node('test_explicit_verified_next_tier_serves_missing_capability')),
 ('capability_eligible_type', vf, 'class FrameCapabilityUnavailable(FrameVisionError, Unsupported):',
  'class FrameCapabilityUnavailable(FrameVisionError):',
  node('test_explicit_verified_next_tier_serves_missing_capability')),
 ('privacy_terminal_type', vf, 'class FrameVisionError(ProviderError):',
  'class FrameVisionError(Unsupported):',
  node('test_frame_privacy_and_invalid_options_stop_before_next_tier')),
 ('malformed_terminal', ch, 'except ProviderError:\n                self._sync_usage()\n                raise',
  'except ProviderError:\n                self._sync_usage()\n                continue',
  node('test_malformed_visual_output_is_terminal_with_coverage')),
 ('global_terminal', ch, 'except AttemptBudgetExhausted:\n                self._sync_usage()\n                raise',
  'except AttemptBudgetExhausted:\n                self._sync_usage()\n                continue',
  'tests/test_video_frames.py::test_repair_and_fallback_obey_shared_physical_budget'),
 ('frame_parts_transport', lp, 'if content_parts else image_url_parts(text, images)',
  'if False else image_url_parts(text, images)',
  'tests/test_video_frames.py::test_real_sanitized_bytes_and_clip_relative_timestamp_payload'),
 ('generation_forwarding', lp, 'kwargs.update(generation_options or {})', 'pass',
  node('test_tier_constructor_and_video_forwarding_preserve_limits_options')),
 ('availability_normalization', lp, 'reason = availability_reason(exc)', 'reason = None',
  'tests/test_video_frames.py::test_fallback_serves_configured_model_only'),
]
(directory / 'mutations.json').write_text(json.dumps(mutations, indent=2))
for label, filename, old, new, test in mutations:
    path = proof / filename
    original = path.read_bytes()
    before = old.encode()
    after = new.encode()
    if b'\r\n' in original:
        before, after = before.replace(b'\n', b'\r\n'), after.replace(b'\n', b'\r\n')
    assert original.count(before) == 1, (label, 'anchor count')
    applied = original.replace(before, after, 1)
    path.write_bytes(applied)
    changed = [name for name, value in inventory(proof, source).items()
               if value != baseline[name]]
    assert changed == [filename]
    mutation = {'path': filename, 'before': old, 'after': new, 'occurrences': 1,
                'original_sha256': hashlib.sha256(original).hexdigest(),
                'applied_sha256': hashlib.sha256(applied).hexdigest(), 'test': test}
    try:
        output = run(label + '-red', arguments + [test], 1, mutation)
        assert 'FAILED ' + test.split('[')[0] in output, (label, 'named failure missing')
    finally:
        path.write_bytes(original)
    assert inventory(proof, source) == baseline
    run(label + '-restored', arguments + [test])
run('restored', arguments + selected)
run('lint', ['-m', 'ruff', 'check', source[0], source[1], source[2],
             'tests/test_provider_vision_integration.py', 'tests/test_video_frames.py'])
assert inventory(proof, source) == inventory(root, source) == baseline
(directory / 'source-binding.json').write_text(json.dumps({
    'frozen_head': frozen, 'candidate': inventory(root, source),
    'restored': inventory(proof, source), 'raw_bytes_equal': True}, indent=2))
shutil.copyfile(root / '.work/provider-vision-proof.py', directory / 'proof.py')
print('combined focused proof complete', flush=True)
