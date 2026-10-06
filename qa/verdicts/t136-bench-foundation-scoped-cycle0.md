# T-136 bounded baseline receipt — cycle 0

VERDICT: INCONCLUSIVE — verification-incomplete
POLICY: proportional-verification/2026-10-05.2
TIER: L — goal-critical bench foundation and new schema validation/tests.
Cycle checked: 0
Bound project: D:/autoTesting
Candidate: C:/Users/Lenovo/.codex/worktrees/t136-bench-provenance/autoTesting
Pinned baseline: bd2fe8f4
Scope: tests/test_bench.py only; no formal unit PASS sought or granted.

## Binding and independent review

Independently recomputed SHA256 bindings before execution:

- src/autotester/schema/bench.py: E26D7CF40913AD758843E37A8577FEED0E742CDF1C07904C5F54F21D9D825ACA
- src/autotester/stages/bench.py: D9C61A7E29045D51E781E567FE617813850D5E3060043CC8EB645671DFF128F5
- scripts/bench_trial.py: 4F938379D64C3605920D9D824DDDE686C590AFE648B1C2551690013A8DFD5DE7
- tests/test_bench.py: D30E96955DAC237FF628AF5F8E159A77C7846B37729561C489D4F2130A4300C5

Read the complete checker skill (paginated), bench contract and core-invariant criteria. Reviewed the test file, schema, stage, actual package initializer, CLI imports, provider registry, environment bootstrap and persistence path. Tests call pure bench/schema logic and temporary ProjectStore roundtrips; no browser/model/network/process invocation appears in their bodies. Actual package imports were retained, not replaced by a synthetic package.

Independent score oracles derived before execution: live denominator excludes prompted S2 truth, leaving S1+S3 weights 3+1; machine high finding yields recall 3/4, human independent low finding yields 1/4; human false-positive rate uses all three reports, yielding 1/3. Missing ordering/kind/provenance/timing and zero reports must preserve unavailable values, while measured zero time remains numeric. These are reviewed expectations, not executed evidence.

## Gate and bounded command

qa/gates/t125-fullsuite-browser-egress.md: `Status: unanswered. No policy weakening, retry of stopped native diagnostic, or full-suite/browser runtime authorized by this record. Goal remains incomplete.` No Answered line exists. Safe mocked fixture tests are permitted; full/native/browser scope was not widened.

Exact command: `D:/autoTesting/.venv/Scripts/python.exe -B D:/autoTesting/.work/t136-checker-baseline/runner.py`

Runner configured plugin autoload off, --noconftest, no pytest cache, no bytecode, synthetic PYTEST_CURRENT_TEST, isolated AUTOTESTER_ROOT and tmp/XML paths. Before pytest or candidate imports its audit hook refused socket events, subprocess/native spawn/os.system/exec events, ctypes events and .env opens. No download/uv invocation occurred.

Owned PID: 50824. Tool execution chunk: 40eb62. No ongoing session handle was returned: process terminated immediately. One invocation only; no kill performed.

## Actual result

Process exit: 1. Guard receipt elapsed: 0.5085523128509521 seconds. Runner status sentinel: 3 because pytest.main never returned. Guard denied exactly one event: ctypes.dlopen.

Failure chain: pytest.main -> _prepareconfig -> pytest_load_initial_conftests -> _pytest.capture._colorama_workaround -> colorama.winterm -> colorama.win32 -> import ctypes -> ctypes.__init__ windll.kernel32.GetLastError -> _dlopen -> runner.py:26 `RuntimeError: CHECKER_GUARD_DENIED: ctypes.dlopen`.

This is an instrument setup refusal caused by the checker scratch guard blocking Colorama's Windows console initialization. It occurred before test collection and before actual autotester package imports. No product assertion failed. No test nodes executed; no baseline XML produced. Guard evidence is .work/t136-checker-baseline/receipt.json, runner source is .work/t136-checker-baseline/runner.py. No repeat was performed.

UNRUN: 32-node bounded baseline; all mandatory tier-L full-suite evidence; capability and changed-line mutations; feature-boundary sweep; real trial/browser/human comparison evidence. scripts/check_acceptance_comparison.py is absent and K9 remains outside this foundation baseline. No unit/goal close-out, commit or push performed.

Metrics: start=unavailable end=2026-10-05T18:02:33.8670689+05:30 suite_runs=1 repeat_runs=0 mutations=0 cycle=0 tokens=unavailable

The end value is the first post-run clock observation, not an asserted process completion timestamp; the runner recorded elapsed time but did not record an absolute start timestamp.

No formal PASS, no product FAIL and no fix cycle consumed. Overall verification remains incomplete.

## Read-only instrument diagnosis and proposed correction

Counter clarification (original metric preserved above): full_suite_runs=0; scoped_baseline_attempts=1; collected_nodes=0; executed_nodes=0. Absolute process start/end were not recorded and remain unavailable. A future runner must record `datetime.now(UTC).isoformat()` immediately before pytest invocation and in finally, plus own PID and process/pytest exit separately; it must not backfill these from this receipt.

Existing scratch runner: D:/autoTesting/.work/t136-checker-baseline/runner.py. SHA256: 02304F871B95B515C219232D29D58081BFB3F889719BA864533234C9AEDE39B5. Audit statement is line 19: `reject = event.startswith(('socket.', 'subprocess.', 'ctypes.')) or event in {` (function audit at line 18). No runner change or retry has been made.

Installed-code evidence: `_pytest/capture.py:156-161` calls `_colorama_workaround()` irrespective of capture method; the helper at lines 68-80 imports Colorama on real win32. Merely adding -s/--color=no does not remove this import. `_pytest/_io/terminalwriter.py:78-84` separately imports Colorama if its output stream is a TTY. `ctypes/__init__.py:473` resolves `windll.kernel32.GetLastError`; the loader at line 376 emits the refused DLL load. Colorama win32 initialization resolves only kernel32 console symbols: GetStdHandle, GetConsoleScreenBufferInfo, SetConsoleTextAttribute, SetConsoleCursorPosition, FillConsoleOutputCharacterA, FillConsoleOutputAttribute, SetConsoleTitleW, GetConsoleMode and SetConsoleMode.

Important independent import-graph limit: avoiding pytest's Colorama import alone cannot establish the actual product import baseline. Actual autotester -> cli -> typer -> click loads `click/_compat.py:517-518` -> `_winconsole.py`, which imports ctypes and resolves kernel32 GetStdHandle, ReadConsoleW, WriteConsoleW, GetConsoleMode, GetLastError, GetCommandLineW and LocalFree; shell32 CommandLineToArgvW; pythonapi PyObject_GetBuffer and PyBuffer_Release. This code also obtains stdin/stdout/stderr handles. This is ordinary installed Windows CLI support, not evidence of a product network or child-process call.

Smallest safe correction for the demonstrated pytest-only failure would be scratch-only `-p no:capture`, ordinary non-TTY file stdout/stderr, `--color=no` and `-p no:terminalprogress`; no sys.platform/os.name fake and no product patch. However the actual Click import still requires a reviewed finite native compatibility policy, so that change alone is not proposed as sufficient for a green runtime.

Candidate complete console-import compatibility proposal for fresh review: replace only the blanket ctypes prefix refusal at audit line 19 with event-specific refusal by default. Permit `ctypes.dlopen` only for the exact kernel32 and shell32 DLL identifiers observed in installed code; permit `ctypes.dlsym` only when its library object's `_name` identifies that allowed DLL AND its symbol is one of the exact console/argv symbols enumerated above. For the already-loaded pythonapi handle, permit only PyObject_GetBuffer and PyBuffer_Release, bound to `sys.dllhandle`, with no new python DLL load. Keep all other ctypes events denied, including dlsym by ordinal, pointer/address-based access, arbitrary DLL paths, unknown symbols and alternate handles. Keep socket.*, subprocess.*, os.system/exec/spawn/fork and .env read refusals unchanged and installed before imports. Record allowed DLL/symbol events separately from denied events. No general native allowance and no model/browser invocation.

Residual risk: an audit DLL-name check alone is not a native security boundary; bare DLL names and library handles need precise path/identity validation in the proposed implementation. ctypes permits cached symbols without a new dlsym audit event, so the permitted symbol set must itself be harmless to network/process creation. Arbitrary native extensions are not contained by Python audit hooks. The static pure-test scope is an independent precondition, and any unexpected import/native event must stop as instrument INCONCLUSIVE. Fresh independent review of an exact scratch-only patch is required before implementation or a retry; no runtime grant is implied by this proposal.

## Atomic pause after instruction replacement

At 2026-10-05T18:11:03.7571261+05:30 the root directed a safe-boundary stop pending current protocol re-read. Before this instruction, the exact scratch-only correction was applied under independently persisted plan approval qa/verdicts/t136-console-guard-plan-review.md SHA256 97A9B7DBE68B07FFFFA3C273319A7D819BD08795086DD6016EAEA969E4B9808C. Actual runner SHA256 after patch: B9CEE55D6CE0B746F4823D25767187FC48FED1D07DB642AB00EEDFA564406018.

Draft in-memory proof source exists at .work/t136-checker-baseline/policy_proof.py SHA256 DF6A8D560593961A9CCC53BD3B4EA9BB0F0D420460926A56CE59357218EAA467. It has never been executed and is not proof evidence; mutation-anchor correctness and UTC receipt proof remain unverified. No policy-proof result exists. The corrected runner has never run, and no retry/native/pytest/product import occurred after patch. No owned live PID/session remains. Product files stayed untouched. This checker has not read/adopted the replacement .3 policy and claims no compliance with it. Original setup INCONCLUSIVE and all outstanding verification remain unchanged.
