# Manifest - mongo-store-u3a

**Status:** ready-for-check
**Fix cycle:** 0
**Contract:** `qa/contracts/mongo-store.md` (ACTIVE 2026-10-29), unit U3a. **Criticality:** normal (U3a row has no dual mark). Behaviour-neutral sweep under the file backend; no Mongo code.
**Authority:** D-120, D-121, D-122, D-123 (edit in place; no new `src/` module; D-122 file list untouched)
Round cap: normal unit, D-014 cap of 2 fix cycles applies.
**Branch:** `feat/mongo-store-u3a` (cut from master `0a2cbe45`; not merged, not pushed)
**Base SHA:** `0a2cbe45`
**Code SHA:** `d7cafb8c6f258d9801d3c899eb7f714a0c2f9bf1` (the only code commit; this manifest is a second commit on top of it)
**Criteria judged by U3a:** M16 (the stages/sources share of the bypass sweep). The doctor rule that enforces M16 is U3c's; the falsifier "reintroduce `Path.write_text` on a `ProjectPaths` path in `stages/`" is covered here by an AST pin (below) and by U3c's rule once it lands.

## Scope as the dispatcher narrowed it (said plainly)

The store API has no public exists / list / mtime / delete by path yet (U4 adds `exists_path`, `list_children`, `mtime_path` to `store/filestore.py`). So this unit moved **only the sites the existing public API covers** (`write_text`, `write_bytes`, `write_json`, `read_json`, `read_jsonl`, `append_jsonl`, `upsert_jsonl`, `delete_jsonl_row`). No path-to-key helper was added and the private `_route` is imported nowhere (`grep -rn "_route" src/autotester/stages src/autotester/sources` shows only `stages/orchestrate.py`'s unrelated graph router). Every `exists` / `glob` / `iterdir` / `stat` / `unlink` site that is left is listed under "Deferred to U3 follow-up". Files owned by sibling units were not edited: `git diff 0a2cbe45 --stat` touches only the eight files in the next table plus tests/evidence.

## What changed

| File | Kind | Change |
|---|---|---|
| `src/autotester/stages/portal_persona.py:257` | E in place | `knowledge.md` written with `write_text(store.paths.knowledge, ...)` (was `mkdir` + `Path.write_text`); import added (file stays at 300 lines) |
| `src/autotester/stages/oracle_payment.py:57,181` | E in place | `load_declaration` reads with `read_json` (absent or `OSError` = "no payment paths declared", invalid = "payment declaration is invalid", same two closed phrases); `_write_report` uses `write_text`. The `is_dir()` guard `:177` is kept (see Deferred) |
| `src/autotester/stages/oracle_credential_policy.py:70` | E in place | `load_policy` reads with `read_json`, same two closed phrases |
| `src/autotester/stages/real_acceptance.py:166` | E in place | evidence files written with `write_text` (design 3.3 lists `:165`). See flag F1 |
| `src/autotester/stages/acceptance_baseline.py:127` | E in place | baseline source input written with `write_bytes` (design 3.3 lists `:128`); redundant `mkdir` dropped (`_atomic_write` creates parents) |
| `src/autotester/stages/leak_evidence.py:99` | E in place | masked screenshot stored with `write_bytes(dest, masked bytes)` instead of `mkdir` + `shutil.copyfile`; `import shutil` removed; redundant `mkdir` before `write_json` (was `:136`) dropped. The raw PNG in `TemporaryDirectory` (`:95`) stays: scratch, deleted on exit |
| `src/autotester/sources/drive_jobs.py:43,56` | E in place | `save_job` writes with `write_text` inside the same `REPLACE_TRIES` loop that retries `PermissionError` (the temp-file + `os.replace` is now `_atomic_write`'s); `load_job` reads with `read_json`, `(OSError, ValueError)` -> `None` (`ValidationError` is a `ValueError`) |
| `tests/test_acceptance_baseline.py` | E in place | `test_partial_write_is_visible_and_refuses_reuse` injected its failure by patching `Path.write_bytes`; it now patches `acceptance_baseline.write_bytes` (the filestore seam). Same intent, same assertions |
| `tests/test_sweep_u3a.py` | N (test) | 9 tests: behavioural per moved function over an in-memory backend, plus the AST pin |
| `qa/evidence/mongo-store-u3a/{mutations.json,mutation-run.txt,regression-pairs.txt}` | N | 15 mutants and their run; the touched-module regression log |

No `src/` module and no non-test file outside the list above was added.

## Criteria map (M16, stages/sources share)

| Part | Code | Test (falsifier it kills) |
|---|---|---|
| State writes in `stages/`+`sources/` go through `filestore` | the seven `src` rows above | `test_sweep_u3a.py::test_a_drive_job_is_saved_and_loaded_through_the_backend`, `::test_the_payment_report_is_written_through_the_backend`, `::test_a_masked_leak_screenshot_is_stored_through_the_backend` assert the bytes are in the backend and no file reached `tmp_path` |
| Reads via `read_json` keep their error contract | `oracle_payment.py:57`, `oracle_credential_policy.py:70`, `drive_jobs.py:56` | `::test_a_payment_declaration_and_a_credential_policy_load_through_the_backend` (absent / invalid phrases), `::test_a_corrupt_drive_job_reads_as_absent` |
| `drive_jobs` Windows busy-replace retry preserved | `drive_jobs.py:40-48` | `::test_save_job_retries_a_busy_replace`, `::test_save_job_gives_up_after_the_last_try` |
| Existing guard behaviour preserved | `oracle_payment.py:177` | `::test_the_payment_report_is_not_written_into_a_missing_folder` |
| No new raw write regrows in `stages/`/`sources/` | `LEFT` table in the test | `::test_every_raw_write_left_in_stages_and_sources_is_listed`: AST walk counting `write_text`, `write_bytes`, `open(..,"w"/"a"/"x")`, `os.replace/rename/open/fdopen`, `shutil.copy*/move/rmtree`, `.rename`; equality against the pinned table. Mutant a15 (an unlisted `write_text` in `stages/review.py`) is killed by it |
| Behaviour identical with `AUTOTESTER_STORE` unset | every route is `FileBackend` (`filestore._backend`); a path outside `repo_root()` is a plain file (`filestore._route`) | the existing tests of every touched module (Verification) |

## Left on disk (write family) - each pinned in `LEFT`, with the reason

| File (count) | Why it is not a state-document write |
|---|---|
| `stages/leak_evidence.py` `raw.write_bytes` (1) | raw PNG into `TemporaryDirectory`, deleted on exit; never leaves scratch |
| `stages/failure_bundle.py` (2 `rmtree`, 2 `write_text`, 1 `rename`, 1 `copyfile`) | the bundle is a directory built in `.partial` and renamed (FB1 "complete or absent"); design 2.3 routes bundles as a `bundles` document plus member blobs, which needs U4 (`bundles`) and U5b (member blobs). Not expressible with the existing public API |
| `stages/report_export.py:299`, `stages/unified_report.py:299` `write_text` (1 each) | generated html exports: M25 "NOT stored, rebuilt per request" |
| `stages/schedule_store.py` (3 `rmtree`, 2 `write_text`, 3 `os.replace`, 1 `os.rename`, 2 `os.open`, 1 `os.fdopen`) | U3c's file (schedule store); not edited |
| `sources/bounded_write.py` `open("wb")` (1) | bounded copy into a staging path (scratch) used by intake and Drive fetch |
| `sources/drive_intake.py` (3 `rmtree`), `sources/gws_drive.py` (3 `rmtree`) | delete of fetch scratch folders under temp/`.work` staging |
| `sources/drive_register.py:196`, `sources/email_register.py:218` `write_bytes` | source media (`source_media` blob, design 5 / GridFS). The unit table gives U5b only "screenshot/video/crawl shot/frames", so see flag F2 |
| `sources/intake_commit.py` (2 `os.replace`, 2 `rmtree`, 1 `os.open`) | the recording commit protocol (stage, then `os.replace`, with stale-folder cleanup): blob `source_media`, same gap as above |
| `sources/pdf_worker.py:55` `write_text` | subprocess writes its result to an argv-supplied temp path (scratch) |

Reports built to `out_path` in `issues.py:256`, `ai_report.py:218`, `crawl_report.py:232` are `workbook.save` xlsx exports (M25); they are not caught by the AST pin and are not state.

## Deferred to U3 follow-up (needs U4 `exists_path` / `list_children` / `mtime_path`, or a delete / raw-read primitive)

Raw reads, `exists`, `is_file`, `is_dir`, `glob`, `iterdir`, `stat`, `unlink` and `mkdir` left in `stages/` and `sources/` (current line numbers; `.work/deferred.txt` has the generating scan). Legend: ex=`.exists()`, isf/isd=`is_file`/`is_dir`, gl=`glob`, it=`iterdir`, st=`stat`, ul=`unlink`, rt/rb=`read_text`/`read_bytes`, mk=`mkdir`.

**A. State paths: need `exists_path` / `list_children` / `mtime_path` (the follow-up)**
- `stages/orchestrate_downstream.py` 49 ex, 92 ex, 148 ex; `stages/orchestrate_execute.py` 203 ex, 209 ex (pipeline progress markers; design 3.3)
- `stages/unified_report.py` 152 ex, 164 ex (crawl network jsonl as a progress signal; design 3.3); `stages/unified_report_findings.py` 23 isd, 26 gl
- `stages/ai_report.py` 56 isd/it, 144 ex, 169 gl/isd; `stages/generic_acceptance.py` 128 ex/it, 131 it; `stages/report_export.py` 42 ex, 45 isd/it; `stages/run_artifacts.py` 57 gl; `stages/video_review_store.py` 16 isd, 18 gl/st; `stages/video_review.py` 210 isf/st, 233 isf; `stages/source_material.py` 100 ex, 103 ex; `stages/grade.py` 224 ex; `stages/adversarial.py` 72 isd, 74 gl, 80 isf; `stages/bench_inputs.py` 79 ex, 81 rb
- `stages/oracle_payment.py` 177 isd (the guard kept in `_write_report`; under a Mongo run dir that is not local this skips the write, so it needs `exists_path`)
- `stages/explore_consent.py` 144 isd/it (project listing: U3b's `list_project_slugs`); 127 isf/rt is the `.env` approval-key read (credential area, U3b/U11)
- `stages/failure_bundle.py` 68 rb, 158 mk, 208 ex, 215 mk, 236 isf, 239 rt, 249 isf (bundle load / verify; goes with the bundle routing above)
- `stages/acceptance_baseline.py` 38 rb (external input files), 80 ex, 91 rb (the source `project.json` bytes, hashed), 97 mk, 121 mk; `stages/real_acceptance.py` 145 mk; `stages/bench_marks.py` 66 mk; `stages/bench_inputs.py` 61 mk
- `stages/video_retention.py` 48 ex, 50 isd/it, 82 ul; `stages/run_case_pipeline.py` 124 ul (video delete: blob lifecycle, needs a delete primitive plus U5b)

**B. Raw reads with no public-API equivalent (list-of-model `TypeAdapter`, bytes or sha over raw text)**
- `stages/oracle_answer_key.py` 82 isf, 84 rt; `stages/oracle_consistency.py` 107 isf, 109 rt; `stages/oracle_negative_input.py` 259 isf, 262 rt; `stages/oracle_state_after.py` 50 isf, 52 rt (each loads a `list[Model]` from one JSON file; `read_json` takes one `BaseModel`)
- `stages/role_port_network.py` 83 isf, 85 rt (`load_budget`: a `read_json` swap would change the invalid-file error from `ValidationError` to the path-prefixed `ValueError`, a visible contract change, so it was left)

**C. Source media / blob territory (`source_media`; see F2)**
- `sources/adapters.py` 97, 99, 143 (`.env` redactor read), 190, 192; `sources/email_register.py` 65, 67, 82, 126, 213, 215; `sources/drive_register.py` 171, 191, 193; `stages/ingest.py` 113, 115, 195, 217; `stages/media_prep.py` 57, 138; `sources/audio.py` 61; `sources/pdf_extract.py` 18, 27, 29; `sources/pdf_ocr.py` 33, 35; `sources/zip_intake.py` 217, 279; `sources/intake_commit.py` 48, 61, 69, 77, 91, 96, 97, 99, 100, 103, 113, 124, 126, 132, 159, 165, 167; `sources/drive_intake.py` 85, 86; `sources/gws_runner.py` 58, 68, 72, 99, 123; `sources/gws_drive.py` 147; `sources/drive_verify.py` 104 ul; `sources/bounded_write.py` 39, 51; `sources/extract.py` 67

**D. Not state (repo code, prompts, scanned target code): no action**
- `stages/agent_loop.py` 64, `stages/grade_images.py` 57, `stages/teach_text.py` 87, `stages/video_review_prompt.py` 32, `sources/audio.py` 30 (prompt files from `RepoDocs().prompts_dir`); `stages/explore_guidance.py` 219 (skill file); `stages/discover.py` 45, 81, 99, 142, 274 (scans the target project's code, not our state); `stages/ux_advisory.py` 111, `stages/video_access.py` 171 (served-file containment checks, blob territory); `stages/crawl_report.py` 232, `stages/issues.py` 256 (xlsx export parent dir)

**E. Sibling-owned, not touched**
- U3c: `stages/schedule_store.py` (all), `stages/scheduler.py` 201 st, `stages/orchestrate_checkpoint.py` 173, 204, 206; U3b: `stages/schedule_wiring.py` 104 gl/isd, 108 st
- Outside the two folders but in design 3.3: `agents/comparison.py:89` (not in this unit's scope)

## Flags for the checker / dispatcher

- **F1 `real_acceptance.py` and the route table.** Design 3.3 lists it, so it was moved. But the key is `qa/evidence/t169-real/<mode>/...` and `filestore.area_of` sends any non-`.work/` key to area `projects`. These files are repo-tree evidence meant to be committed, not run state. If U4's route table is closed, a Mongo run would refuse or swallow them. Cheapest fix is to revert `real_acceptance.py:166` to `Path.write_text` and add it to the doctor allow-list (U3c); it is one line either way. Same question for `acceptance_baseline.py:127` (it writes under a caller-chosen destination root, so under file mode it is a plain file).
- **F2 source-media writers have no unit.** `intake_commit`, `drive_register`, `email_register` write the `source_media` blob (design 5 GridFS kind), but the unit table gives U5b only screenshot / video / crawl shot / frames. They are listed above and pinned in `LEFT`; someone needs to own them.
- **F3 existing test edited.** `tests/test_acceptance_baseline.py::test_partial_write_is_visible_and_refuses_reuse` followed the seam (see table).
- **F4 `load_declaration` / `load_policy`** now catch an invalid file via `ValueError` from `read_json` (message path-prefixed, then discarded); a non-UTF-8 file used to escape as `UnicodeDecodeError`, it now reads as "invalid". Pinned by the new test; both are closed phrases that never quote the file.
- **F5 byte equivalence.** Not diffed byte-for-byte by a dedicated test. `write_text` does the same UTF-8 text-mode write as `Path.write_text(encoding="utf-8")`; `drive_jobs` previously wrote `<id>.tmp` then `os.replace`, now `_atomic_write`'s unique `.tmp-*` then `os.replace` (same atomicity, no fixed temp name).

## Verify (run in `D:/autoTesting/.claude/worktrees/mongo-u3a`, `-o addopts=`, at most 2 test files per call, `env -u ANTHROPIC_BASE_URL`)

```
pytest tests/test_sweep_u3a.py                                          -> 9 passed
pytest tests/test_sweep_u3a.py tests/test_acceptance_baseline.py        -> 33 passed
ruff check src tests scripts                                            -> All checks passed!
autotester doctor  (redirected to .work/doctor-u3a.txt, exit 0)         -> doctor: clean   (only the non-blocking D-087 advisories)
python scripts/mutation_check.py qa/evidence/mongo-store-u3a/mutations.json --repo .   -> 15/15 mutations killed (first run 14/15: a2 over-claimed a kill for the corrupt-job test, claim removed, re-run 15/15)
```

Touched-module regression, 12 two-file calls (`qa/evidence/mongo-store-u3a/regression-pairs.txt`): `test_acceptance_baseline`+`isolation` (24 baseline tests pass after the test re-point), `crawl_guidance_seam`+`explore_completeness` 40 passed, `finding_priority`+`leak_evidence` 28, `leak_repro_replay`+`leak_url_ids` 45, `oracle_credential_mail`+`oracle_credential_policy` 37, `oracle_declarations`+`oracle_mailbox` 24, `oracle_payment`+`oracle_registry` 32, `oracle_tenant`+`persona_diff_pipeline` 22, `portal_persona`+`real_acceptance` 22, `report_banner`+`report_findings_wiring` 12, `role_port_authz`+`ui_intake_drive` 5 failed 23 passed. **The 5 failures are all `test_role_port_authz.py` (`getaddrinfo ENOTFOUND a.localhost`, this host cannot resolve `*.localhost`) and fail identically against the unmodified base `src` (`git archive 0a2cbe45` on `PYTHONPATH`, 5 failed 11 passed): pre-existing, environmental.** `test_ui_intake_drive.py` (the `drive_jobs` consumer) passed.

Not run: the full suite (low-memory rule).
