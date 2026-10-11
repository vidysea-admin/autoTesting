import shutil, subprocess, sys, os, json, time
from pathlib import Path
HERE = Path(__file__).parent
BASE = HERE / "base"
PY = r"D:\autoTesting\.worktrees\t202-any-model-provider\.venv\Scripts\python.exe"
F = "tests/test_provider_factory.py"; P = "tests/test_litellm_provider.py"; G = "tests/test_litellm_guard.py"
rows = [
 ("LL1", "src/autotester/providers/__init__.py", 'if _CREDENTIAL_IN_SPEC.search(model):', 'if False and _CREDENTIAL_IN_SPEC.search(model):', [F+"::test_parse_spec_rejects_empty_models_and_embedded_credentials_without_echoing"]),
 ("LL2", "src/autotester/providers/__init__.py", 'if spec == default and env_model:', 'if env_model:', [F+"::test_a_project_spec_beats_the_env_default_and_is_per_role"]),
 ("LL3", "src/autotester/providers/litellm_schema.py", 'return schema.model_validate(loads_json(answer_text(message, strategy)))', 'return schema.model_construct(**loads_json(answer_text(message, strategy)))', [P+"::test_schema_mismatch_is_an_error_not_a_coerced_answer"]),
 ("LL4", "src/autotester/providers/litellm_provider.py", '    def _unparsable(self, role: str, problem: str) -> str:', '    def see_video(self, *a, **k):\n        return None\n\n    def _unparsable(self, role: str, problem: str) -> str:', [P+"::test_see_video_is_unsupported"]),
 ("LL5", "src/autotester/providers/litellm_provider.py", '    def _guard(self, messages: list[dict[str, Any]]) -> None:\n        try:', '    def _guard(self, messages: list[dict[str, Any]]) -> None:\n        return\n        try:', [G+"::test_a_prompt_carrying_a_secret_never_reaches_litellm"]),
 ("LL6", "src/autotester/providers/litellm_provider.py", '"num_retries": 0,', '"num_retries": 1,', [P+"::test_one_physical_call_zero_retries_and_usage_recorded"]),
 ("LL7", "src/autotester/providers/litellm_provider.py", 'input_tokens=getattr(usage, "prompt_tokens", 0) or 0,', 'input_tokens=0,', [P+"::test_one_physical_call_zero_retries_and_usage_recorded"]),
 ("LL8", "src/autotester/providers/litellm_provider.py", 'if echoed or any(v in text for v in hidden) or len(text) > 300:', 'if echoed or len(text) > 300:', [G+"::test_neither_the_key_nor_the_endpoint_appears_in_an_error"]),
 ("LL9", "src/autotester/providers/litellm_schema.py", 'if model.startswith(("gemini/", "vertex_ai/")):', 'if model.startswith(("zzz/",)):', [P+"::test_gemini_models_get_the_gemini_dialect_schema"]),
 ("LL10", "src/autotester/providers/litellm_provider.py", '    litellm.telemetry = False', '    litellm.success_callback = ["x"]', [G+"::test_no_callbacks_are_registered_and_telemetry_is_off"]),
 ("LL10b-telemetry-line-removed", "src/autotester/providers/litellm_provider.py", '    litellm.telemetry = False   # LL10: 1.104.0 has no such switch (checked in its source); a no-op\n', '', [G+"::test_no_callbacks_are_registered_and_telemetry_is_off", G+"::test_the_real_pinned_sdk_is_quiet_after_the_provider_loads_it"]),
 ("LL11", "src/autotester/providers/litellm_provider.py", '        if missing:\n            return (f"{self.label} is missing credentials', '        if False:\n            return (f"{self.label} is missing credentials', [G+"::test_a_missing_key_is_a_clear_error_naming_the_key_and_makes_no_call"]),
 ("LL12", "tests/litellm_fake.py", '        return host in ("127.0.0.1", "::1", "localhost")', '        return True', [G+"::test_a_test_that_forgets_the_fake_fails_loudly_instead_of_going_online"]),
 ("LL13", "pyproject.toml", '"litellm==1.104.0"', '"litellm>=1.104.0"', [P+"::test_litellm_is_pinned_to_one_exact_version_in_pyproject"]),
]
only = sys.argv[1:]
out = []
for rid, rel, old, new, nodes in rows:
    if only and rid not in only: continue
    d = HERE / f"row-{rid}"
    if d.exists(): shutil.rmtree(d)
    shutil.copytree(BASE, d, ignore=shutil.ignore_patterns("__pycache__", ".git"))
    env = dict(os.environ, PYTHONPATH=str(d / "src"))
    def run():
        t = time.time()
        r = subprocess.run([PY, "-m", "pytest", "-p", "no:xdist", "-p", "no:cacheprovider", *nodes], cwd=d, env=env, capture_output=True, text=True)
        tail = [l for l in r.stdout.splitlines() if " passed" in l or " failed" in l or "error" in l.lower()][-2:]
        return r.returncode, tail, r.stdout
    c0, t0, o0 = run()
    f = d / rel; s = f.read_text(encoding="utf-8")
    assert s.count(old) == 1, (rid, s.count(old))
    f.write_text(s.replace(old, new), encoding="utf-8")
    c1, t1, o1 = run()
    (HERE / f"out-{rid}.txt").write_text("GREEN-BEFORE\n" + o0 + "\nAFTER-EDIT\n" + o1, encoding="utf-8")
    # which assertion fired
    why = [l for l in o1.splitlines() if l.startswith("E ")][:3]
    out.append((rid, c0, t0, c1, t1, why))
    print(rid, "green-before rc", c0, t0, "| after rc", c1, t1, "|", why, flush=True)
