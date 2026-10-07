# Checkpoint -- at757-timing (cycle 0, single checker)

Env: win32, uv/pytest from worktree .venv, HEAD 9e9712c8 (code c9832b19), uv.lock e9bfb8868a57, host heavily loaded

| check | command + scope | code hashes | result | attribution |
|---|---|---|---|---|
| diff read | git diff 642ab4bd..c9832b19 (7 test files) | timing_scale.py 23ee9ec2a018, wrap_perf 1630ae7bab83, ignorable_perf f9a51eb0ac3a, crawl_live b568538a9d06, mc_sessionstart 02ea0dfbe98d, video_sweep 95143f187e41 | 5 bounds equal original at 1.0; ratio guard and 15 s ceiling untouched | checker at757-timing c0 |
| touched tests, default scale | pytest test_timing_scale, redact_wrap_perf, redact_ignorable_perf, mc_sessionstart_loop_status, video_parallel_sweep, crawl_inventory_live (62 collected) | test_timing_scale.py 040d2fd14172 + above | 1 failed (wrap_perf 500KB, 3.25-3.7 s vs 3 s, host load), rest passed | same |
| wrap_perf+ignorable, scale 2 | AUTOTESTER_TIMING_SCALE=2, 30 collected | same | 30 passed | same |
| lint / doctor | ruff check src tests scripts; autotester doctor | same | All checks passed / clean | same |
| falsification | copy in scratchpad/fal/cp: sleep(7.0) in Redactor.contains_folded, node wrap_perf 500KB | redact.py mutated in copy only | mutated RED at unset (10.67<3.0), 1 (10.50<3.0), 2 (10.40<6.0); restored green at scale 2 | same |
| importer grep | git grep timing_scale -- src scripts qa/hooks | n/a | no hit | same |
| full suite | not run (policy .7, not security/prod-write) | n/a | n/a | n/a |
