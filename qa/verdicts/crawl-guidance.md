# Verdict - crawl-guidance (Checker A, contract)

**Verdict:** FAIL
**Status:** FAIL
**Cycle checked:** 0
**Reviewed SHA:** 3e9efa0d6b3ac868099ab09d7760d20b3a404ffe (code/test SHA 9760bac3, base b1ffaf27, branch feat/crawl-guidance)
**Scope:** crawl-guidance Units 1-4, criteria G1-G11, G12 held; amended explore.md X12 and crawl-traversal.md CR6. Checker B (`crawl-guidance.b.md`) is separate; this is the contract check only. No real model called; no src or test edited; no merge, no push.

Two must-fix defects (F1, F2). Everything else holds. Both are small, local fixes; neither needs a contract change.

## Must fix (cycle 1)

**F1 - A guided crawl on a project with no persona writes a graph-only `portal_persona.json`, and the next persona build then loses the profile (G2 "order only", G7 "removing annotations resets reuse and nothing else").**
- `src/autotester/stages/explore_guidance.py:202` builds `PortalPersona(project=slug)` when none exists, and `:234` (`_remember`) saves it mid-crawl.
- `src/autotester/stages/portal_persona.py:213` (`_merge`) treats `existing is None` as the first persona and returns `incoming` whole with `_initial_summary`; with a non-None `existing` it takes the add-only branch (`:225-228`) which keeps `existing.profile` and updates only `overview`.
- Reproduced two ways. (a) `_merge(None, incoming)` gives profile `'Demo' 'https://app.test/'` and summary "initial persona: ..."; `_merge(PortalPersona(project='demo'), incoming)` gives profile `'' ''` and summary None. (b) A guided `run_crawl` over the fixture site (project opted in, bounds on, capturing fake model) leaves `projects/demo/portal_persona.json` with `profile {'name': '', 'base_url': ''}`, 0 screens and one guided graph node. The crawl itself never writes a persona (the guidance-off baseline shows none), so guidance created it.
- Effect: opting in silently strips the persona header (name, base_url) and the "initial persona" revision of the next `build_portal_persona`; `_add_screens` (`stages/knowledge_graph.py:31`) also keeps the guidance-created node, so its label is the URL path rather than the screen name. All of this changes persisted output beyond order.
- Fix direction (maker's call, edit in place): do not create a persona from guidance; keep the annotation only when a persona already exists, or seed `profile` (name, base_url) the way `_build_incoming` does (`portal_persona.py:158-162`). Add a test: guided crawl with no persona, then `build_portal_persona`, profile equals the unguided result.

**F2 - Truncation happens before the scrub, so a secret value cut by the cap leaks a prefix (G3).**
- `src/autotester/stages/explore_guidance_payload.py:54` `scrub(el.name.strip()[:NAME_CHARS])` and `:66` `scrub(node.title.strip()[:TITLE_CHARS])` cut first, then scrub. The redactor and `assert_no_raw_secrets` (called from `explore_guidance.py:131`) both match only the full value, so a cut value passes both.
- Reproduced with `build_payload` and a `SecretStore` holding a planted value: a control named `"A"*50 + SECRET` is sent as `AAAA...AAAZq9-Plante`; a title `"T"*70 + SECRET` as `TTTT...TZq9-Plante`. `guard_prompt` on the finished prompt PASSED (did not refuse) and the 10-char secret prefix is in the outbound text.
- Contract G3: name is "trimmed, and passed through `scrub_optional`" and egress is approved for a payload with no credential value. A partial credential is a credential leak on the one path that sends text to an external service. Probability is low (a secret has to sit inside a control name or title); the gate exists for exactly that case.
- Fix direction: scrub the full string, then truncate (`scrub(name)[:N]`), for name and title. Add a test with a secret straddling the cap (the maker's planted-secret test places it at the start of a short name, so it cannot see this).

## Criteria

| # | Verdict | Evidence |
|---|---|---|
| G1 permutation | PASS | `explore_guidance_payload.py:77-102` one range/duplicate filter (`clean_indices`), `complete_order` appends unmentioned in rule order, `reorder` indexes the code's own list; cap 80 at `:28`, tail appended at `explore_guidance.py:115`. Property tests pass. **My sabotage** (range check removed in a scratch copy): `test_crawl_guidance_payload.py` fails 4 cases (`AssertionError ({'ranked': [1, 11]}, [1, 11, 0])`). |
| G2 reorder only | PASS (see F1 for the side effect) | `explore_traversal.py:107-121` `ordered_candidates`: split via the same `is_destructive` as `destructive_last` (`explore_safety.py:154-156`), model sees only ordinary pressable controls, result `[*model, *unpressable, *destructive]`. Seam tests (reverse, garbage, denied-ranked-first, injection label, bound still fires, 60 fuzzed rankings) pass. **My sabotage** (destructive tail moved ahead): `test_no_destructive_control_is_ever_ahead_of_an_ordinary_one` fails. Residual by design: when a `max_screens`/`max_actions` bound binds, order decides which screens are reached; G12 is the place that measures it. |
| G3 redacted text-only payload | FAIL (F2); otherwise PASS | Independent run: full `run_crawl` with a capturing fake provider over a screen with query-string hrefs (`?token=...#frag`, `?session=...`), two `in_row` controls named like people, a password textbox, a control named with a planted secret. Payload sent: path-only hrefs (`/students/`, `/settings`, `/help`), `<row item>` with empty href for both rows, `type: password` with no value, name `Export [REDACTED]:PLANT_KEY`, no query, fragment, token, cookie, person name, password value or image. `ElementRef` has no value field (adding one raises `extra_forbidden`), so an input value cannot be carried. Provider `guard_text` received exactly the finished prompt (1 guarded == 1 prompt). Persisted files (`portal_persona.json`, crawl dir): planted secret and password absent. Core guard `explore_guidance.py:131` runs before the call; **my sabotage** (guard removed): `test_the_core_secret_check_refuses_even_if_the_scrub_and_the_provider_guard_are_absent` fails. Repair calls: `litellm_provider._complete` calls `_guard` on every physical request, and `model_chain._run` guards before the tier loop. Note (allowed by G3, not a defect): `title` is sent as the page title; on Pathlynks a detail screen title may carry a person's name even though control names in rows are masked. Umesh's egress approval (D-118 a) names `title`, but he should know before Unit 5. Another note: the fixture site's `title()` returns the URL, so the example host shows in `title` in the fixture; that is the fake, not the code. |
| G4 fallback with reason | PASS | `explore_guidance.py:104-115` catch-all, `:183` `_fell_back`, `:167-181` breaker at `STRIKES=3`, `:279-288` reasons, `:251-266` rule-only label. 35 core+kg tests pass, including each failure kind, the three-strike test, the all-fail label. Nested budgets verified in `providers/attempts.py:36-82`: an inner `ModelChainProvider` scope (`model_chain.py:131`) cannot loosen the outer `attempt_budget(2, cap)`, since `reserve_attempt` checks every enclosing scope. |
| G5 off by default, byte-identical | PASS | `schema/project.py:240` None default; `schema/crawl.py:90-95` new bounds None; `explore_guidance.py:63-67` `attach` needs guide AND opt-in AND bounds on; `explore.py:251,281`. **Independent baseline check:** I ran the fixture crawl on `git archive b1ffaf27` (base src + base `crawl_fake.py`, PYTHONPATH from a scratch dir; imported module path confirmed to be the scratch copy) and compared against the checked-in `tests/fixtures/crawl_guidance/baseline_*`: crawl.json, nodes.jsonl, edges.jsonl all IDENTICAL, so the baseline is genuinely pre-change. Pre-change signed approval row verifies (test passes; `RunApproval` signs actions/probes/wall_clock only). Importing `autotester.stages.explore` loads no litellm/anthropic/google SDK (checked), and the same 16 `autotester.providers.*` modules load on the base tree, so import behaviour is unchanged. |
| G6 bounded, counted | PASS | `explore_guidance.py:152-165` `_call`: `attempt_budget(2, wall_clock_s=min(per_call, total - model_s))`, model seconds read off `rt.clock`; `_blocked` enforces calls/total. Timeout also reaches the socket (`reserve_attempt` clamps `kwargs["timeout"]`, `litellm_provider.py` `_complete`). Tests pass. |
| G7 KG storage and reuse | PASS (F1 caveat) | `schema/portal_persona.py:215` additive `GraphNode.guidance`; `explore_guidance.py:208-236`; reuse key = candidate hash + prompt version (skill version + body hash) + model tag in the pinned set; no `crawl_guidance*` data file exists (find shows only the schema module, test support and fixture dir). `build_graph` deep-copies the graph (`knowledge_graph.py:83`) and `_merge` `model_copy` keeps it, so annotations survive later persona builds. Note: reuse accepts a ranking from either pinned model (`:214` `note.model in self.models`), so a stored fallback-model ranking is replayed even if the primary is back; reasonable reading of "exact model tag", flagged not failed. |
| G8 pinned models, served tag | PASS | Built the real `ModelChainProvider` from `GUIDANCE_SPEC` (no call): order `['ollama_chat/deepseek-v4.1-flash:1017', 'ollama_chat/glm-5.3-flash']`, `implicit_fallback: False`, tiers = those two only, no Gemini. `Crawl.provider` is `cap:cap-1` for the capturing fake in my run (the served tag). Note: on a pure KG replay (0 calls) `Crawl.provider` names the model that produced the stored ranking (`_note_served`, `:216`) while `guidance.calls == 0` and `kg_hits > 0`; the summary disambiguates, not blocking. |
| G9 one module, one seam | PASS | `grep -rnE "^(import\|from) (anthropic\|google\|litellm\|ollama)" stages/` returns nothing; `grep Provider stages/explore_*.py` matches only `explore_guidance.py`; `explore_traversal.py` imports no guidance module (duck-typed `rt.guidance`). Seam is `explore_node.py:235`, one in-place line, file still exactly 300. `run_crawl` gains `guide=None` (`explore.py:251`); the four callers are untouched in the diff. |
| G10 prompt is a file | PASS | `skills/crawl-next-action/SKILL.md` (`version: 1`), loaded by `load_skill_prompt` (`explore_guidance.py:189-196`); no inline prompt literal in the guidance modules; tests pass. |
| G11 size and schema | PASS | `uv run ruff check src tests scripts`: All checks passed. `uv run autotester doctor`: clean (advisory D-087 warnings only). Line counts of touched files: explore_node 300, portal_persona 300, explore 299, project 289, explore_guidance 288, crawl 287, test files <= 256; new models in `schema/crawl_guidance.py` all `extra="forbid"`. Nit: the `portal_persona.py` module docstring was reflowed to hold 300 and dropped the phrase "no graph database, no second schema"; harmless, but an unrelated doc edit. |
| G12 measured effect | HELD (correct) | Manifest states Unit 5 not built and makes no effectiveness claim. Not passed, not failed. |

## Amended contracts
- `explore.md` X12 and `crawl-traversal.md` CR6 hold as written: provider-free with guidance off (`attach` returns None; zero calls under all three off switches), byte-identical crawl output when off (independently verified above), `explore_guidance.py` the only `Provider` importer under `stages/explore_*`, and `explore_traversal.py` imports no provider type. The garbage-answer equivalence assertion passes (`test_same_nodes_same_refusals_same_stop_reason_as_the_unguided_crawl[reverse,garbage]`).

## Rulings on the maker's judgement calls
1. **New bounds default None, not 0 (G5/G6): ACCEPTED.** `filestore.write_json` uses `exclude_none`, so None is the only default that leaves an old `crawl.json` byte-identical; both None and 0 read as off (`explore_guidance.py:53-60`), which satisfies "zero means off". Defaults of 20 s and 120 s apply once guidance is on, as G6 states.
2. **Annotation on the screen node only: ACCEPTED.** G7 puts the edge annotation in parentheses ("where one exists"); the KG has no per-control edge for a crawl-time control, and the contract's open question 1 only requires an additive home on the persistent graph. Not a gap.
3. **No entry point passes a guide: ACCEPTED for Units 1-4, with a follow-up required.** It means no egress path exists yet, which is the safe state for a CRITICAL change, and `Project.crawl_guidance` is inert until wired. But Unit 5 cannot run without a caller: a wiring unit (`cli_crawl.py`, `ui/routes_crawls.py`, `cli_orchestrate.py`, `agents/tools.py` calling `explore_guidance.for_project`) must be planned and checked before G12, and it is a user-facing egress switch, so it needs its own check (and a human gate before it runs against Pathlynks). Add it to `docs/plan.md`; the contract lists no unit for it.

## Commands run (this checker, from the worktree, 2 test files per call, one pytest at a time)
- `uv run pytest tests/test_crawl_guidance_schema.py tests/test_crawl_guidance_payload.py -o addopts=`: 22 passed
- `uv run pytest tests/test_crawl_guidance_core.py tests/test_crawl_guidance_kg.py -o addopts=`: 35 passed
- `uv run pytest tests/test_crawl_guidance_seam.py -o addopts=`: 19 passed (58 s)
- `uv run ruff check src tests scripts`: All checks passed; `uv run autotester doctor`: clean
- Scratch scripts (in the session scratchpad, not committed): G3 capture run, base-tree baseline run, F1 `_merge` demonstration, F2 truncation demonstration, pinned-chain construction, three sabotage mutations on a `git archive HEAD` copy.

## Limits
- The full `uv run pytest` was not run (machine memory; a full suite is running elsewhere). `test_explore.py` and `test_explore_bounds_last_node.py` (maker reports 23 passed) were not re-run by me.
- No live model: whether the pinned `ollama_chat/...` tags behave through `ModelChainProvider` is unproven until Unit 5.
- The lifecycle code review (`senior-software-engineer`, `data-engineer`) is not part of this contract check; Checker B or the maker's next step owns it.
- Cycle 1 only needs F1 and F2 fixed and re-checked, plus the two regression tests named above; the rest of this verdict stands.

---

# Cycle 1 (Checker A, contract) - appended; supersedes the Verdict/Status/Cycle header above

**Verdict:** PASS
**Status:** PASS
**Cycle checked:** 1
**Reviewed SHA:** 871c912e504d879cd6eb65f4fff0a31dab6b026f (diff `0ecb057a..871c912e`: 14 files, no `qa/contracts/` change, no enforcement path touched; `docs/DECISIONS.md` gained D-119 only)
**Scope:** F1 and F2 from cycle 0, then a re-confirm of G1-G11 on the cycle-1 diff. G12 stays HELD (Unit 5 not built, no effectiveness claim). Fresh checker; no src or test edited; no real model called; no merge, no push. Checker B (`crawl-guidance.b.md`) is separate.

F1 and F2 are fixed and each is defended by a test that fails when the fix is reverted. No new must-fix. Three non-blocking notes (N1-N3).

## F1 - persona header lost: FIXED (D-119 design, read in `docs/DECISIONS.md:2908`)
Own repro (scratch `repro_c1.py`: full `run_crawl` over the fixture site, a capturing fake `Provider`, project opted in, no persona on disk), output of the run:
- After the guided crawl: `persona file exists after guided crawl: False`; `nodes with guidance: 3` (annotations sit on the crawl's own `ScreenNode.guidance`, `schema/screen_graph.py:85`). No `save_portal_persona` call remains in `explore_guidance*.py`; `_persona` is a read-only `load_portal_persona()` (`explore_guidance.py:225-232`).
- `build_portal_persona(store, crawl_id)`: `profile: Demo https://app.test/`, `history[0]: initial persona: 4 screen(s), 0 flow(s)`, `graph nodes with guidance: 3`. This is the output cycle 0 showed missing (profile empty, summary None). The single writer is `stages/portal_persona.py:290` (`explore_guidance.graft`) after `_merge`; `graft` (`explore_guidance.py:96-110`) labels a new graph node from the persona's known screen name first and adds no revision itself.
- Second crawl over the same store with a fresh fake model: `crawl2 calls 0 kg_hits 3 clicks equal True` (G7 reuse, same click order).
- Falsified in memory (monkeypatch inside the repro process, nothing on disk): `graft` replaced by identity gives `graph nodes with guidance: 0` and `crawl2 calls 3 kg_hits 0`, so the graft is load-bearing and the reuse really comes from `PortalPersona.graph`. Falsified on a `git archive HEAD` scratch copy (graft made a no-op, `PYTHONPATH` to the copy, import path confirmed): `test_crawl_guidance_kg.py` fails 5 tests, among them `test_the_persona_build_grafts_the_annotation_onto_the_graph_screen_node` and `test_a_rerun_over_an_unchanged_screen_makes_zero_calls_and_the_same_order`.
- The persona merge path is untouched: `test_portal_persona.py`, `test_persona_changes.py`, `test_persona_diff_pipeline.py`, `test_knowledge_graph.py` pass (48 tests). Redactor path: `_persist` scrubs the whole persona dump including graph nodes (`portal_persona.py:249-255`), so a grafted label or annotation passes the PP5 scrub and guard.

## F2 - truncate before scrub: FIXED
- `explore_guidance_payload.py:54` (name) and `:66` (title) now scrub the full string and then cut. The only other cut in the guidance modules, `explore_guidance.py:174` (`reason[:REASON_CHARS]`), already cuts a scrubbed string (`:171`). A grep for `[:NAME]`-style slices over `explore_guidance*.py` shows no other pre-scrub cut.
- Own capture over a whole crawl: a control named `"n"*54 + SECRET` (the 60-char name cap lands inside the secret) and a page title `"t"*74 + SECRET` (the 80-char cap lands inside it), secret loaded from `.env` through `SecretStore`. Outbound prompts (provider `guard_text` received exactly the finished prompt, `guarded==prompts: True`): no occurrence of the secret, its first 5 or its last 5 characters (`prompt leaks: []`). A scan of every file under the project tmp dir (crawl dir, `portal_persona.json`, `knowledge.md`, nodes and edges) for the same three strings: `persisted-file leaks: []`. The persona graph label reads `ttt...[REDACTED]:PLANT_KEY`.
- Falsified in memory (old scrub-after-cut restored by monkeypatch): `prompt leaks: [('S3cre', 0)]`, i.e. the 5-character prefix is in the outbound text and the core guard did not refuse it, reproducing cycle 0. On the scratch copy (cut-before-scrub restored in `explore_guidance_payload.py`): `test_a_secret_straddling_either_cap_is_scrubbed_before_the_cut` (payload file) and `test_a_secret_straddling_the_name_or_title_cap_never_leaks_a_prefix` (core file) both fail.

## G1-G11 re-confirmed on the cycle-1 diff
| # | Verdict | Evidence |
|---|---|---|
| G1 | PASS | Cycle-1 diff does not touch `clean_indices`/`complete_order`/`reorder` (`explore_guidance_payload.py:77-102`); `test_crawl_guidance_payload.py` passes (property and sabotage tests). |
| G2 | PASS | `explore_traversal.py` and `explore_node.py` are not in the diff. `test_crawl_guidance_seam.py` 21 passed (reverse and garbage equivalence, denied-ranked-first, injection label, bound still fires, 60 fuzzed rankings). The one persisted addition on a guided crawl is `ScreenNode.guidance` (advisory; not read as identity, coverage or a skip input). |
| G3 | PASS | F2 fixed (above); `guard_prompt` still runs before every call (`explore_guidance.py:157`, unchanged); in-row names masked, path-only hrefs; the repro prompt carries no query, fragment, value or person name. |
| G4 | PASS | Unchanged lines; core tests pass (38 with kg). |
| G5 | PASS | `ScreenNode.guidance` defaults None and `exclude_none` keeps it out of the JSON: `test_guidance_off_is_byte_identical_to_the_pre_change_crawl` and the three off-switch cases pass against the checked-in baseline; pre-change approval and old `crawl.json` tests pass (schema file, 24 with payload). `test_explore.py` and `test_explore_bounds_last_node.py`: 23 passed. |
| G6 | PASS | `_call` and `_blocked` untouched. |
| G7 | PASS | Annotation on `ScreenNode` (staging) then `PortalPersona.graph` via the persona build; reuse key unchanged; repro shows 0 calls on the rerun and no `crawl_guidance*` file. `extra="forbid"` holds (schema test). See N1. |
| G8 | PASS | Pinned list untouched; repro `crawl.provider` is the served tag `fake-1017`. |
| G9 | PASS | See ruling below. |
| G10 | PASS | Skill file untouched; `no_inline_prompt_literal` test passes. |
| G11 | PASS | `uv run ruff check src tests scripts`: All checks passed. `uv run autotester doctor`: `doctor: clean` (only D-087 advisories), which includes the SNAPSHOT freshness check. `wc -l`: explore_node 300, schema/portal_persona 300, stages/portal_persona 300, explore_guidance 300, explore 299, screen_graph 126, payload 102; tests at most 269. No new file in cycle 1. See N2. |
| G12 | HELD | Not built, no claim. |

**G9 ruling (stages/portal_persona.py now imports explore_guidance).** Allowed. G9's text is "`stages/explore_guidance.py` is the only module under `stages/explore_*` that imports `Provider`"; `stages/portal_persona.py` is not under `explore_*` and does not import `Provider` (grep on it: no match). Command output: `grep -rn "Provider" src/autotester/stages/explore_*.py` outside `explore_guidance.py`: no match; `grep -rnE "^(import|from) (anthropic|google|litellm|ollama)" src/autotester/stages/`: no match. CR6's falsifier is scoped to "the traversal/incremental modules this unit adds", and `explore_traversal.py` still imports no guidance or provider module. Import side effects: importing `autotester.stages.portal_persona` loads the same 16 `autotester.providers.*` modules and no vendor SDK on HEAD and on the `b1ffaf27` tree alike (ran both and compared), so the new edge changes no import behaviour. `graft` is pure (no call, no I/O). D-119 `Changes-authorized` names "the persona build path in stages/portal_persona.py". It is a layering smell, not a violation (N2).

**Rename `fold` to `merge_notes`.** `merge_notes` is defined only at `explore_guidance.py:86`; `fold` exists only at `stages/bug_loop.py:233`; no stale `fold(` reference in the guidance modules or tests; doctor's duplicate-concept check is clean. A rename only; behaviour is covered by `test_annotations_fold_newest_five_and_the_graft_adds_only_screens_with_a_ranking`.

**SNAPSHOT regeneration.** `git diff 0ecb057a..871c912e -- docs/SNAPSHOT.md` is 2 lines: D-114 drops out of the "Last decisions" window and D-119 enters. Nothing else is hidden; doctor's freshness check passes.

**Test rewrites.** The removed test lines are the cycle-0 tests that read the persona right after `order`; each was replaced by an equivalent that goes through `commit` or `build_portal_persona` (`tests/crawl_guidance_support.py`). No removed assertion is dropped without an equal or stronger replacement.

## Non-blocking notes
- N1 (contract wording). `crawl-guidance.md` G7 still says a per-crawl `nodes.jsonl` "cannot be reused" and that the home is the persistent graph. Under D-119 `nodes.jsonl` also carries the annotation as a staging copy until the persona build grafts it; the persistent graph is still the only reuse source (second-crawl repro). The reading is consistent, but a one-line G7 amendment-log entry citing D-119 should be added when this contract goes ACTIVE. Not edited here: D-119 `Changes-authorized` does not list the contract.
- N2 (headroom). Four source files sit at exactly 300 lines (`explore_node.py`, both `portal_persona.py`, `explore_guidance.py`). Any addition fails doctor. Moving `merge_notes` and `graft` into a provider-free module in a later unit would free `explore_guidance.py` and remove the persona-to-provider-seam import; that is a new module, so it needs Umesh's say, not a drive-by.
- N3 (carried from cycle 0, unchanged). Wiring a `guide` into the four entry points is still unplanned and needs its own check and a human gate before G12 against Pathlynks. The D-119 residual (a crawl that aborts before the persona build loses its new rankings) is accepted by Umesh in D-119.

## Commands run (this checker, from the worktree, 2 test files per call, one pytest at a time)
- `uv run pytest tests/test_crawl_guidance_schema.py tests/test_crawl_guidance_payload.py -o addopts=`: 24 passed
- `uv run pytest tests/test_crawl_guidance_core.py tests/test_crawl_guidance_kg.py -o addopts=`: 38 passed
- `uv run pytest tests/test_crawl_guidance_seam.py -o addopts=`: 21 passed (72.7 s)
- `uv run pytest tests/test_portal_persona.py tests/test_persona_changes.py -o addopts=`: 31 passed
- `uv run pytest tests/test_persona_diff_pipeline.py tests/test_knowledge_graph.py -o addopts=`: 17 passed
- `uv run pytest tests/test_explore.py tests/test_explore_bounds_last_node.py -o addopts=`: 23 passed
- `uv run ruff check src tests scripts`: All checks passed; `uv run autotester doctor`: clean
- Scratch, not committed: `repro_c1.py` in three modes (fixed, old_scrub, nograft); import-set comparison HEAD vs `b1ffaf27`; two mutations on a `git archive HEAD` copy (deleted afterwards). The worktree was clean before this verdict commit.

## Limits
- The full `uv run pytest` was not run (machine memory; a full 6c suite is running elsewhere).
- No live model: the pinned `ollama_chat/...` tags through `ModelChainProvider` stay unproven until Unit 5. Every PASS here is on a fake provider, so Units 1-4 close as "built and proven on a fake, measured effect unproven", never as "guidance works".
- The lifecycle code review (`senior-software-engineer`, `data-engineer`) is not part of this contract check.
- Criticality is CRITICAL (dual check): this is Checker A's PASS only; the unit closes when Checker B's verdict (`crawl-guidance.b.md`) is also PASS.
