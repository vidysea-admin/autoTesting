# bench-untimed-trial
Status: ready-for-check
Fix cycle: 0
Issue: AT-655 (medium)

Finding: master already implements the fix (BenchTrial.duration_s is `float | None`, default None;
score() emits duration_s None plus duration_s_unavailable_reason "timing not recorded"; FP rate
unavailable over zero findings) per bench.md K8. No source change needed.

Added tests (tests/test_bench.py): untimed vs timed vs mixed time-axis scoring with recall/FP
unaffected; legacy stored trial with no duration_s key loads as untimed. An explicit stored 0.0
stays a measurement (contract: measured zero preserved).

Verify: pytest tests/test_bench.py -p no:xdist -o addopts= -> 34 passed; ruff clean; doctor run.
