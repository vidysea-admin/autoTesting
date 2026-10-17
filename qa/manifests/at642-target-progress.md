# at642-target-progress

Status: merged-no-check (docs-lane) candidate
Fix cycle: 0
Issue: AT-642 (qa/issues.jsonl line 639) -- target.md progress line overstated/undated vs .goal/goal.json
Branch: wave/at642-target-progress (base int/1017 head ab99c07d)

## What changed
- target.md:268 heading `89 / 92 done (97%)` dated 2026-10-16 -> `90 / 106 done (85%)` dated 2026-10-18.
- target.md:270 (new line) adds an italic caveat: point-in-time snapshot, hand-copied, no script regenerates it, re-derive before quoting.
- target.md:277-278 reconciliation paragraph said the count "is now derived from .goal/goal.json rather than maintained by hand"; no generator exists (see below), so it now says it is "taken from .goal/goal.json (copied by hand at each update, dated in the heading, AT-642)".

## Verification commands
- `python -c` over .goal/goal.json `tasks`: total 106, status done 90, pending 16 -> 85%. goal.json `progress` = {total:106, done:90, pending:16, percent:85}, `updated` 2026-10-18T03:33:06.
- Generator check: `grep -rn 'target\.md' src scripts .claude` -> only doctor.py:30,35 (root-entry allowlist and its docstring) and unrelated `ai-target.md` contract references. No code writes target.md, so the line is hand-maintained; this is why the dated caveat was chosen over "generated" wording.
- `git diff --stat` -> target.md only, 5 insertions, 3 deletions.

## Needs code
- Optional: a small script (or `autotester map` extension) that regenerates the target.md progress heading from goal.json, so the drift cannot recur. Not done (docs lane).
- Note: target.md milestones list no Group 11 tasks T-208..T-220 (all pending in goal.json); the new count includes them. Roadmap-body coverage of Group 11 is outside AT-642 and untouched.
