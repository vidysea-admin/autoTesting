# Manifest — t175-prompt-skills
**Contract:** qa/contracts/skills.md (SK1-SK4)
**Goal task:** T-175
**Date:** 2026-09-25
**Fix cycle:** 1 of 3
**Dual check:** no (T-175 `base_criticality`/`criticality`: medium)
**Issues addressed:** none
**Executor:** claude-sonnet-subagent
**Executor rationale:** schema/behaviour-preserving migration touching the shared provider seam
(`providers/base.py`) and four call sites, with a byte-identical-rendering criterion (SK3) — the
kind of unit where a wrong loader silently changes what every model call sees; kept on a Claude
subagent rather than delegated.

## What changed

- `git mv` (history-preserving) the four migrated prompts into Agent-Skills folders, then
  prepended YAML frontmatter (`name` + `description`) to each, body left byte-for-byte the
  original prompt text:
  - `src/autotester/prompts/grade_v1.md` → `src/autotester/skills/grade/SKILL.md`
  - `src/autotester/prompts/expand_case_v1.md` → `src/autotester/skills/expand-case/SKILL.md`
  - `src/autotester/prompts/video_issues_v1.md` → `src/autotester/skills/video-issues/SKILL.md`
  - `src/autotester/prompts/ingest_video_v1.md` → `src/autotester/skills/ingest-video/SKILL.md`
  - Location chosen per the contract's own suggestion (`src/autotester/skills/<name>/SKILL.md`),
    a sibling of the existing `prompts/` tree — ships with the code, same as `prompts/` always did.
- `src/autotester/providers/base.py` — added ONE module-level function,
  `load_skill_prompt(skill: str, *, skills_dir: Path | None = None) -> str` (bottom of file,
  after `Provider.record`), plus `_FRONTMATTER_RE` and an `import re`. This is the ONE reader of a
  migrated `SKILL.md`'s body — the loader the four stages below call before handing the rendered
  prompt to `Provider.see_video`/`act`/`judge`. Kept strictly additive per the dispatch note: no
  line inside `class Provider` (including `record()`) was touched, to stay out of the sibling
  T-172 worktree's concurrent edit to the same file.
- `src/autotester/core/paths.py::RepoDocs` — added `skills_dir` (constructor param +
  property), mirroring the existing `prompts_dir` override shape (AT-137) exactly: ships with the
  code, an explicit override wins, `root` alone still resolves under it. This is what lets a test
  substitute a stub skills tree the same way `prompts_dir=` already let one substitute a stub
  prompts tree — not a second prompt-resolution mechanism, just the existing "which directory"
  seam extended to the new tree.
- `src/autotester/stages/grade.py:23,44` — `PROMPT_NAME = "grade_v1.md"` → `SKILL_NAME = "grade"`;
  `build_grade_prompt` now calls `load_skill_prompt(SKILL_NAME, skills_dir=docs.skills_dir)`
  instead of `(docs.prompts_dir / PROMPT_NAME).read_text(...)`.
- `src/autotester/stages/expand.py:17,81` — same shape, `SKILL_NAME = "expand-case"`.
- `src/autotester/stages/ingest.py:31,50` — same shape, `SKILL_NAME = "ingest-video"`.
- `src/autotester/stages/analyze_video.py:35-46,77` — `PROMPT_NAMES` tuple (cache-key strings,
  persisted in `ModelObservation.prompt_name`) is UNCHANGED on purpose — an existing project's
  cached observations must keep matching. Added `SKILL_NAMES` dict mapping each cache-key string
  to its new skill folder; `build_chunk_prompt` now calls
  `load_skill_prompt(SKILL_NAMES[prompt_name], skills_dir=docs.skills_dir)`.
- Pre-existing tests that asserted the OLD `prompts_dir` location for these four prompts, updated
  to assert the new `skills_dir` location (same properties asserted — file exists, file is read
  from disk not built inline, placeholders present, cache invalidates on edit — only the path
  changed): `tests/test_grade.py` (G5), `tests/test_ingest_persist.py`, `tests/test_analyze_video.py`
  (`test_both_prompts_exist_and_carry_the_placeholders`), `tests/test_analyze_cache.py`
  (`EditablePrompts` → `EditableSkills`, overriding `skills_dir` and writing `SKILL.md` stubs
  instead of raw `.md` files).
- `tests/fixtures/golden_prompts/{grade,expand-case,video-issues,ingest-video}.md` — new. Captured
  via `read_text()` from the four `prompts/*.md` files BEFORE the `git mv`, at base commit
  `a953bc5` — the SK3 byte-identity oracle (see test file below).
- `tests/test_prompt_skills.py` — new. T-175's `done_check`
  (`uv run pytest tests/test_prompt_skills.py`). 16 tests covering SK1-SK4 (see Capability
  coverage).

**Out of scope, untouched (contract no-fire list):** `relitigation_v1.md`, `agent_fix_v1.md`, and
their readers (`ledger/relitigation.py`, `stages/agent_loop.py`) — still read via
`docs.prompts_dir` exactly as before.

**Note for the checker — core-invariants C8 tension, not a violation.** C8's prose says "Prompts
live in `src/autotester/prompts/*.md`"; this unit moves four of six prompts out of that path
under D-041/this contract's own explicit authorization (skills.md's grounding cites D-041 §1 and
CLAUDE.md's broader "prompts are files, not inline strings" principle, not C8 literally). C8's own
stated **Verify** clause (`grep -rE "^(import|from) (anthropic|google)" src/autotester/stages/`)
never actually tested the `prompts/*.md` path, so nothing mechanical regresses; flagging this
explicitly so it reads as a scoped, contract-authorized supersession for these four files rather
than an unnoticed drift. `relitigation_v1.md`/`agent_fix_v1.md` still satisfy C8's prose exactly.

## How to verify (commands + expected)

- `uv run pytest tests/test_prompt_skills.py` → expect exit 0, all tests pass (T-175 `done_check`).
- `uv run pytest tests/test_grade.py tests/test_expand.py tests/test_ingest.py tests/test_ingest_persist.py tests/test_analyze_video.py tests/test_analyze_cache.py` → expect exit 0 (the pre-existing tests this unit's code change touches).
- `uv run ruff check src tests scripts` → expect exit 0.
- `uv run autotester doctor` → expect exit 0.
- Full `uv run pytest` — see RAM note below (not run this cycle).

## Actual outputs (from maker's own run)

```
$ uv run pytest tests/test_prompt_skills.py
................                                                         [100%]
16 passed in 4.82s

$ uv run pytest tests/test_grade.py tests/test_expand.py tests/test_ingest.py tests/test_ingest_persist.py tests/test_analyze_video.py tests/test_analyze_cache.py
........................................................................ [ 88%]
.........                                                                [100%]
81 passed in 5.46s

$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester doctor
doctor: clean
```

**RAM RULE — FULL SUITE NOT RUN this cycle.** Measured once (not polled — both conditions were
unambiguously unmet, not borderline): `Get-CimInstance Win32_OperatingSystem` FreePhysicalMemory
= **1.90 GB free**, below the 3.5 GB floor; `Get-CimInstance Win32_Process` showed an active
`pytest` run from `D:\autoTesting\.worktrees\at110-approval-signing` (live-browser explore tests,
PID 26420 and children) at the same moment. Both gates in the rule are violated at once, not
close to clearing, so this is declared rather than polled for 60 minutes — **checker to run the
full `uv run pytest` when the machine is free.**

## Capability coverage (each new claim -> its isolating falsification)

All four falsifying edits below were made and run in an **isolated copy** of this worktree under
`C:\Users\Lenovo\AppData\Local\Temp\claude\d--autoTesting\dd410a44-7522-428c-9b91-fda96de822cd\scratchpad\at_mutation_t175\wt`
(never the live working tree — C7), driven via
`uv run --project <copy> --directory <copy> pytest tests/test_prompt_skills.py -k <sk>`. Baseline
on the unmutated copy was asserted green first (`16 passed`) before any mutation, per C7's
baseline clause. Each mutation was a single-hunk edit to one file, reverted immediately after its
run, with the revert verified byte-identical to the live worktree (Python text-mode compare) and
the full 16-test file green again before the next mutation.

| capability (one line) | the check that covers it | the falsifying edit | observed (pasted runner output) |
|---|---|---|---|
| SK1: each migrated prompt is a valid Agent-Skills `SKILL.md` (frontmatter `name`+`description`, non-empty body) | `test_sk1_each_skill_is_a_valid_agent_skills_folder` (`tests/test_prompt_skills.py`) | deleted the `description:` line from `skills/video-issues/SKILL.md` | before: `4 passed` (parametrized over 4 skills). after: `assert desc and desc.group(1).strip(), "frontmatter 'description' is missing/empty" — AssertionError: frontmatter 'description' is missing/empty` on `[video-issues]`, others unaffected. Reverted; re-run: `16 passed`. |
| SK2: exactly one loader, no stage reads a migrated prompt itself | `test_sk2_no_stage_reads_a_migrated_prompt_by_itself` (`tests/test_prompt_skills.py`) | in `stages/grade.py`, replaced `template = load_skill_prompt(SKILL_NAME, skills_dir=docs.skills_dir)` with `template = (docs.prompts_dir / "grade_v1.md").read_text(encoding="utf-8")` | before: `3 passed` (this test + 2 siblings under `-k sk2`). after: `AssertionError: src\autotester\stages\grade.py still reads a prompt file itself` — named exactly for the reintroduced inline read. Reverted; re-run: `16 passed`. |
| SK3: rendered prompt text is byte-identical to the pre-migration file | `test_sk3_rendered_prompt_is_byte_identical_to_the_pre_migration_file[grade]` (`tests/test_prompt_skills.py`) | changed one word in the body of `skills/grade/SKILL.md` (`"one test case"` → `"ONE test case MUTATED"`) | before: `4 passed` (parametrized over 4 skills, `-k sk3`). after: `AssertionError` on `[grade]` with the diff showing exactly the inserted words (`- ...grading one test case's...` / `+ ...grading ONE test case MUTATED's...`), the other 3 skills still green. Reverted; re-run: `16 passed`. |
| SK4: `{{SECRET:KEY}}` placeholders survive migration unchanged | `test_sk4_secret_placeholders_survive_unchanged[expand-case]` (`tests/test_prompt_skills.py`) | in `skills/expand-case/SKILL.md`, replaced the literal text `{{SECRET:KEY}}` with `the real credential value` | before: `5 passed` (`-k sk4`). after: `AssertionError: assert [] == ['KEY']` — the placeholder-key set the golden carries is no longer produced by the rendered text. Reverted; re-run: `16 passed`. |

## Live browser evidence

**Not UI-touching — no surface changed.** All edits are in `src/autotester/providers/base.py`,
`src/autotester/core/paths.py`, `src/autotester/stages/{grade,expand,ingest,analyze_video}.py`,
`src/autotester/skills/**/SKILL.md`, and `tests/**` — none match the UI-surface glob
(`*.tsx|jsx|vue|svelte|html|css`, `apps/web/**`, `**/routes/**`, `**/pages/**`,
`**/components/**`) and none feed a page's rendered data (these prompts drive model calls that
land in artifacts on disk, not a live UI route). `qa/ui-surfaces.json` unchanged.

## Status: checked-PASS (qa/verdicts/t175-prompt-skills.md, Cycle checked: 1, supervising acceptance dc56cf7)
