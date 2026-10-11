# Checkpoint - t200b-scheduled-test - cycle 1 - seat B (written by the seat B coordinator only)

Evidence identity (head 371eb7f62961b1d3130149e0cb53fc1b064b3dfe, product 6d6bc318; env: worktree .venv python, Windows, pytest -p no:xdist -o addopts=; no dependency or lock change in the repair range):
- code blob hashes: schedule_gate.py 0e076abe, schedule_store.py 67fabeba, scheduler.py 96e13553, explore_consent.py 679e87d3, schedule_tick.py 5de8bcb9, tests/test_schedule_tick.py 18c41acb, test_schedule_marker.py 9c0a3bca, test_schedule_gate.py acc30801
- Check 1: pytest tests/test_schedule_gate.py test_schedule_tick.py test_schedule_marker.py test_schedule_failures.py -> 61 passed (targeted-run.txt)
- Check 2: model, due, catchup, overlap, explore_consent, credential_run_approval, consent, approval_signing, env_loading -> 175 passed (neighbours-run.txt)
- Check 3: gate probe, 11 scenarios over real ProjectStore and ensure_approval_key in temp roots -> gate-probe.txt
- Check 4: purge probe: 3 spawned neighbours x 200 appends + 231 purges; hard kill at replace #1..#4; SystemExit; TOCTOU; late tick -> purge-probe.txt
- Check 5: 9 isolated-copy edits (F1a-F1e, F2a, F2b, scrub, parity), each green before and red after except F1d (blind spot, stays green); first F1e was an import error and is invalid, rerun valid -> falsification.txt, falsification-f1e.txt
- ruff check src tests scripts: clean; autotester doctor: clean
Result: PASS (verdict qa/verdicts/t200b-scheduled-test.r1.b.md). Attribution: seat B coordinator, claude-sonnet-subagent. No full suite run.
