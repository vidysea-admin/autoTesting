# Verdict - mongo-store-u7 (checker A)

**Verdict: PASS** (cycle 1; the cycle-0 block F1 is closed; two non-blocking warnings and four info items)
**Cycle checked: 1**
**Checked head:** `51fccd44` on `feat/mongo-store-u7` (code commit `67f08f54`, base `fe1ac6c8`). Worktree `D:/autoTesting/.claude/worktrees/mongo-u7`.
**Contract:** `qa/contracts/mongo-store.md` U7 row (dual): M19, M20, M52, M53. D-126 authorizes `store/filestore_paths.py`.
**Method:** fresh checker, own probes and own mutants, no other checker's verdict read. No `.env` value read or printed. Probes live in `.work/` (gitignored). Cycle 0 of this seat: FAIL (F1 escapable fences); W1-W3 and I1-I4 of that verdict are re-judged below.

## Cycle-0 findings, status

| Cycle-0 item | Status at `51fccd44` |
|---|---|
| F1 BLOCK, `scratch_*` / `evidence_mkdir` fences escapable (`..`, symlink, substring) | CLOSED. See "F1 re-attack" below: 0 escapes across `..`, symlink, junction (inside `.work/intake`, as `.work/gws`, as `.work/drive-fetch`, and under `qa/evidence`), look-alikes, `base` widening. |
| W1 half-written test does not bite | CLOSED. Mutant m16 (`os.link` replaced by in-place O_EXCL-then-write) is KILLED by the deterministic twin `test_an_exclusive_create_is_invisible_to_a_reader_until_the_whole_text_is_written` (named as sole killer in the spec, and it is the test that failed). The threaded test remains but is correctly not claimed as the kill. |
| W2 M25 gap lost its baseline marker | STILL OPEN, unchanged, not U7's to close (manifest judgement call 4 says so plainly). Goes to the contract owner. |
| W3 `.lock` sidecars under the data root in Mongo mode | STILL OPEN, unchanged, manifest routes it to the inbox. Not blocking. |
| I1 purge as staged move, not literal `delete_many` | Ruling stands: acceptable. |
| I2 heartbeat without CAS | Ruling stands: acceptable. |

## F1 re-attack (all against `store/filestore_paths.py:150-207`)

Code read: `_scratch` (`:150-162`) takes `os.path.realpath(path)`, requires it below `realpath(base or repo_root())/.work` and its first part in `SCRATCH_DIRS = ("intake","drive-fetch","gws")` (`:147`); every `scratch_*` verb then acts on the RESOLVED path (`:174-195`); `evidence_mkdir` (`:198-207`) requires the resolved path below `realpath(base or repo_root())/qa/evidence`. Python 3.11.15, Windows 11.

Probe `.work/probe_fence_c1.py` and `.work/probe_fence_c1b.py` (fresh temp repo per case, `AUTOTESTER_ROOT` set, state files planted under `projects/p`, `.work/team/schedule`, and an outside dir):

- Refused (`UnsafeName`) for all five scratch verbs, with `base=root` and with the default base: `.work/intake/../../projects/p`, `.work/../projects/p`, `.work/intakeX/y`, `.work/team/schedule`, `.work` itself, `projects/p`, a path outside the repo, `.WORK/INTAKE/../.../p`, `.work/intake/x::$INDEX_ALLOCATION`, `.work/INTAKE~1/x`.
- Links, 2 kinds x 2 targets x 5 verbs x 3 locations x 3 victim shapes, rebuilt per case: a symlink and a `mklink /J` junction at `.work/intake/lnk`, at `.work/gws` and at `.work/drive-fetch`, each pointing at `projects/` and at a directory outside the repo; victim = a child, `state.json`, the link itself. Result: `link failures: 0`, state files intact in every case. (My first run of this probe showed FAIL lines; they were a probe ordering bug, `scratch_rmtree(.work/intake)` removed my own links before the link cases ran. The rewritten per-case probe is the evidence.)
- `evidence_mkdir`, `base=root` and default base: refused for `qa/evidence/../../projects/e`, `projects/p/qa/evidence/z`, `xqa/evidence/y`, `qa/evidence_extra/y`, `<outside>/qa/evidence/o`; refused when `qa/evidence` itself is a symlink or junction to `projects/` or an outside dir (12 of 12).
- `base` keyword: `base=Path("/")` with a `projects/p` path, `base=<root>/projects` with `projects/p`, `base=<root>/projects/p` with `state.json`, `base=<root>/.work/..` with `projects/p`, `base=<root>/.work` with `.work/team`: all refused. A caller-supplied `base` can only RELOCATE the `<base>/.work/{intake,drive-fetch,gws}` subtree (and `<base>/qa/evidence`); it can never widen the fence onto `projects/`, `.work/team/**` or the repo root. Its remaining risk is a caller passing a base whose own `.work/intake` is somewhere harmful, so callers were checked:
  - `grep -rn "scratch_\|evidence_mkdir" src`: callers are `drive_intake.py:85-88,129,146`, `intake_commit.py:95-96,116,120`, `zip_intake.py:218`, `acceptance_baseline.py:124`. Every call passes `base=`: `store.paths.root` (a `ProjectPaths` root), `base` from `_sweep_stale(store.paths.root, ...)` (`drive_intake.py:182`), or `base=root` where `root = destination / mode` in `acceptance_baseline._write_pair` (`destination` is created `exist_ok=False` in `prepare_baselines`, `:100`; the only effect of `evidence_mkdir` is a `mkdir` under `<root>/qa/evidence`). None relies on the default base, none takes `base` from a request body.
- Allowed by design, observed: `.work/intake` itself (needed for `scratch_children(root)`), `.work/intake./x` (Windows strips the trailing dot, so it is `.work/intake/x`), `qa/evidence` itself.
- A junction and a symlink planted INSIDE a staging folder (`.work/intake/slug/jn -> projects`): `scratch_rmtree(.work/intake/slug)` removed the folder and the links and left `projects/p/state.json` (`.work/probe_fence_c1c.py`; Python 3.11 `shutil.rmtree` does not follow them).

Own mutants of the fences (`.work/mut-own-a.json`, run with `scripts/mutation_check.py`):

```
KILLED   own1 SCRATCH_DIRS adds "team"
KILLED   own2 allow-list dropped (anything under .work)
KILLED   own3 evidence check never refuses
KILLED   own4 anchor moved to base.parent (widened)
KILLED   own5 evidence anchor widened to qa/   (killed by the qa/evidence_extra look-alike case; my named kill id was the wrong one, the mutant did fail the suite)
SURVIVED own6 scratch_rmtree acts on the unresolved path after the resolved check (pytest exit 0)
4 killed outright + own5 killed under another id; 1 survivor (see I1)
```

Maker's spec: `mutations-fences.json` 5/5 KILLED (m10, m12-m15).

## Purge recovery (item 2)

`schedule_store._restore_stage` (`stages/schedule_store.py:163-195`): when stage copy and original both exist and `digest_path` is equal it calls `delete_path(held)` (`:187`), so the stage clears; when they differ it raises `FileExistsError` into the `except OSError` and keeps both (`:190`).

Own probe `.work/test_probe_purge_c1.py` (pytest, memory and fake-Mongo legs): the backend's mutating methods (`put`, `delete`, `delete_prefix`, `create_exclusive`, `put_if`) are wrapped; a hard kill (`BaseException`, `_restore_stage` disabled so no rollback) is injected BEFORE and AFTER every mutating backend call of one `purge_project` (13 calls on memory, 12 on Mongo, so 26 and 24 kill points). After each kill: `recover_stale_purges`; the state must be wholly intact or wholly gone (never partial), no `.purge-*` stage may remain, then a real `purge_project`, then a further `recover_stale_purges` must return 0 and no claim or record may return. Result: 2 passed, every kill point, both legs (end state rolled back 16 / committed 10 on memory, 15 / 9 on Mongo; in 2 of the 50 cases the injected kill was swallowed by the code under test and the purge ran on, still ending whole).

Maker's `test_purge_recovery_u7.py` (84 passed with the fences file). Mutant m17 (identical-branch disabled) KILLED. My own7 (`elif True`, recovery overwrites a differing file) KILLED by the unchanged AT-943 test `test_adopting_a_stale_stage_never_overwrites_a_file_that_came_back_in_its_place`. My own8 (identical branch does `rename_path(held, dest)` instead of delete) survives, but it is an equivalent mutant: the text is identical, so put-then-delete leaves the same store.

## Criteria

- **M19, PASS.** `core/file_lock.py`, `store/filestore.py`, `store/mongo_backend.py` are byte-identical between the cycle-0 code `13b79315` and `HEAD` (`git diff --stat 13b79315 HEAD -- <those>` empty), so my cycle-0 race evidence stands: 16 threads at one barrier, 200 repetitions per backend, `create_exclusive_path` 0 bad rounds on file, memory, fake-Mongo. Deterministic half-write twin kills the in-place mutant (m16 KILLED).
- **M20, PASS.** `put_if_path` CAS, the checkpoint `flush` CAS (`stages/orchestrate_checkpoint.py`) and `RevisionedFile` / `ui/run_queue.py` are unchanged since cycle 0 (same diff, empty); their tests pass (70 passed on `test_filestore_paths_u7.py` + `test_coordination_u7.py`); mutants m3-m9 KILLED (11/11).
- **M52, PASS.** READ-SIDE sites unchanged apart from `_restore_stage`, which now reads and lists through the store (`schedule_store.py:163-199`); the `test_coordination_u7.py` workloads end on an empty data root (except the known `.lock` sidecars, W2).
- **M53, PASS.** `git diff fe1ac6c8..HEAD -- pyproject.toml`: 65 `-` rows, 0 `+` rows, 0 changed lines outside rows tagged `U7` or `M53-gated`; `grep -c "| U7\|M53-gated" pyproject.toml` = 0; the `permanent` list (`pyproject.toml:119`) is untouched. `git diff fe1ac6c8..HEAD --name-status -- src | grep ^A` lists one new module, `store/filestore_paths.py` (D-126). No `mongo_bucket.py`, no `state_bypass.py`. The two new files under `tests/` are tests, not modules.
- **Fence stored-claim boundary (judgement calls 1-2):** accepted; staging stays local-disk and now truly cannot reach state.

## Findings

**W1 (WARN, non-blocking) - a stale stage can still put back a purged claim in the "different file came back" case.** `schedule_store.py:188-190` keeps both and leaves the stage (the AT-943 contract, and the right call for not overwriting). The stage's manifest then stays live. Probe `.work/test_probe_differ_c1.py` (memory and Mongo): hard kill after the first move of a purge; a NEW claim with different content is created at the freed key; `recover_stale_purges` returns 0 (stage kept); a later `purge_project` deletes the new claim; the NEXT `recover_stale_purges` returns 1 and `p:fixed:s1` is back. This is the same shape as cycle-0 B-class W3 but with a narrower trigger (a newer claim for the same key between a hard kill and the next purge of a project being deleted); it is the AT-943 tradeoff and is identical on the file backend, so it is not a document-backend regression. The cycle-0 trigger (identical copies from the non-atomic put-then-delete) is fixed and covered. Suggestion for a later unit: when a differing file is kept, also drop the manifest entry for it so a later recovery does not restore it.

**W2 (WARN, carried) - M25 CEO-bench list is not file-only; no row marks the gap** (manifest call 4). Not U7's; needs an owner in the contract or a baseline marker.

**I1 (INFO) - own6 survivor.** `scratch_rmtree` (`filestore_paths.py:191`) and its siblings act on the resolved path; a variant acting on the original path survives the suite because resolve-then-act versus act-on-original differ only in a check-then-use race window. Not exploitable here (callers are single-process under the intake lock) and the shipped code is the safer one; a test that swaps a link in between check and use would pin it.

**I2 (INFO) - `scratch_children` returns `Path(path)/name` (unresolved)** (`:180`); the follow-up verbs re-check each entry, so no escape (verified in the link matrix above).

**I3 (INFO) - `_lock_is_stale` double-takeover race and `delivery/email.py` raw `os.link`** unchanged from cycle 0 (pre-existing, outside the rule).

**I4 (INFO) - `docs/SNAPSHOT.md` stale** (doctor, below). Expected; generated, not a U7 input.

## Commands run (worktree `D:/autoTesting/.claude/worktrees/mongo-u7`; every pytest as `env -u ANTHROPIC_BASE_URL uv run pytest <2 files> -o addopts= -q`)

```
tests/test_scratch_fences_u7.py tests/test_purge_recovery_u7.py          -> 84 passed
tests/test_filestore_paths_u7.py tests/test_coordination_u7.py           -> 70 passed
tests/test_state_backend_contract.py tests/test_sweep_u3a.py             -> 341 passed, 1 skipped
tests/test_state_sweep_u3d.py tests/test_state_bypass_rule.py            -> 81 passed
tests/test_schedule_purge_crash.py tests/test_schedule_marker.py         -> 18 passed
tests/test_zip_intake_atomic.py tests/test_drive_intake.py               -> 26 passed
tests/test_acceptance_baseline.py tests/test_run_queue.py                -> 44 passed
ruff check src tests scripts                                             -> All checks passed!
autotester doctor (redirected to .work/doctor-c1-a.txt)                  -> exit 1, "2 violation(s)": stale-generated and stale-committed, both docs/SNAPSHOT.md (expected); no line-cap, design-rule or state-bypass finding. src files: filestore_paths.py 242, schedule_store.py 266, ui/run_queue.py 297 lines.
scripts/mutation_check.py qa/evidence/mongo-store-u7/mutations.json --repo .         -> 11/11 mutations killed (incl. m16)
scripts/mutation_check.py qa/evidence/mongo-store-u7/mutations-fences.json --repo .  -> 5/5 mutations killed
scripts/mutation_check.py qa/evidence/mongo-store-u7/mutations-purge.json --repo .   -> 1/1 mutations killed
own fence probes (.work/probe_fence_c1*.py)                              -> link failures: 0; state intact
own purge kill-point probe (.work/test_probe_purge_c1.py)                -> 2 passed (26 and 24 kill points)
own mutants .work/mut-own-a.json / mut-own-b.json                        -> own1-4 and own7 killed, own5 killed (other id), own6 survives (I1), own8 equivalent
```

Not run: the full suite in one invocation (low-memory rule). The 5 known environmental failures of `tests/test_role_port_authz.py` were not in scope of this unit and not run. M19 200x16 races were not repeated this cycle because the racing code is unchanged since the cycle-0 run (diff empty).

## Close-out

Everything this seat required in cycle 0 is met: the fences resolve before anchoring and cannot be widened by `base`, the half-write mutant is killed, the purge crash window between put and delete is closed, and M19/M20/M52/M53 hold with 65 rows gone and none moved to `permanent`. W1 and W2 are routed to the maker through the inbox; they do not block this unit. PASS from checker A; the dual PASS also needs checker B.
