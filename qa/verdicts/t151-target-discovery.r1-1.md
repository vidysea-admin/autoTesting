# Verdict — t151-target-discovery (coordinator A, dual check)
Date: 2026-10-07 · Cycle checked: 1 · Policy: proportional-verification/2026-10-06.6 · Bound root: D:/autoTesting/.worktrees/t151-target-discovery · HEAD 18243792 · Base 2fae2504 (merge-base verified = 2fae2504)

## Check plan (step 0)
Diff: 25 files; product code = schema/ai_target.py, stages/discover.py, stages/read_context.py, providers/mock.py (act hunk), prompts/ai_target_classify_v1.md, pyproject/uv.lock (pyyaml==6.0.3), docs/MAP.md (generated), tests/test_discover.py, plus qa evidence/manifests/verdicts. Not UI-touching (no browser/live check). The prompt file changed, but it is a static naming prompt fed only signal-kind counts; no rubric grading dispatched (classification output is schema-validated; AI2/AI3 live in T-152).
Checks: (1) manifest verify commands; (2) ONE full suite (L); (3) falsification rows in throwaway copies (3 read-only sub-checkers, Sonnet, in parallel, separate copies, no shared tree); (4) my own diff read and security probes (secrets refusal, path escape, YAML bombs, parser bombs); (5) step 4c diff scope; (6) D-065 authority (read-only from master) and doctor.
TIER: L (dependency bump pyyaml==6.0.3 at pyproject.toml:26; credential/path-escape/approval boundary code in stages/discover.py:42-123; dual check as dispatched). Not lowered, not raised.
SERIAL: only one pytest suite in the bound tree; falsification ran in separate copies (no shared lock).

## Re-run results (mine)
- uv run ruff check src tests scripts: All checks passed.
- uv run pytest tests/test_discover.py: 63 passed.
- grep -rniE obsidian pyproject.toml: no output, exit 1.
- uv run autotester doctor: 5 violations, all decision-citation-dangling (qa/manifests/t151-target-discovery.md:16,17,18,26,57 cite D-065). The manifest's "doctor: clean" is NOT reproduced on this branch. Per the dispatch, D-065 missing from the branch is expected and not a FAIL by itself; a sub-checker confirmed in a copy with master's DECISIONS.md that the 5 vanish and only a stale docs/SNAPSHOT.md remains (regenerate with `autotester snapshot` at merge).
- Authority: `git show master:docs/DECISIONS.md` has "## D-065 | 2026-10-07" with Changes-authorized = pyproject/uv.lock (pyyaml==6.0.3), the T-151 prompt file, mock.py act hunk, Approved-by Umesh; gate qa/gates/t151-dependency-authorization.md Answered "2026-10-07T01:34:13Z - A". The diff for the three items matches (pyproject +1 line, uv.lock +2 lines promoting an existing transitive pyyaml 6.0.3 block to a direct pin; mock.py act hunk plus its two imports only; prompt file ai_target_classify_v1.md). OK.
- Full suite (`uv run pytest`, no -x): started 07:14, still running at 07:57 (~55% done; two F seen at ~12% and ~50%, not attributable until the run ends because addopts -q prints no names). The L wall deadline (45 min) was reached with the suite unfinished, so it counts as evidence neither way. It is on the Remaining list. The verdict stands on the floor failures below, which do not depend on it.

## Criteria
- [AI1] NOT MET. The scan path is right (scan citations killed by test_signals_match_real_lines_without_importing_target; never-executes and no-Provider-on-emission-path rows KILLED; the literal "Provider" grep hits discover.py only as the import/type of classify_target, which is off the signal-emission path, so I judged the criterion text, see P5). But (a) the AI1 Verify requires a test asserting every emitted Signal file/line resolves on disk across discover.py AND read_context.py; no repo test asserts read_context signal lines: mutants `line=line+1` in read_context.py for the "Markdown tag" and "Frontmatter metadata" Signals both SURVIVE all 63 tests (R-1b, R-1c); the manifest's named defender test_reader_signal_lines_match_exact_source is not in tests/. (b) Concrete wrong line: read_context.py:71 uses text.splitlines(); a Markdown file containing U+2028 (or form feed, U+0085) reports tags one line too late. Reproduced: file "---\ntags: [x]\n---\nfoo<U+2028> #bar\nbaz #qux\n" gives "Markdown tag" Signals at lines 5 and 6; the physical \n lines are 4 and 5. discover.py:233 and :236 (prompt / ground_truth first non-blank line) use the same splitlines.
- [AI8] Behaviour holds on everything I probed (body, [[backlinks]] and the dataview fence are not persisted; Source.text is None; obsidian grep exit 1), but the floor fails: a mutant deleting read_context.py:123-124 (`if path.suffix.lower() != ".md": continue`) SURVIVES 63/63 (R-4c; a notes.txt then yields a ContextDocument). The manifest row claims "admit non-Markdown" is KILLED, via a scratch G4 oracle that is not in the repo.
- [C5] Invariants hold on behaviour: dirty signal and encoded root secret refused before any provider call; metadata and provider-error scrubbing; approval and preflight before any open (no content opened before every root is approved); physical read budget and final deadline; symlink and junction refused (tests/test_discover.py:104). Floor gap on the YAML row (below).

## Capability coverage (re-run in throwaway copies, green-before verified in each copy)
8 of 11 rows reproduced; 3 not:
- AI1 every Signal names a real file:line: scan hunk KILLED (2 failed: expected {(agent_framework,2),(sdk,1)}); the two reader hunks SURVIVED. NOT reproduced.
- AI1 no Provider call on emission path: KILLED, both hunks (scan, read_context), by test_discovery_never_calls_provider.
- AI1 parsed never executed: `exec(text)` before ast.parse KILLED by test_signals_match_real_lines_without_importing_target (ModuleNotFoundError from executing the fixture's import; the named test is absent from the repo, this analogue exists for the purpose).
- AI8: persist body KILLED (by the secret gate; by the test's content assert when the body is secret-free); emit backlink names KILLED (assert ['hidden','rag','safe'] == ['rag','safe']); admit non-Markdown SURVIVED. NOT reproduced.
- C5 dirty signal / encoded root secret: both KILLED (test_discover.py:252; DID NOT RAISE).
- C5 metadata and provider errors: scrub-disable KILLED via the assert_clean backstop (read_context.py:146) before the named assertion (with the backstop also removed the named assertion fires); provider-error sanitization KILLED (test_discover.py:275).
- C5 approval/preflight: both KILLED (DID NOT RAISE ApprovalRequired; __suppress_context__ and secret-echo asserts at 147-148). test_denial_class_and_formatted_chain_are_safe is not in the repo; the repo test kills the mutant.
- C5 bounds: physical-budget (assert 51 <= 20), scan final deadline and context final deadline all KILLED (test_discover.py:125, :300).
- C5 YAML alias: deleting read_context.py:31-32 (AliasEvent detection) is killed ONLY for the cyclic param, by an incidental RecursionError in _metadata (read_context.py:48-50), not by a refusal assertion; the non-cyclic alias param `x: &a [1]\ny: *a` stays GREEN (shadowed by max_yaml_nodes) and no test pins the yaml_alias refusal; test_noncyclic_alias_exact_refusal is not in the repo. Not isolated. NOT reproduced.
- C5 path-escape: KILLED, 2 failed (symlink and junction both ran), assertion test_discover.py:104.
- dependency pyyaml==6.0.3: confirmed (pyproject.toml:26; uv.lock +2 lines; only stages/read_context.py imports yaml).

## Step 4c diff scope
No function, export or test deleted. mock.py: act hunk only (unrelated reflow reverted). SIM105 fixed. D-061/F-067 hunks are gone (docs/DECISIONS.md and FEATURES.jsonl unchanged vs base). One file not in the manifest's "What changed": docs/MAP.md (generated by `autotester map`; the regeneration also corrected pre-existing stale rows: browser/session.py docstring and ledger.py DecisionClaim/CitationReview rows no longer in source). Generated, non-blocking (P6).

FAILURES
- [AI1] sev: medium · reader (read_context.py) signal lines undefended: `line=line+1` mutants survive (R-1b, R-1c), no repo test covers them, and read_context.py:71 mis-numbers lines after U+2028/U+0085/form feed (probe: tags at 5,6 vs physical 4,5) · add a repo test asserting exact reader Signal lines (frontmatter and tag), and number lines by \n, \r\n, \r only (not str.splitlines) in read_context.py:71 and discover.py:233,236 · issue: P1
- [AI8] sev: medium · the Markdown-only gate (read_context.py:123-124) is undefended: deleting it survives 63/63 and lets .txt through as a ContextDocument · add a repo test with a non-.md file carrying frontmatter/tags and assert no document · issue: P2
- [C5] sev: medium · YAML alias row not isolated: no repo test pins the alias refusal (yaml_alias reason); the cyclic param dies by RecursionError, the non-cyclic one is shadowed by the node limit · add a repo test with generous limits and a non-cyclic alias asserting reason yaml_alias (a refusal, not a crash) · issue: P3

PROPOSED-ISSUE: {"id":"P1","type":"floor","sev":"medium","title":"read_context signal lines undefended and mis-numbered by str.splitlines (U+2028)","files":["src/autotester/stages/read_context.py:71","src/autotester/stages/discover.py:233","src/autotester/stages/discover.py:236"]}
PROPOSED-ISSUE: {"id":"P2","type":"floor","sev":"medium","title":".md-only gate in read_context undefended (mutant survives)","files":["src/autotester/stages/read_context.py:123"]}
PROPOSED-ISSUE: {"id":"P3","type":"floor","sev":"medium","title":"YAML alias refusal not pinned by an isolating test","files":["src/autotester/stages/read_context.py:31","tests/test_discover.py:47"]}
PROPOSED-ISSUE: {"id":"P4","type":"correctness","sev":"medium","title":"scan() lets RecursionError from ast.parse escape (only SyntaxError is caught); a hostile file such as 'x = a+a+...' with 30000 terms, or an '@a+a+...' x20000 decorator, aborts the whole scan instead of a visible invalid_python refusal. Fails closed, no leak, so non-blocking; fix in the same cycle as P1-P3","files":["src/autotester/stages/discover.py:177-180","src/autotester/stages/discover.py:228-231"]}
PROPOSED-ISSUE: {"id":"P5","type":"contract","sev":"low","title":"AI1 Verify literal grep hits discover.py (Provider import/type in classify_target, D-017-authorized naming); checker to amend AI1 Verify scope to the signal-emission modules/functions at Mode B (plan-approval change 5)"}
PROPOSED-ISSUE: {"id":"P6","type":"low","sev":"low","title":"docs/MAP.md regenerated but not listed in What changed; manifest says D-065 is recorded in the branch DECISIONS.md and doctor clean, but the branch lacks D-065 until merged (5 dangling-citation violations); docs/SNAPSHOT.md needs regeneration on merge"}
PROPOSED-ISSUE: {"id":"P7","type":"low","sev":"low","title":"safe_load swapped for UnsafeLoader survives all tests (explicit-tag event scan shadows it); frontmatter closing '---' labelled Frontmatter metadata; tests/test_discover.py lacks the blank lines between tests that plan-approval change 1 asked to restore"}

Remaining for the repair checker (cycle 2): the single full suite (this run did not finish; two unattributed F at ~12% and ~50%), a re-run of the three failed floor rows, and a non-regression pass of the other rows by evidence identity (code hashes in the checkpoint).
HUMAN_GATE-REQUEST: none

VERDICT: FAIL
SCOREBOARD: 0/2 criteria met (AI1 and AI8: evidence/floor unmet), C5 1/1 holds in behaviour with one floor gap
TIER: L (dependency bump pyyaml==6.0.3 at pyproject.toml:26; secrets/path-escape code in stages/discover.py)
LIVE-BROWSER: not-applicable (no UI paths changed)
CAPABILITY-COVERAGE: 8/11 rows reproduced (3 not: AI1 reader lines, AI8 non-Markdown gate, C5 YAML alias)
ISSUES-WRITTEN: none (dual check; PROPOSED-ISSUE lines only)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: Code behaviour on the security boundary is sound (secrets, approval, bounds, path escape, dependency all reproduced), but three floor rows do not hold in the repo's own tests: reader signal lines, the Markdown-only gate and the YAML alias refusal survive their falsifying edits, and reader line numbers are wrong after U+2028. The full suite did not finish inside the L wall budget and is carried to cycle 2.
Metrics: start=2026-10-07T07:13:32+05:30 end=2026-10-07T07:59:47+05:30 wall_min=46 agent_min=62 blocked_min=0 suite_runs=1 repeat_runs=0 mutations=23 cycle=1 resumes=0 tokens=unavailable policy=2026-10-06.6
