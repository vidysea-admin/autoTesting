# Verdict - mongo-store-u3c

**Verdict:** FAIL
**Status:** FAIL
**Cycle checked:** 0
**Checker:** chk-mongo-u3c-a (independent; no other checker's verdict read)
**Reviewed SHA:** d0a9c516 (code commit 15079067, base 0a2cbe45), worktree `D:/autoTesting/.claude/worktrees/mongo-u3c`
**Contract:** `qa/contracts/mongo-store.md` M16 and the U3c unit-table row.

## One-line reason

The doctor rule (the M16 half) is sound, tested and non-vacuous. The sweep half of the U3c row is mostly not done: `core/trace.py`, `auth/audit.py` and `delivery/inbox.py` are untouched, `stages/schedule_store.py` has 1 of 16 raw sites rerouted, and the checkpoint has 1 of 3. 25 baseline rows are tagged `U3c-deferred`. FAIL on scope, not on quality. The route to PASS is a re-scope or an API decision, not rework of what was built (finding 1).

## Findings

1. **BLOCKING - scope of the U3c row is not met.** The row reads "E bypass sweep, trace, checkpoint (put_if), audit, delivery inbox, schedule store; doctor rule", judged by M16, whose text says "The bypass sites of design 3.3 are moved first (U3a-U3c)", and the contract's ordering risk is "U3 lands before U4 is switched on". Delivered: `orchestrate_checkpoint.py:257` (flush via `write_text`) and `schedule_store.py:245-247` (heartbeat via `write_text`). Not delivered: `core/trace.py:70,142,156`; `auth/audit.py:23`; `delivery/inbox.py:85,87,92,122`; `orchestrate_checkpoint.py:173,204`; `schedule_store.py:45,59,96,144,171,180,183,185,189,195,233,235,237,238,242` (25 `U3c-deferred` rows in `pyproject.toml`). The "explicit allow-listed scratch set" that M16 permits is for scratch, not for known state bypasses; a baseline of unmoved bypass sites is a debt ledger the contract does not provide for. I do not accept "can PASS with a partial sweep".
   - The maker's reason is real and stated honestly: `filestore.py` is at the 300-line cap (`wc -l` = 300), `_route` is private, and the coordinator forbade a private path-to-key helper. The `StateBackend` Protocol already has `exists`, `keys`, `create_exclusive`, `put_if`, `delete`, `delete_prefix`, `append_row` (`store/filestore.py:40-56`), so what is missing is a public path-level wrapper surface, which has no owning unit and needs either a D-entry for a module or a split of `filestore.py`. That is a coordinator or Umesh decision, not a maker one.
   - **Way to PASS (pick one):** (A) authorise a home for the path wrappers (new module via D-entry, or a `filestore.py` split) and have U3c use it for the 25 sites; or (B) a criticality-gated contract amendment that splits U3c into "U3c-1: rule + sites expressible today" and "U3c-2: the rest, after the wrapper unit". Under (B), the work as shipped would PASS U3c-1 with the warnings below. The checker makes that amendment only on an explicit instruction, and I have not made it.

2. **WARNING - half-routed state is a latent read/write split once a non-file backend is wired.** `flush` now writes through the store (`orchestrate_checkpoint.py:257`) but `_digest` reads `self.path.read_bytes()` (`:173`) and `_load` reads `self.path.read_text()` (`:204`). `write_heartbeat` writes through the store but `read_heartbeat` reads the path (`schedule_store.py:253`). With a non-file backend the stale-instance guard (`_check_disk`, M20) would compare None to None and always pass, and the heartbeat would read as absent. Not live today: `_backend` raises for any name but `file` (`filestore.py:194-197`), so there is no behavior change with `AUTOTESTER_STORE` unset (test `test_with_the_file_backend_the_heartbeat_is_the_same_file_as_before` passes). It must be closed in the same unit that wires the backend. The manifest records the read sites as deferred but does not call out this hazard.

3. **Home (question 1) - acceptable as a stopgap, with a cost.** `ledger/committed_fresh.py:1-18` is the only available home (`doctor.py` 300, `ledger/checks.py` 298, `ledger/render.py` 300, and a new module needs a D-entry), and the docstring says so and says to move it. The cost is real: the module's one job (`docs/MAP.md:101`, "committed blob must equal a fresh regeneration") is now two jobs, so "one concept, one place" is bent and MAP.md under-describes the module. The rule is wired in `doctor.py:298` through the same `check(base)` loop, with no special-casing. Condition: carry a follow-up item to move the rule into its own module once one is authorised; the file has 91 lines of headroom, so the bend is not urgent.

4. **Baseline robustness (question 2) - exact `file:line:kind` is acceptable for now, but costly.** Measured in a scratch copy: pin a row, add one unrelated comment line above the call, and doctor reports both `state-bypass` (new line) and `state-bypass-stale` (old line). 83 rows concentrate in a few files (`schedule_store.py` 15, `sources/intake_commit.py` 10, `ui/routes_role_accounts.py` 5), and 14 commits (log capped at 30) already touch `schedule_store.py` or `trace.py`. Every sibling unit that edits a baselined file must re-pin its rows. Keying on file + kind + enclosing function (with a count) would survive unrelated edits and still shrink on removal. It is a robustness improvement, not a blocker: the contract asks for `file:line`, and the brittleness errs on the safe side (red, never silently green). Recommend moving to function-keyed rows when the baseline is next touched.

5. **Recall (question 3) - the heuristic misses real state writes.** Run in a scratch root with an empty baseline (`check_state_bypass` against 24 hand-written cases in `stages/`; scratch deleted afterwards):
   - **Caught:** direct `ProjectPaths(..).x.write_text`; alias variable (`p = paths.runs_dir; q = p / "a"; q.write_text`); `os.replace(paths.tmp, paths.final)`; `shutil.copy(paths.a, paths.b)` and copy from a foreign source into a state path; `repo_root() / ".work" / x`; `paths.f.open("w")`; `json.dump({}, open(paths.f, "w"))`; `shutil.rmtree(str(paths.d))`; `Path(paths.f).write_text`; `self.p = ProjectPaths(..).f; self.p.write_text`.
   - **Missed (writes or mutations):** (a) a helper that returns a project path, then `.write_text` on its result (`d = helper(slug); (d / "a").write_text`), a documented limitation (manifest judgement 3); (b) `open(paths.f, mode)` with a variable mode (documented, judgement 6); (c) `paths.d.mkdir(...)` and `paths.d.touch()`, which are not in `_METHODS` (`committed_fresh.py:108`); (d) `os.makedirs(paths.d)`, because `makedirs` is not in `_OS_CALLS` (`:110`); (e) `from shutil import copyfile` or `from os import remove` followed by a bare call, because only `os.` and `shutil.` attribute calls are recognised (`:154`); (f) tuple-unpack taint (`a, b = ProjectPaths(..).x, ..`), because `_bindings` only handles single-Name targets (`:135`).
   - **Correctly not flagged:** `.read_text()` on a state path; a plain `path.write_text` on a parameter in a non-listed module (by design).
   - Only (c), (d) and (e) are cheap to close (add `mkdir`, `touch`, `makedirs`; resolve `from X import` aliases); (a), (b) and (f) are inherent to an AST heuristic. A sloppy mkdir on the container disk is low harm, but the rule's own docstring claims "no raw filesystem call on a state path". Also note the scan covers `src/autotester/**` only, not `scripts/`. Warning, not blocking: the baseline protects the known sites and the heuristic catches the common shapes.

6. **Stale-row check (question 4) - fires.** Scratch: an extra row for a nonexistent site gives `state-bypass-stale stages/gone.py:9:open`; a line shift gives a violation plus a stale row; a pinned row gives no violation. Matches `tests/test_state_bypass_rule.py`.

7. **Permanent rows - verified host or `.env` presence only, with one wrinkle.** `core/env.py:119` (`path.exists()` in `_device`) and `:121` (`path.stat().st_dev`): a host filesystem probe, no state read or write. `core/env.py:98` and `:197`: `path.exists()` on the repo-root `.env`, existence check only, no value read or written there. The wrinkle: the `.env` presence checks are credential-adjacent and U11 will have to revisit them; they are correctly tagged "U11 owns credential moves". None writes. The `permanent` list is a hand-curated pass-through for any flagged line in `core/env.py`, so a future write added to that module on a line in this list's neighbourhood still needs its own row (the match is exact, so it would be flagged).

8. **Behaviour with the store unset (M14 half).** `write_text` -> `FileBackend.put` -> `_atomic_write` (`filestore.py:66-98`) does the same temp + `os.replace` + `mkdir(parents=True)` as before; the heartbeat temp-file name changes (`.tmp-*` rather than `.<name>.<pid>.tmp`), which is benign. Diff of the two `src/` edits reviewed (`git diff 0a2cbe45 HEAD`): 6 lines in the checkpoint, 9 in the schedule store, no signature changed.

## Independent checks (all run by me in the worktree, `.venv`, `PYTHONPATH=src`, `-o addopts=`, two files per call)

| Command | Result |
|---|---|
| `python -m pytest tests/test_state_bypass_rule.py tests/test_state_sweep_u3c.py` | 33 passed |
| `python -m pytest tests/test_committed_fresh.py tests/test_doctor.py` | 48 passed |
| `python -m ruff check src tests scripts` | All checks passed! |
| `.venv/Scripts/autotester.exe doctor` (redirected to a file) | exit 0, last line `doctor: clean`; only the non-blocking `decision-citation-known-disputed` notes appear |
| `python scripts/mutation_check.py qa/evidence/mongo-store-u3c/mutations.json --repo .` | `14/14 mutations killed` (m1-m11 on the rule, s1-s3 on the sweep; each named test is the one that failed) |
| Scratch recall and stale-row probes | see findings 5 and 6; scratch dirs deleted; `git status` clean before the verdict |

`tests/test_schedule_tick.py` TS6 (unrelated, fails on master `0a2cbe45`) was not run and is not counted. No `.env` value was read or printed. Nothing under `src/` or `tests/` was edited; nothing merged or pushed.

## What the maker should do next (cycle 1 is not consumed until the re-scope or API decision lands)

- Wait for the coordinator or Umesh to choose A or B in finding 1. Nothing in the shipped code needs reverting under either.
- Whichever is chosen: close finding 2 in the unit that wires a non-file backend, and optionally cheap-close finding 5 (c), (d), (e) in place in `ledger/committed_fresh.py` with tests and mutants.
