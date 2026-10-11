# Checkpoint B - at758-759-host-allowlist (cycle 0, commit c642dcb5, product 2e9b3bf8)
Environment: Windows, Python 3.11.15, D:/autoTesting/.venv, PYTHONPATH=<git archive copy>/src. Code hash = commit c642dcb5; dependency lock = uv.lock at that commit; conftest = tests/conftest.py at that commit.
- Affected tests (origin guard, credential approval, consent, hosting deploy/config, healthz): 170 passed, 1 failed (pre-existing env.example red, also red on 3d8f7d5a). Attribution: coordinator B, qa/verdicts/at758-759-host-allowlist.b.md.
- tests/test_ui_*.py + test_env_loading.py: 495 passed, 1 skipped, 1 failed (a git-archive copy has no .git).
- Falsifications C1a C1b C1c C2a C2b C3a C3b C4a C4b C5: all green before, red after (qa/evidence/at758-759-host-allowlist-b/falsify-out.txt).
- Raw ASGI attack (65 cases) and approval attack (15 cases): asgi-attack-out.txt, approval-attack-out.txt in the evidence dir.
- ruff check src tests scripts: clean. autotester doctor: clean. No full suite (coordinator A).
- Result: PASS.
