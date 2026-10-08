# Manifest — t152-ai-check-registry
**Contract:** qa/contracts/ai-target.md (AI2, AI3, AI4, AI5 bind T-152) · qa/contracts/catalog.md CT7 · core-invariants C1/C2/C3
**Goal task:** T-152 (deps T-151 done, T-125 done)
**Date:** 2026-10-07
**Fix cycle:** 0
**Dual check:** not required (Tier S: no security, auth, data-write, concurrency, config or dependency surface)
**Persona walk:** skip (backend-only: no human screen; Track C registry)
**Issues addressed:** none
**Executor:** claude-sonnet-subagent (maker, worktree .worktrees/t152-153, branch t152-153)
**Relitigation:** `uv run autotester ledger relitigation "T-152 ..."` → "no gate — no retired features (rule)". No HUMAN_GATE.

## What changed
- `src/autotester/schema/ai_check.py` (new, 31 lines) — `AiCheckKind` (5 members) and `AiCheckMethod` (computed | judged), closed enums. Reason for a new module: D-017 names `schema/ai_check.py` for exactly this; it holds no `Catalog`/`BlockedReason`.
- `src/autotester/schema/catalog.py` (138 → 178, edited in place) — `AiCheckEntry` (reuses `BlockedReason` and `Tier`; a validator makes "applicable and not runnable" carry both a reason and an action, and no other state carry either) and `Catalog.ai_checks` plus `ai_check()`, `ai_runnable_count`, `runnable_ai_in_tier()`. Additive, same precedent as `Catalog.packs`; `entries` and CT2 are untouched.
- `src/autotester/stages/ai_catalog.py` (new, 103) — `CHECKS_BY_KIND` literal dict (kind → checks), `CHECK_METHOD`, `CHECK_TIER` literals, `resolve_kind` (exact member or plain `str` equal to a value, else `UnclassifiedTarget`), `match(target, base) -> Catalog`. Reason for a new module: D-017 names `stages/ai_catalog.py`; plan §5B has `match` there.
- `tests/test_ai_catalog.py` (new, 28 cases).
- `docs/MAP.md` regenerated (`autotester map`).

Design choices a checker should know:
1. **`match(target, base)` takes the project's own `Catalog` and returns it extended**, instead of `match(target) -> Catalog` building a second one. This is how "never a second Catalog" (CT7/AI4) holds structurally; the web `entries`/`packs` pass through unchanged and the input is not mutated.
2. **AI3 refusal is an exception, `UnclassifiedTarget`, not a `BlockedReason`.** `BlockedReason` is closed at six values (CT3, D-039) and none of them says "kind unknown"; adding a seventh is a D-039 amendment. The contract says "a real member's exact entry, or a named BlockedReason-shaped refusal"; this is the named refusal, as an error that echoes no input text. **[ASSUMPTION — flag to checker: if a literal `BlockedReason`-valued row is required, that needs a CT3 amendment first.]**
3. A non-AI target (`not_ai_target=True`) lists all five checks as `applicable=False` with no reason (the `PackEntry` "not applicable" convention). An unclassified target (kind `None`, not flagged non-AI) is refused.
4. Blocked reason precedence is endpoint first (`no_live_endpoint`), then ground truth (`no_ground_truth`, only for `ground_truth_answer`). One reason + one action per row (CT8 shape); both texts name the target's `root_path`.
5. The concrete five checks, their tier (computed → static, judged → behavioural) and method are my choice inside D-017's "kind → checks is a table in code"; the contract fixes none of them. Adding or dropping a check is a one-literal edit.

`docs/ARCHITECTURE.md` is not edited: it is at its 150-line cap and ARCHITECTURE prose changes need a DECISIONS entry naming the section; D-017 authorizes the concept→file rows but there is no room. The module map in `docs/MAP.md` is the generated record.

## Verification scope
Policy-Version: proportional-verification/2026-10-07.7
Tier: S (single new stage + additive schema edit; no security/auth/data-write/concurrency/config/deps surface; `schema/catalog.py` is a shared module but the edit is additive and defaulted, so a checker may promote to M)
Base SHA: 3adc00d8 (origin/master, T-125 merged)
Gate answers: none required. `qa/gates/t151-dependency-authorization.md` (answered A) covers T-151 only; T-152 adds no dependency, prompt file or provider hunk.
Affected tests: `tests/test_ai_catalog.py` (28) plus the catalog neighbours that read the edited schema: `tests/test_catalog.py`, `tests/test_catalog_packs.py`, `tests/test_ui_catalog.py`, `tests/test_schema.py`. No full suite (suite_runs=0).
Metrics: start=2026-10-07 end=unavailable wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=9 cycle=0 resumes=0 tokens=unavailable policy=2026-10-07.7

## How to verify (commands + expected)
- `uv run pytest tests/test_ai_catalog.py -m "not harness"` → 28 passed
- `uv run pytest tests/test_ai_catalog.py tests/test_catalog.py tests/test_catalog_packs.py tests/test_ui_catalog.py tests/test_schema.py -m "not harness"` → 93 passed
- `uv run ruff check src tests scripts` → All checks passed
- `uv run autotester doctor` → one violation, `ledger-row-missing: T-125`, which is on base 3adc00d8 and not in this diff (T-125 closed without a FEATURES row); nothing else
- `grep -rn "class Catalog" src/autotester/schema/` and `grep -rn "class BlockedReason" src/` → one hit each (also asserted by `test_there_is_one_catalog_and_one_blocked_reason_in_src`)

## Capability coverage and falsification
Each row: a throwaway copy of the tree outside the worktree, baseline asserted green (28 passed), one anchored single-hunk mutation (anchor counted exactly once, file changed), the run, then the failing node attributed by name, then restored (28 passed). Harness output: `.work` not used; transcript kept in the maker's scratch and summarised here.

| Criterion | claim | defending test | the falsifying edit | mutant result |
|---|---|---|---|---|
| AI2 | each kind returns exactly its own table entry | `test_every_target_kind_has_exactly_its_literal_entry`, `test_match_returns_exactly_the_tables_checks_for_each_kind[agentic]` | AGENTIC row gains `_HANDOFF` | 2 failed, both named nodes |
| AI2 | no model call on the selection path | `test_no_model_call_sits_in_the_registry` | `import Provider` added to `ai_catalog.py` | 1 failed, named node |
| AI3 | text is never normalised into a kind | `test_an_out_of_table_kind_is_refused_never_mapped[...]` | `resolve_kind` strips and lower-cases | 3 failed (`CONVERSATIONAL`, `agentic `, `hybrid` subclass) |
| AI3 | a lying `str` subclass cannot select a kind | same node, `[hybrid]` param | `type(raw) is str` → `isinstance(raw, str)` | 1 failed, `[hybrid]` |
| AI3 | an unknown kind has no fallback check set | same node + `test_an_unclassified_target_is_refused_but_a_non_ai_target_has_no_checks` | the refusal replaced by `return AiTargetKind.HYBRID` | 13 failed, both named nodes |
| AI5 | missing ground truth blocks and names the fixture | `test_no_ground_truth_blocks_only_the_ground_truth_check` | the ground-truth branch of `_blocker` → `if False:` | 1 failed, named node |
| AI5 | a blank/absent endpoint blocks, endpoint reported first | `test_both_missing_reports_the_endpoint_first_and_a_blank_endpoint_counts_as_missing` | `.strip()` check → `endpoint is None` | 1 failed, named node |
| AI5 | a blocked row without a reason cannot exist | `test_a_blocked_entry_without_a_reason_cannot_be_built` | `AiCheckEntry` validator body → `if False:` | 1 failed, named node |
| AI4/CT7 | the web rows pass through; one Catalog | `test_match_extends_the_projects_catalog_without_touching_its_web_rows` | `match` drops `entries=base.entries, packs=base.packs` | 1 failed, named node |

Also asserted, not separately mutated: AI3 refusal does not echo the poisoned string; a classifier returning a poisoned kind is stopped in `classify_target` (existing `ValueError`) before `match` (`test_a_classifier_returning_a_poisoned_kind_never_reaches_match`); CT7 grep-in-test; purity (same inputs → same JSON, input unmutated).

## Live browser evidence
Not UI-touching. No page or route changed (`schema/ai_check.py`, `schema/catalog.py`, `stages/ai_catalog.py`, one test file, `docs/MAP.md`). The existing `/projects/{slug}/catalog` page reads `entries` only and is unchanged (`tests/test_ui_catalog.py` green).

## Not done / handed on
- No wiring: nothing calls `match()` yet (T-153 consumes the check kinds; a report/UI surface is T-155).
- No `docs/ARCHITECTURE.md` row (see above).
- No `.goal/goal.json` / ledger edit: closing T-152 is the checker's.

## Closeout
Cycle0 independent PASS by `/root/check_t152` is preserved in qa/verdicts/t152-ai-check-registry.md and its matching checkpoint. Merged release attribution PASS by `/root/t152_release_integration` is qa/verdicts/t152-release-integration.md: checked cc4743e6, own114 affected passed, lint/doctor clean, one complete full-suite instrument initial RED with three unchanged-origin failures outside T152. This is not a clean-suite/live/deployment claim. Original ai_check.py whole hash differs because unjudged T153 types were removed; only judged enum ASTs and applicable inputs are identical. T153 is absent and not accepted.

## Status: checked-PASS
