# Verdict - at887-crawl-to-flows (AT-887 + AT-890), coordinator B, repair check

Date: 2026-10-12 · Bound to `D:/autoTesting` · Policy-Version: proportional-verification/2026-10-10.9
Cycle checked: 1 · Dual check: coordinator B (blind; read no other verdict, checkpoint or evidence of this unit)
Head checked: b3a365a1 (product 54dced40), `Repair base: 6d70c0ec` verified an ancestor of HEAD; base 3748cb83 = `git merge-base b3a365a1 master`.
Verdict path: qa/verdicts/at887-crawl-to-flows.r1.b.md · Checkpoint: qa/checkpoints/at887-crawl-to-flows.r1.b.md · Evidence: qa/evidence/at887-crawl-to-flows-r1-B/

## Check plan (step 0)

Emphasis assigned: the data path end to end, with my own probes. Signals: logic changed (merge, expand prompt, route) -> own probes + falsification per repaired item; no UI markup changed (the route returns the existing themed refusal page, driven through the test client, no browser needed); no security-audit skill run (dual trigger already cited; the guard is exercised by probe 2). Work done in a copy extracted with `git archive b3a365a1` into a unique folder on C: with its own venv; `autotester.__file__` is inside that copy; every src/tests/scripts file hash-compared to the git tree (581 files, 0 mismatches, before and after the probes). No full suite, no suite lock.

## Block

VERDICT: PASS
SCOREBOARD: 3/3 repaired criteria met (F1 dangling ids, F2 guard refusal as themed 400, F3 per-step PII mask); 0 invariants touched and violated (C2: routes_learn.py exactly 300 lines, ruff clean, doctor clean; C5: secret guard probed)
TIER: L (dual-trigger src/autotester/stages/expand.py:183, the secret gate before `provider.act`; I read the line)
FAILURES: none
CAPABILITY-COVERAGE: 3/3 repaired rows reproduced by me (F1, F2, F3), each green before, red after, restored
LIVE-BROWSER: not-applicable (no UI markup or template changed; the Generate route and the merge button driven through the test client, results in p1/p2 evidence)
ISSUES-WRITTEN: none (dual coordinator; findings as PROPOSED-ISSUE below)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: The three repaired defects are gone on the data path through all three merge doors, with the provider spied and the encoded-secret path refused. Two low findings and one process note are listed; none blocks. The manifest does not claim to close AT-887 (it says both issues "stay open until the checker decides"); my view is that AT-887 stays open because the reachability warning is not built.

## Data-path table (probe 1: synthetic crawl graph, scratch project, no browser, no provider; doors = `cli_crawl._merge_into_flowspec`, `POST /projects/demo/crawls/<id>/merge` via TestClient, orchestrated `make_discover_runner` + `make_model_runner`)

Seed = APPROVED v4 spec with one human screen + one human flow (`flow_human`) plus the screens named in the case. After every run: `dangling_references(spec)` = [], flows well formed (unique ids, steps 1..n, step 1 NAVIGATE, entry/exit are held screens), `flow_human` and every seed screen present and equal.

| Case | Door(s) | Dangling | Flow ids before -> after | Version / review | Verdict |
|---|---|---|---|---|---|
| 1 no rediscovery | cli, ui, orch | 0 | 1 -> 3 (`flow_0dc10d14f690`, `flow_5f566a6230bf`) | 4 -> 5, DRAFT | OK |
| 2 one rediscovered node mid-flow (Courses -> `scr_courses`) | cli, ui, orch | 0 | 1 -> 3, same two ids | 4 -> 5, DRAFT | OK |
| 3 rediscovered entry and exit (Home -> `scr_home`, Detail -> `scr_detail`) | cli, ui, orch | 0 | 1 -> 3, same two ids; cli/ui flows cite `scr_home`/`scr_detail` | 4 -> 5, DRAFT | OK |
| 4 two crawl nodes (SPA states, same URL and name) -> one existing screen | cli, ui, orch | 0 | 1 -> 3 (`flow_e7954738788b`, `flow_8240c3f82483`); cli/ui both nodes cite `scr_dash` | 4 -> 5, DRAFT | OK |
| 5a/5b re-crawl, same crawl id, after case 2 / case 4 | cli, ui, orch | 0 | 3 -> 3 | 5 -> 5, bytes identical | OK |
| 5a/5b re-crawl, NEW crawl id, same structure | cli, ui, orch | 0 | 3 -> 3 (ids stable: path, not crawl) | 5 -> 5, bytes identical | OK |
| 5c re-crawl that adds one real leaf (Settings) | cli, ui | 0 | 3 -> 4 (`flow_68d6db7f8454` new) | 5 -> 6 (exactly +1) | OK |
| 6 crawl adds only flows (all node screens already held) | cli, ui, orch | 0 | 1 -> 3 | 4 -> 5, DRAFT, `review.by` None, `at` None | OK |
| 7 real cycle (A<->B, no root) | cli, ui, orch | 0 | 1 -> 1 (no flow) | 4 -> 5 (2 node screens added), DRAFT | OK |

Flow ids are identical across the three doors for every case. APPROVED human truth (screens and `flow_human`) never overwritten in any of the 39 runs. Raw output: `p1.txt`, `p1.json`.

## Generation probe (probe 2: crawl with 9 edges whose locators END in PII/secret tokens, merged by the CLI door, approved, proposals approved, provider = MockProvider spy; `p2.txt`)

- 9 provider calls, every prompt carries exactly these lines (asserted equal to the full expected list, all 10 lines, ordinals intact): `1. navigate https://demo.test/home?email=<email>` · `2. click text=Helpline <phone>` (+91 98765 43210, at end of step) · `3. ... Mail <email>` · `4. ... Fax <phone>` (415-555-2671) · `5. ... Office <phone>` (+44 20 7946 0958) · `6. ... Mobile <phone>` (9876543210) · `7. ... Call <phone>` ((415) 555-2671) · `8. click text=Token [REDACTED]:ST_PASS` · `9. click text=Other [REDACTED]:OTHER_KEY` (undeclared .env value) · `10. click role=link[name="Finish"] >> nth=0`. No raw secret, undeclared value, local part, phone digits or the base64 spelling in any prompt (0 hits each).
- Encoded secret planted in a step (base64, hex, single percent, double percent, reversed, upper-spaced), each through `POST /projects/demo/cases/generate`: 6/6 answer themed HTML 400, 0 provider calls, 0 cases written, neither the raw value nor the planted spelling in the page.
- Unrelated `ValueError` (probe 2 case C): a `ValueError` raised by the provider after the prompt was sent, and a pydantic `ValidationError` on the model reply, both show the user "Generating cases failed partway through: a prompt was refused unsent" (status 400, `provider_calls`=1). A `ProviderError` still shows its own text ("quota exhausted"). See P1.

## Falsifications (one per repaired item, each in its own `git archive b3a365a1` copy, PYTHONPATH at the copy, import path printed = the copy)

| Item | Edit (single hunk) | Green before | Red after |
|---|---|---|---|
| F1 | `explore_merge.py`: `alias = _rediscovered_ids(spec, nodes)` -> `alias = {}` | 3 passed | 3 failed (the model-level rediscovery test, the CLI door and the UI door tests), assertion failures, no import error |
| F2 | `routes_learn.py`: `except (ProviderError, ValueError)` -> `except ProviderError` | 1 passed | 1 failed: the guard `ValueError: refusing to proceed: raw secret value present ...` escapes the route |
| F3 | `expand.py`: per-step `mask_pii(...)` back to `mask_pii(steps_text)` on the joined text | 1 passed | 1 failed on the full expected lines (`2. fill phone field = <phone>\n3. click Continue...` not in prompt) |

Logs: `falsify-F1.txt`, `falsify-F2.txt`, `falsify-F3.txt`. Copies are throwaway folders under the session scratchpad.

## Static and scope (evidence `static-and-tests.txt`)

- Repair diff 6d70c0ec..b3a365a1 read in full: product 4 files (`explore_merge.py` +`_rediscovered_ids`, alias rewrite via the repo's own `screen_identity.rewrite_screen_refs`; `expand.py` per-step mask; `routes_learn.py` except clause; `explore_flows.py` docstring) plus 4 test files and the manifest. Tests: 189 insertions, 3 deletions, the 3 deleted lines are imports; no assertion removed or weakened.
- Whole-unit diff 3748cb83..b3a365a1: only files named in the manifest (docs/MAP.md and docs/SNAPSHOT.md are listed there). Nothing deleted or renamed in product code.
- `ui/routes_learn.py` = 300 lines (also in git). `ruff check src tests scripts`: all passed. `autotester doctor`: clean. The four affected test files: 55 passed (no full suite run).
- Manifest does not close AT-887: "AT-887 and AT-890 stay open until the checker decides"; clause 2 (reachability warning) listed "NOT built". No `qa/issues.jsonl` or goal change in the diff.
- Known, low wording: the manifest's "copy deleted" sentence is untrue (delete denied); not a FAIL.

## Findings (PROPOSED-ISSUE, none blocking)

PROPOSED-ISSUE: {"severity":"low","feature":"expand","title":"Generate route reports every ValueError as 'a prompt was refused unsent'","evidence":"src/autotester/ui/routes_learn.py:259 (read) catches ValueError broadly; qa/evidence/at887-crawl-to-flows-r1-B/probes/p2_generation.py case C: a ValueError/ValidationError raised after the prompt was sent (provider_calls=1) still shows 'a prompt was refused unsent'. With the real LangChainFallbackProvider a post-send ValueError is not reachable (its _call wraps every vendor failure in ProviderError; Case validators are not reachable from ExpandedSteps), so the reachable ones are pre-send: expand._reviewed_batch 'proposal differs from the staged current taxonomy', load_skill_prompt 'no YAML frontmatter'. Those are themed 400 pages with a wrong cause, not 500s.","fix":"catch the guard refusal by type (a dedicated exception from guard_expand_prompt) or show a generic 'could not generate' line for other ValueErrors; keep the no-echo rule"}

PROPOSED-ISSUE: {"severity":"low","feature":"explore","title":"Orchestrated DISCOVER->MODEL door leaves duplicate screens and flows citing node ids, unlike the CLI and UI doors","evidence":"qa/evidence/at887-crawl-to-flows-r1-B/p1b.txt: with human scr_home/scr_detail held, the orch door ends with 7 screens (human Home beside node Home, human Course detail beside node Course detail, no Conflict) and flows citing node_731f2b58a8db; cli ends with 5 screens and flows citing scr_home. merge_flowspec._new_screens adds by id only, so AT-102's rediscovery rule does not apply on this door. No dangling reference (F1 is satisfied); behaviour predates the unit.","fix":"decide whether MODEL's fold should apply the same rediscovery rule; separate unit"}

PROPOSED-ISSUE: {"severity":"low","feature":"process","title":"Shared scratchpad folder r1b-copy was overwritten by an unknown second extraction while in use","evidence":"files in my first extraction showed a second commit's mtime (01:07:15) and base-version content for cli_crawl.py, routes_crawls.py, orchestrate_runners.py, explore_merge.py; I deleted that folder and redid the check in a uniquely named folder, hash-verifying every file against the git tree. Disclosure: the deleted folder name matched my seat, so I treated it as mine; if another agent used it, its copy is gone.","fix":"coordinators use per-agent random folder names (the dispatch already asks for unique names)"}

Disposition of the issues named by the unit (for the maker, after both coordinators PASS): AT-890 is addressed by this unit (prompt masked per step, guard before `provider.act`, route answers the themed 400). AT-887 should stay open: the producer, the doors and the guard are in, but clause 2 (pre-run reachability warning) is not built.

Metrics: start=2026-10-12T01:04:00+05:30 (estimated from the first extraction) end=2026-10-12T01:31:00+05:30 wall_min=27 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=3 cycle=1 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=1620 mutants=0 defects_unit=0 defects_6c=0
slow: contaminated first copy, second extraction and venv sync about 8 min; within the L 45-min wall.
