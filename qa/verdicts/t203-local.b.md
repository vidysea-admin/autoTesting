# t203-local checker verdict (independent)

Cycle checked: 1
Head checked: 20ceefb3

| HO | Verdict | Evidence |
|---|---|---|
| HO39 | PENDING | Installer scripted: AtStartup trigger, user prompted via Get-Credential (no password in script/repo). -WhatIf prints plan and registers nothing (`schtasks /Query /TN AutoTester` -> not found). Real install not run (forbidden here). |
| HO40 | PENDING | RestartCount 5 / 1 min, ExecutionTimeLimit 0 present in script. Kill-and-recheck not exercised; needs real install. |
| HO41 | PENDING | Launcher never sets AUTH_DISABLED and removes it from env; 401/302 test skipped, blocked on T-204. |
| HO42 | PASS | Data root = AUTOTESTER_ROOT or %ProgramData%\AutoTester, logs under it; test asserts outside code tree. Restart persistence not run live. |
| HO43 | PASS | /healthz (routes_live.py:79) reused; `-Check` exits 1 on failure; test + smoke test pass. |
| HO44 | PASS (note) | DryRun default bind_host=127.0.0.1; -Lan -> 0.0.0.0; LAN logged in serve.log. Note: env AUTOTESTER_BIND_HOST is a second knob (serve_windows.ps1:32); documented in DEPLOY.md, tolerable but not strictly "one setting". |
| HO45 | PASS | DEPLOY.md B.1 covers launcher, task create/remove, data root, bind, health check, admin-first, Ubuntu later; Part A untouched (diff is +28 lines only), no secret. |
| HO46 | FAIL | ruff clean; scripts parse with 0 errors; docker/ diff vs master is DEPLOY.md only. But `autotester doctor` shows 2 NEW violations from this unit: qa/verdicts/t203-local.md:16 cites two non-existent decision ids (dangling). Other 5 (stale MAP/SNAPSHOT, t196 verdicts) look pre-existing. |

Tests: tests/test_windows_host.py 8 passed, 1 skipped (the HO41 T-204 test).

## Defects
1. qa/verdicts/t203-local.md:16 - dangling decision citations (reword without any decision-id pattern). Fix cycle needed.
2. serve_windows.ps1:32 - extra env bind knob (minor, see HO44).
