# Checkpoint B -- t202-any-model-provider (cycle 0)
Attribution: seat B coordinator + 3 read-only Sonnet sub-checkers (guard, spec, net). Verdict: qa/verdicts/t202-any-model-provider.b.md
Code identity: branch head 94c569c0, product 8e66190b, litellm==1.104.0, uv.lock +1555/-0 vs db77d7bf, pyproject.toml +1 line. Env: Windows 11, worktree .venv python 3.11, PYTHONPATH=copy/src for mutants.

| Check | Command / scope | Result |
|---|---|---|
| LL1 | pytest tests/test_provider_factory.py -k "parse_spec or round_trippable" | 14 passed |
| LL2 | -k "ll2 or neither_route or asks_the_factory or malformed" | 10 passed; ui grep: 1 comment hit ui/app.py:64 (also on master) |
| LL11 | -k "ll11 or learn_route" | 4 passed |
| LL3,4,6,7,9 | tests/test_litellm_provider.py | 16 passed |
| LL5,8,10 | tests/test_litellm_guard.py | 21 passed (twice; second after the venv file restore) |
| LL12 | test_providers.py test_langchain_fallback.py test_ensemble_honesty.py | 29 passed |
| LL13 | uv lock --check; numstat | Resolved 123 packages; lock +1555/-0 |
| LL14 | ruff check src tests scripts; autotester doctor | clean; clean |
| Falsification | qa/evidence/t202-any-model-provider-B/fals/fals.py, one copy per row | 14 rows + LL10b: all green-before, red-after |
| Attacks | evidence guard/ spec/ net/ | see verdict |

No full suite run (seat A owns it). No reuse of builder output.
