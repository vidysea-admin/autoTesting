# Checkpoint - t201a-delivery-core - cycle 2 - coordinator B

Attribution: claude-sonnet-subagent, coordinator B; verdict `qa/verdicts/t201a-delivery-core.r2.b.md`; evidence `qa/evidence/t201a-delivery-core-r2-B/`.
Environment: Windows 11, uv 0.11.27, each copy with its own `uv sync --frozen` venv on C: (lock hash = uv.lock of the archived commit, unchanged between 7dd225d4 and 701a50e6). Code hashes: git commits 7dd225d4 (base), 701a50e6 / code 76ba7da5 (head).

| Check | Command and scope | Identity | Result |
|---|---|---|---|
| equality base vs head | `probe_equality.py build` then `dump` in the base and head copies; 88 deliveries, 149 records, 47 run lookups, 934 key lookups, 918 latest | dump sha256 6e5b01a2... for all four code x store combinations; build sha256 72610c54... | identical, 0 mismatches |
| cross-read | head code over base store, base code over head store | same hashes | identical |
| deliver_once basics | `probe_basics.py` on head: once, replay, 20 two-thread races | head copy | 1 send, 0 replay sends, 20/20 single send |
| repair diff | `git diff 7dd225d4 701a50e6`; whole-unit `6504de03..701a50e6` | commits | 2 files in repair; 13 in unit, all listed; guards untouched |
| head tests | `pytest tests/test_cli_advice_resolves.py tests/test_delivery_smtp.py tests/test_report_email.py tests/test_delivery_failure.py -p no:xdist -o addopts=` | head copy | 130 passed |
| lint, doctor | `ruff check src tests scripts`; `autotester doctor` | head copy | clean, clean |
| falsification m1 | f-string back, same 4 files | pristine copy m0 130 passed first | 1 failed: `test_the_collector_reports_what_it_could_not_resolve` |
| falsification m3, m4 | drop `__` / `.*` | m0 green | red (5 and 2 tests) |
| mutant m2 | drop `re.escape` | m0 green | 130 passed (unguarded; probe differs on 4 run ids) |
| pre-existing red | `pytest tests/test_hosting_deploy.py` on head | merge-base 6504de03 lacks the keys | 1 failed, not this unit |

Copies deleted by the coordinator after the run (names: `t201a_r2b_657a14737238_{base,head,m0..m4}` under the user Temp folder on C:).
