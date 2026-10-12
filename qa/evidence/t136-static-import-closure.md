# T-136 static import closure inventory

Status: BLOCK pending unresolved vendor/import effects. This is a static inventory, not a runtime PASS, plan approval, checker verdict, or gate override.

Reviewed candidate: `C:/Users/Lenovo/.codex/worktrees/t136-bench-provenance/autoTesting`. Read-only PowerShell source reads and source-text import traversal only; no Python, import, collection, tests, models, network, subprocess from candidate code, environment values, or secret files executed/read. Inventory stopped at the parent-requested safe boundary after protocol steering; no claim that the newly supplied protocol was adopted.

`tests/test_bench.py` SHA256 directly measured: `D30E96955DAC237FF628AF5F8E159A77C7846B37729561C489D4F2130A4300C5`. Other supplied frozen-file digests were not independently remeasured by this reviewer. No frozen code file was changed.

## Test caller boundary

Full test file reviewed. 23 test functions, statically expanding to 32 nodes: ordering-independence 2, ordering-roundtrip 4, duration 4, kind/participant 3; the other 19 functions have one node each. This is a source count, not a collected count.

Reached bodies construct bench/verdict Pydantic objects, validate/serialize/deserialize them, call `BenchTrial.score` and `_eligible_truth`, and call `stages.bench.findings_from_verdicts`, `run_autotester_trial`, `oracle_human_trial`, and `scorecard`. The scorecard sentinel test temporarily replaces `BenchTrial.score` through pytest monkeypatch. The store test constructs `ProjectStore` with explicit `tmp_path`, reaches `save_bench_corpus`, `save_bench_trial`, `load_bench_corpus`, `list_bench_trials`, path accessors, and `filestore.write_json`, `_atomic_write`, `read_json`. It creates directories, uses mkstemp, writes, replaces and reads JSON under that temporary tree; it is not an entirely read-only test. No test body invokes CLI, browser, media prep, providers, consent, signing, real grading or execution.

`core.paths.ProjectPaths.__init__` uses explicit nonempty temporary root, so its `repo_root` environment fallback is not needed by this test. Artifact timestamp default factory runs on model instantiation, not class definition. Bench model-validator decorators register validation; validation bodies run at instantiation/validation, not merely import. Names mentioning a real run in bench functions do not themselves run a browser or model.

## Real package import boundary

`autotester/__init__.py:10` imports `autotester.cli.main`; importing a schema therefore imports the CLI first. `cli.py:10-22` imports CLI registration modules, providers, doctor, env, paths, ledger, expand, manual-login, report export, review, store. `cli.py:24-32` constructs Typer objects and registers subapps; decorators and final command registrations run at module load. `_bootstrap` is registered at `cli.py:35`; its `load_repo_env()` call at line 45 is inside the callback, not a module-level invocation. Bench tests never invoke the app or callback.

Source-text traversal (top-level absolute imports, multiline import lists and existing package parent initializers) returned 89 local module paths. This inventory is NOT an independently complete AST/import-resolution proof: conditional imports, dynamically imported names, vendor lazy exports and executable class bodies require further closure analysis. It must not be interpreted as an ALLOW.

Local families inventoried: package/CLI modules; schema base, bench, enums, issue-kind, verdict, analysis, approval, case, flowspec, issue, media, observation, portal-persona, project, run, screenmap, coverage, ledger, crawl, screen-graph, run-state, trace; store package, project-store, crawl-store, request-store, filestore; core package, paths, env, ids, trace, pricing, excel, redact, redact-fold, redact-encodings, redact-wrap, urls; provider registry/base/anthropic/gemini/gemini-files/gemini-schema/langchain-fallback/mock; browser package, secrets, session, assertions, evidence, launch, video; UI package, helpers, credential-guard; ledger package, render/store/relitigation; loop-status/doctor; stages package, bench, expand, manual-login, report-export, review, issues, orchestrate/orchestrate-runners, ingest, media-prep, merge-flowspec, explore-merge; media package, chunks/frames/probe/transcribe.

Provider sources fully read show registry stores classes (`providers/__init__.py:13-18`), rather than constructing providers. Anthropic/Gemini client imports and client construction are inside `_structured`; LangChain model factories and credential lookups are inside `_default_chain`/constructors/call bodies. These are not reached by bench tests. Media transcription imports subprocess at module load, but whisper import/model construction/subprocess calls are in functions; its main guard is false for normal imports. Core env source only defines the dotenv loader; it does not call it at top level.

## Concrete vendor effects and unresolved scope

Actual import path: `cli.py:10` -> `cli_issues.py:29` -> `stages/issues.py:26` -> installed `openpyxl/__init__.py:5-9`. `report_export.py:16` independently reaches openpyxl too.

Installed `D:/autoTesting/.venv/Lib/site-packages/openpyxl/compat/numbers.py:8-12` attempts importing numpy at module load. Installed `openpyxl/xml/__init__.py:10` imports lxml.etree inside `lxml_available`, which is called at module level at line 26; `defusedxml_available` is called at line 42. These functions may inspect vendor-selection environment keys (23,39). `openpyxl/xml/functions.py:24` constructs a native XMLParser when LXML is true; lines 62 onward register namespaces.

Read-only existence checks found numpy/__init__.py absent and the tested lxml etree CPython 3.11 extension path absent; the lxml directory scan returned no etree `.pyd`. These checks reduce evidence for that particular installed native path, but do not prove Python import resolution cannot find an alternate package on sys.path. No environment values were read and no import was attempted.

`D:/autoTesting/.venv/Lib/site-packages/pydantic_core/_pydantic_core.cp311-win_amd64.pyd` exists. The Pydantic/vendor metaclass and extension path still needs explicit scope/review if the intended authorization is strictly console-only native execution. Full installed closure of pytest, Typer/Click, FastAPI/Starlette, Pydantic/pydantic-core, openpyxl/et-xmlfile/defusedxml/dotenv and stdlib dynamic/native import behavior was not completed at this stopping boundary. No module-level network/client construction has been established in reviewed application sources; absence across the whole closure has not been proven.

## Decision

BLOCK pending unresolved import/vendor effects and explicit bounded-runtime scope. A proposed console audit is not an OS sandbox and cannot make unresolved native/vendor behavior safe by assertion. The unanswered `qa/gates/t125` full-suite gate remains untouched. No runtime, baseline collection, tests, commits, pushes, provider/model calls or production activity is authorized by this inventory.
