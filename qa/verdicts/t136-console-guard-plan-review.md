# T-136 console audit correction — independent static plan review

Decision: APPROVE THE BOUNDED SCRATCH PLAN BELOW; not product PASS and not permission for full-suite/browser runtime.
Policy-Version: proportional-verification/2026-10-05.2
Cycle checked: 0 (plan review only)
Risk tier: L — changes a runtime refusal. This static review does not discharge tier-L runtime evidence.
Bound root: D:/autoTesting
Candidate: C:/Users/Lenovo/.codex/worktrees/t136-bench-provenance/autoTesting
Reviewed scratch: .work/t136-checker-baseline/runner.py
Pinned SHA256: 02304F871B95B515C219232D29D58081BFB3F889719BA864533234C9AEDE39B5
Budget: 25 minutes; no owned workload PID, no kills.
Contract references: core-invariants.md:42 (C4 scratch), :48 (C5 secrets), :76 and :132 (C7 independent verification and each new guard's falsification), :253 (C12 faithful measurements); t125-fullsuite-browser-egress.md:7, :11, :15 (scope exclusions and unanswered gate).

## Independent source findings

Sources were read as text, without importing packages or invoking Python/native libraries. The installed runtime is CPython 3.11, per `.venv/pyvenv.cfg`; source line references below are to this installation, not an inferred other version.

- `.venv/Lib/site-packages/colorama/win32.py:10-13` creates its own `LibraryLoader(ctypes.WinDLL)`, so object identity with `ctypes.windll.kernel32` would reject a legitimate wrapper. Lines 41-106 bind nine kernel32 symbols: GetStdHandle, GetConsoleScreenBufferInfo, SetConsoleTextAttribute, SetConsoleCursorPosition, FillConsoleOutputCharacterA, FillConsoleOutputAttribute, SetConsoleTitleW, GetConsoleMode, SetConsoleMode.
- `.venv/Lib/site-packages/click/_compat.py:516-517` imports the Windows console implementation on Windows. `.venv/Lib/site-packages/click/_winconsole.py:42-52` binds GetStdHandle, ReadConsoleW, WriteConsoleW, GetConsoleMode, GetLastError, GetCommandLineW, LocalFree from kernel32 and CommandLineToArgvW from shell32. Lines 103-104 bind PyObject_GetBuffer and PyBuffer_Release from pythonapi. These bindings happen at import even where a fixture never reads a real console.
- `C:/Users/Lenovo/AppData/Roaming/uv/python/cpython-3.11-windows-x86_64-none/Lib/ctypes/__init__.py:375-378` loads only when `handle is None`. Lines 461-462 construct `pythonapi = PyDLL("python dll", None, _sys.dllhandle)`: there is no pythonapi dlopen to allow on this Windows interpreter. Lines 443-447 cache a successful LibraryLoader load before returning it; line 473 resolves kernel32.GetLastError after that cache is populated. Hence the proposed canonical cache lookup can work during bootstrap without importing ctypes from inside the hook.
- The inspected Python source uses name-and-library tuple function construction at lines 393-394 and in Click at lines 48-52. The CPython C audit emitter source was not present among these inspected sources. No claim that native audit emission or real argument shapes have been runtime verified is made here; unexpected shapes must stop, not widen the policy.

The independently derived finite union is:

| Library identifier | Allowed symbol strings |
| --- | --- |
| kernel32 | GetLastError, GetStdHandle, GetConsoleScreenBufferInfo, SetConsoleTextAttribute, SetConsoleCursorPosition, FillConsoleOutputCharacterA, FillConsoleOutputAttribute, SetConsoleTitleW, GetConsoleMode, SetConsoleMode, ReadConsoleW, WriteConsoleW, GetCommandLineW, LocalFree |
| shell32 | CommandLineToArgvW |
| existing ctypes.pythonapi object | PyObject_GetBuffer, PyBuffer_Release |

## Exact approved edit boundaries and requirements

Only `.work/t136-checker-baseline/runner.py` may change, in place: its existing `audit` at lines 18-26, finite constants/state immediately preceding it, and its existing receipt block at lines 30-43. Product source, product tests, conftest, dependency manifests, platform identity, gates and contracts are outside this plan.

1. Preserve the existing socket/subprocess prefixes, existing os execution/spawn/fork event refusal, and `.env` basename refusal from lines 19-26. Hook registration at line 28 must remain before real pytest/product imports at lines 33 onward. Do not preload ctypes to bypass the hook.
2. For every `ctypes.*` event begin with denial. Permit `ctypes.dlopen` only for an exactly one-element tuple whose element is exactly the string `kernel32` or `shell32`. No basename normalization, substring, suffix, path, bytes, None, ordinal, or wildcard admission. This is the exact library spelling used by inspected sources, not proof of on-disk system DLL origin.
3. Permit `ctypes.dlsym` only for an exactly two-element tuple with a string symbol in the corresponding finite set. Read the already-present ctypes module via `sys.modules`, then its `__dict__`, without attribute fallthrough that might load a DLL. For kernel32/shell32 require the exact installed WinDLL type, an exact allowed `_name`, a canonical object already cached in the stdlib `windll.__dict__`, the canonical object's same exact WinDLL type and `_name`, and equal positive integer handles. A separately created Colorama wrapper can share that handle. Missing module/cache/name/handle, unequal handles, malformed objects or unexpected argument types must deny.
4. For the buffer pair require `lib is ctypes.__dict__["pythonapi"]`, the exact installed PyDLL type, `_name == "python dll"`, and `_handle == sys.dllhandle` with positive integer handles; no alternate PyDLL wrapper is admitted. Do not permit a pythonapi dlopen, arbitrary Python C API names or ordinal lookup.
5. Deny `ctypes.dlsym/handle` and all other `ctypes.*` events, including memory-address/string-address/call-function events, by default. Unknown imports failing on this boundary remain blocked evidence; they are not grounds for an automatic new allowance.
6. Receipt state uses absolute UTC ISO start/end and per-decision entries for each allowed or denied ctypes event, plus denied socket/spawn/env events. Record event, decision, reason, finite identifier and symbol where recognized, and safe integer handles where relevant. Do not stringify arbitrary event arguments, filenames or objects: that can leak values or invoke user-defined repr. Preserve existing candidate, PID, elapsed duration and status. A pre-pytest/import refusal records a stopped baseline, never a zero-node product pass.

Identity and safety limit: name/handle equality binds ctypes wrapper metadata to its canonical cached object. Those Python attributes are mutable, and bare-name loading uses the OS loader; this plan neither proves authenticated System32 DLL provenance nor prevents native calls bypassing Python audit events. Some allowed console functions have side effects and buffer access is native memory access. The plan is permissible only as a narrow compatibility instrument for statically reviewed cooperative pure fixture scope, never as an adversarial sandbox or OS-native egress boundary. If the intended claim requires either stronger identity or native containment, this plan is BLOCKED for that claim rather than silently upgraded.

## Independent named failing-first proposals — in memory, no native calls

Use an AST-selected copy of the existing audit function and constants in an in-memory namespace with inert sys/ctypes/library objects. Do not import ctypes, pytest or product modules for these policy tests. Run one asserted green baseline, then one single-hunk semantic mutation per newly changed family; assert the named assertion fails for the intended admission/recording reason. Never count import errors or generic nonzero exit as a kill. These are proposals; no tests or mutations ran in this review.

| Named assertion | Healthy arrangement | Single-hunk weakening that must redden it |
| --- | --- | --- |
| console_policy_rejects_nonexact_dlopen | exact kernel32/shell32 permitted; kernel32.dll, path, bytes, None, malformed arity and unrelated library refused | replace exact allowed-name membership with startswith or default acceptance |
| console_policy_rejects_symbol_or_handle_mismatch | legitimate canonical/Colorama same-handle wrapper permitted; wrong handle, unknown symbol, ordinal, cross-library symbol and missing canonical object refused | remove finite-symbol or canonical-handle condition, covering each changed admission branch in the batch |
| console_policy_rejects_noncanonical_pythonapi | exact pythonapi object plus two buffer names permitted; clone with matching name/handle, wrong handle and PyRun_SimpleString refused | remove object-identity requirement or broaden Python symbol set |
| console_policy_rejects_other_ctypes_events | ctypes.dlsym/handle, ctypes.call_function, ctypes.string_at and unknown ctypes event refused | invert/remove the default-deny branch |
| console_policy_keeps_prior_refusals_before_import | socket.connect, subprocess.Popen, os.system and open of .env refused; AST/source ordering places hook registration before pytest import | remove the original reject family or move registration after import, asserting each directly in one batch |
| console_policy_records_every_decision_utc | allowed and denied tuples yield distinguishable scrubbed entries; UTC start/end are present even on import refusal | omit one decision append or substitute elapsed-only/absence for absolute timestamps |

Each guard family above needs its own same-receipt failing-first row under core C7. Batch finite variants rather than spawning another proof-review cycle. Added test assertions are exercised by their associated semantic mutation; no recursive meta-test requirement is invented here. In-memory mutation never changes the candidate or judged runner bytes.

## Remaining execution gates

`qa/gates/t125-fullsuite-browser-egress.md` is unanswered and has no `Answered:` line. It explicitly permits safe mocked fixtures/isolated mutations while withholding full-suite/browser runtime and any native diagnostic retry whose required containment is absent. This review approves only the scratch correction and in-memory policy verification proposal. Before any real import/test retry, the owner must independently pin exact test nodes and statically trace the imported dependency/caller closure to cooperative pure fixture behavior. A grep alone is not that trace. If unresolved native/network/secret paths appear, stop that retry.

The remaining T-136 real affected baseline, product mutations and any feature-boundary full suite remain unrun in this review. Do not close a goal or mark a manifest checked-PASS from this document. Plan approval is not the completion verdict.

Metrics: start=2026-10-05T12:37:07.6518819Z end=2026-10-05T12:38:36.4039074Z suite_runs=0 repeat_runs=0 mutations=0 cycle=0 tokens=unavailable
Timing note: start is the first recorded UTC clock observation in this review; initial source reads preceded it, so total review elapsed is unavailable. End is the latest recorded UTC observation. No workload/native/network/model/browser execution occurred, and no process was killed.
