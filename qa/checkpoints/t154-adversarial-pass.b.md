# Checkpoint t154-adversarial-pass (coordinator B), cycle 0
- tree: git archive 575a7c3f (throwaway copy; code identity = commit 575a7c3f, product commit fd7362a8); base ff901f72; policy proportional-verification/2026-10-10.9
- cmd: pytest -p no:xdist tests/test_adversarial.py (25 collected) -> 25 passed. env: repo .venv python, PYTHONPATH=copy/src (asserted by import path)
- cmd: python scripts/adversarial_proof.py -> exit 0, 10 HELD, ADVERSARIAL PROOF OK
- cmd: grep -rniE "garak|pyrit|deepteam" src pyproject.toml -> exit 1 (no output); grep "Result\.|Verdict(" stages/adversarial.py -> exit 1
- ruff on the 4 changed py files -> clean
- not run (not owed here): tests/test_consent.py (core/consent.py unchanged), full suite (other coordinator)
- attacks and falsifications: qa/evidence/t154-adversarial-pass-b/attacks.md
- result: PASS. checker: coordinator B (claude-sonnet-subagent), 2026-10-10T20:09Z to 20:28Z
