# d105-g11-docs — bring the docs in line with Group 11 (T-207..T-220), D-105

Status: merged-no-check (docs-lane)
Fix cycle: 0
Branch: wave/d105-g11-docs (base int/1017 d9a70882)
Lane: docs (only `docs/*.md`, `target.md` and this manifest changed; no `.py`, no `qa/contracts`, no CLAUDE.md, no hook)
Policy-Version: proportional-verification/2026-10-18.15
Tier: S
Authority: D-105 (`docs/DECISIONS.md`, Approved-by Umesh, chat 2026-10-18 "haan, docs update kar"), appended with `scripts/append_decision.ps1`; Changes-authorized names exactly two `docs/ARCHITECTURE.md` sections.
Dual check: no (docs only)

## What changed
- `docs/DECISIONS.md`: D-105 appended through the safe-door (`APPENDED: D-105 | type: decision | status: ACTIVE`). Links T-207..T-220. Nothing REJECTED or SUPERSEDED is revived; the decision index held no REJECTED entry about G11 (`grep -nE 'status: REJECTED' docs/DECISIONS.md` returned no line).
- `docs/ARCHITECTURE.md` (still 150 lines, the `ARCHITECTURE_MAX_LINES` budget): "Concept -> file" gains two rows (multi-role data shapes, **built**, T-207; multi-role runtime, oracles, leak evidence, onboarding, **planned**, T-208..T-220) and the "Closed vocabularies" row now names `schema/multi_role_enums.py`; "Commands" has two pairs of lines merged to stay inside the budget (no command removed). No other section touched; no generated section hand-edited.
- `docs/spec.md`: requirements R66-R89 (each cites its MP criteria and unit; R66-R68 marked shipped, the rest target), Group 11 user types (`onboarder`, `lead`, `dev`, `benchmark-owner`), screens M1-M4, flows F8-F10, flow-to-user-type rows, Group 11 out-of-scope bullet; header says R1-R89.
- `docs/plan.md`: "Group 11 build units" (units, files N/E, tier, dependencies, waves W1-W7, file ownership, five credential/human gates, risks), slice S8, a gates pointer in "Held / blocked", header status.
- `docs/intent.md`: pointer to O16-O21 in `docs/features/multi-role-platform/intent.md` (one concept, one place: the outcomes are not copied), a user-type pointer and a Group 11 open-questions pointer.
- `target.md`: milestone M13 (T-207 `[x]`, T-208..T-220 `[ ]`, the live legs MP34 and MP35 `[!]`). The hand-copied "Progress" count line is left untouched.
- `docs/SNAPSHOT.md`: regenerated with `autotester snapshot` (its decision index gained D-105); `autotester map` regenerated `docs/MAP.md` with no diff. Neither was hand-edited.

## Truth check (claims against code that exists on int/1017)
- Built: only T-207. `ls src/autotester/schema | grep -E 'platform|role|mailbox|multi'` -> `mailbox_ref.py multi_role_enums.py platform.py platform_link.py role_account.py`; `Project.platforms`, `platform_links`, `role_accounts`, `effective_platforms` at `src/autotester/schema/project.py:226-262`.
- Not built: `ls src/autotester/stages | grep -E 'oracle|multi_role|platform_links|role_onb|leak|finding_prio|report_banner|cross_role|ceo'`, `ls src/autotester/sources | grep imap` and `ls src/autotester/ui | grep role` all returned nothing, so every other G11 file is labelled planned.
- `.goal/goal.json`: T-207 `done`, T-208..T-220 `pending` (python read of the file).
- Contract `qa/contracts/multi-role-platform.md` exists on int/1017 (MP1-MP35, MPI1-MPI6); the wave plan's "no contract file" blocker (`.work/g11-wave-plan.md` section 0) is superseded by commit 4df66032.

## Verification (commands run)
- `uv run --directory D:/autoTesting/.worktrees/d105-g11-docs autotester doctor` before regeneration: 2 violations, both generated-doc staleness (`stale-generated` and `stale-committed` for `docs/SNAPSHOT.md`, caused by the D-105 decision index entry). After `autotester map` and `autotester snapshot`: 1 violation, `stale-committed: docs/SNAPSHOT.md`, which clears when the regenerated file is committed. The same doctor on the int/1017 checkout printed no stale or router line. Advisory `decision-citation-*` warnings are the pre-existing non-blocking D-087 set.
- `wc -l docs/ARCHITECTURE.md` -> 150 (budget 150, `src/autotester/ledger/render.py:22`).

## Needs code
- None. Open points for the owner: (1) `CLAUDE.md` router still says "R1-R65" and "O1-O15" (it is outside this unit's allowed files); a one-line update there needs its own authorization. (2) The generated `docs/MAP.md` and `docs/SNAPSHOT.md` will conflict with any other branch that regenerates them; the merge owner regenerates once per merge.
