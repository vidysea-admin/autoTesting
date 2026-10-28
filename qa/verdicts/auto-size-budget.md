# Verdict - auto-size-budget (checker A, Mode A)

**Verdict:** PASS
**Cycle checked:** 0
**Unit:** auto-size-budget, branch `fix/auto-size-budget`, code head 975fafbb (worktree `D:/autoTesting/.claude/worktrees/auto-size-budget`)
**Authority:** D-112 item (2), `Approved-by: Umesh` (main checkout `docs/DECISIONS.md:2808-2820`; not yet in this tree, so doctor lists the D-112 citations as dangling, as it did for D-110/D-111).
**Judged against:** `qa/manifests/auto-size-budget.md` S1-S6 plus `qa/contracts/consent.md` CN6 (the refusal's command must work), CN10, CN4.
**Dual check:** the manifest recommends A+B (security trigger: consent). This is the A verdict; B is `qa/verdicts/auto-size-budget.b.md`.

## Criteria

| # | Result | Evidence |
|---|---|---|
| S1 one derivation | PASS | `src/autotester/schema/approval.py:62-90`: `GRANT_SAFETY_MARGIN=1.25`, `GrantBounds`, `derive_grant_bounds`. The probe rule (`max(floor, actions x 20)` capped 40000) is the consent-followups rule moved, not copied. Independent probe: `derive(LIVE,9,9,477.0)=12/240/597.0`; `(LIVE,0,0,0.0)=0/0/0.0`; `(LIVE,5000,10,1e9)=2000/40000/86400.0`; `(LIVE,1,0,10.0)=2/0/13.0`; `inf` and `nan` wall clock pass through; `(CRAWL,3,5,7.5)` unchanged. grep over `src/` finds the margin and ceilings used only via this function; `consent.py:74 account_probe_budget` (D-068 account grants, pre-existing, no margin or cap) is a different job, not a second grant estimator. |
| S2 gate's own request feeds it | PASS | `src/autotester/stages/run_gates.py:91-98` `derive_live_case_grant` = `sum(action_cost)`, `max(probe_request,1)`, `wall_clock_request_s`, the same three functions `require_live_case_approval` uses. `tests/test_auto_size_budget.py:83` (never below the gate's request) and `:164` (derived grant passes the real gate) pass. |
| S3 refusal hint | PASS | `src/autotester/core/consent.py:146-165` `_grant_command` derives first, then prints. `_shortfalls`, `_reject_reason`, `require_approval` are untouched by the diff. Crawl/adversarial/read pass through (`test_auto_size_budget.py:135`). The pinned hint change in `tests/test_ui_runs_serial_entry_order.py:266-268` (9 -> 12, 477.0 -> 597.0) equals ceil(9x1.25)=12, ceil(477x1.25)=597: deliberate and correct. CN6 holds: hint numbers are >= the run's request, so the pasted command clears the gate. |
| S4 CLI approve | PASS | `src/autotester/cli_crawl.py:173-180,238-270`: options now `int\|None`/`float\|None`; `_resolved_bounds` prints the cyan note before `RunApproval` is built and signed; a typed flag overrides only itself; non-live and no-cases keep 200/200/600 (`run_gates.py:101-122`); over-ceiling still refused by `_caps_or_refuse` (`test_auto_size_budget.py:205`). Signed row construction unchanged. |
| S5 UI grant form | PASS (with note W2) | `src/autotester/ui/routes_credentials.py:182-205,219,234` and `routes_crawl_approval.py:53-56,60,96`. `data-live-*` attributes and the note render only when planned cases exist; default kind stays `crawl`; inputs stay plain editable number inputs (`ca-probes max='40000'` holds the derived probe ceiling); the POST path (`_bounds`/`_capped`) is untouched, so the server does not trust the prefill. No-cases form unchanged (`test_auto_size_budget.py:229`). |
| S6 ceilings, row shape | PASS | Clamps at 2000 / 86400 / 40000 verified above; `RunApproval` fields and HMAC payload untouched (the `schema/approval.py` diff adds constants and functions only). |

## Commands re-run by the checker (one pytest at a time, `-o addopts=`, in the worktree)

- `tests/test_auto_size_budget.py tests/test_ui_runs_serial_entry_order.py` -> 38 passed
- the 10-file consent/approve batch from the manifest -> 212 passed
- the 8-file UI/launcher/crawl batch -> 89 passed, 1 failed (`test_crawl_real_cli.py::test_the_refusals_command_grants_the_run_once_a_human_fills_it_in`, pre-existing, classified below)
- the 13-file approval/revoke/explore batch -> 180 passed
- the 5-file credential-safety batch -> 50 passed
- `uv run ruff check src tests scripts` -> All checks passed!
- `uv run autotester doctor` -> 46 violations, all `decision-citation-dangling` (D-110/D-111/D-112 are not yet entries in this tree); no function-too-long or file-too-long. Baseline on `fix/consent-followups` 077b7fb9 is 36; the +10 are exactly the D-110/D-111/D-112 citations in the new `qa/manifests/auto-size-budget.md` (lines 5, 6, 8, 19, 30, 50, 52). They resolve when D-110..D-112 land with the merge. `consent.py`, `cli_crawl.py`, `routes_crawl_approval.py` sit at exactly 300 lines, not over.
- The full suite was not run (machine low on memory, by instruction). Not claimed.

## Classification of the failing test (`test_the_refusals_command_grants_the_run_once_a_human_fills_it_in`, "No such option: --standing,")

Pre-existing, NOT caused by this unit.

| Commit | Result |
|---|---|
| master-equivalent e74664f8 (worktree `signup-requests-f1`, clean) | passes. It has no D-111 text in the hint (`git show e74664f8:src/autotester/core/consent.py` has 0 matches for "or --standing"). |
| `feat/d111-standing-approval` d20eb037 (clean export via `git archive`; the `d111-standing` worktree is dirty, so it was not used) | FAILS |
| `fix/consent-followups` 077b7fb9 (clean worktree) | FAILS, identical message |
| `fix/auto-size-budget` 975fafbb | FAILS, identical message |

Introducing commit: **e35066ad** `feat(consent): D-111 standing (until-revoked) crawl approvals`. It added `+ (" (or --standing, until revoked)" if kind in STANDING_KINDS else "")` to `_grant_command` (now `consent.py:157`) on the crawl path; the test `shlex`-splits the printed `approve ...` line, so `(or` and `--standing,` reach the parser. The test file has no diff d20eb037..077b7fb9. D-111's own PASS and consent-followups' dual PASS did not run this file. Master is clean only because D-111 is not merged to it yet: **it will fail on master the moment D-111 merges.** Not this unit's to fix (the unit leaves the crawl hint text unchanged, `test_auto_size_budget.py:135`). The `d111-standing` worktree has uncommitted edits to `consent.py` and two tests, possibly an attempt at this; not touched.

## Findings

- **W1 (scope, non-blocking):** D-112 `Changes-authorized` (main checkout `docs/DECISIONS.md:2820`) names `schema/approval.py`, `core/consent.py`, `cli_crawl.py`, the UI grant route and view, and tests. The diff also edits `src/autotester/stages/run_gates.py:86-122` (new `planned_cases`, `derive_live_case_grant`, `resolve_grant_bounds`; the gate `require_live_case_approval` itself is unchanged) and `src/autotester/ui/routes_credentials.py:182-234` (the page that hosts the grant form). Neither is an enforcement path and the placement is defensible (the derivation needs `Case`/`action_cost`; `consent.py` is at the cap). Umesh should know and ratify; no gate was crossed.
- **W2 (test gap, non-blocking):** nothing executes `_GRANT_SCRIPT` (`routes_credentials.py:182-190`). By reading: the form lookups (`f.kind`, `f.max_actions`, `f.max_probes`, `f.wall_clock_s`) match the input names, the "edited field not overwritten" flag and the `crawl` restore to 200/4000/600 match the HTML defaults (`routes_crawl_approval.py:86-93`). A browser-level check is advisable before relying on the UI fill.
- **W3 (contract):** `qa/contracts/consent.md` has no criterion for D-112 item 2 (derived bounds, margin, ceilings). Contract amendment is checker-only; left for the merge-time contract pass together with D-112 item 1, so the wall-clock criterion is written once.
- **N1:** wall clock derives from `wall_clock_request_s`, which still includes the 45 s/case judge allowance until D-112 item 1 (`fix/run-teardown-stall`) lands; the derived grant shrinks with the request after that merge and stays valid on either side. Accepted as maker judgement call 3.
- **N2:** the maker's six judgement calls are accepted: #1 (constants moved to the schema; the only importers were updated, grep confirms), #2 (margin LIVE_CASE only; crawl 200/600 pinned by `test_crawl_real_cli`), #4 (clamp at 2000), #5 (CLI sizes from all non-retired cases), #6 (default kind stays crawl).
- No doubled margin: only `derive_live_case_grant` and `_grant_command` call `derive_grant_bounds`, on different inputs (planned cases vs the gate's raw request); derived output is never fed back in.
