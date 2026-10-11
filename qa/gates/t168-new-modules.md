# HUMAN_GATE: four new modules in t168-damage-control-report

**Asked:** 2026-10-11 by the maker. **Answered:** 2026-10-11 by Umesh, option C (D-082): a standing
rule. A new module needs no gate when the contract or brief names it, its docstring states one job,
`autotester doctor` is clean and the checker lists it in its verdict. The modules of T-168, T-155,
T-202 and `stages/ai_judge.py` (AT-895) are confirmed by the same entry.

## What is blocked

`wave/t168-damage-control-report` holds a dual-check PASS at 4b93d952 (cycle 2: A
`qa/verdicts/t168-damage-control-report.r2.a.md`, B `qa/verdicts/t168-damage-control-report.r2.b.md`;
full suite on 4b93d952: 3374 passed, 4 failed, none new). It is NOT merged.

The unit's manifest says the owner confirms its new modules before merge:

- `src/autotester/schema/unified_report.py`
- `src/autotester/stages/unified_report.py`
- `src/autotester/stages/unified_report_render.py`
- `src/autotester/ui/routes_unified_report.py`

## The question

- **A. Confirm the four modules.** The maker merges at 4b93d952 (re-checking the sha and the manifest
  lint first) and the checker closes out.
- **B. Do not confirm.** Say which module should fold into which existing file. That is a new build
  cycle, and the fix-cycle cap (2) is already used, so it reopens the unit by your decision.

Maker's recommendation: A. Each module has one job (shape, build, render, route), `autotester doctor`
is clean with them, and folding them into existing files would push those files over the 300-line cap.

## Same gate, more units (added 2026-10-11)

`qa/gates/new-module-authorization.md` says a new module is a human gate and was answered for AT-710
only (D-057, standing rule not chosen). So each of these waits on the same answer:

| Unit | State | New modules |
|---|---|---|
| t155-ai-report | checker PASS at a4308b35 (`qa/verdicts/t155-ai-report.md`), NOT merged | `stages/ai_report.py` |
| t202-any-model-provider | dual check PASS at 94c569c0 (`qa/verdicts/t202-any-model-provider.a.md`, `.b.md`; suite 3444 passed, 6 failed: 4 known, 2 are this unit's own tests failing only because the root `.venv` lacks litellm), NOT merged. Also adds the dependency `litellm==1.104.0` (36 new packages, 12 native wheels) | `providers/litellm_provider.py`, `providers/litellm_schema.py`, `providers/images.py` |
| t198a-zip-drive-intake | dual check running | `ui/upload_stream.py`, `ui/intake_upload.py`, `ui/routes_intake.py`, `ui/intake_gate.py`, `sources/drive_link.py`, `sources/drive_errors.py`, `sources/gws_runner.py`, `sources/gws_drive.py`, `sources/drive_intake.py`, `sources/drive_jobs.py`, `cli_intake.py`, `schema/intake.py`, `core/upload_limit.py` (plus the zip core carried from g3) |
| t204-team-login | building | not known yet |

**C. A standing rule instead of a per-unit gate.** For example: a new module is allowed without a
gate when the unit's contract or brief names it, it has one job stated in its docstring, `autotester
doctor` is clean, and the checker lists it in its verdict; anything else stays a gate. That is a
`docs/DECISIONS.md` entry with `Approved-by: Umesh` and it supersedes the "AT-710 only" scope of D-057.

Maker's recommendation: C. Group 10 is new surface (intake, login, providers), so nearly every
remaining unit adds modules, and a per-unit gate stops each one after its PASS.

## Related, same question, already merged

`src/autotester/stages/ai_judge.py` came in with T-153 (merged 349f3e97) with its confirmation still
open (AT-895). One answer can cover both.
