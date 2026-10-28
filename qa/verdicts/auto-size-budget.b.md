# Verdict - auto-size-budget (checker B: adversarial security)

**Verdict:** PASS
**Cycle checked:** 0
**Branch / head judged:** `fix/auto-size-budget` 975fafbb (worktree `.claude/worktrees/auto-size-budget`)
**Authority:** D-112 item 2 (`docs/DECISIONS.md:2808` on master, `Approved-by: Umesh`). Judged against `qa/contracts/consent.md` (CN10 single meaning of bounds; line 275 "system-selected bounds positive and finite"; lines 74-75 "the 2000-action and 24h per-run caps stay") and manifest criteria S1-S6.
**Probe (throwaway, in-process fake signing key, no `.env` value read or printed):** `.work/probe_autosize_b.py`, `.work/js_probe.js` (gitignored, not committed).

## Re-runs (mine, one pytest at a time, `-o addopts=`, in the worktree)
- `tests/test_auto_size_budget.py tests/test_ui_runs_serial_entry_order.py` -> 38 passed
- the ten consent/approve files named in the manifest -> 212 passed
- the eight UI/launcher/crawl files -> 89 passed, 1 failed (`test_crawl_real_cli.py::test_the_refusals_command_grants_the_run_once_a_human_fills_it_in`, classified below)
- the thirteen approval/revoke/signing files -> 180 passed; the five credential-safety files -> 50 passed
- `uv run ruff check src tests scripts` -> All checks passed
- `uv run autotester doctor` -> 46 violations, ALL `decision-citation-dangling`: 9x D-110, 31x D-111, 6x D-112 (entries not yet in this tree). No function-too-long, file-too-long, duplicate-definition or other rule. `core/consent.py`, `cli_crawl.py`, `ui/routes_crawl_approval.py` are exactly 300 lines (at the cap, not over).

## Criteria
- **S1 one derivation: PASS.** `schema/approval.py:76-90` is the only place the margin, rounding and clamp live. Callers: `core/consent.py:151` (hint), `stages/run_gates.py:96` (`derive_live_case_grant`, used by `resolve_grant_bounds` at :110 and by the UI at `ui/routes_credentials.py:198`). grep finds no second estimator; the old `wide = actions * PROBES_PER_ACTION` block in `_grant_command` is gone.
- **S2 fed by the gate's own request: PASS.** `run_gates.py:96-98` uses `action_cost`, `probe_request`, `wall_clock_request_s`. Fuzz of 3000 random case sets (0-300 steps, up to 40 cases): 0 derived values outside (0, 2000] / (0, 86400] / (0, 40000], 0 non-finite, 0 cases where the request was inside the ceilings and the derived bound fell below it.
- **S3 hint: PASS.** `core/consent.py:151-162`; only LIVE_CASE is widened, `_shortfalls` / `_reject_reason` untouched (diff). The crawl hint test (`--max-actions 150`, `--wall-clock 900.0`) passes. Other LIVE_CASE `require_approval` callers (`agents/guards.py:82`, `stages/ai_capture.py:139`, `stages/orchestrate_gate.py:47`, `stages/schedule_gate.py:75`, `stages/schedule_wiring.py:154`) only get a wider, clamped hint; the derivation runs once per hint (nothing feeds a derived value back in, so no double margin).
- **S4 CLI: PASS.** 12 random project/case sets through `CliRunner` `approve --kind live_case` with no bound flags: the numbers in the cyan line equal the signed row (`max_actions`, `max_probes`, `wall_clock_s`) in 12/12 (`printed != signed: 0`). The same 12 rows then cleared `require_live_case_approval` (`gate-refused: 0`). `:g` cannot truncate: the wall is a whole number <= 86400 (5 digits, `:g` keeps 6). A typed flag overrides only itself (`run_gates.py:111-112`, test passes); `--max-actions 2001` is still refused (`cli_crawl.py` `_caps_or_refuse`, test passes).
- **S5 UI: PASS.** Ran the exact `_GRANT_SCRIPT` (`ui/routes_credentials.py:182-189`) in node against a stub DOM: choosing `live_case` fills 7/140/163; back to `crawl` restores 200/4000/600; a field typed BEFORE the kind change is kept (50 stays, the others fill); a field edited AFTER the fill survives both a switch to crawl and back to live_case (999 stays). The fill assigns `.value`, which does not fire `input`, so it cannot mark a field "edited" itself. Server side unchanged (`_bounds` / `_capped`; plain editable number inputs). Not exercised: a real browser (none available to me); the stub covers `f.kind`, `f[name]` and `form.dataset`.
- **S6 ceilings and row shape: PASS.** Direct calls with 1e30 actions/probes and 1e300 / 1e308 wall return `GrantBounds(2000, 40000, 86400.0)`. The `RunApproval` model is not touched (diff is additions in `schema/approval.py`), and the new CLI test asserts `is_signed_and_verified`.

## Mode B attempts
1. Exceed 2000 / 24h / 40000 through derived values: not achievable (all clamped, fuzz above).
2. Overflow / negative / NaN, **calling `derive_grant_bounds` directly (no caller reaches these today):**
   - `schema/approval.py:87`: wall >= ~1.44e308 makes `wall_clock_s * 1.25` equal `inf`, and `math.ceil(inf)` raises `OverflowError` (the `isfinite` guard checks the input, not the product). `(5, 5, 1.7e308)` -> `OverflowError`.
   - `schema/approval.py:86-89`: negatives are not clamped at zero: `(-5, -5, -5.0)` -> `GrantBounds(-6, -5, -6.0)`.
   - NaN / inf wall pass through unchanged, as S1 says. The contract line 275 "positive and finite" holds for everything the derive-from-cases path can produce (`action_cost >= 1`; `probe_request` and `wall_clock_request_s` are non-negative sums). Latent, non-blocking.
3. Empty case set: `derive_live_case_grant([])` returns `(0, 1, 0.0)`; both real callers guard it (`run_gates.py:110` `if cases`, `ui/routes_credentials.py:195` `if not cases`), so the old 200/200/600 defaults apply. A zero-step case costs 1.
4. CLI signs a value it did not print: no. The note lists only the omitted bounds, a typed bound is the operator's own, and the no-cases fallback says it is using defaults.
5. Derived grant fails the gate it was sized for: only when the PLAN itself exceeds a ceiling (F1).

## Findings (none blocking)
- **F1 (low, UX; manifest judgement call 4 confirmed): an over-ceiling plan loops without saying why at the grant step.** One 2100-step case: the refusal hint prints `--max-actions 2000 --max-probes 40000 --wall-clock 21057.0`; `approve` with flags omitted prints "derived from 1 planned case(s), with margin: 2000 actions, 40000 probes, 21057s wall clock" and signs it (exit 0); the run is then refused with `narrower than this run - actions 2100 > approved 2000` and the SAME hint. The 2000/24h ceiling held (D-112 keeps it as the emergency brake), so this is not a safety defect, but `run_gates.py:121-122` / `cli_crawl.py:175-179` could say "clamped to the 2000-action ceiling; the plan needs N". Suggested follow-up, not required for PASS.
- **F2 (info): latent edges in `derive_grant_bounds`** (`schema/approval.py:86-89`): OverflowError above ~1.4e308 wall, negatives unclamped. A `max(0, ...)` and a finite-product check would make it total.
- **F3 (info): D-112 `Changes-authorized` does not name `stages/run_gates.py`** (it lists schema/approval.py, core/consent.py, cli_crawl.py, "the UI approval grant route and view"). The new helpers are at `run_gates.py:86-122` and the form wiring in `ui/routes_credentials.py`. Neither is an enforcement path and no ARCHITECTURE prose changed, so I read it as inside item 2's intent; flagged for whoever closes D-112.
- **F4 (info): test docstring drift.** `tests/test_auto_size_budget.py:3` names `core.consent.derive_grant_bounds`; the function lives in `schema.approval`.

## Classification of the red test: `tests/test_crawl_real_cli.py::test_the_refusals_command_grants_the_run_once_a_human_fills_it_in` ("No such option: --standing,")
Same command (`pytest tests/test_crawl_real_cli.py -o addopts=`) in each tree:

| commit | worktree | result |
|---|---|---|
| master e74664f8 | `.claude/worktrees/base-e74664f8` | 7 passed |
| feat/d111-standing-approval d20eb037 | `.claude/worktrees/d111-standing` | 1 failed, 6 passed (`No such option: --standing,`) |
| fix/consent-followups 077b7fb9 | `.claude/worktrees/consent-followups` | 1 failed, 6 passed (same) |
| fix/auto-size-budget 975fafbb | this tree | 1 failed (same); the other 89 in that group pass |

**Introduced by `e35066ad feat(consent): D-111 standing (until-revoked) crawl approvals`** (`git log -S"or --standing, until revoked" -- src/autotester/core/consent.py`), which appends ` (or --standing, until revoked)` to the CRAWL hint; the test `shlex`-splits the printed command and passes `--standing,` to the CLI. d20eb037 contains that commit, master e74664f8 does not (`merge-base --is-ancestor` is false for master). So it is **pre-existing relative to this branch, not caused by it, and will turn master red when D-111 merges.** This branch does not touch that hint text (the `_grant_command` diff changes only the bounds block). The fix belongs to the D-111 line: have the test strip the parenthetical, or print the alternative on its own line.

## Closing
PASS. S1-S6 all hold; the adversarial probes found no safety-relevant defect; F1-F4 are advisory or latent. The red test is a D-111 carry-over, not this unit's. No merge, no push, no edit to src, tests or contracts.
