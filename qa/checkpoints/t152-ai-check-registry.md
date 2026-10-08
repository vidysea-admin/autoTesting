# T-152 — completed evidence identity

Original checker: `/root/check_t152`; verdict `qa/verdicts/t152-ai-check-registry.md`; cycle 0; Policy-Version: proportional-verification/2026-10-07.7; result PASS. Completed evidence 2026-10-08 07:02:17 UTC; unchanged-identity recheck for authorized persistence 07:40:11 UTC. Dispatch start/active-wall exact metrics unavailable; measured interval from first own clock 06:56:02 to completion = 6.25 minutes. No resumes; no full suite.

## Immutable input and environment identity

Root `D:/autoTesting/.worktrees/codex-t152-check`; HEAD `97103cf3e98e5fc774cfeddaea4bd7820f2c8c02`; T152 commit `4375739b`, base `3adc00d8`. Original and persistence states contain no tracked edits in src/tests/scripts/pyproject.toml/uv.lock: `git diff --exit-code -- src tests scripts pyproject.toml uv.lock` exits 0. This immutable commit-plus-clean-path identity covers all downstream imports and tracked fixtures/conftest. Explicit previously captured SHA256 hashes were rechecked and match:

| Input | SHA256 |
|---|---|
| src/autotester/schema/catalog.py | 49E4BC5172FA9F508C052C9CC60DEE084918C56D7D23957B205E9685C6BE6904 |
| src/autotester/schema/ai_check.py | 10B9DF5A780EAD3ABC25C0A39FDDBB2B1277BF1ECA74BBC1E8D3774C7B4B87AB |
| src/autotester/stages/ai_catalog.py | 7478A9EEDD548B9D20D1347C1F32163D7313E33FC904CEE016198A69053F4785 |
| tests/test_ai_catalog.py | 5F611E1848E1DFAE0D1525D2F393AA7D35D5B9707460F35B63A7832CEF141A15 |
| tests/conftest.py | 9BBB6A4BC2BE7EB9ADFB1B6ADFDFCC8DA4708287349ECB108A0C66C99FF4652A |
| pyproject.toml | 4B56E19C01E8BCC00450B51A32360CE8466BD3090BB9F548F20A8A7E05F2B0F0 |
| uv.lock | 0F25D574AE096863A23B6F6E1B03E3D797E1BDEC10341C5316A848AEA937F41D |

Additional hashes computed at persistence; original execution identity for these was the same unchanged committed HEAD, not an invented prior SHA sample:
- tests/test_catalog.py `370B3BF8A34CCE361A5FC431C991E63A3F31A092AE27D8AF26AA57CEDBF2DEEF`
- tests/test_catalog_packs.py `9E21D415AAAC45DC8288FD6FE1A85CA6C7FCF4606C512ECFF409861CB308DFA5`
- tests/test_ui_catalog.py `312E6211CFACD66F8AC57F61157AC16980DC38798DFB0A51A92DCA84043FD6DD`
- tests/test_schema.py `6C9947AAB86A33403E9C25E275CBDB705B5AA302077606DD6374FCB7D7E861E9`

Python executable `D:/autoTesting/.venv/Scripts/python.exe`; original runtime fingerprint Python 3.11.15, Windows 10.0.26300, pydantic 2.13.5, pytest 9.1.1. Actual imports printed own checkout src paths for ai_catalog and catalog. PYTHONPATH own src; TEMP/TMP own `.work/temp`. No service/build/deploy/data snapshot applies: synthetic API-only registry/fixtures, no live target. No dependency install or mutation. Native protocol checker SHA256 `4C153467FC9F826601F67A8DD66E233402AA9F26B4FC65AEBFFD2FA96F5ACC90`; maker protocol pin `11E05EC50948AFF374EB95925C98EFF7344E819501C285B6538C77B9C9A6CFB0`.

Persistence runtime recheck: `D:/autoTesting/.venv/Scripts/python.exe -c 'import sys,platform,pydantic,pytest; print(sys.version); print(platform.platform()); print("pydantic",pydantic.__version__,"pytest",pytest.__version__)'` printed the same versions/OS above. Post-write `git diff --exit-code -- src tests scripts pyproject.toml uv.lock` again exits 0. Source/config/fixture/environment identity has no observed change; no required rerun is outstanding.

## Commands and actual outcomes

From own root with environment above:

`D:/autoTesting/.venv/Scripts/python.exe -m pytest tests/test_ai_catalog.py tests/test_catalog.py tests/test_catalog_packs.py tests/test_ui_catalog.py tests/test_schema.py -m 'not harness' --basetemp D:/autoTesting/.worktrees/codex-t152-check/.work/temp/affected-elevated -o faulthandler_timeout=30`

Collected 93; exit 0, `93 passed, 1 warning in 0.96s`. Native escalation approved, no external targets. Warning is Starlette's deprecated BlockingPortal alias. Sandbox default TEMP setup denial and first-TestClient stall were interrupted and excluded as infrastructure failures, not product evidence.

`D:/autoTesting/.venv/Scripts/python.exe -m ruff check src tests scripts` -> `All checks passed!`. Touched-path independent lint: `-m ruff check src/autotester/schema/ai_check.py src/autotester/schema/catalog.py src/autotester/stages/ai_catalog.py tests/test_ai_catalog.py` -> exit 0, `All checks passed!`.

`D:/autoTesting/.venv/Scripts/python.exe -c 'from autotester.cli import main; main()' doctor` -> standalone exit 1, only T125 `ledger-row-missing`, one violation. Independently traced to base3adc's already-done high-value task plus no T125 FEATURES row; T152 changes neither record. No new T152 design violation. No-op module-mode CLI attempt is excluded.

## Seven independent falsifications

Every row runs `D:/autoTesting/.venv/Scripts/python.exe -m pytest tests/test_ai_catalog.py::<node>` in a separate disposable copy under own `.work/temp`, with copy PYTHONPATH and no __pycache__/.pytest_cache. All assert baseline exit0, one anchor/changed bytes, mutant exit1/explicit intended FAILED node/no collection error, finally restoration byte equality, restored exit0. Zero setup failures counted as kills. Successful rows:

| Criterion | File and single-hunk mutation | Failed node | green/red/restored |
|---|---|---|---|
| AI2 | ai_catalog.py: AGENTIC tuple gains _HANDOFF | test_every_target_kind_has_exactly_its_literal_entry | 1/1/1 |
| AI3 | ai_catalog.py: exact str type guard becomes isinstance | test_an_out_of_table_kind_is_refused_never_mapped[hybrid] | 11/1 fail plus 10 pass/11 |
| AI4 | ai_catalog.py: base entries/packs replaced by empty lists | test_match_extends_the_projects_catalog_without_touching_its_web_rows | 1/1/1 |
| AI4/CT7 | ai_catalog.py: add class Catalog(Catalog): pass | test_there_is_one_catalog_and_one_blocked_reason_in_src | 1/1/1 |
| AI5 | ai_catalog.py: ground-truth blocker becomes if False | test_no_ground_truth_blocks_only_the_ground_truth_check | 1/1/1 |
| AI5 | ai_catalog.py: endpoint blocker becomes if False | test_no_endpoint_blocks_every_applicable_check_naming_the_endpoint | 1/1/1 |
| AI5 | schema/catalog.py: blocked state becomes False | test_a_blocked_entry_without_a_reason_cannot_be_built | 1/1/1 |

A multiline schema anchor missed because of CRLF, aborted before mutation; excluded. Successful replacement guard mutation is the final row. Full original raw evidence and outcomes authored by this checker remain in the dated T152 section of `qa/feedback-inbox.md`.

No mandatory unit checks remain. Parent maker owns merged integration and closeout. Formal QA persistence authorized by relayed human instruction, no product/manifest/goal edit, contract change, commit or push by this checker.

Metrics: start=unavailable end=2026-10-08T07:02:17Z wall_min=unavailable agent_min=unavailable blocked_min=unavailable suite_runs=0 repeat_runs=0 mutations=7 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-07.7
