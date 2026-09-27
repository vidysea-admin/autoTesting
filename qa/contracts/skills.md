# Contract — skills (prompts as SKILL.md, D-041)

**Status:** ACTIVE (DRAFT->ACTIVE by /checker on T-175's checker PASS, 2026-09-25; qa/verdicts/t175-prompt-skills.md Cycle checked: 1, merged 9b3fd5e). core-invariants C8 prompt-location wording scoped to this migration by D-043.
**Feature:** move the grader, test-design (expand), bug-hunting, and ingest prompts out of the loose
`src/autotester/prompts/*.md` files and into per-skill folders following the Agent Skills open
standard (frontmatter `name` + `description`, a body of instructions, an optional `references/`
subfolder), loaded only through the provider seam — one loader, no inline prompt strings anywhere
else — with the migration behaviour-preserving for every prompt it touches.
**Covers:** goal task T-175. **Deps:** none. **Grounding:** D-041 §1 "Skills: `SKILL.md`" and §6
row T-175 (`docs/DECISIONS.md`); `CLAUDE.md` "Design rules" — "prompts are files, not inline strings";
`providers/base.py::Provider` (the seam every model call already goes through, C8); the current prompt
files this unit migrates — `src/autotester/prompts/grade_v1.md` (grader), `expand_case_v1.md`
(test-design), `video_issues_v1.md` (bug-hunting), `ingest_video_v1.md` (ingest); the current inline
read pattern this unit replaces, e.g. `stages/grade.py:23,44`
(`PROMPT_NAME = "grade_v1.md"` then `(docs.prompts_dir / PROMPT_NAME).read_text(...)` inline in the
stage).

## What it is

Today each stage that needs a prompt reads its `.md` file directly off `core/paths.py::Paths.prompts_dir`
(e.g. `stages/grade.py:44`) — a separate inline read per stage, no shared loader. This unit gives the
four named prompts (grader, test-design/expand, bug-hunting, ingest) a home as `SKILL.md` folders
(the Agent Skills open standard) — the maker judges the right location against `CLAUDE.md`'s "prompts
are files" rule and the existing `prompts/` location (e.g. `src/autotester/skills/<name>/SKILL.md`) —
and introduces exactly ONE loader that every migrated prompt goes through on its way to a `Provider`
call. No stage does its own `read_text` for a migrated prompt after this unit lands; the loader is the
only reader.

## Criteria (SK1-SKn) — each judged on re-runnable evidence

- **SK1 — Four prompts become SKILL.md folders, each in the Agent Skills shape.** The grader
  (`grade_v1.md`), test-design/expand (`expand_case_v1.md`), bug-hunting (`video_issues_v1.md`), and
  ingest (`ingest_video_v1.md`) prompts each get a `SKILL.md` with YAML frontmatter carrying at minimum
  `name` and `description`, a body holding the instructions the current prompt carries, and an optional
  `references/` subfolder for anything the body doesn't need inline. (Falsifiable: each of the four
  target `SKILL.md` files parses as valid frontmatter + body, with `name`/`description` present and
  non-empty.)
- **SK2 — One loader, no inline prompt strings, reached only through the provider seam.** Exactly one
  function loads a migrated `SKILL.md`'s prompt text, and every stage that needs one of the four migrated
  prompts calls that loader rather than reading its own file or embedding prompt text as a Python string
  literal — the loader sits on the path a `Provider.see_video`/`act`/`judge` call already takes (C8), not
  as a second, parallel prompt-resolution mechanism. (Falsifiable: `grep -rn` for
  `read_text\(.*encoding` or an inline triple-quoted prompt string in `stages/` for any of the four
  migrated prompt names returns nothing outside the one loader module; the four stages that used to call
  `stages/grade.py:44`-style inline reads for these prompts no longer do.)
- **SK3 — Behaviour-preserving: byte-identical or a documented, reviewed diff.** For each of the four
  migrated prompts, the text actually sent to the provider after migration is byte-identical to what
  `prompts_dir / "<old-name>.md"` produced today, UNLESS the manifest documents an intentional diff with
  its reason and the diff is reviewed as part of the unit. (Falsifiable: render each migrated prompt
  through the new loader and diff it against a snapshot of the corresponding old `.md` file's rendered
  text taken before the migration; empty diff, or a manifest-documented diff, is the only pass shape —
  an undocumented diff is a fail.)
- **SK4 — Credentials boundary is unchanged (core-invariants C5).** No `SKILL.md` or its `references/`
  content ever carries a raw secret value; secret references stay `{{SECRET:KEY}}` placeholders exactly
  as the migrated prompt carried them, substituted only at `page.fill()` time as today. (Falsifiable: a
  migrated `SKILL.md` whose source prompt contained a `{{SECRET:KEY}}` placeholder → the placeholder
  survives unchanged in the new file; `grep` for a literal secret value in any migrated `SKILL.md` or
  `references/` file returns nothing.)

## Explicit no-fire list (do not raise these as findings)

- The two prompts D-041 does not name for this unit — `relitigation_v1.md` and `agent_fix_v1.md` —
  staying as loose files under `src/autotester/prompts/`; raising "migrate these too" is out of scope
  for T-175 (a later unit may pick them up).
- Any change to WHAT a prompt instructs the model to do — this unit is a location + loading-mechanism
  migration; a content/behaviour change to a prompt is a different unit's concern, gated by SK3.
- Choice of exact `SKILL.md` folder path (e.g. `src/autotester/skills/` vs `prompts/skills/`) — the
  criterion is "one loader, Agent Skills shape, behaviour-preserving", not a specific directory name.
- Adopting more of the Agent Skills standard than frontmatter + body + optional `references/` (e.g.
  bundled scripts/tools) — not claimed by this unit, not required by any criterion here.

## How a unit is verified (adapter slot 1)

`uv run pytest tests/test_prompt_skills.py` (bare, no CLI `-q`, AT-503; this is T-175's `done_check`
in `.goal/goal.json`) + `uv run ruff check src tests scripts` + `uv run autotester doctor`, all exit 0;
each SK criterion carries a capability-coverage row with a single-hunk falsifying edit reproduced
green→red-for-the-named-reason→revert→green. File/function caps (core-invariants C2) apply.

## Amendment log (append-only; git history is the version)

- 2026-09-24 · init · contract authored by /checker as DRAFT, from D-041 (Approved-by Umesh —
  AskUserQuestion answers + plan approval, chat 2026-09-24). No prior draft existed; nothing amended.
- 2026-09-25 · DRAFT->ACTIVE · /checker Mode B sweep, on T-175 checker PASS (qa/verdicts/t175-prompt-skills.md Cycle checked: 1, merged 9b3fd5e), as this contract's own status line pre-authorized; precedent network-assertions.md at the T-170 PASS. No criterion text changed.
