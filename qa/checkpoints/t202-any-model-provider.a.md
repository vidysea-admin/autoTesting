# Checkpoint — t202-any-model-provider, coordinator A, cycle 0

Head 94c569c0 (product 8e66190b). Checker: claude-sonnet-subagent (seat A). Policy .9. Verdict: PASS (qa/verdicts/t202-any-model-provider.a.md).

| Check | Command / scope | Code hash | Result |
|---|---|---|---|
| Criterion tests | worktree .venv python, `-p no:xdist`: test_provider_factory.py (31), test_litellm_provider.py (16), test_litellm_guard.py (21), test_providers+test_langchain_fallback+test_ensemble_honesty (29), test_ui_runs_queue+test_expand_cli+test_cli_advice_resolves (49) | commit 94c569c0; uv.lock sha256 fd7d6408bca242b3.., pyproject sha256 17819903097ecee6.. | 146 passed |
| Falsification | 17 mutants, one `git archive 94c569c0` copy each, PYTHONPATH proven into copy; detail qa/evidence/t202-any-model-provider-A/falsification.md | same | 17/17 red on intended assertion |
| Full suite | shard_suite.py --shards 4 --ref 94c569c0 -- -o addopts=; root .venv python D:/autoTesting/.venv (no litellm); collect proof 3470 | same | 3444 passed, 6 failed (4 known, 2 runner-env artefacts), 20 skipped; qa/evidence/.../suite-summary.json |
| Lock | `uv lock --check --offline` on worktree | uv.lock fd7d6408bca242b3 | Resolved 123 packages, exit 0; diff additions only |
| Doctor / ruff | `uv run --frozen --no-sync autotester doctor`, `ruff check src tests scripts` | same | clean / all checks passed |
| Egress probe | worktree python -I, getaddrinfo+connect trapped, litellm.completion mock_response x2; qa/evidence/.../egress-probe.py | litellm 1.104.0 | HITS [] |

Environment: Windows 11, python 3.11 (uv), litellm 1.104.0; worktree .venv tokenizer file deleted by a sub-checker's run (see verdict disclosures).
Attribution: sub-checkers ae1732d5.., aa9f2496.., a54782ed.., ac80cfbc.. (reports folded into the verdict); coordinator wrote the verdict.
