# t204-team-login r1 seat A - sub-checker summaries (head 6ea9b688)

## Env-reader audit (read-only sub-checker; scratch only, no real .env opened)
- Readers of os.environ/getenv in src/ and scripts/: none read a project-declared or project-namespace key (grep of PATHLYNKS_ in src+scripts: only {{SECRET:..}} literals, key names for SecretStore, docstrings, PUBLIC_ENV_KEYS core/env.py:120).
- SecretStore resolves from the .env FILE (browser/secrets.py:117-137 parse_env; env_path = core/paths.py ProjectPaths.env_file), never os.environ. About 25 call sites pass env_file.
- Provider keys (providers/*.py, ui/routes_settings.py) and AUTOTESTER_* (core/ids.py, paths.py, auth/*, ui/helpers.py, stages/scheduler.py) stay exported.
- Children: src subprocess calls (media/*) inherit os.environ; they are ffmpeg/ffprobe/whisper, none needs a project key.
- scripts/bench_trial.py:109, scripts/regression_proof.py:171, scripts/run_pathlynks_first_cases.py:146 call dotenv.load_dotenv(.env) directly: they still export every key (project namespaces included) into the script's own process. Operator-run dev scripts, not the server (verdict P2).
- Scratch run (dummy values, scratch root with a copy of the pathlynks project.json): load_repo_env returned [ANTHROPIC_API_KEY, AUTOTESTER_APPROVAL_KEY, OLLAMA_MODEL, FOO_BAR]; the 4 declared PATHLYNKS_* keys and PATHLYNKS_EXTRA were not exported; SecretStore.load(strict=True) resolved all 4 declared keys to their dummy values, "in os.environ: False" for each.
- refuse_reserved_slug (credential_guard.py:39-49) reads the live os.environ: slug http is accepted when HTTP_PROXY is not exported and rejected (400) when it is; node the same; ld/demo/pathlynks accepted. autotester, autotester-x, anthropic always 400. The loader, not the slug guard, keeps a project key out of the process.

## Browser leg AU26 (Playwright, http://localhost:8795, worktree venv, scratch root/auth under the scratchpad, HTTP_PROXY dummy set; server PID 37396 + child 72072 stopped by PID, 0 listeners on 8795 afterwards)
1. first signup -> Admin; second -> /auth/waiting: PASS
2. admin ticks Tester for user2; user2's next GET / = 200 (own browser context): PASS
3. disable user2 -> next click lands on /auth/login?next=/; right password while disabled, wrong password and unknown email give identical text; user3 signed up and deleted, row gone, its next click -> login: PASS
4. onboard slug http -> readable 400 "the key prefix HTTP_ of that slug is used by a setting on this server; choose a different slug"; autotester-x and autotester -> 400; demoapp -> 303: PASS
5. non-admin user2 (custom group users.manage + groups.manage): add self to Admin/CEO -> 403 "only an Admin/CEO member can change who is in Admin/CEO"; tick credentials.view -> 403 "you can only grant permissions you hold yourself"; audit.jsonl holds {actor user2, target user2, action user.groups.refused} and {actor user2, target Tester, action group.update.refused}, no password/cookie/session text: PASS
6. login, signup, /admin/users, /admin/groups, /admin/groups/5, project access, home, project page, /settings/providers, /onboard load; console errors 0 on all admin pages, 1 each on logged-out login and signup (GET /favicon.ico 401): PASS with notes (unlabelled controls on /onboard and /settings/providers, placeholder only; no saved secret value in this walk, masking of a set value is covered by test_au21)
7. logout then /admin/users and /projects/demoapp redirect to login: PASS

Evidence: qa/evidence/browser-t204-team-login-r1-A/ (report.json + screenshots).
