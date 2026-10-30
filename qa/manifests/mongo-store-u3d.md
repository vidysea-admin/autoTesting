# Manifest - mongo-store-u3d

**Status:** ready-for-check
**Fix cycle:** 1 (checker A verdict FAIL cycle 0: `qa/verdicts/mongo-store-u3d.md`, commit `d218c494`)
**Contract:** `qa/contracts/mongo-store.md` (ACTIVE 2026-10-29, amended 2026-10-31 at `001d10d6`), unit U3d, criteria M16 (pointer), M49, M50. Normal criticality (U3d row has no dual mark).
**Authority:** D-121, D-123 (no new `src/` module, no file on the D-123 list added; `store/*` untouched, so no path-level primitive was invented, M53)
Round cap: normal unit, D-014 cap of 2 fix cycles applies.
**Branch:** `feat/mongo-store-u3d` (worktree `D:/autoTesting/.claude/worktrees/mongo-u3d`). Not merged to master, not pushed.
**Base SHA:** `001d10d6`; cycle 1 first merged master `30db1b7a` (merge commit `24389544`).
**Code SHA:** cycle 0 `1cc3f851a4091b68671ce88f295330373dd01688`; cycle 1 `d7592895c4e333adef114d05f66952d5bcb5701f` (the cycle-1 code commit; this manifest is a second commit on top of it).
**Task id:** `mk-mongo-u3d`

## What changed

| File | Kind | Change |
|---|---|---|
| `src/autotester/ledger/committed_fresh.py` (300 lines, cap 300) | E in place | M50 rule recall: `_STATE_NAMES` adds `work_dir` `:100`; `_METHODS` adds `open`, `replace`, `is_file`, `is_dir`, `read_text`, `read_bytes` `:103`; `_method` `:221` resolves `p.m`, `getattr(p, "m")` and a bound-method alias; `_kind` `:235` treats `Path.replace(target)` (one positional arg) as a verb and `str.replace(a, b)` as not (`:246`); `_sites` `:262-269` builds the alias map. To stay at 300 lines I shortened docstrings and inlined `_lf` into `_compare`; behaviour of the committed-blob check is unchanged. |
| `pyproject.toml` `[tool.autotester.doctor.state-bypass]` | E in place | baseline 98 -> 104 rows, permanent 4 -> 27 rows (after cycle 1); every row owner-tagged or reasoned (disposition below). No `U3d` or `UNOWNED` tag remains. |
| `stages/orchestrate_downstream.py`, `orchestrate_execute.py`, `ai_report.py`, `report_export.py` (298 lines), `unified_report.py` (300 lines), `unified_report_findings.py`, `generic_acceptance.py`, `run_artifacts.py`, `video_review_store.py`, `video_retention.py`, `source_material.py`, `bench_marks.py`, `explore_consent.py` | E in place | `exists`/`glob`/`iterdir`/`stat`/`unlink`/`mkdir` on state paths replaced by `filestore.exists_path`, `list_children`, `mtime_path`, `delete_path` (imports at the top of each; call sites in the diff). |
| `stages/real_acceptance.py:164-165` | E in place | back to raw `(out / name).write_text(...)  # checked-in evidence, not state (M49)`; LEFT row in `tests/test_sweep_u3a.py`, two `permanent` rows (`write_text`, `mkdir`). |
| `sources/intake_commit.py` `:34`, `:97-103`, `:129`, `:162`, `:168` | E in place | `sweep_orphans` lists through `list_children` and deletes recordings through `delete_path`; `_copy_in` mismatch cleanup and `commit_video` through `delete_path`/`exists_path`. `_copy_in`'s `os.replace` (`:130`) and the `write_bytes` lines are not touched (U5b, M51). |
| `sources/drive_register.py:194`, `sources/email_register.py:216` | E in place | `exists` -> `exists_path` only; the `write_bytes` lines are U5b's and untouched. |
| `providers/config_migration.py:121,123` | E in place | the two `_payload` `exists` sites -> `exists_path` (M49 names these two). |
| `tests/test_state_bypass_rule.py` (263 lines) | E in place | M50 planted-form tests (below) and M49 owner test; one older assertion changed because `read_text` is now flagged (`:114`). |
| `tests/test_sweep_u3a.py:36` | E in place | LEFT row `"stages/real_acceptance.py": {"write_text": 1}`. |
| `qa/evidence/mongo-store-u3d/` | N | `mutations.json`, `mutation-run.txt`, `doctor.txt`, `ruff.txt`, `tests-final.txt`, `regression-pairs.txt`. |

No `src/` module added, no `store/*` edit, nothing under `auth/`, `core/env.py`, `core/safe_names.py`, `ui/error_pages.py`, `ui/routes_live.py`.

## Fix cycle 1 (answers the cycle-0 FAIL)

| Finding | Fix | Evidence |
|---|---|---|
| 1 BLOCK: three `stages/bench_inputs.py` rows in `permanent` | Moved to `baseline`, owner `M53-gated`, reason: M25 wants the list file-only but no route implements it (`mongo_routes` sends `.work/ceo-bench` to `server_state/settings`); write side (`bench_inputs.py:69-70`) goes through `filestore`, read side (`:79-81`) and the `mkdir` (`:61`) are raw; no unit owns the M25 file-only routing yet. No store code added. | `pyproject.toml` rows `stages/bench_inputs.py:*`; `test_m49_every_baseline_row_has_a_live_owner_and_a_reason` passes; doctor clean |
| 2 WARN: no store-routing test | New `tests/test_state_sweep_u3d.py` (6 tests): path verbs on the in-memory backend, `stored_reviews`, `load_run_findings`, `_approval_history`, `sweep_orphans` on the double (nothing under `projects/` on disk) and `sweep_orphans` in file mode (recordings, `.tmp-*` temps, staging leftover, stray file, emptied folder removed). | `tests-cycle1.txt`; 5/5 mutants killed (`mutations-cycle1.json`, `mutation-run-cycle1.txt`) |
| 3 WARN: readiness table understated | Table below rewritten; raw reads the rule cannot see are listed, documented only, not fixed. | section "Per-area readiness" |
| 6 INFO: ui_bench_inputs+explore_consent flake | Re-run: 28 passed. | `tests-cycle1.txt` |
| merge | Master `30db1b7a` brought `core/env.py:mongo_uri` (`is_file` on the repo-root `.env`); one `permanent` row added, same class as `load_repo_env` (the store URI bootstrap cannot read itself from the store). | doctor clean |

## Criteria map

| Crit | Code | Test / command |
|---|---|---|
| M49 U3d rows routed or re-tagged | disposition table below; `git diff 001d10d6 -- pyproject.toml` | `uv run autotester doctor` -> `doctor: clean` (no `state-bypass`, no `state-bypass-stale`); `tests/test_state_bypass_rule.py::test_m49_every_baseline_row_has_a_live_owner_and_a_reason` (owners subset of M53-gated/U5b/U7/U9/U11, every row has a reason; mutant m10 kills it) |
| M49 `real_acceptance` revert | `stages/real_acceptance.py:164-165`; LEFT row `tests/test_sweep_u3a.py:36`; `permanent` rows in `pyproject.toml` | `tests/test_sweep_u3a.py::test_every_raw_write_left_in_stages_and_sources_is_listed` |
| M49 UNOWNED owners | `ui/app.py`, `ui/routes_settings.py` -> U11; `core/image_privacy.py::_sanitize_one` -> U5b; `core/paths.py` x2 -> U9; `config_migration::_payload` x2 routed; `vision_probe` stat, `ui/intake_upload.py` and `ui/routes_bench_inputs.py` rmtree -> `permanent` | disposition table |
| M50 `work_dir()` root | `committed_fresh.py:100` | `test_m50_a_work_dir_root_is_a_state_root[call-root, bound-name, mkdir]`; mutant m1 |
| M50 `getattr` / alias | `committed_fresh.py:221-232`, `:267` | `test_m50_a_getattr_or_bound_method_alias_cannot_hide_a_verb[getattr, getattr-unlink, bound-alias, getattr-alias]`; mutants m2, m3 |
| M50 `is_file`/`is_dir`/`read_text`/`read_bytes` | `committed_fresh.py:103` | `test_m50_existence_and_read_verbs_are_flagged[...]` x4; mutants m4-m7 |
| M50 `Path.replace`/`touch`/deletions | `committed_fresh.py:103`, `:246` | `test_m50_replace_touch_and_deletions_are_flagged[replace, touch, unlink, os.remove, rmtree]`, `test_m50_a_str_replace_is_not_a_path_replace`; mutants m8, m9 |
| Store unset: behaviour unchanged | every edit is a public `filestore` function whose File backend does the old operation | touched modules' existing tests, 21 two-file pairs, all green (below) |

## Disposition of the old baseline (72 rows tagged `U3d` or `UNOWNED`; the checker re-derives)

| Old tag -> new | Rows | Which |
|---|---|---|
| U3d -> deleted (routed through the path API) | 31 | `ai_report` x2, `bench_marks` mkdir (removed, `filestore` writes create parents), `explore_consent::_approval_history`, `generic_acceptance` x3, `orchestrate_downstream` x3, `orchestrate_execute` x2, `report_export` x2, `run_artifacts`, `source_material` x2, `unified_report` x2, `unified_report_findings`, `video_retention` x3, `video_review_store`, `intake_commit` (`_copy_in` unlink, `commit_video` exists + unlink, `sweep_orphans` one `glob` + one `iterdir`), `drive_register`/`email_register` `exists` |
| U3d -> M53-gated (reason on each row) | 23 | O_EXCL lock (`intake_lock` mkdir/os.open/os.utime/unlink x2, `_lock_is_stale` stat), `.work` scratch with mkdir/rmdir/rmtree/stat (`drive_intake` x4, `intake_session` x2, `sweep_orphans` x5, `_place` mkdir, `commit_video` rmdir, `zip_intake` unlink), mkdir that goes with a U5b write (`drive_register`, `email_register`), `acceptance_baseline::_write_pair` create-exclusive mkdir |
| U3d -> U5b | 4 | `drive_register`/`email_register` `write_bytes`, `intake_commit` `os.replace` x2 (M51, tag change only) |
| U3d -> U11 | 1 | `sources/adapters.py::_sanitize_pdf_reading` `.env` exists |
| U3d -> permanent | 3 | `real_acceptance::write_evidence` mkdir (M49 revert), `discover` `iterdir` and `stat` (judgment call 3) |
| UNOWNED -> deleted | 2 | `config_migration::_payload` x2 |
| UNOWNED -> U11 / U5b / U9 / permanent | 2 / 1 / 2 / 3 | as the contract assigns |

## Sites the wider rule newly surfaced (M50: owner-tagged, listed here) - 62 rows (61 + the `mongo_uri` row from the master merge)

| Owner | Rows | Where |
|---|---|---|
| U5b (M24/M51) media read/scratch | 14 | `core/image_privacy.py`, `media/redacted.py` (6), `stages/leak_evidence.py`, `ux_advisory.py`, `video_access.py`, `ui/routes_product_map.py`, `ui/routes_video.py`, `drive_register`/`email_register` `read_bytes` |
| U7 (M52 READ-SIDE) | 12 | `core/trace.py` x2, `delivery/inbox.py::claimed_at`, `stages/orchestrate_checkpoint.py` x2, `stages/schedule_store.py` x7 (the `:119`, `:124`, `:171-197` sites M52 names) |
| U11 (M35) `.env` presence/read | 8 | `ui/app.py`, `routes_settings.py`, `routes_credentials.py`, `routes_role_accounts.py` x2, `explore_consent::signing_key_available` x2, `sources/adapters.py` |
| M53-gated | 11 | `config_migration` x6 (raw bytes read for the content hash), `acceptance_baseline` raw read of the source config, `intake_commit::sweep_orphans` `is_dir`, `stages/bench_inputs.py` x3 (cycle 1: write side routed, read side raw, M25 file-only route missing) |
| permanent | 17 | `ledger/citations.py` x5, `providers/vision_probe.py` x2, `stages/adversarial.py` x2, `ui/routes_bench_inputs.py` read, `discover` is_dir x2, `core/env.py::storage_warning` and `mongo_uri`, `image_privacy::_find_tesseract`, `acceptance_baseline::_input_bytes`, `real_acceptance` write_text |

## Per-area readiness for M52 (no area flips with a raw read left)

Baseline rows are what the rule sees. The rule does NOT see the two groups under the table, so an empty row here is not a G1 go-ahead.

| Area | Remaining baseline rows | READ-SIDE sites left |
|---|---|---|
| runs / projects / crawls (stages, sources) | 0 `U3d`; `M53-gated` 34 (scratch, lock, config_migration, acceptance_baseline, bench_inputs), `U5b` 6 (source media in `sources/`) | `config_migration` raw bytes reads; plus both groups below |
| settings (`.work/ceo-bench`, schedule heartbeat, config) | `M53-gated` 3 (`bench_inputs`) | `bench_inputs.py:79-81` raw read, `:61` mkdir; M25 file-only route does not exist, so on `settings` the private list would be written to Mongo and read back as absent |
| schedule / checkpoint / inbox / trace | `U7` 32 (`schedule_store` 21, `orchestrate_checkpoint` 4, `delivery/inbox` 5, `core/trace` 2) | the 12 M52 read sites |
| credentials / `.env` | `U11` 17 | `.env` reads |
| media (screenshots, video, frames, redaction) | `U5b` 13 | via `materialize` after U5b |

**Raw reads the rule cannot see (documented only, not fixed in this unit; they need owners in M52/M16):**

1. `store/` internals, exempt from the rule (`ledger/committed_fresh.py` `_EXEMPT_DIRS`): `store/project_store.py:186-199,213-217,246-249` (`load_results`, verdict loader, bench trials, observations), `store/crawl_store.py:37-49`, `store/run_store.py:85-88`, `store/bug_store.py:104,164`. They still use raw `exists`/`glob`/`iterdir`. Checker-confirmed effect: with the in-memory backend `ProjectStore.load_results` returns `[]` for runs written through `save_result`, so `prune_old_videos` (routed in this unit) prunes nothing on a non-file backend.
2. Paths derived from a function argument, invisible to the taint rule: `stages/ai_report.py:144-148` (`_refusal_rows` reads `refusals.jsonl` raw), `stages/oracle_answer_key.py:80-84`, `stages/role_port_network.py:83-85`, `stages/source_material.py:104` (`file_sha256` after the routed `exists_path`: on a non-file backend `exists_path` is true and the raw read raises), and the report writers `stages/report_export.py:296`, `stages/unified_report.py:298`.

M16 is not closed by U3d (contract M49): it closes when the U5b, U7, U9, U11 and `M53-gated` rows are gone.

## Things the checker should look at (judgment calls)

1. **`.env` presence/reads are tagged U11, not routed.** Routing a `.env` read through the store would put credentials in a state document and defeat redaction; U11 owns it (M35). 17 rows.
2. **Scratch under `.work/` is `M53-gated`, not routed and not `permanent`.** `filestore._route` has a catch-all (`** -> server_state/settings`), so a routed `.work/intake/...` write would become a state document in Mongo. Scratch needs delete-tree/mkdir/stat verbs the path API lacks. This puts 23 old U3d rows in `M53-gated` where the contract expected "about 17" of 62; the extra ones are the same class (mkdir/rmdir/rmtree pairs). A `permanent` tag would hide them (M49 falsifier a), so I did not use it.
3. **Two old `U3d` rows went to `permanent` on judgment:** `stages/discover.py` walks caller-approved host trees of the product under test (`scope.project_root`, `approved_roots`), never the data root; the checker accepted this. (Cycle 0 also tagged three `bench_inputs` rows `permanent`; the checker rejected that and they are `M53-gated` now.)
4. **`sources/intake_commit.py::sweep_orphans`**: `.tmp-*` atomic-write temps are hidden by `list_children`, so one raw `folder.glob(".tmp-*")` + `unlink` stays (M53-gated row, comment at `:102`). Behaviour with the store unset is identical: same files removed, same count. `list_children` on a non-directory returns `[]` (checked), matching the old `is_dir` guard.
5. **`stages/source_material.py::_reading_bytes`**: the existence checks are routed; the content hash still reads the file raw through `file_sha256` (a raw bytes read, no public verb). Not flagged by the rule because the read is inside another module; noted for U7/M53.
6. **U5b adjacency**: in `intake_commit.py` I changed only `_copy_in`'s cleanup `unlink` (`:129`) and left the `os.replace` (`:130`) line untouched; `drive_register.py:194` and `email_register.py:216` changed only the `exists` half of the condition, the `write_bytes` line below is untouched.
7. **Rule fits in the same file at exactly 300 lines.** Docstrings were shortened and `_lf` inlined to make room; the 300-line cap was not raised or exempted. A further widening of the rule needs the D-entry home (M53).
8. **Known recall gaps, not fixed here:** `Path.replace(target=...)` (keyword) is not flagged because `str.replace` is indistinguishable without types; the rule is name/taint based, so a path built only from a function argument in a module outside `_STATE_MODULES` is not seen.
9. **No review agent was dispatched** (task said no checkers). The lifecycle `senior-software-engineer` review of this diff is the caller's to run.

## Verify (run in the worktree, `PYTHONPATH=<worktree>/src`, `-o addopts=`, at most 2 test files per call)

Cycle 1 results (`tests-cycle1.txt`, `ruff.txt`, `doctor.txt`): ruff clean; doctor clean; `test_state_bypass_rule`+`test_sweep_u3a` 84 passed; `test_state_sweep_u3d`+`test_bench_marks` 22 passed; `test_ui_bench_inputs`+`test_explore_consent` 28 passed; `test_state_sweep_u3b`+`u3c` 17 passed; cycle-1 mutation run 5/5 killed. Cycle 0 results follow.

```
ruff check src tests scripts                         -> All checks passed!   (qa/evidence/mongo-store-u3d/ruff.txt)
autotester doctor                                     -> doctor: clean        (qa/evidence/mongo-store-u3d/doctor.txt; advisory D-087 citation warnings only)
pytest tests/test_state_bypass_rule.py tests/test_sweep_u3a.py -> 84 passed   (tests-final.txt)
scripts/mutation_check.py qa/evidence/mongo-store-u3d/mutations.json -> 10/10 mutations killed (mutation-run.txt)
touched-module regression, 21 two-file pairs (regression-pairs.txt): orchestrate_downstream(+privacy) 13, at1384+ai_report 29,
  ai_persist+report_export 26, report_export_reason+secrets 14, run_failure_artifacts+ui_report_no_runs 9,
  video_evidence+video_report_export 4, unified_report+secrets 20, report_findings_wiring+banner 12,
  generic_acceptance+real_acceptance 20, acceptance_isolation+video_review_route 15, prune_guard+video_retention 7,
  teaching_documents+bench_marks 19, ui_bench_inputs+explore_consent 28, approval_prod_gate+schedule_gate 24,
  drive_verify+zip_intake_atomic 23, cli_intake+provider_migration 14, analysis_flows+user_persona_report 25,
  xlsx_formula_guard+goal_contract_registration 10, state_sweep_u3b+u3c 17, drive_intake+ui_intake_drive 33,
  ui_intake+ui_project_intake 39 -> all passed, none failed
```

Not run: the full suite in one invocation (low-memory rule); `tests/test_role_port_authz.py` (5 known environmental failures, untouched); tests of modules this unit did not change.
