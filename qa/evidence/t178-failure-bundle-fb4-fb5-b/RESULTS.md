# Coordinator B evidence, t178-failure-bundle-fb4-fb5 at a7d3fa6c (git archive copy)

Runs (uv run --offline pytest -p no:xdist, one process at a time, copy `t178b-fb45/base`):
- FB4 set: test_schema, test_store, test_pinned_regression, test_ui_runs -> 60 passed
- FB5 set: test_expand, test_expand_cli, test_ui_learn, test_eval_compiler -> 61 passed
- containment + queue/regression/issues set: test_failure_bundle, test_run_queue, test_run_queue_resilience,
  test_ui_runs_queue, test_regression_proof, test_cli_issues -> 87 passed
- `ruff check src tests scripts` -> All checks passed; `autotester doctor` -> clean

Falsifications (own mutants, each in its own fresh git-archive copy, green before / red after):
- FB4 `list_cases` filter -> `if True or c.pinned or ...`: 3 passed -> 3 failed (list equality on selected ids, both nodes)
- FB5 `CaseProposal.approved_batch` returns `status != "x"` (pruned reach provider): 2 passed -> `assert 5 == 2`, `assert 5 == 0`
- Containment `load_bundle` `if not target.is_relative_to(root)` -> `if False`: 1 passed -> "escaped file reached hashing/read"
- Containment validator drops `".."` from the refused segments: 8 passed -> `[../outside]` red (the validator layer)

Adversarial pass: tests/test_attack_b.py and test_attack_b2.py (this folder; run in the throwaway copy).
- 33 hostile manifest names (traversal, drive letters, UNC, \?\, ADS, NUL/CON, trailing dot/space, %2e, fullwidth dots):
  all refused with PartialBundleError or resolved inside the bundle (CASE.JSON, `case.json.`, `case.json ` = same file); nothing hashed outside.
- 5 absolute spellings of a hash-matching decoy file outside the bundle: all refused, nothing hashed.
- NTFS junctions (mklink /J): to the bundle's parent, to a decoy dir, mixed-case names, a chain of two, all refused ("escapes");
  an inside-pointing junction loads. Bundle passed as a junction to a `.partial` dir, and via its 8.3 short name: refused.
- run id with `..\..\evil/../../x:y`: bundle id is content-hashed, every new path stays under out_dir.
- Priority filter over HTTP: empty, `P0`, `p0,p1`, `p9`, `p4`, `%20p0`, NUL, `null`, trailing empty: all 422 and no run created;
  absent = every case (default unchanged); four presses with four different filters each ran exactly their own set (entry.priorities);
  a pre-change queue row loads with priorities=None; a hand-written `p9` row is rejected by the model.
- FB5: `proposal_ids=[]`, unknown and `../../etc` ids, whitespace reviewer name: all refuse, 0 provider calls.
Findings: see the verdict (PROPOSED-ISSUE P1-P4). Reproduction for P1: `test_trace_leak_minimal[ab\ncd1234]` prints LEAK ['trace.jsonl'];
`ab"cd1234` and `ab\cd1234` fail closed (assert_clean), `abcd1234` and `ab<cd>1234&` clean.
Reproduction for P2: `test_compile_evals_partial_spend` -> 12 provider calls before the ValueError.
