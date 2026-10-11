# HUMAN_GATE: one new module of t198a-zip-drive-intake does two jobs

**Asked:** 2026-10-11 by the maker, on the checker's new-module ruling
(`qa/verdicts/t198a-zip-drive-intake.r2.modules.md`, master 6504de03). **Answered:** pending.

## What is blocked

`wave/t198a-zip-drive-intake` holds a dual-check PASS at dba80100 (cycle 2: A
`qa/verdicts/t198a-zip-drive-intake.r2.a.md` with the full suite, B
`qa/verdicts/t198a-zip-drive-intake.r2.b.md`). It is NOT merged.

The standing new-module rule (D-082 item 1) needs each new module to state one job in its docstring
and the checker to list it. The checker judged all 18 new modules. 17 pass. One does not:

- `src/autotester/ui/intake_upload.py` (143 lines). Its docstring says it is the upload door. It also
  holds five page fragments that the Drive door and `routes_sources` import (`refusal_page`,
  `gate_refusal`, `report_table`, `report_page`, `intake_forms`, the last of which includes the Drive
  link form). Five of its seven functions are presentation, not the upload handler.

No behaviour is wrong: every acceptance criterion is met and `autotester doctor` is clean. This is a
design-rule finding (one concept, one place).

## Why the maker cannot just fix it

The unit has used both allowed fix cycles. A third cycle, even one that only moves functions, is the
owner's decision.

## The question

- **A. Merge as it is, and fix the module in a follow-up unit.** The maker merges at dba80100 and
  files one low issue: move the five fragments and the Drive form into one sibling UI module (for
  example `ui/intake_pages.py`). T-198b, which builds on this code, can start at once.
- **B. Allow a third fix cycle now.** A builder moves the fragments on the branch, then a checker
  re-checks the moved code and the unit merges after that. T-198b waits for it.

Maker's recommendation: A. The finding is about where five small functions live, not about what the
product does, and the follow-up is a pure move that a checker can verify by comparing function bodies.

## Also for the owner to confirm (does not block)

Five of the 18 modules (`sources/drive_errors.py`, `sources/gws_runner.py`, `sources/drive_jobs.py`,
`sources/drive_intake.py`, `ui/intake_gate.py`) are not named by file in the brief or the contract. The
checker counted them as named through D-072 item 2 ("yes to all new modules ... the Group 10 split
modules ... the checker judges it"). If "names it" in D-082 means file names only, say so.

The same reading was used for t200b-scheduled-test, which IS merged (a3c3a324, local only, not
pushed): its two new modules `stages/schedule_gate.py` and `stages/schedule_tick.py` are named by file
in the manifest and in checker B's verdict, but the brief and contract name only their jobs. Both have
one-job docstrings and neither has a caller in `src/` yet (scheduling stays off). Its manifest also
leaves "keep `schedule_gate.py` separate or fold it into `explore_consent.py`" as your ruling. If you
do not accept this reading, the merge is undone with `git revert -m 1 a3c3a324`.
