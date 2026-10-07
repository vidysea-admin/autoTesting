# Verdict — at758-759-security (coordinator A, blind)

Date: 2026-10-07. Bound to D:/autoTesting/.worktrees/at758-759-security (wave/at758-759-security, tip b9ce7983, base af8f3218). Checkpoint: qa/checkpoints/at758-759-security.md.
Policy-Version: proportional-verification/2026-10-06.6
Cycle checked: 0

## Check plan (step 0)
Signals: security/auth guard on every UI request (L); approval coverage change (L); protected conftest edit (L). Checks: ruff, doctor and design rules; Host allow-list adversarial probes (direct and over a real uvicorn socket); covering_approval read and falsification; conftest masking review; falsification floor, one row per criterion in throwaway copies; one full suite. UI: no screen, template or navigation path changed, so no Mode D and no persona walk (backend-only; a refused Host gets an empty 403). This is coordinator A of a dual check; coordinator B's verdict, checkpoint and evidence were not read.

VERDICT: CONTINUE-NEEDED
SCOREBOARD: 5/5 criteria evidenced on the checks run, 0 invariants contradicted. The mandatory full suite did not complete, so this is not a PASS.
TIER: L (security/auth: Host/Origin guard in ui/helpers.py `_OriginGuard.__call__` on every request; protected conftest edit tests/conftest.py `_ui_test_host`). Dispatched tier unchanged.

## Criteria
- [1] AT-758 Host allow-list on every request, empty 403: MET. Real uvicorn with no AUTOTESTER_ALLOWED_HOSTS: loopback 127.0.0.1 and localhost return 200 with the saved credential in the body; `Host: evil.example:18758` returns 403 with an empty body and no credential. Same refusal for HEAD, OPTIONS, a 404 path, /static, /docs and /openapi.json. Env lists work: hosts of AUTOTESTER_ALLOWED_ORIGINS and exact AUTOTESTER_ALLOWED_HOSTS entries are admitted (lower-cased), `*` is never a wildcard, the port must match exactly.
- [2] AT-760 unparsable port: MET. `localhost:8000.evil.com`, `localhost:99999`, `localhost:-1`, `localhost:+80`, `localhost:0x50` and `localhost:80:80` are refused as a Host; the unparsable-port Origin is refused 403 over the socket.
- [3] AT-761 duplicate Origin or Host: MET. Both orders of duplicate Host and a duplicate Origin are refused 403 over the real socket. An absent Host is refused (HTTP/1.0 without Host reaches the app and gets 403).
- [4] AT-759 covering_approval: MET. In stages/explore_consent.py, `human` (non-account rows) feeds both fallbacks, and `_credential_approval` still sees every row but only after `validate_account_scope` and `validate_account_bounds` pass against the current .env and declaration. Credential removed, domain changed and declaration dropped are each refused; a human row still covers; ADVERSARIAL is refused (falsification below).
- [5] Constraints: MET. ui/app.py is 300 and untouched, ui/helpers.py 292, no new src modules, no file over 300 (tests/test_credential_run_approval.py is exactly 300), longest function in the two changed src files 36 lines. The env page still displays values (G4 untouched). `ruff check src tests scripts` passes; `autotester doctor` prints `doctor: clean`.

## Host allow-list probes (`_host_allowed`, about 60 inputs, and a real socket)
Refused: trailing dot (`localhost.`, `localhost.:8000`); bare or unbracketed `::1`, `[::1`, `[::1]x`; `[0:0:0:0:0:0:0:1]` and `[::ffff:127.0.0.1]` (not in the loopback set, fail closed); `127.1`, `0.0.0.0`; userinfo in either order (`localhost@evil.com`, `evil.com@localhost`); `#`, `?`, backslash, `%2e`, `%00`, CR/LF, comma, space and path separators; fullwidth and Kelvin-sign look-alikes; `localhost.localdomain`, `foo.localhost`; the empty value. Accepted by design: `localhost`, `LOCALHOST`, `Localhost:8000`, `localhost:`, `127.0.0.1[:port]`, `[::1][:port]`.
Over a real socket: X-Forwarded-Host, X-Forwarded-For and Forwarded are ignored (evil Host plus loopback XFH is 403; loopback Host plus evil XFH is 200, correct because only Host is trusted); an obs-fold Host is rejected by the server itself (400); a duplicate Host in either order is 403; an absent Host is 403.
Non-blocking observations, each a low PROPOSED-ISSUE below or an accepted by-design behaviour: (a) `local\thost` is accepted because `urlparse` strips tabs; the result is a loopback name, so there is no rebinding gain. (b) An absolute-form request line (`GET http://evil.example/...`) with a loopback Host header is accepted; browsers never send that form to an origin server and Starlette routes on the Host header, so it is not a browser-reachable rebinding path. (c) An origin listed with an explicit default port (`https://x:443`) only admits `Host: x:443`, which browsers do not send; the existing Origin check has the same property.

## Protected change: tests/conftest.py `_ui_test_host`
Judgement: it does not weaken any test. It only sets AUTOTESTER_ALLOWED_HOSTS=testserver (setdefault, restored at exit). A grep of tests/ finds no other test that depends on a non-testserver Host or on AUTOTESTER_ALLOWED_*. The guard tests that need the real default call `monkeypatch.delenv("AUTOTESTER_ALLOWED_HOSTS")` and assert that `testserver` itself is then refused (tests/test_ui_origin_guard.py, `get("testserver") == 403`). It also strengthens the pre-existing D-066 case `{"Origin": "http://testserver", "Host": "testserver"}`: without the fixture that case would be refused at the Host stage for the wrong reason; with it only the Origin check can refuse. If a developer's shell already sets AUTOTESTER_ALLOWED_HOSTS to something else, UI tests fail loudly with 403 and are not masked. No assertion was edited or deleted in the diff.

## Falsification (throwaway copies under the scratchpad, never the bound tree)
| Criterion | edit (single hunk) | node | before (in copy) | after |
|---|---|---|---|---|
| 1 | helpers.py `or not _host_allowed(headers["host"])` -> `or False` | test_the_rebinding_repro_cannot_read_a_saved_credential_but_loopback_can | 1 passed | 1 failed |
| 2 | helpers.py `_ = parts.port  # AT-760` -> `_ = None  # AT-760` | test_an_origin_with_an_unparsable_port_is_refused | 4 passed | 4 failed |
| 3 | helpers.py `names.count("origin") > 1` -> `> 99` | test_more_than_one_origin_or_host_header_is_refused | 4 passed | 1 failed, 3 passed |
| 4 | explore_consent.py first fallback `_require(human,` -> `_require(rows,` | test_an_account_row_stops_covering_when_its_credential_is_gone | 3 passed | 1 failed ([declaration]) |
| 4 | explore_consent.py second fallback `_require(human,` -> `_require(rows,` | same | 3 passed | 2 failed ([env], [domain]) |
| 4 | core/consent.py ACCOUNT_KINDS gains ADVERSARIAL | test_adversarial_never_gets_an_automatic_grant | 1 passed | 1 failed (DID NOT RAISE ApprovalRequired) |

Method note: a first set of green-before runs resolved `autotester` into the worktree (a `:` separator in PYTHONPATH on Windows); they were discarded and redone with `;`, and `autotester.__file__` was confirmed inside the copy before any edit.

## Diff scope (4c)
`git diff af8f3218...HEAD --stat`: 6 files, all in the manifest's What changed. No function, class, export, route, test or config key was deleted or renamed. The only edited existing test line is a comment on an assertion in tests/test_credential_run_approval.py.

## Full suite: NOT COMPLETE
`uv run pytest` (no -q, no -x), started 16:19:23, died silently at 17:08:11 at 56% (1422 of 2541 tests), exit=1, no summary line, about 49 min wall on a loaded machine, past the 45 min L budget. Four F:
- tests/test_crawl_inventory_live.py: fails and then hangs. On both this branch and a `git archive` of base af8f3218 it ended by `timeout` (exit 124) after one F, so it is pre-existing.
- tests/test_flake_probe_real_process.py: 2 passed when run alone.
- tests/test_mc_sessionstart_loop_status.py (two F): 9 passed when run alone.
None of the four touches ui/, consent or approvals. Mandatory evidence is missing, so no PASS. `full-suite trigger: conftest edit` is also recorded.

## Remaining (for the resume)
1. One complete `uv run pytest` in the bound worktree on an otherwise idle machine, with at least 60 min of wall budget. Expect tests/test_crawl_inventory_live.py to fail and hang as it does on base (P1); the maker has to decide how that is handled before a full run can finish.
2. Nothing else. Criteria, probes, falsification, diff scope, ruff and doctor are done and reusable while the code hashes in the checkpoint are unchanged.

FAILURES: none (no criterion failed and no defect was found in the changed code).
PROPOSED-ISSUE: {"severity":"low","type":"process","title":"tests/test_crawl_inventory_live.py fails and then hangs on base af8f3218 and on wave/at758-759-security; it blocks a complete full-suite run","evidence":"pytest of that file alone in the base archive and in the bound tree, both ended by timeout (exit 124) after one F"}
PROPOSED-ISSUE: {"severity":"low","type":"process","title":"the full suite took about 49 min for 56% with two coordinators running, and the process ended silently at 1422/2541 with exit=1 and no summary","evidence":"qa/checkpoints/at758-759-security.md"}
PROPOSED-ISSUE: {"severity":"low","type":"docs","title":".env.example and the docs/plan.md T-203 row do not mention AUTOTESTER_ALLOWED_HOSTS although a hosted server returns 403 on every request without it","evidence":"manifest What changed, last behaviour bullet; D-072 item 12 authorizes the .env.example key"}
PROPOSED-ISSUE: {"severity":"low","type":"hardening","title":"the Host guard ignores an absolute-form request line and accepts a tab inside Host (urlparse strips it); neither is browser-reachable","evidence":"raw-socket probe with an evil absolute-form URI and loopback Host returned 200; _host_allowed with an embedded tab returns True"}

CAPABILITY-COVERAGE: 6/6 rows reproduced
LIVE-BROWSER: not-applicable (changed paths: ui/helpers.py middleware, stages/explore_consent.py, tests; no screen or template). A real uvicorn socket probe was run instead.
ISSUES-WRITTEN: none (dual coordinator: PROPOSED-ISSUE lines only)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: Every acceptance criterion is evidenced end to end and the falsification floor is met with no defect found, but the one mandatory full suite for this L security unit did not finish (the process died at 56% after about 49 min under load, with a failing and hanging live-crawl test that is pre-existing on base), so a PASS is not allowed. Open question, not a failure: whether the three other F in the partial run reproduce in a complete run, since each passed alone.
Metrics: start=2026-10-07T16:14:31+05:30 end=2026-10-07T17:38:00+05:30 wall_min=83 agent_min=unavailable blocked_min=0 suite_runs=1 repeat_runs=0 mutations=6 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-06.6 slow: full suite 49 min (died at 56%), base-comparison runs about 20 min
