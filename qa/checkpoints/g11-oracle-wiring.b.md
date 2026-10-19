# Checkpoint B - g11-oracle-wiring (coordinator B, cycle 1)

Evidence identity (code SHA b2eb6c7b, head 9cca3e6d, worktree .worktrees/g11-oracle-wiring, deps = worktree .venv, uv.lock unchanged):
- verify run A: 9 unit files -> 97 passed. checker B (qa/evidence/g11-oracle-wiring-b/runA.log).
- verify run B: 22 importer files -> 385 passed, 26 failed; the same 26 fail on base 8b93e475 (runB.fails vs base.fails identical). checker B.
- diff scope: `git diff --name-only 8b93e475..b2eb6c7b` -> 34 files; no qa/contracts, no DECISIONS.md. checker B.
- lint: ruff clean; doctor only stale docs/SNAPSHOT.md. checker B.
- falsification: 7 isolated copies (D:/autoTesting/.work/tmp/ow-b-mut), all green before and red after on the named assertions; tool mutate_b_c1.py, outputs in qa/evidence/g11-oracle-wiring-b/mutants/. checker B.
- security read: gate, ceiling, signed max_probes, platform-only redirects, read-only mailbox, revert path read line by line. checker B.
Result: PASS. Remaining: none.
