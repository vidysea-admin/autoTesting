# dispatch-hardening: F2 F3 F4 F5 on HEAD c489e201 (agents/tools.py)

Run as: `unset VIRTUAL_ENV; uv --directory <HEAD> run python <ROOT>/scripts/dispatch-hardening/<script>.py`
(every script asserts `autotester.__file__` is inside HEAD). Fake canary `CANARY-pw-7f3a9c`, temp data roots, spies for
`execute.run_case`, `explore.run_crawl`, `grade.grade`, `catalog.catalog`, the session factory, the judge provider. HEAD/BASE untouched.

Scripts: common.py f2.py f2b.py f3.py f3b.py f3c.py f4.py seps.py (+ mut1/ for F5). Tables (CSV) and stdout in this dir.

## F2 typed refusals
f2.py: 520 dispatch rows (f2_rows.csv) + 77 BaseException rows (f2_baseexc.csv).
- handler-raising: 11 sources (run_case, open_session, judge via real grade.grade, store.get_case, catalog, crawl, persona reader,
  save_result, save_verdict, load_results, load_rubric) x (9 message forms: raw/reversed/b64/hex/pct/spaced/zw/split-in-two/first-half,
  16 "x"*pad+form cut-boundary rows, `__str__` raising, canary in type name, canary in exception args, ValueError, MemoryError,
  RecursionError, UnicodeDecodeError, KeyError, OSError path, 10 MB message). Every one returned a ToolOutcome with typed refusal
  (stage_error / secret / approval) and no canary variant (raw, lower, reversed, hex, pct, spaced, zw, b32, b64 std/url x3 offsets) in `model_dump_json()`.
- name rows (23: None, 5, list, bytes, dict, tuple, hostile object, hostile str subclass, known-prefix+canary, >100 chars, empty, case/space/NUL/homoglyph variants,
  canary raw/reversed/b64 as name): all typed; tool label `unknown` in every row except LyingStr (finding 3).
- args rows (45 shapes x run_case/get_catalog): None, [], "str", 5, list of pairs, non-str keys (1, None, (1,2), bytes), canary keys, cycles (dict+list),
  depth 5/6/7/50/5000/100000 (list and dict; no RecursionError), ints 2**256 ok / 2**257+ refused, nan/inf, bytes/bytearray/set/frozenset/object/complex/Decimal,
  hostile leaf objects, dict/list subclasses whose `__iter__` raises, int subclass with raising or canary `__repr__`, 5M-item list, 300-key dict:
  all returned typed refusals, max 0.18 s each.
- Only mismatch in 520 rows: LyingStr (finding 3). Plus finding 1 (truncation) and finding 2 (control-char split).
- BaseException: KeyboardInterrupt, SystemExit, GeneratorExit, asyncio.CancelledError, plain BaseException PROPAGATE out of `dispatch` from every one of the 11 sources
  (crawl run with explicit bounds so the stage is really reached; the first run used default bounds and was refused earlier by the approval; re-run fixed it).
  An Exception whose `__str__` raises KeyboardInterrupt: propagates. MemoryError: RETURNED as a STAGE_ERROR refusal in all 11 sources (it is an `Exception` subclass; this is by design of `except Exception`, reported as asked).

## F3 nothing on disk (f3.py, f3b.py, f3c.py)
f3.py: 482 dispatches. Result carriers: error, hitl_prompt, not_run_reason, evidence.path, evidence.label, log_ref, case_id (file name).
Verdict carriers: note, scoreboard, grader_provider, rubric_hash, failures[].reason/evidence_refs/fix_hint, case_id (file name).
38 canary forms (raw, lower, upper, reversed, hex lo/up, percent x2, spaced, zw-split, dash-split, base32, base64 std/url at all 3 alignments, rev-hex, rev-b64,
double-b64, html-entity, \u-escape, swapcase, rot13, tab/nl/nbsp/crlf split, soft-hyphen/ZWJ/BOM mid, fullwidth, reversed-spaced, hyphen-split).
After each call the whole data root is walked, every file read as bytes, grepped for every form (also with whitespace/JSON-escape normalisation, and UTF-16).
- Positive control: benign result/verdict stored (file changed/added, content benign). 
- No refusal wrote anything: 0 of 482 rows where `ok=False` added or changed any file under the root (before/after sha256 of every file).
- Raw canary in a result: scrubbed to a placeholder, stored (no canary on disk). Raw in a verdict: SECRET refusal, nothing stored.
- Forms refused (SECRET) and absent from disk: reversed, hex, percent, base32, base64 std/url x3, double-b64, html-entity, spaced, zw-split, dash-split, nbsp, soft-hyphen, ZWJ, BOM, swapcase, fullwidth, case variants.
- Forms STORED and recoverable (finding 2, tables f3_rows.csv f3b_separators.csv): reversed-hex, reversed-base64, rot13, `\uXXXX` escapes (f3c.py: stored field decodes to the canary), and a secret split by TAB/LF/CR/CRLF/VT/FS/US/NUL/ESC/BS/FF (any JSON-escaped control char), in all result and verdict carriers.
  The same texts also come back to the model in the outcome summary (error/scoreboard carriers) and in STAGE_ERROR text (exception message).
- Split across two different fields (first half in `error`, second in `hitl_prompt`): stored; no single field or file span holds the secret (design limit, the gates scan one document, not a join).
- What `execute.run_case` itself writes (screenshots, evidence dir, logs under the session) is outside this probe: the stage and session are spies and write nothing. `save_result` writes only `<run_dir>/<case_id>.json`, `save_verdict` only `<run_dir>/<case_id>.verdict.json` (store/project_store.py:180-192, `write_json` atomic temp+rename); no index or log file is written. The gate (`_withhold_if_credential`) runs before both saves (tools.py `_scrubbed`, `_grade_case`).

## F4 call gate (f4.py)
- 1333 rows = 37 separators (TAB LF CR CRLF VT FF FS US NEL LS PS NBSP SPACE 2xSPACE U+3000 U+2002 U+2009 ZWSP ZWNJ ZWJ LRM RLM WJ BOM SHY U+180E CGJ ALM NUL BS ESC DEL TAG VS16 combining-acute backslash quote) x 3 shapes (split mid, between every char, reversed canary between every char) x 12 positions
  (run_case/grade_case case_id, crawl extra value, get_catalog extra value, extra key, tool name alone, tool name suffix on run_case, nested list/dict/key at leaf depth 5, two pieces in two list items) + 1.
  Where `assert_no_raw_secrets(text, [CANARY])` refused (all 1333 check texts) dispatch refused too, handler/stage/session call count 0 (counting wrappers on `_HANDLERS`, stage spies, session counter). Gap list is EMPTY. Reverse (dispatch refuses SECRET where assert_no_raw_secrets does not): 0.
- Caveat in that count: the 112 rows where the two halves sit in two separate leaves (list_value_two_pieces, two_leaves_split) are refused only by schema validation (extra_forbidden), not by the secret gate: the gate scans each string alone and never joins leaves. No handler joins two arguments today.
- Cap semantics read from `_call_texts`: `chars` = len(name) + sum of every str leaf AND dict key; `nodes` = every popped item (root, containers, keys, values, leaves); `depth` of a leaf: root dict 0, so leaf may sit at depth 6 (dict + 5 nested lists + leaf); `_children` refuses a container with more than 256 keys+values.
  Measured boundaries (f4_boundaries.csv): chars 16384 reaches validation (4 scans) / 16385 refused with 0 scans; same with the length in a key; many-leaf split row 16383+16384 pass, 16385 refused.
  Flat dict: 127 keys pass, 128 refused (nodes, not children: 1+2n <= 256). List value: 253 items pass, 254 refused. Leaf depth 6 passes, 7 refused (list and dict, also empty list at depth 7).
  The brief's "128 keys OK / 129 refused" is off by one: the limit is 127/128 because the root dict is a node.
- 2,000,000-char value, key and tool name: refused in ~0.0001 s, `guard_model_bound` call count 0 (value-with-canary-at-end refused unscanned too). 100k value also refused unscanned.
- Largest real argument any tool needs (schema/agent_layer.py:64-81): `case_id` max 200 chars (RunCaseArgs, GradeCaseArgs), crawl `max_actions` int, `wall_clock_s` float, `incremental` bool, get_persona/get_catalog nothing (extras forbidden). So a maximal valid call is ~250 chars, 1% of the 16384 cap.
  Run (f4_legit.csv): 200-char ASCII and 200-char Devanagari case_ids ran/graded OK; crawl with all three fields passes the gate (OK with a covering approval; huge values like 2**200 or 1e300 pass the gate and are refused by the approval check, not the caps). Smallest legitimate-looking call the caps reject: none found (a legitimate call has no free text; anything over 16384 chars or 127 keys is by construction extra/forbidden fields).

## F5 mutant (mut1/)
Copy of HEAD src+tests+scripts+pyproject in `scripts/dispatch-hardening/mut1/`, run with PYTHONPATH=mut1/src;mut1/scripts using the HEAD venv python directly (`uv --directory` was NOT used for pytest because it changes cwd back to HEAD; first attempt noticed and discarded). `autotester.__file__` printed inside mut1/src.
- Green before (f5_green.txt): `tests/test_agent_read_only.py::test_get_persona_calls_the_wrapped_reader` 1 passed.
- Mutant (f5_mutant.diff): `_get_persona` returns a fixed ToolOutcome, never calls `ctx.store.load_portal_persona()`.
- Red after (f5_red.txt): 1 failed (`calls == []`, `Right contains one more item: 1`). Whole agent test files under the mutant: 2 failed (that test and `test_agent_tools.py::test_read_tools_and_grade_wrap_catalog_persona_grade`), 129 passed. The mutant dies.

## FINDINGS (each reproduced)
1. Truncate-after-scrub leaks a long prefix of encoded secrets (F2). `tools.py:_error_text` scrubs the exact value then cuts to 300 chars, and `_release` gates only the cut text.
   Repro: `uv --directory HEAD run python scripts/dispatch-hardening/f2b.py` (f2b_stdout.txt, f2_truncation_leak.csv): message `"x"*pad + <form>` with the form cut by the 300 limit is released as STAGE_ERROR (not SECRET) carrying: reversed 15 of 16 chars, base64 19 of 21, hex 31 of 32, percent 47 of 48, base32 23 of 26.
   Control: the same forms fully inside 300 chars are all refused SECRET. Expected: gate the untruncated scrubbed text, then truncate.
2. Gates scan `model_dump_json()`, where control characters are JSON-escaped (F2/F3, and AL6 release). A secret split by TAB, LF, CR, VT, FF, FS, US, NUL, ESC or BS is stored on disk, in the model-bound outcome and in STAGE_ERROR text; `assert_no_raw_secrets` on the real string refuses it (dispatch's own call gate, which scans real strings, does too: F4 is clean).
   Repro: `f3b.py` (f3b_separators.csv, 74 rows; flagged REAL-REFUSES/JSON-PASSES; DISK-RECOVERABLE and RELEASED-RECOVERABLE for result, verdict and exception). Same for `\uXXXX`-escaped canary, rot13, reversed-hex, reversed-base64 (f3.py, f3c.py). The last three are transform classes beyond what AT-347 claims to cover; the control-character split is the same class F4 fixed on the input side.
   Expected: scan the real strings (`scrub_obj`-style walk), not the JSON text. file:line: tools.py `_withhold_if_credential` (model.model_dump_json()), `_release` (clean.model_dump_json()), `_error_text`.
3. Caller text echoed as the tool label (F2). A `str` subclass with `__hash__`=hash("run_case") and `__eq__`=True makes `name in {n.value ...}` true, so `label = name` and the outcome `tool` is the caller's own text (`"ZQMARK-lying-content"`, any text up to 100 chars that passes the secret scan).
   Repro: `f2.py` row `name/LyingStr` (f2_rows.csv, problems column). Expected: `tool` is a known tool name or "unknown" (tools.py `_dispatch`, the `label = ...` line). Only reachable from in-process callers, not from decoded JSON.

## QUESTIONS (not reproduced as a defect or judged by design)
- MemoryError from a stage is returned as STAGE_ERROR (is `Exception`), not propagated. CancelledError/KeyboardInterrupt/SystemExit/GeneratorExit do propagate.
- `_children` builds `[*node, *node.values()]` before checking its length, so "size-checked BEFORE expanded" is not literally true: a caller-built 3,000,000-key dict costs 0.5 s and ~48 MB before refusal (f3c_stdout.txt). Not reachable from a decoded JSON payload larger than the already-parsed object.
- A `ValueError` raised inside the call walk (e.g. a dict subclass whose `__iter__` raises ValueError) is labelled SECRET ("the call carried a credential value"), because `_dispatch` catches `ValueError` for the guard (mislabel, still typed and scrubbed).
- Secret halves in two different arguments are never joined by the gate (see F4 caveat); nothing joins them today.
- A stage result whose `case_id` (the file name) carries the raw canary (or a tab/newline-split one) ends as STAGE_ERROR in `save_result` (the scrubbed/odd name is not a writable Windows file name, f3_rows.csv carrier `case_id`); nothing was written and nothing leaked, so it is a refusal, not a defect. Not investigated further.

## Could not run
Nothing blocked. Not exercised: the real browser session/executor outputs (spied), a real model judge (a `MockProvider` subclass raising from `judge()` through the real `grade.grade`).
