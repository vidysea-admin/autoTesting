# Verdict — t175-prompt-skills

**Cycle checked:** 1
**Contract:** qa/contracts/skills.md (SK1-SK4)
**Manifest:** qa/manifests/t175-prompt-skills.md
**Checker:** Mode A, fresh context, read-only toward code/tests/manifest, worktree
`D:/autoTesting/.worktrees/t175-prompt-skills` (HEAD 3cd919d, branch wave/t175-prompt-skills)

## VERDICT: PASS

## SCOREBOARD

- Diff matches "What changed": yes — `git diff --stat -M` against merge-base `a953bc5` shows exactly
  the files the manifest names, with the 4 old `prompts/*.md` files detected as `R100` renames into
  `tests/fixtures/golden_prompts/*.md` (git's 100%-match heuristic; functionally they are deletions
  from `prompts/` plus new golden fixtures, matching the manifest's "git mv into skills/, capture golden
  before" story). No unrequested deletion/rename of any existing function/class/export/route/test/config
  key found.
- SK1-SK4 capability coverage: 4/4, each independently reproduced in a throwaway copy (see below).
- `tests/test_prompt_skills.py`: 16 passed (re-run, matches manifest).
- Pre-existing affected suites (`test_grade.py test_expand.py test_ingest.py test_ingest_persist.py
  test_analyze_video.py test_analyze_cache.py`): **65 passed** (re-run) — manifest's pasted "81 passed"
  does not match; see PROPOSED FINDINGS.
- `uv run ruff check src tests scripts`: All checks passed.
- `uv run autotester doctor`: doctor: clean.
- Checker-bar non-browser suite: **1503 passed, 5 skipped, 0 failed** (see NON-BROWSER SUITE).
- Prompt equivalence (SK3): all 4 migrated prompts byte-identical to their pre-migration
  `prompts/*.md` source at the merge-base, independently re-derived (not just re-reading the manifest's
  claim).
- Loader fallback: no silent fallback — missing skill raises `FileNotFoundError`; malformed frontmatter
  raises `ValueError` naming the path and "frontmatter" (SK1 wording).
- C8/D-041: D-041 §1 ("Skills: `SKILL.md`") and §6 row T-175 ("prompts become `SKILL.md`") do authorize
  this migration; C8's prose is stale for these 4 files only. Ruling below; proposed amendment text
  included.
- Merge risk: real, concrete semantic conflict in `grade.py`/`expand.py`/`ingest.py` between this unit
  and the concurrent T-172 worktree (T-172 references the `PROMPT_NAME` constant this unit renamed to
  `SKILL_NAME`). Noted for the merge step, not charged against this unit.
- UI: no UI-surface path touched; `qa/ui-surfaces.json` unchanged. LIVE-BROWSER not-applicable.

## FAILURES

None at >80% confidence. (One manifest-accuracy discrepancy is recorded under PROPOSED FINDINGS, not
FAILURES — it does not change any SK criterion's outcome: the tests genuinely pass, just fewer of them
than claimed.)

## CAPABILITY-COVERAGE: 4/4

Reproduced in a throwaway copy (`shutil.copytree` with the specified ignore patterns, `uv sync`,
baseline asserted green — `16 passed` — before any mutation), each a single-hunk edit to exactly the
file/line the manifest named, reverted and re-verified green + byte-identical to the live worktree
after each row.

| row | falsifying edit | before | after (named assertion) | revert |
|---|---|---|---|---|
| SK1 | deleted `description:` line from `skills/video-issues/SKILL.md` | `16 passed` (baseline) | `1 failed, 3 passed` — `AssertionError: frontmatter 'description' is missing/empty` on `[video-issues]`, exactly the assertion the manifest named | `16 passed` |
| SK2 | `stages/grade.py`: `load_skill_prompt(...)` → `(docs.prompts_dir / "grade_v1.md").read_text(encoding="utf-8")` | `3 passed` (`-k sk2` baseline) | `1 failed, 2 passed` — `AssertionError: src\autotester\stages\grade.py still reads a prompt file itself` | `16 passed` |
| SK3 | `skills/grade/SKILL.md` body: `"one test case"` → `"ONE test case MUTATED"` | `4 passed` (`-k sk3` baseline) | `1 failed, 3 passed` — byte-diff shown exactly on `[grade]`, other 3 skills green | `16 passed` |
| SK4 | `skills/expand-case/SKILL.md`: `{{SECRET:KEY}}` → `the real credential value` | `5 passed` (`-k sk4` baseline) | `1 failed, 4 passed` — `AssertionError: assert [] == ['KEY']` | `16 passed` |

All four match the manifest's claimed observed output exactly (assertion text, pass/fail counts).

## NON-BROWSER SUITE

`BROWSER=$(grep -lE "playwright|chromium|sync_playwright|BrowserSession\(|launch_browser|browser_session" tests/*.py | sort)`
found 20 files (18 of them `test_*.py`, plus `conftest.py`/`crawl_fake.py` which are not test files and
don't count against the `test_*.py` total). `NONB` = 154 total `test_*.py` files − 18 browser-touching
= **136 files**.

`uv run pytest $NONB -p no:randomly` (background, ~4 min): **1503 passed, 5 skipped, 0 failed**, exit 0.
No failures, so no master comparison needed.

## PROMPT EQUIVALENCE

Independently re-derived (not re-reading the manifest's claim): loaded each migrated prompt through
`load_skill_prompt()` in the live worktree and diffed against `git show <merge-base>:src/autotester/prompts/<old-name>.md`.

- grade: **identical** (1359 chars both sides)
- expand-case: **identical** (1114 chars both sides)
- ingest-video: **identical** (2673 chars both sides)
- video-issues: **identical** (4042 chars both sides)

Loader fallback behaviour (`src/autotester/providers/base.py:121-145`, `load_skill_prompt`):
- Missing skill folder/file → `path.read_text()` raises `FileNotFoundError` (verified directly:
  `load_skill_prompt('nonexistent-typo')` → `FileNotFoundError: [Errno 2] No such file or directory`).
- SKILL.md present but no leading `---`...`---` frontmatter block → `_FRONTMATTER_RE.match()` returns
  `None` → the loader raises `ValueError` naming the path and "Agent Skills shape, SK1".
- No code path returns an empty string or swallows either exception. No silent fallback exists.

## C8 / D-041 JUDGEMENT

**C8 quote** (`qa/contracts/core-invariants.md:134-135`): "All model calls go through
`providers.base.Provider`. No stage imports a vendor SDK directly. Prompts live in
`src/autotester/prompts/*.md` as versioned files, never inline string literals."

**D-041 quote** (`docs/DECISIONS.md:885-889`, point 1 "Framework layers"): "Skills: `SKILL.md`." And
(`docs/DECISIONS.md:900-905`, point 6 table): "T-175 | prompts become `SKILL.md` | none". D-041's
**Changes-authorized** section (`docs/DECISIONS.md:923-928`) does not explicitly list `qa/contracts/
core-invariants.md` among files it authorizes changing — it authorizes `.goal/goal.json`,
`tests/test_goal_done_checks.py`, `pyproject.toml`, "New checker-authored DRAFT contracts under
`qa/contracts/`" (which is how `skills.md` itself came to exist, per its own amendment log: "contract
authored by /checker as DRAFT, from D-041"), and one line in `docs/ARCHITECTURE.md`.

**Ruling: D-041 does authorize the migration itself** (point 1 names `SKILL.md` as the skills layer;
point 6's table explicitly assigns "prompts become `SKILL.md`" to T-175, with no stated dependency,
i.e. unconditionally authorized) — so this unit does not contradict C8 without authorization; the
manifest's "not a violation" framing for the *migration* is correct. But D-041 authorizes moving the
**prompts**, not editing **C8's own text** — and it does not need to: D-041 is a later, more specific
authorization than C8's general prose, so C8's "prompts live in `prompts/*.md`" is now stale exactly for
these four files, not violated by them. This is a **PROPOSED CONTRACT AMENDMENT**, not a fail:

> Proposed amendment to `qa/contracts/core-invariants.md` C8, to be made by `/checker` (never by the
> maker): scope the "Prompts live in `src/autotester/prompts/*.md`" line to name the exception —
> "...except the four prompts D-041/T-175 moved to `src/autotester/skills/<name>/SKILL.md` (grader,
> expand-case, ingest-video, video-issues); `relitigation_v1.md` and `agent_fix_v1.md` remain under
> `prompts/*.md` until a later unit migrates them." This is a scoping clarification (routine gate, per
> the pattern of every other C8/C-series amendment in the log) — it authorizes what D-041 already
> authorized in fact, and does not weaken the invariant that a prompt is a file, never an inline string.

The manifest's own framing ("not a violation... C8's own stated Verify clause never actually tested the
`prompts/*.md` path, so nothing mechanical regresses") is accurate as a description of why nothing
currently breaks, but is not itself a substitute for the amendment — the checker is the contract writer,
per this dispatch's step 7, and the amendment above is offered for that purpose.

## MERGE-RISK NOTE

`providers/base.py`: **no line-level conflict.** T-172's worktree (`D:/autoTesting/.worktrees/
t172-run-trace`, merge-base `6d849d9`) edits *inside* `class Provider` — `__init__` (adds
`self.trace`), the `see_video`/`act`/`judge` signatures (adds `prompt_file`/`fed_id` kwargs), and
rewrites `record()`'s body. T-175 adds strictly *after* `record()` (this worktree's lines 105-145: the
`_FRONTMATTER_RE` regex and `load_skill_prompt()`), touching no line inside `class Provider` — confirmed
by direct diff comparison of both worktrees against their respective merge-bases. A textual merge of
`base.py` should apply cleanly.

`grade.py` / `expand.py` / `ingest.py`: **real semantic conflict, not just textual.** T-172 adds calls
like `judge.judge(prompt, Judgment, images=seen, prompt_file=PROMPT_NAME, fed_id=result.case_id)` /
`provider.act(prompt, ExpandedSteps, prompt_file=PROMPT_NAME, fed_id=flow.id)` /
`provider.see_video(..., prompt_file=PROMPT_NAME, fed_id=source.id)` — all three reference the
module-level `PROMPT_NAME` constant. T-175 **renames that constant to `SKILL_NAME`** in all three files
(`grade.py:23`, `expand.py:17`, `ingest.py:31`) and removes `PROMPT_NAME` entirely. A merge of these two
branches will either textually conflict (adjacent-line edits in the same function) or, worse, merge
cleanly and leave `PROMPT_NAME` referenced but undefined — a `NameError` at call time, not caught by
either unit's own tests since neither branch sees the other's edit. Whoever merges T-172 and T-175 must
update T-172's `prompt_file=PROMPT_NAME` references to `prompt_file=SKILL_NAME` (or another suitable
cache-key string) by hand.

`analyze_video.py`: **low risk.** T-172 edits `observe_chunk`'s call to `provider.see_video(...,
prompt_file=prompt_name, fed_id=source.id)` using the lowercase **local parameter** `prompt_name`
(the cache-key string, e.g. `"grade_v1.md"`) — unrelated to T-175's `SKILL_NAMES` dict or the
`PROMPT_NAMES` tuple, which T-175 deliberately left unchanged for exactly this reason (cache-key
stability). The two units' edits are also in different line regions (T-175: lines ~35-46 constants and
line 88 `build_chunk_prompt`; T-172: line ~108-111 inside `observe_chunk`). Should merge cleanly.

## LIVE-BROWSER

Not-applicable. Changed paths: `src/autotester/providers/base.py`, `src/autotester/core/paths.py`,
`src/autotester/stages/{grade,expand,ingest,analyze_video}.py`, `src/autotester/skills/**/SKILL.md`,
`tests/**`, `qa/manifests/t175-prompt-skills.md`. None match the UI-surface glob
(`*.tsx|jsx|vue|svelte|html|css`, `apps/web/**`, `**/routes/**`, `**/pages/**`, `**/components/**`);
`qa/ui-surfaces.json` unchanged (confirmed by diff against merge-base — no hunks).

## EXPLANATION

All four SK criteria are met with independently re-derived evidence (not just re-running the manifest's
pasted commands): byte-identical prompt rendering, a single additive loader with no silent fallback, all
four capability-coverage mutations reproduce exactly, the full non-browser suite is green (1503 passed),
and D-041 genuinely authorizes the migration (C8's prose is stale, not violated — proposed amendment
above). The unit is scoped correctly: the two out-of-scope prompts and their readers are untouched, and
the old `prompts/*.md` files for the four migrated prompts are confirmed gone with no other module still
referencing them by path.

## VERDICT-COMMIT: (pending — see commit below)

## PROPOSED FINDINGS

- **low · manifest's "Actual outputs" for the pre-existing-suite re-run does not match reality ·
  `qa/manifests/t175-prompt-skills.md:90-93`** — manifest pastes "81 passed in 5.46s" for
  `tests/test_grade.py tests/test_expand.py tests/test_ingest.py tests/test_ingest_persist.py
  tests/test_analyze_video.py tests/test_analyze_cache.py`; re-run by this checker (both combined and
  per-file, `--collect-only` cross-checked) gives **65 passed** (10+13+8+14+13+7), reproducibly. Does
  not change SK1-SK4's outcome — all 65 genuinely pass — but C7 requires "the manifest pastes real
  output, not a summary," and this pasted number does not match a re-run. Fix direction: re-run and
  re-paste before the next manifest, or note if the maker's environment genuinely differed (e.g. a
  stale `.pyc`/collection artifact inflating the count) — worth a one-line root-cause note in the next
  cycle if this recurs.
- **PROPOSED CONTRACT AMENDMENT** (see C8/D-041 JUDGEMENT above) — scope C8's "prompts live in
  `prompts/*.md`" line to name the D-041/T-175 exception for the four migrated prompts. Routine gate.

---

## SUPERVISING CHECKER — PASS accepted · 2026-09-25

Meets the checker bar: all 136 non-browser test files green (1503 passed, 5 skipped, 0 failed),
SK1–SK4 reproduced 4/4 in a throwaway copy, all four prompts byte-identical to their pre-move
prompts/*.md at the merge-base (re-derived through `load_skill_prompt`), the loader fails loudly
(FileNotFoundError / ValueError, no empty-prompt fallback), no UI path changed.

**C8 amendment — deferred, not applied here.** D-041 authorizes the migration itself (point 6:
"T-175 | prompts become SKILL.md"), but its `Changes-authorized` does not name
`qa/contracts/core-invariants.md`. Under this repo's Lab Protocol a contract edit needs an
authorizing DECISIONS entry, so the checker will scope C8's path line via a small routine D-entry
citing D-041, after this unit merges (master must not describe skills that are not there yet).
C8's intent — versioned prompt files, never inline strings — is satisfied by the SKILL.md files.

**MERGE HAZARD with t172 (for the merge step, not charged to this unit):** this unit renames
`PROMPT_NAME` -> `SKILL_NAME` at stages/grade.py:23, expand.py:17, ingest.py:31, while t172 adds
new `prompt_file=PROMPT_NAME` uses at grade.py:173, expand.py:126, ingest.py:262. Resolving the
definition conflict by taking this unit's side leaves t172's call sites referencing an undefined
name -> NameError on every grade/expand/ingest model call. Whichever merges second must convert
those call sites (and decide that `prompt_file` records the skill id), and its merged-tree verify
must include the grade/expand/ingest and trace test files.

Finding filed: AT-563 (low) — the manifest's pasted "81 passed" for the pre-existing suites
reproduces as 65 passed (pasted-output accuracy).
