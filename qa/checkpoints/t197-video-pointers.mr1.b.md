# Checkpoint: t197-video-pointers merge-reconcile 1, coordinator B

Result: PASS (verdict `qa/verdicts/t197-video-pointers.mr1.b.md`). Cycle checked 2, merge-reconcile 1. Policy-Version proportional-verification/2026-10-10.9.

## Evidence identity
- Code: head df5d6f5b (tree 72e73d39e5f9), merge 89371ca4 (tree 0e427ff7f712), unit base b59dda0d (tree f40abd7d4776), master d42e9445 (tree be1d3a6685e9). Merge-base 09828f2d.
- Environment: three `git archive` copies on C: under the session scratchpad, one venv each, suffix 133531921. Windows 11, copy venv python with `-I`. Dependency lock = each commit's own `uv.lock`.
- Commands and results (all under `qa/evidence/t197-video-pointers-mr1-B/`):
  - `probes/review_rows.py` (75 rows) on unit and head: `res-review-unit.json` / `res-review-head.json` (sha256 prefix 6e4cfe992de9 / d9afb39d74ce); 74 equal, 1 differing (litellm in the known-provider list, from master).
  - `probes/master_rows.py` (43 rows) on master and head: `res-master-master.json` / `res-master-head.json` (f8cfb3d9e4d0 / 7c819ab86ea5); 40 equal, 3 differing (review line in `ingest --help`; two traceback line-number shifts).
  - `probes/tree.py` on all three: `tree-*.json` (head b4f1d77ab118); head = master + `ingest review`.
  - `probes/render_probe.py`: `render/hashes-*.json`; review hashes 6 of 6 equal, unified 2 of 2 equal.
  - `probes/paths_probe.py`: `paths_out.json` (7c74816f9d11); trees equal, values equal to the variant.
  - `logs/ruff-head.txt` (clean), `logs/doctor-head.txt` (clean).
  - `logs/fals1-*.txt` (146 passed to 61 failed), `logs/fals2-*.txt` (58 passed to 7 failed); the throwaway copies were discarded, the bound tree was never mutated.
- Data snapshot: synthetic recordings and fake provider only; no real data.
- Attribution: checker coordinator B (agent a578067a34123a9be), this file and the verdict.
- Not run, by instruction: full suite, real browser, real model, network.
- Invalid and excluded: `INVALID-v1-res-master-*.json` (harness bug, superseded by the re-run above).
