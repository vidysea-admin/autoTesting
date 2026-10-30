# Verdict - mongo-store-u3d (checker A, cycle 0)
Verdict: FAIL
Cycle checked: 0
Head tested: b4752163 (feat/mongo-store-u3d; code commit 1cc3f851, base 001d10d6). Unit U3d, normal criticality (not dual). Judged: M16 pointer, M49, M50 and the U3d row of `qa/contracts/mongo-store.md`.
Class: all LOCAL. No Mongo connection; no `.env` value read or printed. Worktree `.venv`, `PYTHONPATH=<worktree>/src`, `-o addopts=`, at most 2 test files per pytest call. I read no other checker's verdict on this unit (none exists).

## One-line reason
Everything the contract enumerates holds (routing is behaviour-preserving, no `U3d`/`UNOWNED` tag is left, the rule catches every M50 form, all commands green) except one thing: three newly surfaced rows for `stages/bench_inputs.py` were put in `permanent` with a reason the code contradicts, which is the M49 falsifier (a) "a state path moved to `permanent`". The fix is a three-row retag; cycle 1 should be short.

## Result per check
| Check | Result | Evidence |
|---|---|---|
| stages/ and sources/ sites routed, store-unset behaviour unchanged | PASS | `git diff 001d10d6 HEAD -- src/autotester/{stages,sources,providers}` read in full. `FileBackend.children` (`store/filestore.py:104-108`) lists files and dirs sorted, hides `.tmp-*` and `*.lock`; `exists_path` (`:285`) is `exists or is_dir`; `delete_path` (`:238`) defaults `missing_ok=True`. Each rewrite matches its old form (differences listed under findings 4-5, both harmless). `sweep_orphans` differential below. |
| No `U3d` / `UNOWNED` tag left, every row has owner + reason | PASS | `tomllib` over `pyproject.toml`: 101 baseline rows, owners `M53-gated` 31, `U7` 32, `U5b` 19, `U11` 17, `U9` 2; 29 `permanent`; 0 rows without ` | reason`. `tests/test_state_bypass_rule.py::test_m49_every_baseline_row_has_a_live_owner_and_a_reason` passes and mutant m10 kills it. |
| M49 UNOWNED owners as the contract assigns | PASS | `ui/app.py::_guard_intake`, `ui/routes_settings.py::_present_keys` -> U11; `core/image_privacy.py::_sanitize_one` -> U5b; `core/paths.py` `ProjectPaths.ensure`, `work_dir` -> U9; `config_migration._payload` x2 routed (`providers/config_migration.py:121,123`); `vision_probe`, `intake_upload`, `routes_bench_inputs` rmtree -> `permanent` (upload staging under `.work/uploads`, `ui/routes_bench_inputs.py:83`, `ui/intake_upload.py:119`). |
| `real_acceptance` revert | PASS | `stages/real_acceptance.py:164-165` raw `write_text`; LEFT row `tests/test_sweep_u3a.py:36`; two `permanent` rows. |
| M50: rule flags the new forms, not `str.replace` | PASS | Planted by me in a scratch repo under the scratchpad (`check_state_bypass(<scratch>)`, empty baseline): flagged `work_dir()` root (call, bound name, `work_dir("x").write_text`), `getattr(p,"write_text")(x)`, `w = p.write_text; w(x)`, `u = getattr(p,"unlink"); u()`, `is_file`, `is_dir`, `read_text`, `read_bytes`, `p.replace(q)`, `touch`, `os.remove`, `unlink`, `shutil.rmtree` (15 of 15). Not flagged, correctly: `str(p).replace("a","b")`, `p.name.replace("a","b")`. Not flagged, as the maker states (manifest item 8): `p.replace(target=q)`. |
| `ledger/committed_fresh.py` exactly 300 lines, readable | PASS | `wc -l` = 300; doctor enforces file <= 300 and function <= 50 and is clean. Diff `:221-269`: `_method` is a small, single-job function with a docstring; `_kind` got simpler than before. The only density cost is the walrus comprehension in `_sites` (`:267`), acceptable. Shortened docstrings still state the one job and why the rule lives here (`:10-11`). |
| Tests | PASS | `uv run pytest tests/test_state_bypass_rule.py tests/test_sweep_u3a.py -o addopts=` -> 84 passed in 16.87 s. |
| Lint / doctor | PASS | `uv run ruff check src tests scripts` -> `All checks passed!`. `uv run autotester doctor` (redirected to a file) -> exit 0, last line `doctor: clean` (advisory D-087 citation lines only). |
| Mutation harness | PASS | `uv run python scripts/mutation_check.py qa/evidence/mongo-store-u3d/mutations.json` -> `10/10 mutations killed`; `git status` clean afterwards. |
| Regression sample | PASS (one unexplained flake, finding 6) | prune_guard+video_retention 7; drive_intake+ui_intake_drive 33; ui_intake+ui_project_intake 39; unified_report+report_export 28; teaching_documents+bench_marks 19; generic_acceptance+real_acceptance 20 -> all passed. ui_bench_inputs+explore_consent: 1 failed / 27 passed once, then 28 passed on 7 consecutive re-runs. |
| `.env` reads tagged U11, not routed | ACCEPT | Routing a `.env` read through the store would put a credential in a state document; M35/M31 own that. 17 U11 rows, each with reason. |
| `.work` scratch tagged `M53-gated` (23 vs ~17) | ACCEPT | The contract (M49 (ii)) names "mkdir/rmdir/rmtree pairs" and says "the checker re-derives the count". The catch-all route is real: `store/mongo_routes.py:90` `("**", "server_state", "settings")`, and I confirmed `route(".work/intake/a/b")` -> `server_state/settings`. A routed scratch write would become a Mongo document, so raw is right until M53. No row is in `permanent`, so nothing is hidden. |
| `permanent` calls | `discover` ACCEPT, `real_acceptance` ACCEPT, upload staging ACCEPT, `bench_inputs` FAIL | `stages/discover.py:34-61,77-102` walks caller-approved host trees (`scope.project_root`), never the data root. `bench_inputs`: finding 1. |
| `sweep_orphans` raw `.tmp-*` glob | ACCEPT | `intake_commit.py:102-104`, M53-gated row with a comment. Differential (scratch script, old body vs new, same fixture: two orphan folders, one holding `recording.mp4` + `.tmp-abc`, a row-less folder with a transcript, a stray file, a known folder, a staging leftover): both return 3, both leave identical trees. |
| `source_material` raw byte hash | ACCEPT with finding 3 | `stages/source_material.py:104`. |
| U5b adjacency | PASS | `intake_commit.py:129` only the cleanup `unlink`; `os.replace` at `:130` untouched; `drive_register.py:194` and `email_register.py:216` change the `exists` half only, the `write_bytes` lines are untouched. No `store/*`, `auth/*`, `core/*` file in the diff (`git diff --name-only`), no new `src/` module (M53). |
| M49 falsifier (b): routed workload leaves the data root untouched | PASS for the routed sites, not evidenced by the maker | The unit adds no `InMemoryBackend` test (U3b and U3c did). I ran one myself (scratch, `tests/state_backends.InMemoryBackend` swapped in as `filestore._backend`): seeding runs, then `valid_runs_newest_first`, `_approval_history`, `stored_reviews`, `load_run_findings` -> disk tree `[]` before and after, runs read back from the double. `list_children(suffix=".json")`, `mtime_path`, `exists_path`, `delete_path` (incl. missing file) behave as the callers need. See finding 2. |

## Findings

### 1. BLOCK - `stages/bench_inputs.py` rows in `permanent` contradict the code (M49 falsifier (a), M50)
`pyproject.toml` `permanent` rows `stages/bench_inputs.py:load_pinned_list:exists`, `:load_pinned_list:read_bytes`, `:save_atomic_list:mkdir`, reason "M25: the CEO-benchmark private list is file-only by design".
- The writes are not file-only. `stages/bench_inputs.py:69-70` stores the list with `write_bytes(folder / LIST_NAME, raw)` and `write_json(folder / PIN_NAME, pin)` from `store.filestore`, and `store/mongo_routes.py:90` sends `.work/ceo-bench/...` to `server_state` / area `settings` (I ran `route(".work/ceo-bench/x/atomic-list.json")` -> `Route(collection='server_state', area='settings', ...)`). `grep -rn ceo-bench src/autotester/store` is empty: nothing implements the M25 exemption.
- The reads are raw: `stages/bench_inputs.py:79-81` (`path.exists()`, `path.read_bytes()`) and the `mkdir` at `:61`.
- Consequence once `settings` flips: the upload stores the private answer list in Mongo (M25 violation) and `load_pinned_list` raises "no atomic list is pinned" because the raw read finds nothing. The `permanent` tag removes the only place that would show it.
- M50 says a newly surfaced site goes to the baseline "only with an owner tag"; the maker's own judgment call 3 invites the retag. These three rows were new in this unit (surfaced by the `work_dir()` root form).
Required: move the three rows from `permanent` to `baseline` with an owner and a reason that states the read/write split (the maker's suggested `M53-gated` fits the raw-read and mkdir halves; the reason should also say the M25 file-only route does not exist yet), keep the owner set in `test_m49_every_baseline_row_has_a_live_owner_and_a_reason` consistent, and list the site in the manifest readiness table (settings area). Contract note for the checker seat: no unit owns the M25 file-only routing of `.work/ceo-bench/`; it should be assigned (U4 routes or U8).

### 2. WARN - no store-routing test for the routed sites (M49 falsifier (b))
The unit's evidence is the rule tests plus file-mode regression pairs. Nothing proves the 30-odd routed call sites read and write through the store; U3b/U3c each shipped an `InMemoryBackend` sweep test. My scratch probe passed, so this is a gap in evidence, not a defect. Add one `tests/test_state_sweep_u3d.py`-style test in cycle 1 (run list, child listing with suffix, `mtime_path` ordering, `delete_path`, `exists_path`, tree hash unchanged). `sweep_orphans` has no test at all (`grep -rn sweep_orphans tests` is empty); my differential showed it correct, so a test would pin it.

### 3. WARN - M52 readiness table understates the READ-SIDE sites
The manifest table says runs/projects/crawls have only `config_migration` raw reads left. Not so, for two reasons the rule cannot see:
- `store/` is exempt from the rule (`ledger/committed_fresh.py:96` `_EXEMPT_DIRS`), yet `store/project_store.py:186-199,213-217,246-249` (`load_results`, verdict loader, bench trials, observations), `store/crawl_store.py:37-49`, `store/run_store.py:85-88`, `store/bug_store.py:104,164` still use raw `exists`/`glob`/`iterdir`. I confirmed it: with the in-memory double, `ProjectStore.load_results` returned `[]` for runs written through `save_result`, so `prune_old_videos` pruned nothing in my probe.
- Argument-derived paths are invisible to the taint rule (the maker's gap 8): `stages/ai_report.py:144-148` (`_refusal_rows` reads `refusals.jsonl` raw, six lines below two sites this unit routed, and would print "no refused attempts recorded" on Mongo), `stages/oracle_answer_key.py:80-84`, `stages/role_port_network.py:83-85`, `stages/source_material.py:104` (`file_sha256` after the new `exists_path`: on Mongo `exists_path` is true and the raw read raises), and the report writers `stages/report_export.py:296`, `unified_report.py:298`.
None of this is in M49/M50's enumerated scope, so it does not fail the unit, but per M52 G1 must not flip an area from this table. The checker seat should amend M52/M16 so `store/*_store.py` raw readers and argument-derived readers get owners, or widen the rule.

### 4. INFO - `list_children` is slightly broader than the old `is_dir` filters
`stages/report_export.py:42-43`, `stages/video_retention.py:48`, `stages/explore_consent.py:145-146` previously kept directories only; they now take every child name (files too). A stray file there yields `load_run(...) is None` / empty results / `ProjectStore(<name>).list_approvals() == []`, all benign (checked: `projects/` holds directories only). `stages/run_artifacts.py:57-58` loses the `_inside` symlink-escape check for `.tmp-*` and `*.lock` entries because `list_children` hides them; negligible.

### 5. INFO - `stages/bench_marks.py:66` mkdir removal is safe
`core/file_lock.py:38` creates the lock's parent directory, so dropping `bench_dir.mkdir` before `file_lock` is behaviour-neutral.

### 6. INFO - one unexplained failure
`tests/test_ui_bench_inputs.py tests/test_explore_consent.py` failed 1 test on the first run (I did not capture the name) and passed 28/28 on seven re-runs while other agents loaded the machine. Not attributed to this diff; the maker should run that pair again at cycle 1.

### 7. INFO - recall limits beyond M50's list
Not flagged by the rule: `Path.read_text(p)` (unbound call), `functools.partial(p.write_text, x)()`, `getattr(p, name_variable)()`, `p.replace(target=q)`. The contract's M50 list does not require them; noted so the next widening knows.

## Commands run (worktree D:/autoTesting/.claude/worktrees/mongo-u3d)
```
git -C <wt> log --oneline -5                       -> b4752163, 1cc3f851, 001d10d6 ...
git diff --stat 001d10d6 HEAD                      -> 29 files, no store/auth/core src file
uv run pytest tests/test_state_bypass_rule.py tests/test_sweep_u3a.py -o addopts=   -> 84 passed in 16.87s
uv run ruff check src tests scripts                -> All checks passed!
uv run autotester doctor > file                    -> exit 0, "doctor: clean"
uv run python scripts/mutation_check.py qa/evidence/mongo-store-u3d/mutations.json  -> 10/10 mutations killed
pytest pairs (7): 7; 33; 39; 28; 19; 20 passed; ui_bench_inputs+explore_consent 27/28 once, 28/28 x7
scratch rule probe (15 planted forms flagged, str.replace and keyword replace not flagged, 3 further gaps)
scratch sweep_orphans old-vs-new differential -> "3 3 True"
scratch InMemoryBackend probe -> disk tree [] before/after; valid_runs_newest_first reads the double
```

## What the maker must do for cycle 1
1. Finding 1: retag the three `bench_inputs` rows to `baseline` with an owner and an honest reason; adjust the owner-set test if a new tag is used; add the site to the readiness table.
2. Finding 2: add the store-routing test for the routed sites and a `sweep_orphans` test.
3. Finding 3: correct the readiness table (or state its limits) so G1 does not rely on it; no code change required beyond the manifest.
4. Re-run the ui_bench_inputs+explore_consent pair and record the result.
