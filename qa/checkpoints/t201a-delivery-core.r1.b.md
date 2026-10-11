# Checkpoint - t201a-delivery-core, coordinator B, fix cycle 1

Environment fingerprint: Windows 11 (NTFS, case-insensitive), CPython 3.11.15 in a uv venv built from `uv.lock` (blob 4882ef560a75) inside a `git archive 7dd225d4` copy on C: (folder t201a-r1B-u7k3 of the session scratchpad). `autotester.__file__` asserted inside the copy on every run.
Code identity (git blobs at 7dd225d4): inbox.py 7804f0ff8330, email.py 478ce461da75, schema/delivery.py a0c742d1616a; tree 2c1c55f23b65. conftest/fixtures: tests/delivery_fakes.py not used by my probes. Data snapshot: not applicable (scratch data root, synthetic example.com addresses).
Attribution: claude-sonnet-subagent, coordinator B, verdict qa/verdicts/t201a-delivery-core.r1.b.md.

| Check | Command / scope | Result |
|---|---|---|
| send-once matrix | `h.py matrix` (520 pairs x 4 passes, loopback sink, SmtpAdapter) | 520 messages, 0 suppressed, 0 exceptions, key/run lookups exact (matrix.json) |
| concurrency | `h.py concurrent` and `concurrent_skew` (6 procs x 4 threads x 200 rounds x 6 keys, 28 800 calls each) | exactly 1 message per key, 0 exceptions, 0 torn files (concurrent*.json) |
| stale close, real timing | `h.py stale` (4 scenarios, separate processes, 3 s stall) | never 2 messages, no exception in worker 1 (stale.json) |
| failure paths | `h.py failures`, `h.py longids` | contained; ValueError propagates for over-long keys, unreachable from product run ids (failures.json, longids.json) |
| report_url | `h.py url` (62 forms) | required refusals/accepts hold; non-ASCII digit port accepted (url.json) |
| lint, doctor, sizes | `uv --directory <copy> run --frozen ruff check src tests scripts`; `... autotester doctor`; wc and AST function lengths | clean; max file 272 lines; no function over 40 |
| affected tests | `pytest tests/test_delivery_smtp.py tests/test_report_email.py tests/test_delivery_failure.py -p no:xdist -o addopts=` in the copy | 97 passed in 5.45 s |
| falsifications | `fal.py` green copy, then 5 mutant copies from `mkmut.py` | each mutant reddens only its own check |
| full suite | not run (instructed; coordinator A owns it) | n/a |
