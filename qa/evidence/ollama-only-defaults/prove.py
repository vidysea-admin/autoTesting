import json, os, shutil, subprocess, sys
from pathlib import Path
root = Path.cwd()
copy = root / '.work' / 'provider-mutation-copy'
copy.mkdir(parents=True, exist_ok=True)
shutil.copytree(root/'src',copy/'src',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
(copy/'tests').mkdir(exist_ok=True)
for name in ('conftest.py','tests_mutation_fixtures.py','auth_login_fixture.py','test_model_chain.py','test_litellm_provider.py','litellm_fake.py'):
    shutil.copy2(root/'tests'/name,copy/'tests'/name)
(copy/'scripts').mkdir(exist_ok=True)
shutil.copy2(root/'scripts'/'regression_proof.py',copy/'scripts'/'regression_proof.py')
shutil.copy2(root/'pyproject.toml',copy/'pyproject.toml')
cases = [
('defaults','providers/model_chain.py','DEFAULT_ORDER = (ollama_cloud.GLM, ollama_cloud.DEEPSEEK)','DEFAULT_ORDER = (ollama_cloud.GLM, ollama_cloud.DEEPSEEK, "gemini/gemini-3.6-flash")','tests/test_model_chain.py::test_default_order_is_ollama_only_and_schema_default_uses_it'),
('fallback_order','providers/model_chain.py','DEFAULT_ORDER = (ollama_cloud.GLM, ollama_cloud.DEEPSEEK)','DEFAULT_ORDER = (ollama_cloud.DEEPSEEK, ollama_cloud.GLM)','tests/test_model_chain.py::test_falls_back_in_order_on_error_and_timeout'),
('explicit_override','providers/model_chain.py','raw = model or os.environ.get(ORDER_ENV) or ""','raw = os.environ.get(ORDER_ENV) or ""','tests/test_model_chain.py::test_unconfigured_tier_is_skipped'),
('cloud_json','providers/litellm_provider.py','if ollama_cloud.is_ollama(self._model):\n            return "json"','if False:\n            return "json"','tests/test_litellm_provider.py::test_ollama_cloud_uses_json_even_when_sdk_advertises_schema'),
('cloud_no_native_format','providers/litellm_provider.py','output_options = ({} if ollama_cloud.is_ollama(self._model)\n                          else request_options(strategy, self._model, schema))','output_options = request_options(strategy, self._model, schema)','tests/test_litellm_provider.py::test_ollama_cloud_uses_json_even_when_sdk_advertises_schema'),
('strict_types','providers/litellm_schema.py','strict=strict)','strict=False)','tests/test_litellm_provider.py::test_ollama_answer_rejects_coerced_types'),
]
env = dict(os.environ, PYTHONPATH=str(copy/'src'), PYTHONDONTWRITEBYTECODE='1')
def run(nodes):
    return subprocess.run([sys.executable,'-m','pytest',*nodes,'--tb=short'],cwd=copy,env=env,text=True,capture_output=True,timeout=90)
baseline=run([c[4] for c in cases]); assert baseline.returncode == 0, baseline.stdout+baseline.stderr
results=[]
for name,file,old,new,node in cases:
    path=copy/'src'/'autotester'/file
    original=path.read_text(encoding='utf-8'); assert original.count(old)==1,(name,original.count(old))
    try:
        path.write_text(original.replace(old,new),encoding='utf-8'); assert path.read_text(encoding='utf-8')!=original
        outcome=run([node]); expected='FAILED '+node
        killed=outcome.returncode!=0 and expected in outcome.stdout
        results.append(dict(name=name,killed=killed,exit=outcome.returncode,node=node,output=outcome.stdout))
        assert killed,outcome.stdout+outcome.stderr
    finally:
        path.write_text(original,encoding='utf-8')
out=Path(os.environ.get('PROVIDER_PROOF_OUTPUT',str(root/'qa'/'evidence'/'ollama-only-defaults')));out.mkdir(parents=True,exist_ok=True)
(out/'mutations.json').write_text(json.dumps(dict(baseline=baseline.stdout,results=results),indent=2),encoding='utf-8')
print(json.dumps([dict(name=r['name'],killed=r['killed']) for r in results]))
