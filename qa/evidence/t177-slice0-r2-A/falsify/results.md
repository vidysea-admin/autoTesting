# t177 slice0 r2 A - falsification results (bound tree 1f4f0514)
One throwaway copy per edit (no .venv, bound venv python, PYTHONPATH=<copy>/src:scripts:tests, rootdir = copy; autotester.__file__ inside the copy for every run - see result.json per dir).
Per dir: 1-green.log, 2-edited.log, (2b-edited-fullfile.log for quality probes), 3-restored.log, edit.diff, result.json. Driver: falsify-driver.py. Bound launch.py unchanged (restored_same=True everywhere).

| point | edit | green | edited | restored | first red message | survives? |
|---|---|---|---|---|---|---|
| 1a main | remove watchdog.start() AND `while True` (one hunk) | 3 pass | 3 FAIL (trickling[drip_body], trickling[drip_headers], closes_exposed_browser[drip_body]) | 3 pass | `the probe held start() for 5.0s against a 0.6s deadline` | no |
| 1a q2 | ONLY `while True` (watchdog kept) | 3 pass | 3 pass (full file 11 pass) | 3 pass | - | YES (watchdog covers it) |
| 1a q3 | ONLY delete watchdog.start() (loop kept) | 3 pass | 1 FAIL (trickling[drip_headers]); drip_body still passes | 3 pass | `held start() for 5.1s against a 0.6s deadline` | no (caught by drip_headers only) |
| 1b main | remove CL check AND size check | 3 pass | 3 FAIL (padded_declared, padded_undeclared, huge_reply) | 3 pass | `Failed: DID NOT RAISE CdpEndpointError` | no |
| 1b qa | ONLY remove declared Content-Length check | 3 pass | 3 pass (full 11 pass) | 3 pass | - | YES (stream cap covers it) |
| 1b qb | ONLY remove `size > PROBE_MAX_BYTES` | 3 pass | 1 FAIL (padded_undeclared) | 3 pass | `DID NOT RAISE CdpEndpointError` | no (only padded_undeclared) |
| 1b qc | read1(PROBE_MAX_BYTES+1-size) -> read1(65536) | 3 pass | 3 pass (full 11 pass) | 3 pass | - | YES |
| 2 | `except Exception` -> `except (OSError, ValueError, http.client.HTTPException)` | 2 pass | 2 FAIL (deep nested test, closes_exposed_browser[deep]) | 2 pass | `RecursionError: maximum recursion depth exceeded while decoding a JSON array from a unicode string` | no |
| 3 | on 3xx urlopen(Location).read() | 3 pass | 2 FAIL (redirect_never_followed[loopback_port], [other_host]); closes_exposed_browser[redirect] PASSES | 3 pass | `Failed: DID NOT RAISE CdpEndpointError` | no (caught by 2 of 3) |
| d | `reply.status != 200` -> `>= 500` | 11 pass (full file) | 11 pass | 11 pass | - | YES |

Wall time per pytest run 22-49 s (mostly fixed startup; the tests themselves are seconds).
Survivors: see report. 1a-q2, 1b-qa: redundant defence-in-depth layers (no behavioural difference observable). 1b-qc: reads up to 2x cap before refusing; no test asserts bytes buffered <= cap+1. d: no test sends a non-200 status carrying a correct-guid body (inferred, not run).
