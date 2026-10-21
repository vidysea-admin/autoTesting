# Verdict t169-harness-login (coordinator B, dual check) - Cycle checked: 0
Date: 2026-10-21 · Head checked: 4ff07564 (code state a271a187, clean) · Base 8956c9bc · Policy-Version: proportional-verification/2026-10-19.17 · Bound to D:/autoTesting/.worktrees/t169-harness-login

## Check plan (step 0)
Diff = core/env.py (+3), ui/routes_settings.py, scripts/run_real_acceptance.py, .env.example, 2 test files. Signals: logic changed -> tests + falsification floor; UI changed (settings page) -> Mode D own browser; auth/credential handling -> security read of changed lines (dual-trigger routes_settings.py:89 confirmed: line 89 is the `set_env_value` write in `provider_settings_submit`, unchanged by the diff). No persona walk (internal admin settings page, one user type with `settings.manage`; manifest says skip, plan agrees). No data/prompt/portal check.
TIER: L (credential written to the repo-root .env and read by a sign-in script; cited trigger routes_settings.py:89). No raise.

## Evidence
- Diff read in full (4c): `git diff 8956c9bc..HEAD`: nothing deleted beyond the `--email`/`input()`/`getpass` lines the criteria require removing (script lines 12-17, 75-80, 98-110); every touched file is in the manifest's What changed (the qa/manifests file is bookkeeping).
- Tests (step 3, own run): `uv run pytest tests/test_ui_settings.py tests/test_ui_env_labels.py tests/test_real_acceptance.py tests/test_acceptance_isolation.py tests/test_hosting_deploy.py` -> 50 passed (matches Pre-check C1 12 + C2 23 + C3 15). `ruff check src tests scripts` -> All checks passed; `autotester doctor` -> clean. Files within caps (routes_settings.py 106, env.py 139, script 122 lines).
- Falsification floor (4b, one per criterion, 3 isolated copies of `git archive HEAD`, green-before in the copy = 8 passed, PYTHONPATH pinned to the copy):
  C1 `_WRITE_ONLY = frozenset()` -> 2 failed (page + submit tests); C2 script checks `HARNESS_KEYS[:1]` -> 2 failed (missing1 = password only, missing2 = both); C3 `.env.example` password line deleted -> 1 failed (documents-every-key test). mutations=3, mutants=0 beyond floor. Bound tree not edited.
- Tests selection reviewed: each criterion has a covering test and the Pre-check commands name the files; sibling path (other callers of `PROVIDER_KEYS`/`_PROVIDER_KEYS`) is the same page only.

## Criteria
- C1 MET. Mode D (own server 127.0.0.1:8791, AUTOTESTER_ROOT=D:/autoTesting/.work/tmp/chkB/root, first loopback account signed up): /settings/providers lists AUTOTESTER_HARNESS_EMAIL (text) and AUTOTESTER_HARNESS_PASSWORD (type=password, value empty, no show/hide button). Saving each via its Save button -> 303, status "Set", `.env` of the temp root holds both keys (written by the one `set_env_value` writer, routes_settings.py:89). The saved password string is absent from the page DOM after save and in a fresh sign-in (leaksPw=false), absent from the POST response, and absent from server.log. An empty POST is refused 400 and erases nothing (wipe-guard). Evidence: qa/evidence/browser-t169-harness-login-2026-10-21-checker-b/report.json + settings-providers.png.
- C2 MET. scripts/run_real_acceptance.py:57-64 reads both keys from os.environ, filled by `load_repo_env(root)` (line 89) from core/env.py; no input()/getpass/--email remain (grep of the script and `HARNESS_KEYS` sites); with either missing it prints `MISSING <KEY>[, <KEY>]: ... <origin>/settings/providers` to stderr and returns 4 (line 101-103), before the app import; values are never printed (tests assert the password is in no output with input/getpass rigged to raise). Dry run exits before the login check (line 98-100), approvals preflight (exit 3) comes first, both as the manifest states.
- C3 MET. `.env.example` +5 lines documents both keys with empty values; tests/test_hosting_deploy.py checks both name coverage and "no secret-looking value" and pass.
- Invariants: core-invariants credential rules held (no value in a model prompt, log or page; key only in the repo-root .env; D:/autoTesting/.env never opened by this check). Contract amendment (ui-settings US1/No-fire "six keys" -> eight): authorized by Umesh's request quoted in the dispatch, folded as P1 below; not a FAIL.

SCOREBOARD: 3/3 criteria met, credential invariants hold
VERDICT: PASS
FAILURES: none
CAPABILITY-COVERAGE: 3/3 rows reproduced
LIVE-BROWSER: qa/evidence/browser-t169-harness-login-2026-10-21-checker-b/ (console errors 0 on normal navigation; the single error recorded is my deliberate empty-POST 400)
ISSUES-WRITTEN: none (dual coordinator, no side effects)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: The page-to-.env-to-script chain works end to end on my own server and tests: the password is write-only (masked, never prefilled, no reveal toggle, absent from every body and log I searched) and the script refuses naming the missing KEY and /settings/providers. Question, not a finding: whether `core.redact.Redactor` includes the exported AUTOTESTER_HARNESS_PASSWORD value in its scrub list for run logs was not verified (the script and page never print it, which is what the criteria require).

PROPOSED-ISSUE: {"id":"P1","sev":"low","type":"contract","unit":"t169-harness-login","text":"qa/contracts/ui-settings.md US1 and its no-fire line still say exactly six keys; the settable set is now eight (AUTOTESTER_HARNESS_EMAIL, AUTOTESTER_HARNESS_PASSWORD, write-only password). Checker routine amendment citing Umesh 2026-10-21 request."}
PROPOSED-ISSUE: {"id":"P2","sev":"low","type":"process","unit":"t169-harness-login","text":"Not verified here: whether core/redact.py Redactor scrubs the AUTOTESTER_HARNESS_PASSWORD value if it ever reaches a run log; load_repo_env exports it into the server process environment (server key). Candidate: add the value to the Redactor secret list or a test that it is scrubbed."}

Metrics: start=2026-10-21T07:22:00Z end=2026-10-21T07:40:00Z wall_min=18 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=3 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-19.17 check_s=1080 mutants=0 defects_unit=0 defects_6c=0
slow: mutant copies 6 min (three `cp -r` copies of a 129 MB tree on Windows) · L budget 45 min not exceeded
