# Verdict A — t177-agent-fallback (blind dual check, checker A)

**Checker:** coordinator A, fresh context, security-L. **Date:** 2026-10-07. **Cycle checked:** 0
**Bound:** branch `wave/t177-agent-fallback`, head `4e06f18c`, worktree `D:/autoTesting/.worktrees/t177`.
**Contract:** `qa/contracts/agent-fallback.md` AF1-AF6 (DRAFT) · `explore.md` X7 · core-invariants C3/C7/C11.
**Policy:** proportional-verification/2026-10-07.7, tier L (triggers: dependency bump browser-use; security controls AF3 and AF6).
**Judged blind:** B's file and evidence were not read.

## Check plan (written first)

1. Read the whole diff (11 files, `uv.lock` reviewed separately) and map AF1-AF6 to code and tests.
2. Security probes: destination bypass (redirect, `javascript:`, IDN, suffix, userinfo, open redirect), deny-list and budget bypass, secrets to the model prompt, prompt file, `ProviderError` handling.
3. Supply chain: licence, `uv.lock` delta, import-time and runtime telemetry, `.env` auto-load.
4. Scoped tests, ruff, doctor (run by me).
5. Mutants, at least one per AF (run by me in a throwaway copy, one pytest at a time).
6. Decide whether any AF needs a live browser run.
7. Full suite: deferred by coordinator instruction.

## Verdict: **FAIL**

AF1, AF2, AF4, AF5 and the unit-test side of AF6 are met. **AF3 is not met.** X7 is the named
destination check, and it requires a post-action landing-URL re-check. That re-check is not
implemented, and the write guard has a bypass. In addition, the browser-use backend cannot construct
its `Agent` at all, which no test exercises (see F2).

full-suite: deferred to combined integration head (suite.lock queue #5)

## What I ran myself

- `uv run pytest tests/test_agent_fallback.py tests/test_agent_loop.py tests/test_run_case_pipeline.py tests/test_script_replay.py tests/test_prompt_skills.py tests/test_doctor.py` -> **117 passed in 297.86s**.
- `ruff check src tests scripts` -> **All checks passed!**
- `autotester doctor` -> **doctor: clean**.
- F2 probe (`isinstance(ProviderChatModel(...), browser_use.llm.base.BaseChatModel)`, then `Agent(task="t", llm=model)`) -> **`isinstance: False`**, then **`ValueError invalid llm, must be from browser_use.llm`**.
- Mutants: 26 applied in a throwaway copy (27 defined), 22 killed, 4 survived, 1 not applied (see table).

## Per-criterion evidence

| AF | Result | Evidence |
|---|---|---|
| AF1 | met on stubs | `test_af1_*`: known screen 0 invocations, unknown screen exactly 1, after the fix loop. Mutant "engage twice" killed. Mutant "drop the ERRORED condition" survived, but it is behaviourally equivalent: `_try_actuator` returns None when no step lacks a screenshot. Not a defect, but the test does not pin the intended guard. |
| AF2 | met | `parse_result` raises `MalformedActuatorResult`; status is `MALFORMED`, never a pass. Mutants no-validation, `extra=allow`, and no `min_length` on actions or observed were all killed. |
| AF3 | **NOT met** | Present and tested: destination host check on the literal URL, `write_policy` refusal of fill/select/upload, Enter refusal, deny-list, budget spend (a `RunBudget` with 3 actions admits 3, refuses the 4th), unvetted-action refusal, and no verdict anywhere. All 7 mutants of these were killed. **Absent: the X7 re-check of the landing URL** (F1). **Bypass: `send_keys` under read_only** (F3). |
| AF4 | met | `max_steps` and the wall clock both end as `BOUND_EXHAUSTED` with a reason that names the bound; this is never PASS (no PASS status exists). Mutants killed except the redundant `_finish` clock check. |
| AF5 | met as written, with a caveat | `run_with_fallback` is called from `run_case_pipeline.py::fallback_executor`, and the test reaches it via `run_and_grade_case(agent=...)`. All five AF5 mutants were killed. Caveat: no production entry point passes `agent=` or `actuator=` (`ui/run_execution.py:52` does not), so the path is dead in production (F4). The page in the test is a fake, not a real browser. The contract text does not require a real browser. |
| AF6 | partly met | `browser-use>=0.5.9` is declared in this unit only. It is MIT. `check_dependencies_declared` is clean (doctor clean). No vendor import exists outside `providers/` (mutant killed). The model call goes through `Provider.act`. But `ProviderChatModel` is not accepted by browser-use (F2), and the secret guard defaults to the identity function (F5). |

## Findings

**F1 (HIGH, AF3/X7) — No landing-URL check.**
- `explore.md` X7 says "the host is re-checked after every action". The adapter's own docstring and the schema (`agent_actuator.py:9-11`, `agent_fallback.py:35`) promise a check on "the page the action lands on".
- Nothing implements it. `state.url` is used only as the `urljoin` base (`browser_use_backend.py:100`).
- A click on an in-domain link that 302s off-domain, an open redirect via a query parameter, a JS `location` change, a form action that goes off-domain, and any click whose `href` was not captured (`url=None`) are all unchecked.
- `BuSession(cdp_url=...)` (`browser_use_backend.py:163`) passes no `allowed_domains`, so browser-use's own validation is off too.
- The next step runs on whatever page the agent landed on.
- Probed: `https://example.com/redirect?url=https://evil.com` is correctly judged on its literal URL only, so redirects are the gap.

**F2 (HIGH, functional) — The browser-use backend cannot construct an `Agent`.**
- `ProviderChatModel` is not an instance of `BaseChatModel` under installed browser-use 0.5.9, so `_drive` would raise `ValueError` before taking a single action.
- The tests call only `ainvoke` and never construct the real `Agent`. `to_actions` was exercised against real `AgentOutput` types only by my sub-probe, not by any repo test.
- So AF3's browser-use half and the backend as a whole are unproven. The manifest discloses "live path unproven" but not that the shim is rejected.

**F3 (MEDIUM, AF3) — `PRESS_KEY` under read_only blocks only the strings "enter" and "return".**
- Allowed: `NumpadEnter`, `Control+Enter`, `Shift+Enter`, `"Enter "`, and `"x\n"`.
- browser-use `send_keys` falls back to typing each character when a key is unknown, so `"hello"` types into the focused field under read_only. That bypasses the write guard.

**F4 (MEDIUM, AF5 intent) — No production wiring.**
- Nothing constructs `FallbackActuator` or `BrowserUseBackend`, and `BrowserSession` exposes no CDP URL (the manifest records this).
- The UI and CLI paths never pass `agent=` or `actuator=`, so `run_with_fallback` has a call site but no live path.
- My decision on the "Known gap" question: **no AF criterion literally demands a real-browser run**, so F4 alone is not an AFx FAIL. It is a tracked issue, and it is the reason F1 and F2 could not be caught.

**F5 (MEDIUM, AF6/C3) — The secret guard defaults to identity.**
- `ProviderChatModel(guard=str)` and `BrowserUseBackend(guard=str)` mean no guard unless a caller supplies one, and no production caller exists.
- The test uses a lambda that replaces one literal string.
- `_try_actuator` does not scrub or assert the task text before it goes to the backend (`Redactor.scrub` masks exact values only).
- browser-use sends the current URL and element `value` attributes in its prompts, so a resolved-secret URL or a filled input is model-visible when the guard is the identity.
- `input_text` itself is safe: it maps to FILL with the literal `{{SECRET:KEY}}`, `sensitive_data` is not passed, and nothing substitutes before the guard.
- `build_fix_prompt` substitutes placeholders sequentially, so a value containing `{{RATIONALE}}` is substituted again (LOW).
- `FallbackOutcome.vetted`, `reason` and `refusals` are unscrubbed in memory. I found nothing persisting them (LOW).

**F6 (MEDIUM, AF3) — The destination check never examines the scheme.**
- `javascript://example.com/%0aalert(1)`, `data://example.com/...`, `file://example.com/...`, `ftp://example.com` and `blob://` are all ALLOWED.
- Plain `javascript:`, `data:`, `file:///` and `about:blank` are refused, but only because `host_of` mis-parses them.
- Probed and fine: IDN, punycode, suffix, `example.com@evil.com` and `evil.com@example.com`, backslash forms, trailing dot, IP literals and `//evil.com` are all refused.

**F7 (HIGH per the brief's wording; not a FAIL) — browser-use telemetry and cloud sync default ON.**
- `ANONYMIZED_TELEMETRY` defaults true and `BROWSER_USE_CLOUD_SYNC` follows it.
- PostHog `eu.i.posthog.com` receives the task text, the visited URLs, the action history (including typed text) and the final result. Cloud sync goes to `api.browser-use.com`.
- Mitigated, though: `_load()` sets `ANONYMIZED_TELEMETRY=false` via `setdefault`, and it runs before every lazy `import browser_use`. I verified empirically that `import browser_use` makes **zero** network calls with socket-level hooks, and that after `_load()` the telemetry client is None and cloud sync is off.
- Weaknesses: it uses `setdefault`, so a `.env` value would win. `BROWSER_USE_CLOUD_SYNC` is not set explicitly. If any future code imports and constructs `Agent` without `_load()`, Pathlynks task text and URLs go to a third party.
- This is not a FAIL, because no Pathlynks data is sent under the shipped code path.

**F8 (MEDIUM) — browser-use calls `load_dotenv()` at import.**
- I confirmed it loaded `D:/autoTesting/.env` into `os.environ`: `ANTHROPIC_API_KEY`, `GEMINI_API_KEY` and every `PATHLYNKS_*` value including passwords and the Mongo URI.
- This bypasses CLAUDE.md's "SecretRef-only" key scoping.
- browser-use makes no LLM call by itself, because `Agent` requires an explicit `llm`.

**F9 (MEDIUM, licence) — AGPL in the dependency closure.**
- Closure: `browser-use` -> `markdown-pdf` -> `pymupdf 1.25.3`, which is "GNU AGPL 3.0 or Artifex Commercial". It is unconditional.
- browser-use itself is MIT. The repo is public, so this needs a licensing decision.
- `uv.lock` grows from 82 to 291 packages (209 added, 0 removed). One existing pin changed: `markdown-it-py 4.2.0 -> 3.0.0`, a downgrade forced by `markdown-pdf`. All sources are the pypi.org registry. The footprint includes posthog, authlib, google-api-python-client, openai, groq, ollama and mcp.
- This is more than "browser-use and its transitive dependencies, nothing else": it is those plus a changed pin.

**F10 (LOW) — `ProviderError` handling is untested.**
- The mutant "remove the `except ProviderError`" **survived**.
- Behaviour read: after the break the result stays ERRORED and `grade.py` makes it INCONCLUSIVE, so it is never silently a pass.
- But `agent_error` is set and never read or surfaced anywhere in `src/` or `tests/`, so the "recorded" claim is weak.
- The actuator also runs after a `ProviderError` anyway.

**Other LOW findings:**
- The deny-list is name-only and bypassable by homoglyph, zero-width and fullwidth text, CamelCase, and verbs not on the list (buy, place order, transfer, erase, wipe, close account).
- `<button>` without a `type` inside a form is not flagged as a submit.
- UPLOAD drops the file path.
- `search_google` is mapped to a constant URL.
- The `evidence_ref` `min_length` mutant survived.

## Mutants (throwaway copy; tests = test_agent_fallback.py + test_agent_loop.py)

Killed (22): AF1 engage-twice; AF2 no-validation, `extra=allow`, no `min_length` on actions, no `min_length` on observed; AF3 no `check_destination`, no read_only write refusal, no Enter refusal, no `deny_reason`, no budget check, unseen check off, refusal swallowed; AF4 no max_steps, no wall-clock in vet, bound->RESOLVED, empty reason; AF5 executor bypass, ignore-agent, no persist, replay-repaired; AF6 guard skipped, vendor import in stages.

Survived (4): AF1 drop-the-ERRORED-condition (equivalent), AF2 `evidence_ref` `min_length`, AF4 redundant wall-clock check in `_finish`, plus **AF6 ProviderError not caught (real gap, F10)**.

Not applied (1): "ProviderError marked COMPLETED". Text mismatch; judged by reading instead.

The contract's own AF1 and AF3 sabotages are confirmed: removing the destination check turns the off-domain refusal assertions red.

## PROPOSED-ISSUE lines

- PROPOSED-ISSUE (high, AF3/X7): After every agent step, re-check the page URL against `allowed_domains`, back out on a refusal, and pass `allowed_domains` to `BuSession`. Cite `agent_actuator.py:9-11`, `browser_use_backend.py:163`.
- PROPOSED-ISSUE (high): Make `ProviderChatModel` an actual browser-use `BaseChatModel` (it currently fails `isinstance`, so `Agent(...)` raises `ValueError`). Add a test that builds the real `Agent` with a fake page or CDP.
- PROPOSED-ISSUE (high): Set `ANONYMIZED_TELEMETRY` and `BROWSER_USE_CLOUD_SYNC` to false by forced assignment (not `setdefault`), add a test that fails if either is ever true, and stop `load_dotenv()` from importing `.env` secrets before the `browser_use` import.
- PROPOSED-ISSUE (medium): Refuse any `PRESS_KEY` outside a navigation allowlist under read_only, including the `Control+Enter`, `NumpadEnter` and multi-character typing paths.
- PROPOSED-ISSUE (medium): `check_destination` must allow only `http` and `https` schemes.
- PROPOSED-ISSUE (medium): Make `guard` a required argument defaulting to a real `SecretStore` guard, scrub or assert the task text in `_try_actuator`, and add a test with a real secret in a URL or input value.
- PROPOSED-ISSUE (medium): AGPL `pymupdf` via `markdown-pdf` needs a licensing decision, or an exclusion of browser-use's PDF extra. Review the `markdown-it-py` downgrade.
- PROPOSED-ISSUE (medium): Expose a CDP URL from `BrowserSession` and wire `FallbackActuator` and `BrowserUseBackend` into the run launch (AT-253 stays open until then).
- PROPOSED-ISSUE (medium): Add a test for the `ProviderError` branch, and surface `agent_error` as DOM evidence.
- PROPOSED-ISSUE (low): Flag a bare `<button>` inside a form as a submit; widen the deny-list verbs and normalise unicode; record the `upload_file` path; and fix the sequential-replace double substitution in `build_fix_prompt`.

Metrics: start=2026-10-07T14:15Z end=2026-10-07T14:55Z wall_min=40 agent_min=unavailable blocked_min=14 suite_runs=0 repeat_runs=0 mutations=26 cycle=0 resumes=1 tokens=unavailable policy=proportional-verification/2026-10-07.7
