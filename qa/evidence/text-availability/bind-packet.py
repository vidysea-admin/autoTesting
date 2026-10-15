"""Record policy/source/fixture bindings and the final supplemental command receipts."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

root = Path.cwd()
evidence = root / 'qa/evidence/text-availability'
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
bindings = {}
for name in ('tests/conftest.py', 'tests/litellm_fake.py', 'tests/tests_mutation_fixtures.py',
             'tests/auth_login_fixture.py', 'scripts/regression_proof.py',
             'qa/contracts/core-invariants.md', 'qa/contracts/langchain-fallback.md',
             'qa/contracts/providers-litellm.md', 'qa/loop.md', 'qa/adapter.json'):
    bindings[name] = digest(root / name)
receipts = []
for name, arguments, exit_code in [
    ('doctor-corrected', ['-c', 'from autotester import main; main()', 'doctor'], 1),
    ('missing-fallback', ['.work/probe-missing-fallback.py'], 0),
]:
    path = evidence / (name + '.log')
    receipts.append({'command': [sys.executable, *arguments], 'cwd': str(root),
                     'output': str(path.relative_to(root)), 'sha256': digest(path),
                     'exit': exit_code, 'source_commit':
                     '1ecf58cef26e96b713c005e1b089363e4a7fbc18',
                     'policy_commit': '40f5b4b20e91d3806ee313fb8e67af109b62b0ae'})
data = {'head_before_packet': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'fixture_config_contract_sha256': bindings,
        'supplemental_receipts': receipts,
        'model_reference': 'https://ai.google.dev/gemini-api/docs/models.md',
        'model_reference_observed_utc': '2026-10-15',
        'maker_active_seconds': None, 'maker_tokens': None, 'maker_cost': None,
        'checker_ratio': 'unverified',
        'scope': 'text-only LiteLLM; no Gemini SDK/upload/poll/media attempt certification'}
(evidence / 'packet-bindings.json').write_text(json.dumps(data, indent=2))
