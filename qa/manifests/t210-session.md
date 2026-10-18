# Manifest - t210-session (T-210, G11-4)

**Status:** ready-for-check
**Fix cycle:** 0
**Contract:** qa/contracts/multi-role-platform.md (MP11, MP12; invariants MPI1, MPI2, MPI3, MPI5 held)
**Goal task:** T-210
**Authority:** D-104 (Approved-by: Umesh 2026-10-17: build G11 now)
**Dual check:** no
dual-check-reason: browser-context isolation (one persistent profile per account) is not an AutoTester auth boundary; credentials are typed only as `{{SECRET:KEY}}` placeholders resolved by the existing `SecretStore`, which this unit does not edit. The checker may raise it.
**Persona walk:** skip (no UI surface; no route, template or static asset)
**Issues addressed:** none
**Executor:** claude-sonnet-subagent
**Base SHA:** 36a87037 (worktree .worktrees/t210-session, branch wave/t210-session)
**Code SHA:** 42fc8dc9

## Criteria (quoted verbatim from the contract)
- **MP11 - One isolated context per role.** Two role accounts in one run share no cookies, storage or profile directory; a sign-out in one leaves the other signed in. Verify: local two-account fixture app. serves: intent#O18 - closes T-210
- **MP12 - Links are followed and accounted for.** Every declared PlatformLink is reported followed, failed (with reason) or not reached; a hop landing on a host outside every declared platform stops and becomes a finding. Verify: fixture with a redirect, an SSO hop and one off-platform redirect. serves: intent#O16, intent#O4 - closes T-210
- **MPI3 - One enums file, one editor.** `schema/multi_role_enums.py` is not in `git diff --name-only 36a87037..42fc8dc9`.

## What changed (6 new files, nothing existing edited)
- `src/autotester/stages/multi_role_session.py` (new, 202): `RoleSessions` - one `BrowserSession`, one profile dir (`ProjectPaths(f"{slug}-role-{account.id}")`) and one single-thread executor per `RoleAccount`; `run_as`, `run_parallel`, `sign_in` (typed `{{SECRET:KEY}}` placeholders; refuses a sign-in host outside the account's platform before typing), `host_in_platform`.
- `src/autotester/stages/platform_links.py` (new, 280): `follow_platform_links` (one `LinkOutcome` per declared link, in order), pure `judge_hops`, `trace_link` (route guard + request events), `_off_platform_finding` (a `MultiRoleFinding` of class OFF_PLATFORM_HOP, value-free template).
- `src/autotester/schema/link_outcome.py` (new, 56): `LinkStatus` (followed / failed / not_reached) and `LinkOutcome` (extra=forbid). New schema file rather than an edit of `multi_role_enums.py` (MPI3, A2).
- `tests/multi_role_app.py` (new, 175): two-account local fixture app (stdlib server, real server-side session store; routes for login, logout, storage, redirect, SSO meta-refresh, off-platform redirect, mid-chain off-platform hop, 404). Hosts are `*.localhost`; synthetic passwords only (MPI2).
- `tests/test_multi_role_session.py` (220), `tests/test_platform_links.py` (240).
- Not touched: any T-207 or T-209 file, `browser/session.py`, `stages/parallel_run.py`, `schema/multi_role_enums.py`, `qa/contracts`, `qa/issues.jsonl`.

## Judgement calls for the checker
1. **One thread per role.** Playwright's sync API refuses a second driver on one thread (measured: "Sync API inside the asyncio loop"), so each account owns a one-thread executor that starts, uses and closes its session. `run_as` runs inline when already on that role's thread.
2. **Containment is two layers, and only the first prevents.** A route guard fetches the first request of a navigation with `max_redirects=0` and aborts if the page or its redirect target is outside every declared platform: the stray host is never contacted (test: 0 hits on the evil host). A redirect deeper in a chain is followed inside the browser (Playwright does not route it): it is detected from `request` events, judged, and the page is parked on `about:blank`; the stray host was contacted once (test: exactly one hit, `/phish`). The contract says "stops and becomes a finding", which this meets; "never contacted" is only true for the first hop.
3. **Host boundary is host-only,** like `Project.allows_domain`; ports are not part of it. `expected_landing_host` compares the port only when the declared value has one.
4. **`LinkOutcome.finding` only for an off-platform hop.** Other failures carry a reason, not a finding. Reasons pass through `_safe_reason` (class name + first line, every URL replaced by `<url>`) and `SecretStore.scrub_optional`.
5. **Not verified, not required by MP12:** whether the session is still signed in after a hop (`carries_session`), and sign-in itself inside `follow_platform_links` (links are driven in the already-open role contexts).
6. A link whose from-platform has no role account is `NOT_REACHED`; otherwise the platform's first account drives it.
7. `autotester doctor` reports 2 violations, both stale-generated (`docs/MAP.md`, `docs/SNAPSHOT.md`); not hand-edited, the merge-queue regenerates. The rest is the pre-existing decision-citation advisories.

## Verification scope
Policy-Version: proportional-verification/2026-10-18.15
Tier: L (concurrency: threads, per-role executors, real Chromium)
Round: 6 new files (3 src, 3 test), 2 criteria (+MPI1, MPI3, MPI5), est 60 min
Owners: OG-SESSION
Base / checked state: 36a87037 / 42fc8dc9, clean tree
Gate answers: none apply (D-104 opens the build).
Affected tests / full-suite trigger: no existing file changed, so none. Neighbour suites run: `tests/test_schema.py`, `tests/test_multi_role_schema.py`, `tests/test_parallel_run.py` (122 passed together with the two new files). The builder ran no full suite.
Tests[MP11]: tests/test_multi_role_session.py - 9 cases: one session and one distinct profile dir per account, thread affinity, failed start closes those that started, `run_parallel` overlap (barrier of 3), unknown account, `sign_in` placeholders and scope refusal, re-entrant `run_as`, and the live test: cookies, storage and profile disjoint and a logout in one context leaves the other signed in.
Tests[MP12]: tests/test_platform_links.py - 18 cases: `judge_hops` matrix (7), port rule, `host_in_platform`, value-free finding round trip, every link in order with NOT_REACHED, scrubbed crash reason, URL-with-query never in a reason, finding-build failure keeps later links, non-http scheme, no links, live 7-link fixture (redirect, SSO, control click, off-platform direct, off-platform mid-chain, 404, no account), live containment (first hop 0 stray hits, chained hop 1 and parked).
Tests[MPI3]: none - diff check: `git diff --name-only 36a87037..42fc8dc9` lists only the six new files above.
Falsification[MP11]: copy-mutant in scratchpad/t210-session/copy (every role shares one profile dir, `f"{project.slug}-role"`): before 9 passed; mutated 9 failed; restored 9 passed.
Falsification[MP12]: copy-mutant (`judge_hops` off-platform host check replaced by `if False:`): before 18 passed; mutated 7 failed, 11 passed; restored 18 passed.
Pre-check[MP11]: 42fc8dc9 uv run --directory <worktree> pytest tests/test_multi_role_session.py -> 9 passed t=19 blobs=tests/test_multi_role_session.py:b98625e,tests/multi_role_app.py:2efc8ff
Pre-check[MP12]: 42fc8dc9 uv run --directory <worktree> pytest tests/test_platform_links.py -> 18 passed t=20 blobs=tests/test_platform_links.py:ebacced,tests/multi_role_app.py:2efc8ff
Lint: 42fc8dc9 `uv run ruff check src tests scripts` -> All checks passed; `uv run autotester doctor` -> 2 violations, both stale-generated (judgement call 7). Collection: `pytest --collect-only` on both files -> 27 tests collected.
Metrics: start=2026-10-18T14:00:00Z end=2026-10-18T20:30:00Z wall_min=390 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=2 mutations=2 cycle=0 resumes=1 tokens=unavailable policy=proportional-verification/2026-10-18.15 lane=normal check_s=unavailable mutants=2 defects_unit=0 defects_6c=0 tests=27 tests_min=1

## How to verify (commands + expected)
- `uv run pytest tests/test_multi_role_session.py tests/test_platform_links.py` -> expected: 27 passed.
- `git diff --name-only 36a87037..42fc8dc9` -> expected: the six new files only.

## Capability coverage (each new claim -> its isolating falsification)
| Criterion | capability | the check that covers it | the falsifying edit | observed |
|---|---|---|---|---|
| MP11 | one profile and context per role, sign-out isolated | tests/test_multi_role_session.py (live isolation test) | share one profile dir across roles | green on tree; 9 failed on the mutant |
| MP12 | off-platform hop stops and becomes a finding | tests/test_platform_links.py::test_judge_hops_matrix | skip the host check in `judge_hops` | green; 7 failed on the mutant |

## Live browser evidence
Real headless Chromium against the local fixture app only (`tests/multi_role_app.py`); no real product, no external service. Skips if no Chromium is installed.

## Status: ready-for-check
