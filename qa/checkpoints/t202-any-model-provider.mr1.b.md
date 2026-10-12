# Checkpoint - t202-any-model-provider, merge reconcile 1, seat B

Policy-Version: proportional-verification/2026-10-10.9
Status: COMPLETE (verdict PASS, qa/verdicts/t202-any-model-provider.mr1.b.md)
Resume: 0 of 2 | Retry: 0
Checker: claude-sonnet-subagent (coordinator B, blind to coordinator A and to all other mr1 artifacts of this unit)

## Evidence identity
- Branch / head: wave/t202-any-model-provider @ 868e3682e0d307b1908b791646706d94bebc1619 (detached worktree D:/autoTesting/.worktrees/check-t202-mr-b, clean, left in place)
- Master side compared: 29d02c4b
- Code hashes (git blobs at head): src/autotester/providers/litellm_provider.py f08e96cc774932830779a8a7b65ff045bc8cd37a (267 lines); pyproject.toml 81739ae212b356febe5d686bafd2dad2ad33e6db
- Dependency lock hash (git blob): uv.lock 93f572ebd6d09389ce818ffd7be5e8719603ccbd; `uv lock --check` -> Resolved 123 packages; litellm==1.104.0
- Environment: Windows 11, uv-managed venv inside the checkout; `autotester.__file__` = D:\autoTesting\.worktrees\check-t202-mr-b\src\autotester\__init__.py (autotester-file.txt); no live model call, no vendor network, `.env` not read
- Collected test paths: all inside the checkout (pytest rootdir = checkout)

## Commands and results (outputs under qa/evidence/t202-any-model-provider-mr1-B/)
- pytest part 1 (invalid loopback proxy env, stopped by me at test_expand): 158 passed, 1 env-artifact failure (forgot-the-fake test) -> pytest-proxy-run-aborted.txt
- pytest part 2 (no proxy): 248 passed, guard-forget test + test_expand + cli_advice_resolves + cli_surface + ai_report + unified_report(+secrets) + failure_bundle + ui_origin_guard -> pytest-affected2.txt (sha256 prefix 42d998b178159443). pytest-affected.txt is truncated by a disk-full event; ignore it.
- `ruff check src tests scripts` -> ruff.txt (clean); `autotester doctor` -> doctor.txt (clean); `uv lock --check` -> lock-check.txt
- netprobe.py / netprobe-out2.txt: import-time and construction-time network, litellm telemetry and callbacks off (netprobe-out.txt is a 0-byte remnant of the disk-full event)
- cliprobe.py / cliprobe-out.txt, providers-cmd.txt, help.txt, expand-help.txt: CLI provider paths
- probe_at790.py.txt / at790-probe-out.txt: AT-790 moved test, both states
- fals.py, fals2.py / fals-out.txt, fals2-out.txt: F1, F1b, F2, F3, F4 (copies deleted)

## Result
PASS. LL1-LL14 met; LL15 and LL16 not claimed. Falsifications: F2, F3, F4, F1b red; F1 survived (stale assertion, PROPOSED-ISSUE). Reusable by a later check only while the head, litellm_provider.py, uv.lock and the master-side files named in the verdict are unchanged.

## Remaining
none
