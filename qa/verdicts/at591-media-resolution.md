# Verdict — at591-media-resolution

**Date:** 2026-09-26 · **Cycle checked:** 1 · **Checker:** orchestrator (checker seat), direct re-run

```
VERDICT: PASS
SCOREBOARD: AT-591 met: media_resolution is Literal["low","medium","high"], an invalid value raises at construction, the default stays "high", and the gemini.py conversion is unchanged
FAILURES: none
CAPABILITY-COVERAGE: 3/3 rows reproduced in copy c591 (the copy imports its own src; baseline 45 passed): (1) field back to a bare str → test_visionoptions_rejects_an_invalid_media_resolution red only; (2) default "medium" → test_vision_options_defaults_match_the_proven_pipeline_settings red only; (3) gemini.py:100 prefix → WRONG_PREFIX_ → test_config_applies_media_resolution_for_the_fully_qualified_form red only. Each reverted.
LIVE-BROWSER: not-applicable (schema/observation.py, tests/test_gemini_config.py)
ISSUES-WRITTEN: none
EXECUTOR: maker (checker: orchestrator direct)
EXPLANATION: The Literal matches the installed SDK: google-genai MediaResolution = UNSPECIFIED|LOW|MEDIUM|HIGH, with UNSPECIFIED rightly excluded. No persisted project or fixture sets media_resolution (grep of projects/ and tests/fixtures is empty), so narrowing the type invalidates nothing on disk. "fully_qualified_form" refers to the model name (models/gemini-3.6-flash), not a stored enum string.
```

Evidence: worktree `uv run pytest tests/test_gemini_config.py tests/test_providers.py tests/test_schema_video.py` → 53 passed · ruff clean · doctor clean · `git diff --stat a331614..HEAD` = manifest, schema/observation.py (+8/-1), tests/test_gemini_config.py (+16); nothing deleted.
