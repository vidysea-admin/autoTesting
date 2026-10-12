# T-125 cycle 4 — independent restore continuation

Bound root: `D:/autoTesting`. Checker scope: pending restore and final focused suite only. This is partial verification evidence, not a unit PASS or a consumed fix cycle.

Candidate: `.worktrees/t125-cycle4`. Existing checker copy: `.work/t125-checker-28c32c0da94b4c97bbacea853355d88d`.

Before and after execution, all 466 paths in the existing `freeze.xml` matched both candidate and checker copy by SHA256. No source restore or mutation was required. Freeze XML SHA256: `BBC636D7E73BFAC3F0C423F884D6B332887F4F798E828C89045F083676E8AA05`.

Resource prerequisite: CIM operating-system query denied; read-only GlobalMemoryStatusEx returned success, 87 percent memory load, 3066 MB available physical and 4668 MB available pagefile. A fresh thread started and joined successfully. No user process was stopped.

Both commands used cwd equal to the checker copy, `PYTHONPATH=<copy>/src`, `AUTOTESTER_ROOT=<copy>`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, synthetic `AUTOTESTER_APPROVAL_KEY=test-only-signing-key-never-a-real-secret`, and `D:/autoTesting/.venv/Scripts/python.exe`. Import binding independently printed `<copy>/src/autotester/__init__.py`. No provider, browser, network, installation or full-suite invocation occurred. Native outputs were redirected directly to retained logs without a pipe; native exits were captured immediately.

Pending restore command:

```text
D:/autoTesting/.venv/Scripts/python.exe -m pytest tests/test_ui_runs_serial_entry_order.py::test_internal_execution_spends_one_budget_across_tiers_and_all_legs --basetemp=D:/autoTesting/.work/t125-checker-28c32c0da94b4c97bbacea853355d88d/tmp-final-restore-1005 --tb=short --junitxml=D:/autoTesting/.work/t125-checker-28c32c0da94b4c97bbacea853355d88d/final-restore-1005.xml
```

Native exit 0: `16 passed, 1 warning in 10.21s`. XML independently read: tests 16, failures 0, errors 0, time 10.127. XML SHA256 `8246A12118EB639B6BFB781F4C7E934C01A105ABCD9470B4329F1B10C0C274F0`. Complete log is `<copy>/final-restore-1005.log`.

Final focused command:

```text
D:/autoTesting/.venv/Scripts/python.exe -m pytest tests/test_catalog.py tests/test_catalog_packs.py tests/test_ui_runs_serial_entry_order.py --basetemp=D:/autoTesting/.work/t125-checker-28c32c0da94b4c97bbacea853355d88d/tmp-final-suite-1005 --tb=short --junitxml=D:/autoTesting/.work/t125-checker-28c32c0da94b4c97bbacea853355d88d/final-suite-1005.xml
```

Native exit 0: `57 passed, 1 warning in 20.55s`. XML independently read: tests 57, failures 0, errors 0, time 20.546. XML SHA256 `9295C773CC715966D6F38DDB984235CE71B249FE856E6BF0FA1D70F6A833BB60`. Complete log is `<copy>/final-suite-1005.log`. Warning is the Starlette TestClient BlockingPortal deprecation.

Existing mutation evidence limitation: 13 mutation XMLs contain failures in named tests, and all preceding restores except budget-double are clean. Budget-double's old restore failure was `RuntimeError: can't start new thread`, not a product assertion; the pending rerun above supplies its green restore. However, `ct6-stop.xml` and `ct6-zero.xml` both fail the `Run.catalog_runnable_counts` complete-three-tier schema validator with `{}` before the intended executed-set oracle. Therefore 13 raw kills must not be compressed into 13 completed independent behavioral proofs. No mutation was rerun during this continuation.

CT6 correction PLAN ONLY: preserve the persisted three-key count map; in the existing checker copy, replace the single loop line in `ui/routes_runs.py::_execute_with_trace` from `for tier in tiers_to_run(cat):` to `for tier in (tier for tier in tiers_to_run(cat) if len(cat.runnable_in_tier(tier)) > 0):`. `runnable_in_tier` returns a list, so the gate must use its length. The current real-trigger fixture has zero runnable counts in all tiers; its existing test indexes `observed[0]` before checking IDs, so this corrected mutation would produce an IndexError, which is not the intended proof. Add exactly `assert sorted(observed) == sorted(c.id for c in cases)` immediately after the existing `observed` assignment in the existing checker-copy test, leaving every later assertion unchanged. This checks all nine fixture IDs and multiplicity before ordinal indexing, uses the existing real trigger and fake execution collaborators, preserves candidate tests, and leaves the production mutation one hunk. No new module or mocked subject. First green on both widths with the additive oracle, then source mutation red at that exact assertion on both widths, source restore green on both widths, and byte-restore the scratch test followed by frozen-hash comparison. Fresh plan approval and a new scoped runtime grant are required before applying or executing it. Helper ordering and zero-count schema kills remain distinct evidence.

Remaining unit gates include CT8 independent visible-browser evidence and full adapter verification with independently attributed residual failures. No verdict PASS, manifest close, goal close, commit of unit code or push is authorized by these focused greens.

## Approved CT6 continuation — actual evidence

Root subsequently granted the exclusive fixture lane after independent `review_t125_ct6_oracle` static APPROVE. The plan above was executed in the existing checker copy only. Before editing, the 466-path preflight matched both trees. Raw-byte backups `ct6-routes-original.bytes` and `ct6-test-original.bytes` matched original hashes `C69DB248043DBE771CFA19EFC891F20140316F982231015FD77649EF66AFCF30` and `87164314302F0CF18A490DABBA46CD4957195D22C258A3958364D7D64EE04137`. A fresh thread prerequisite succeeded.

Additive scratch oracle: `assert sorted(observed) == sorted(c.id for c in cases)` immediately after the existing observed-ID assignment, before every existing ordinal assertion. The source mutation anchor matched exactly once. One source-line mutation gated the dispatch loop on `len(cat.runnable_in_tier(tier)) > 0`. Mutated source SHA256 `CA42346F678BCE4B46C24959B4B5668E0F132BB1915D244F6A2C34311078FE26`; oracle test SHA256 `AA004CC6A08F6081CDEFDEA1FC8C267A7BAB0D78829F249DE99C7D38B3901D99`. Persisted count-map code remained unchanged.

Each invocation used the same interpreter, cwd and environment as the focused commands above. Exact common command prefix:

```text
D:/autoTesting/.venv/Scripts/python.exe -m pytest tests/test_ui_runs_serial_entry_order.py::test_real_trigger_orders_tiers_and_persists_blocked_pinned_cases
```

Each appended `--basetemp=<copy>/tmp-<name> --tb=short --junitxml=<copy>/<name>.xml`, redirecting directly to `<copy>/<name>.log` and immediately capturing native exit. Names and results:

| Name | Native exit / actual summary | XML tests / failures / errors | XML SHA256 |
|---|---|---|---|
| ct6-set-green-1005 | 0 / 2 passed, 1 warning in 2.30s | 2 / 0 / 0 | 9644C2BFDC7330AA168A344CB151F8F52737BBE9293FF655A5F9011CB10514D0 |
| ct6-set-red-1005 | 1 / 2 failed, 1 warning in 4.48s | 2 / 2 / 0 | E4F8960A47C674E32C2AB62582280E2F2C8313195CB7148149595FB7FC99966C |
| ct6-set-restored-green-1005 | 0 / 2 passed, 1 warning in 7.61s | 2 / 0 / 0 | C2DC3018EDD12B5B7AEDFDE464FCA5C57C22DDB1EE7AD30035F76089CB8CE2FB |
| ct6-original-final-1005 | 0 / 2 passed, 1 warning in 4.55s | 2 / 0 / 0 | E366EF35D4406315B22F1DC2F25B331886B0EEDE2FD8B704C04241918A211B48 |

The RED XML independently contains both named `[1]` and `[2]` width variants failing exactly `tests/test_ui_runs_serial_entry_order.py:171`, `assert sorted(observed) == sorted(c.id for c in cases)`: actual `[]`, expected nine stored IDs. The response-status assertion passed first. Thus this evidence reaches the intended missing-execution assertion, without a schema-validation failure, collection error or IndexError. It supersedes the old `ct6-stop.xml` as proof of the zero-runnable-tier dispatch filtering defect; the old file remains intact.

A `finally` block restored both scratch source and test from the exact raw-byte backups on every orchestration exit. Source restored green with the additive oracle first; after finally restoring the test, both original hashes matched, all 466 frozen paths matched candidate and scratch, and the final original test passed. A second 466-path comparison after that final run again had zero mismatches. No candidate files changed, no remaining gate was waived, and the runtime lane was released to root.
