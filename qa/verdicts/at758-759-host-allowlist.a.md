# Verdict A - at758-759-host-allowlist (coordinator A of a blind dual check)

Cycle checked: 0
Commit checked: c642dcb5 (product 2e9b3bf8) on wave/at758-759-host-allowlist. Policy-Version: proportional-verification/2026-10-10.9
Checker: coordinator A. Never read: any `.b.md` verdict, checkpoint or evidence directory, nor the old branch's at758 verdicts.
Evidence: qa/evidence/at758-759-host-allowlist-a/ · checkpoint qa/checkpoints/at758-759-host-allowlist.a.md

## Plan
Tier L (security: request-host validation in front of the hosted UI; protected-file edit tests/conftest.py). Checks: (1) each of C1-C5 re-run by me, no builder output reused; (2) one falsification per criterion, each in its own copy; (3) my own attack on the Host guard and on `covering_approval`, each run against c642dcb5 and master 16efd426 as a differential; (4) step 4c diff read in full; (5) the builder's one red against master; (6) the one full suite, sharded; (7) ruff + doctor. Persona walk: skip (no screen changed; a refused Host gets an empty 403). Live browser: not applicable (changed paths are `ui/helpers.py` middleware, `stages/explore_consent.py`, docs, tests; no rendered output changed).
Dual trigger: manifest line `dual-trigger: security src/autotester/ui/helpers.py:280`. I read line 280 of c642dcb5: `or not _host_allowed(headers["host"])):`, the Host check inside `_OriginGuard.__call__`. It points at the real check.

VERDICT: PASS
SCOREBOARD: 5/5 criteria met (C1-C5), 0/0 invariants touched (core-invariants not in the diff)
TIER: L (security request-host validation, `ui/helpers.py:280`; conftest edit `tests/conftest.py:93`)

## Per criterion
- C1 (AT-758) MET. Own attack (`attack_host.py`, TestClient, no network): 39 hostile Host values (other host, with port, uppercase, trailing dot, userinfo both orders, path/query/fragment, empty and blank, bracketed and bare IPv6, `::ffff:127.0.0.1`, `0.0.0.0`, out-of-range and negative port, comma-joined, backslash, non-ASCII look-alikes, NUL) against 75 method/route probes (every OpenAPI route and method, HEAD, OPTIONS, /healthz, /docs, /redoc, /openapi.json, an unmapped path, a traversal path): 2,850 requests, all `403` with an empty body, 0 responses carrying the planted credential or project name. Master 16efd426, same script: 2,850 not-403, 1,026 leaking. `Host: evil` + `X-Forwarded-Host: localhost` -> 403; `Host: localhost` + `X-Forwarded-Host: evil` -> 200 (the app does not read the header, so it neither vouches nor condemns). Loopback names (any case, any port, `[::1]`) still show the saved value on the env page (display unchanged, G4). Allow-list unset on a non-loopback name: 403 (fails closed). `AUTOTESTER_ALLOWED_ORIGINS=https://autotester.example.org/` admits exactly that host (200), not the host with another port, a subdomain, a bare name with no scheme, or junk entries (`https://x@evil.example`, `http://localhost:8000.evil.com`, `*`). `AUTOTESTER_ALLOWED_HOSTS` is exact and port-sensitive, `*` is not a wildcard, empty string admits nothing. Raw ASGI: missing Host, absolute-form target with an evil Host, an evil Host with a loopback target, an HTTP/2-style `:authority` without Host: all refused before the app.
- C2 (AT-760) MET. `Origin: http://localhost:8000.evil.com`, `localhost:80a`, `[::1]:8000.evil.com` -> 403 on a loopback Host. `localhost:8000.evil.com` as a Host -> 403.
- C3 (AT-761) MET. Repeated Host (any order, any case, even two identical values), repeated Origin (even two identical values), and a missing Host are each refused, with an empty body.
- C4 (AT-759) MET. Own script (`attack_approval.py`): mint an account-derived row for each of CRAWL, LIVE_CASE, READ, then remove the credential from .env, re-scope its domain, drop the declaration, blank the value: all 12 later runs REFUSED on c642dcb5; the same 12 are COVERED by the old row on master 16efd426 (differential). A human-granted row still covers with the credential gone; ADVERSARIAL stays refused with or without an account row.
- C5 MET. `ui/app.py` untouched (300 lines), `ui/helpers.py` 292, `explore_consent.py` 133, no new src module (9 changed files, all declared in "What changed" plus the manifest). `ruff check src tests scripts`: clean. `autotester doctor`: clean.
- The unit also claims AT-760 and AT-761 closed: both evidenced above (C2, C3).

## Falsification (isolated copy per row; green before, red after, restored; `falsification.txt`)
C1a drop `_host_allowed` call -> rebinding repro 1 failed. C1b `username is not None` -> `False`: 6 of 33 failed. C1c Host list match -> `True`: allow-list test failed. C2 `_ = parts.port` -> `None`: 4 of 4 failed. C3a `origin > 1` -> `> 99`: 1 failed. C3b `host != 1` -> `== 0`: 1 failed. C3c `host != 1` -> `False`: no-Host test failed. C4a fallback `_require(human` -> `_require(rows`: 2 of 3 failed. C4b first fallback `human` -> `rows`: 1 of 25 failed. C5 helpers.py padded to 304 lines: doctor clean -> 1 violation. All nine restored runs green. Five rows beyond the floor, under the L cap of 10.

## Diff scope (step 4c, read in full)
`git diff 3d8f7d5a..c642dcb5`: 9 files, 265 insertions, 20 deletions, all in the declared set. Nothing deleted or renamed except the replaced doc and comment wording. Edits to existing assertions: one (below). `conftest.py` +12 lines: a session-scoped autouse fixture setting `AUTOTESTER_ALLOWED_HOSTS=testserver` with `setdefault` and restore; guard tests `delenv` it, and the C1a/C1b falsifications go red, so the guard tests do see the real default.

## Rulings asked for
- Item 4, `test_deploy_guide_claims_only_what_the_compose_file_does`: NOT a protected test change. No assertion is deleted or weakened: `assert "ships with AT-758" in guide` became `assert ... "ships with AT-758" not in guide and "AT-758 is in your release" not in guide` plus `assert "empty 403" in guide`, and the two other assertions are untouched. It is justified: the guide text it pinned ("not in this release") became false by this unit's own DEPLOY.md edit. The unit is L regardless (security, conftest), so the ruling changes no tier.
- Item 5, `test_env_example_documents_every_key_the_code_reads`: PRE-EXISTING. Run alone on a git-archive copy of master 16efd426 it fails with the same two missing keys (`AUTOTESTER_SCHEDULE_GRACE_MINUTES`, `AUTOTESTER_TICK_INTERVAL_S`), `master-env-example-node.txt`. Not a FAIL of this unit; PROPOSED-ISSUE P2.

## Full suite (one, sharded 4, lock wait about 8 min counted as blocked)
`shard_suite.py --repo D:/autoTesting --ref c642dcb5 --shards 4 -- -o addopts=`: collect proof ok (3,107 = 3,107); 3,084 passed, 19 skipped, 4 failed. None is new:
- `test_hosting_deploy.py::test_env_example_documents_every_key_the_code_reads`: shown red on master (above).
- `test_reconcile_schema.py::test_rc2_ingest_video_keeps_narration_on_screen_text_and_exit_screen`: AT-792, ledgered.
- `test_mc_sessionstart_loop_status.py::test_hook_prints_the_report_and_exits_zero_on_a_healthy_log`: AT-858, ledgered; passed alone on the rerun.
- `test_hosting_config.py::test_healthz_source_root_is_the_package_even_when_the_data_root_is_elsewhere`: fails alone in the shard AND fails on master 16efd426 under the same condition (git-archive copy, no PYTHONPATH): its subprocess imports the editable install at D:/autoTesting/src, not the copy. It passes in a copy with PYTHONPATH on both trees. Environmental to archive runs, not caused by this diff; P3.
`test_redact_wrap_perf.py` (AT-725) and `test_crawl_inventory_live.py` (AT-750) did not fail in this run. Full tree: `suite-summary.json`.

FAILURES: none
CAPABILITY-COVERAGE: 9/9 falsification rows reproduced (+ C5 doctor row); 0 UNVERIFIED
LIVE-BROWSER: not-applicable (middleware, consent stage, docs, tests; no rendered output)
ISSUES-WRITTEN: none (dual check: findings below are PROPOSED-ISSUE lines only)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: The Host allow-list refuses every disallowed, malformed, repeated or missing Host on every method and route before any handler runs, the AT-759 fallback ends coverage the moment the credential is removed or re-scoped, and both were shown red on master and green here with falsifications for each criterion. Residual gaps are low hardening items, none reachable from a browser today.

PROPOSED-ISSUE: {"severity":"low","type":"hardening","title":"_OriginGuard only inspects scope type 'http', so a websocket scope skips the Host and Origin checks; the app has no websocket route today (route classes: APIRoute, Route)","file":"src/autotester/ui/helpers.py:274","fix":"also refuse a websocket scope with a disallowed Host, so a future websocket route cannot reopen AT-758"}
PROPOSED-ISSUE: {"severity":"low","type":"test-gap","title":".env.example lacks AUTOTESTER_SCHEDULE_GRACE_MINUTES and AUTOTESTER_TICK_INTERVAL_S, so test_env_example_documents_every_key_the_code_reads is red on master 16efd426 as well (HO9)","file":".env.example","fix":"add the two keys with a one-line comment each"}
PROPOSED-ISSUE: {"severity":"low","type":"test-env","title":"test_healthz_source_root_is_the_package_even_when_the_data_root_is_elsewhere fails in any git-archive or sharded copy (its subprocess imports the editable install at D:/autoTesting/src, not the copy); fails on master 16efd426 the same way","file":"tests/test_hosting_config.py:40","fix":"pass PYTHONPATH of the copy's src to the subprocess, or compare against the same import root"}
PROPOSED-ISSUE: {"severity":"low","type":"hardening","title":"Host check ignores the absolute-form request target (Host: localhost with a target naming another host passes) and urlparse strips a tab inside Host; builder disclosed both; confirmed by me at ASGI level; neither is browser-reachable","file":"src/autotester/ui/helpers.py:233","fix":"match the raw Host against a strict pattern before urlparse; optionally refuse an absolute-form target"}

Metrics: start=2026-10-11T02:14:38+05:30 end=2026-10-11T05:42:00+05:30 wall_min=unavailable agent_min=unavailable blocked_min=8 suite_runs=1 repeat_runs=0 mutations=10 cycle=0 resumes=1 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=unavailable mutants=5 defects_unit=0 defects_6c=0
Note: wall_min is unavailable because a session limit interrupted the run between 02:25 and 05:11; the scratch directories first used (`base`, `master`) were overwritten by another session, so every number above was re-run in uniquely named copies (A758fresh, A758master).
