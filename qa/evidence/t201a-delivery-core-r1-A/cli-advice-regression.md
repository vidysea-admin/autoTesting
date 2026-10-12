# t201a-delivery-core r1 A: tests/test_cli_advice_resolves.py regression (checker A, 2026-10-11)

Test: `tests/test_cli_advice_resolves.py::test_the_collector_reports_what_it_could_not_resolve`
(`assert unresolved_in_source(SRC) == []`, SRC = the checked tree's `src/autotester`).

| Tree (git archive, own folder on C:) | Command | Result |
|---|---|---|
| `7dd225d4` (head under check) | `python -m pytest tests/test_cli_advice_resolves.py -p no:xdist -p no:cacheprovider -o addopts=` | 1 failed, 32 passed. `Left contains one more item: (WindowsPath('delivery/inbox.py'), 130)` |
| `9b6d44c1` (Repair base, cycle 0 head) | same, `PYTHONPATH=<copy>/src` | 33 passed |
| `6504de03` (merge base, master at branch point) | same, `PYTHONPATH=<copy>/src` | 33 passed |
| `7dd225d4` inside the sharded full suite (`suite_run1.txt`) | shard 3 | failed, and `failed_still_failing_alone` lists it |

Cause (read at `tests/advice_scan.py:160-195` and `src/autotester/delivery/inbox.py:128-130`, this check):
`unresolved_in` flags every f-string that interpolates a bare `Name` with `id.isupper()` that it cannot
resolve to a string constant and that is not bound to a literal container. `"_CHANNELS".isupper()` is
True. `_CHANNELS = "|".join(...)` (inbox.py:78) is a call, so the scanner cannot resolve it, and the
repair's new `rf"(?:{_CHANNELS})__..."` at inbox.py:130 (`records_for_run`) is reported as a hole
(reported line = the f-string's start line, 130 in the numbering of the file as archived). Cycle 0 had
`f"{safe_id(run_id)}__*.json"` there (a Call, not a Name), which the scanner ignores.

Introduced by the repair diff `9b6d44c1..7dd225d4` (`delivery/inbox.py`). Not in the builder's affected set
(the three delivery test files); the scanner reads every file under `src/`, so any new f-string in any
product file can reach it.

Fix direction (not applied; the checker edits nothing): build that pattern without interpolating an
unresolved upper-case name into an f-string (concatenate, or bind the alternation to a lower-case name or a
literal the scanner resolves), then re-run this test. Do not change the test or `advice_scan.py`.
