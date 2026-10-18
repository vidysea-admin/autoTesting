# Verdict - t209-leak-severity (T-209, G11-3) - coordinator A

**Verdict:** PASS
**Cycle checked:** 0
**Checked state:** 7746a2b8 code (HEAD 36a87037 adds only the manifest). Base 722bf3df = `git merge-base HEAD int/1017`.
**TIER:** L (dual-trigger lines read: `src/autotester/stages/leak_evidence.py:50` HMAC key from `.env`, `:96` screenshot masking). LANE: normal (dual check, step 0a n/a).
**Policy-Version:** proportional-verification/2026-10-18.15 (dual check, coordinator A; blind to B).

## Plan
Logic + security read of the changed code; manifest verify command re-run; one falsification per criterion in copies outside the repo (D:/chk-scratch-t209a/mp7..mp10); synthetic-leak probe (fake secret, fake email, fake phone, fake master key); step 4c diff scope. No full suite (6c runs it). No Tesseract on this machine, so the real OCR path is not exercised by anyone here (manifest judgement 3; fail-closed path proven).

## Criteria
- **MP7 PASS.** `finding_priority.py:14-15,36-38` P0 for data_leak and privilege_escalation, one parameter, no priority field on `MultiRoleFinding` (`multi_role_finding.py:52-66`, extra=forbid). Falsified (mine, privilege_escalation P0->P1 in a copy): green 15 passed, red `assert <Priority.P1> is <Priority.P0>` in `test_priority_by_class_over_every_class[privilege_escalation]`.
- **MP8 PASS.** `report_banner.py:32-45` banner only for P0; `unified_report_render.py` places it before `<h1>`, no-findings output byte-identical to base (I rendered base 722bf3df's `render_html` vs the new one on a fixture: identical, also with `[]`). `unified_report.py` not in `git diff --name-only 722bf3df..HEAD`. Falsified (banner moved after `<h1>`): green, red on `_first_block(html).startswith('<div id="release-blocker"')`.
- **MP9 PASS.** Probe with a fake secret, email, phone and master key through `collect_leak_evidence` + `write_finding`: the only run file is `multi_role_findings/leak-1.json`; none of name, email, phone, secret, master key, derived project key (hex and base64), or `013-7788`/`zorblax` is in any file (utf-8 and utf-16) or in the captured DEBUG log. Evidence holds count 8, headers, 5 hashes, template `.../students/{id}?token={value}&e={value}`, screenshot withheld `local_ocr_unavailable` (nothing written raw). Missing key: ids withheld, count kept, no raw id. The key value is read only at `leak_evidence.py:47`, never logged or stored; `LeakKeyMissing` carries the env var NAME only. No model call in the module. Falsified (raw PNG written instead of the masked copy): green, red `assert ['Zorblax Quimby'] == []` in `test_canary_sweep_over_run_dir_log_and_prompts`.
- **MP10 PASS.** Finding carries role, platform_id, url_template, ordered steps, count (`multi_role_finding.py:52-66`); count must equal evidence count (`:79`). Falsified (persist drops the last step): green, red `assert 0 == 3` in `test_replaying_the_recorded_repro_gives_the_same_count`.
- **MPI1 PASS** (via MP9). **MPI3 PASS**: `git diff --name-only 722bf3df..HEAD` lists no `multi_role_enums.py`, `schema/enums.py`, `unified_report.py` or `core/image_privacy.py`.

## Commands I ran
- `uv run --directory <worktree> pytest tests/test_finding_priority.py tests/test_report_banner.py tests/test_leak_evidence.py tests/test_leak_repro_replay.py tests/test_unified_report.py` -> 49 passed (106 s).
- `ruff check src tests scripts` -> All checks passed. `autotester doctor` -> 2 violations, both `stale-generated` (docs/MAP.md, docs/SNAPSHOT.md), as the manifest says; no design-rule (size, docstring, duplicate) violation.
- Falsification floor: 4 criteria x 1, each green-before in its own copy, red-after on the named assertion; bound tree never edited (status clean except an untracked `qa/evidence/t209-leak-severity/` I did not create).

## Diff scope (4c)
11 files, all listed in the manifest "What changed". Only existing file edited: `unified_report_render.py` (adds import, `findings=()` parameter, banner and repros; nothing removed). No deleted or renamed function, test or key.

## PROPOSED-ISSUE (none blocks PASS; the maker reconciles)
- P1: PROPOSED-ISSUE: {"severity":"low","kind":"security","title":"collect_leak_evidence joins unvalidated finding_id into the screenshot path","where":"src/autotester/stages/leak_evidence.py:112-114","repro":"finding_id='../../outside/esc' with a working OCR engine wrote outside/esc.png outside run_dir (masked copy only; the ValidationError for '..' fires after the write). Probe: D:/chk-scratch-t209a/probe2.py","why_low":"finding_id is internal oracle code, the file is the masked copy, no caller exists yet","fix":"validate finding_id against the MultiRoleFinding pattern before building dest"}
- P2: PROPOSED-ISSUE: {"severity":"low","kind":"security","title":"LeakEvidence validation errors echo the rejected input","where":"src/autotester/schema/leak_evidence.py:56-59","repro":"LeakEvidence(hashed_ids=['STU-<secret>']) -> str(ValidationError) contains the value (probe.py, 'hashed_ids=raw': True)","why_low":"only on a caller bug; no caller logs it yet","fix":"model_config hide_input_in_errors=True on LeakEvidence and MultiRoleFinding"}
- P3: PROPOSED-ISSUE: {"severity":"low","kind":"residual","title":"Residual PII shapes not named in judgement 4","where":"stages/leak_evidence.py:76-84, schema/leak_evidence.py:20-24","repro":"templatise_url keeps '/app;jsessionid=Zm9vYmFy', '/reset/eyJhbGciOiJIUzI1NiJ9abc' and '/students/john.smith'; a column header that is a person's name passes `field_names`","fix":"document beside judgement 4; callers pass the route pattern; consider matrix-style tables as header-PII risk for T-213"}

## Notes
- MP8 wiring into `unified_report.py:282` is a CORE-REQUEST for a later unit (manifest judgement 5); the contract criterion as written (render test + file not edited) is met.
- The sweep tests use synthetic prompts and a faked OCR; the real Tesseract masking path is unproven on this machine (declared by the maker, fail-closed path verified).

Metrics: start=2026-10-18T17:20:00Z end=2026-10-18T17:58:00Z wall_min=38 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=4 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-18.15 lane=normal check_s=2280 mutants=0 defects_unit=0 defects_6c=0
