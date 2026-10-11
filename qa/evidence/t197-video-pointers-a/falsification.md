# t197-video-pointers seat A - falsification record (head 3d0be650)

Every row ran in its own `git archive 3d0be650` copy under the scratchpad (never the bound tree), PYTHONPATH at the copy, `autotester.__file__` verified inside the copy, green before then red after, red on an assertion (no Import/Syntax/collection error), copy deleted.

| Row | Edit (file:line) | Green -> Red | Failing assertion |
|---|---|---|---|
| TV1 a | clamp a time at/past duration (video_pointers.py:56-57) | 27 -> 2 failed | parsed.parsed == [] for 60:00 / 62:00 past duration |
| TV1 b | `continue` on bad line (video_pointers.py:94-95) | 27 -> 11 failed | count identity 6+0 == 11 |
| TV2 a | gap in not_reviewed (video_review_plan.py:89) | 55 -> 1 failed | exact partition 69.0 == 70.0 |
| TV2 b | POINTER_FRAMES_PER_MIN 12 -> 4 (video_pointers.py:18) | 55 -> 4 failed | 4 > 4 depth strictly greater |
| TV3 | overflow = [] (video_review_items.py:142) | 28 -> 1 failed | len(overflow) == 4, got 0 |
| TV4 | unknown_source check `if False` (video_review_items.py:117) | 28 -> 1 failed | ['foreign','good'] == ['good'] |
| TV5 | drop overlap requirement on quote (video_review_items.py:91) | 28 -> 3 failed | far-segment quote stays narration |
| TV6 | unreadable text -> "no narration on record" (video_review_prompt.py:26) | 28 -> 1 failed | 'narration unreadable' in md |
| TV7.3 a | verify_blackout returns at once (redacted.py:94) | 29 -> 3 failed | DID NOT RAISE RedactionError |
| TV7.3 b | blackout filter replaced by `null` (redacted.py:56) | 29 -> 5 failed | RedactionError "not blacked out in the copy" (end-to-end path refuses) |
| TV7.3 c | self.origin stays the original video (redacted.py:123-124) | 29 -> 1 failed | frames.origin == work/redacted.mp4 (internal attribute only) |
| TV7.3 d | windows dropped from frames_fn (video_review.py:241) | 29 -> 1 failed | redacted.mp4 is_file (file-exists only) |
| TV7.2 | approval matched on any stored project (cli_video_review.py:62) | 20 -> 1 failed | exit_code == 3 (run proceeded) |
| TV8 a | quote scrub only removed (video_review_items.py:92) | 48 -> 48 | SURVIVES (equivalent: _finish rescrubs everything) |
| TV8 b | _finish whole-review scrub only removed (video_review.py:289) | 48 -> 2 failed | canary in stored json/md/html/caplog and CLI stdout+stderr |
| TV8 c1 | pointer free-text scrub removed in prompt (video_review_prompt.py:87) | 48 -> 2 failed | assert_no_raw_secrets refuses (3 == 0) |
| TV8 c3 | narration scrub removed in prompt (video_review_prompt.py:74) | 48 -> 1 failed | canary test |
| TV8 g | drop `or quote in scrub(s.text)` (video_review_items.py:53) | 76 -> 76 | SURVIVES: a model quoting scrubbed narration is downgraded, no test sees it |
| TV10 a | time_ns() in the id (video_review.py:94) | 40 -> 4 failed | same-id / no-clock tests |
| TV10 b | _merge_human_status removed (video_review.py:253) | 40 -> 1 failed | 'open' == 'confirmed' |
| TV10 c | pointer canonical form dropped from id (video_review.py:93) | 40 -> 1 failed | new-id-on-changed-pointer |
| TV10 d | plain re-run returns stored with every status reset to open (video_review.py:235) | 40 -> 40 | SURVIVES: the only mark-survival test re-runs with refresh=True |

Not built (no clean single hunk): "redaction applied after the provider call" (the frame source is lazy). TV7.3 c and d are the nearest equivalents.

## TV8 survivor ruling
Row TV8 a is an equivalent mutant at the system level: every output channel (stored json, md, html, return value, caplog) passes through `_finish`, and the pre-`_finish` items are never persisted, returned or logged. TV8 is therefore tested at the real leak surface (TV8 b, c1, c3 red; canary in store, exports, log, prompt, CLI stdout and stderr). It is not tested at the contract's literal mutation, and row TV8 g shows the scrubbed-quote verification branch is unprotected. Ruling: TV8 holds, not a FAIL, PROPOSED-ISSUE P5.
