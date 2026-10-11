# HUMAN_GATE: two new modules of t205-g10-headroom are not named by file

**Asked:** 2026-10-11 by the maker, when the merge step stopped on the new-module rule (D-082 item 1).
**Answered:** pending.

## What is blocked

`wave/t205-g10-headroom` holds a blind dual-check PASS at fb93776b: A
`qa/verdicts/t205-g10-headroom.r1.a.md` (with the one full suite: 4039 passed, 9 failed, none owned
by the unit) and B `qa/verdicts/t205-g10-headroom.r1.b.md`. It is NOT merged. AT-774, the rest of
T-201a, T-199a and T-200, and the local deployment all wait on it.

## The finding

The unit adds 9 files under `src/`. Seven are named by the contract (`qa/contracts/team-foundation.md`),
the brief or a cycle-1 verdict. Two are not named by file there:

- `src/autotester/cli_subapps.py`. Contract TF5 and the brief require this module ("CLI sub-app list
  module, new, name is the maker's choice"), so only the file name was left open. Both cycle-0
  verdicts list it.
- `src/autotester/core/repo_docs.py`. The brief names `RepoDocs` only as a split candidate inside
  `core/paths.py`. The builder moved it to its own module. Cycle-0 checker A listed it as
  "builder-only, needs explicit confirmation" and asked for your confirmation; no answer is on disk.

Both have one-job docstrings, `autotester doctor` is clean, and both checkers passed the unit with
them in place.

## The question

- **A. Confirm both modules and merge at fb93776b.** `cli_subapps.py` is the module the contract asks
  for. `core/repo_docs.py` is a move of an existing class out of a file near the 300-line cap, which
  is the "Group 10 split modules" case of D-072 item 2.
- **B. Refuse `core/repo_docs.py`.** A builder folds `RepoDocs` back into `core/paths.py` (fix cycle 2,
  the last allowed), then a repair check and a new full suite. Roughly half a day on this machine.

Maker's recommendation: A.

## Also yours to rule (does not block the merge)

`Source.origin` is typed two ways on two branches: the closed enum `SourceOriginKind`
(upload, zip, drive, recording) here, and the union `SourceOrigin` in `wave/t198a-zip-drive-intake`
(`schema/intake.py:83`). Whichever merges second conflicts in `schema/project.py`. The checker's
suggestion: the enum stays as the discriminator and the intake models carry the detail.
