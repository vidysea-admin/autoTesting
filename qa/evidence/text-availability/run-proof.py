"""Sequential offline proof in a complete cache-free source/test/script copy."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

root = Path.cwd()
copy = root / '.work/proof-copy'
evidence = root / 'qa/evidence/text-availability'
evidence.mkdir(parents=True, exist_ok=True)
copy.mkdir()
for name in ('src', 'tests', 'scripts'):
    shutil.copytree(root / name, copy / name,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.pytest_cache'))
for name in ('pyproject.toml', 'uv.lock'):
    shutil.copy2(root / name, copy / name)
assert (copy / 'tests/tests_mutation_fixtures.py').is_file()
(copy / '.work').mkdir()
env = dict(os.environ, PYTHONPATH=str(copy / 'src'), PYTHONDONTWRITEBYTECODE='1')
files = ['src/autotester/providers/' + n + '.py' for n in
         ('availability', 'model_chain', 'litellm_provider')]
files += ['tests/test_text_availability.py', 'tests/test_model_chain.py',
          'tests/test_provider_attempts.py']
hashfile = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
identity = {name: hashfile(root / name) for name in files + ['pyproject.toml', 'uv.lock']}
environment = {'python': sys.executable, 'version': sys.version,
               'dependencies': sorted((d.metadata['Name'], d.version)
                                      for d in importlib.metadata.distributions()),
               'source': identity, 'fixtures': 'complete tests directory, including tests_mutation_fixtures.py',
               'excluded': ['__pycache__', '*.pyc', '.pytest_cache']}
(evidence / 'environment.json').write_text(json.dumps(environment, indent=2))
receipts = []
def run(label, args, expected):
    command = [sys.executable, *args]
    result = subprocess.run(command, cwd=copy, env=env, capture_output=True, text=True)
    output = result.stdout + result.stderr
    path = evidence / (label + '.log')
    path.write_text(output, encoding='utf-8')
    receipts.append({'label': label, 'command': command, 'cwd': str(copy),
                     'exit': result.returncode, 'expected': expected,
                     'output': str(path.relative_to(root)), 'sha256': hashfile(path),
                     'source': {n: hashfile(copy / n) for n in files},
                     'environment_sha256': hashfile(evidence / 'environment.json')})
    print(label, result.returncode, flush=True)
    if result.returncode != expected:
        raise RuntimeError(label + '\n' + output[-3000:])
    return output
test_args = ['-m', 'pytest', '-p', 'no:cacheprovider', '--basetemp=.work/pytest']
selected = ['tests/test_text_availability.py', 'tests/test_model_chain.py',
            'tests/test_provider_attempts.py']
run('preflight', ['C:/Users/product/.agents/skills/checker/scripts/review_budget.py',
    'preflight', '--root', str(copy), '--import-name', 'autotester',
    '--import-root', str(copy / 'src'), '--temp-parent', str(copy / '.work')], 0)
run('baseline', test_args + selected, 0)
av = files[0]
ch = files[1]
lp = files[2]
def node(name):
    return 'tests/test_text_availability.py::' + name
mutations = [
 ('auth', av, '== 401:', '== 499:', node('test_allowlisted_failure_reaches_guarded_gemini[failure0]')),
 ('service', av, 'in (502, 503, 504):', 'in (599,):', node('test_allowlisted_failure_reaches_guarded_gemini[failure1]')),
 ('network', av, '(TimeoutError, ConnectionError)', '(TimeoutError,)', node('test_allowlisted_failure_reaches_guarded_gemini[failure2]')),
 ('capability', av, 'if isinstance(exc, Unsupported):', 'if False:', node('test_allowlisted_failure_reaches_guarded_gemini[failure3]')),
 ('fail_closed', av, '    return None\n', '    return "service"\n', node('test_ambiguous_and_policy_failures_stop')),
 ('chain_gate', ch, 'except (AvailabilityFailure, Unsupported) as exc:', 'except ProviderError as exc:', node('test_ambiguous_and_policy_failures_stop')),
 ('strict_repair', lp, 'strict=ollama_cloud.is_ollama(self._model)\n                                or self.options.get("strict", False)', 'strict=False', node('test_malformed_output_repairs_once_then_stops')),
 ('global_count', 'src/autotester/providers/attempts.py', 'if scope.used >= scope.max_calls:', 'if False:', node('test_enclosing_budget_never_falls_through[2-30]')),
 ('global_deadline', 'src/autotester/providers/attempts.py', 'if scope.deadline is not None:', 'if False:', node('test_enclosing_budget_never_falls_through[6-0]')),
 ('text_only', ch, 'self._implicit_fallback and extra.get("images")', 'False', node('test_implicit_gemini_excludes_images_and_explicit_order_wins')),
 ('explicit_order', ch, 'not (options.get("model") or os.environ.get(ORDER_ENV))', 'True', node('test_implicit_gemini_excludes_images_and_explicit_order_wins')),
 ('credentials_skip', ch, 'if tier.available():', 'if True:', node('test_missing_ollama_keys_and_fallback_model_override')),
 ('fallback_override', ch, 'os.environ.get(FALLBACK_ENV) or TEXT_FALLBACK', 'TEXT_FALLBACK', node('test_missing_ollama_keys_and_fallback_model_override')),
 ('secret_guard', lp, 'assert_no_raw_secrets(text, self._secret_values())', 'pass', node('test_secret_never_reaches_any_tier')),
 ('unknown_usage', lp, 'getattr(usage, "prompt_tokens", None)', 'getattr(usage, "prompt_tokens", 0)', node('test_allowlisted_failure_reaches_guarded_gemini')),
 ('finite_timeout', lp, '"timeout": _TIMEOUT_S,', '"timeout": 999,', node('test_allowlisted_failure_reaches_guarded_gemini')),
 ('no_hidden_retries', lp, '"num_retries": 0', '"num_retries": 1', node('test_allowlisted_failure_reaches_guarded_gemini')),
 ('visible_reason', ch, 'self._call.fallback_reasons.append(errors[-1])', 'pass', node('test_allowlisted_failure_reaches_guarded_gemini')),
]
# Remaining-time cap overrides initial kwargs timeout, so mutate that assignment itself.
mutations[15] = ('finite_timeout', lp, 'receipt, kwargs["timeout"] = reserve_attempt(self.label, role, _TIMEOUT_S)',
                 'receipt, ignored_timeout = reserve_attempt(self.label, role, _TIMEOUT_S)',
                 node('test_allowlisted_failure_reaches_guarded_gemini'))
(evidence / 'mutations.json').write_text(json.dumps(mutations, indent=2))
try:
    for label, filename, before, after, test in mutations:
        path = copy / filename
        original = path.read_text(encoding='utf-8')
        assert before in original, label
        path.write_text(original.replace(before, after), encoding='utf-8')
        try:
            output = run(label + '-red', test_args + [test], 1)
            assert 'FAILED ' + test.split('[')[0] in output, (label, 'named failure missing')
        finally:
            path.write_text(original, encoding='utf-8')
        run(label + '-restored', test_args + [test], 0)
    run('restored', test_args + selected, 0)
finally:
    (evidence / 'receipts.json').write_text(json.dumps(receipts, indent=2))
    (evidence / 'source-binding.json').write_text(json.dumps({
        'candidate': {n: hashfile(root / n) for n in files},
        'restored': {n: hashfile(copy / n) for n in files}}, indent=2))
