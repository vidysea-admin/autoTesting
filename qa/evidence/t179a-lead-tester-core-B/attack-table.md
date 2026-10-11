# t179a attack table (checker B, cycle 0) - 403 black-box dispatcher calls

Columns: n | cat | call | tool | verdict | text | spies browser/run_case/run_crawl/grade_prompts | leaks ret/exc/files/logs/prompt | arg_in_exc
Canaries are fake, labelled <A|B|S:variant>; variants raw, b64, b64url, b64nopad, b32, hexl, hexu, pct, pct2, rev, upper, lower, spaced, zw, hexsp, fold.

| n | cat | call | tool | verdict | text | b/rc/cr/gp | leaks r/e/f/l/p | arg_in_exc |
|---|---|---|---|---|---|---|---|---|
| 1 | S1 | raw A in case_id | run_case | REFUSED:secret | refused: the call carried a credential value; use {{SECRET:KEY}} | 0/0/0/0 | 0/0/0/0/0 | False |
| 2 | S1 | raw A in extra key value (get_catalog) | get_catalog | REFUSED:secret | refused: the call carried a credential value; use {{SECRET:KEY}} | 0/0/0/0 | 0/0/0/0/0 | False |
| 3 | S1 | A as b64 in case_id | run_case | REFUSED:secret | refused: the call carried a credential value; use {{SECRET:KEY}} | 0/0/0/0 | 0/0/0/0/0 | False |
| 4 | S1 | A as b64url in case_id | run_case | REFUSED:secret | refused: the call carried a credential value; use {{SECRET:KEY}} | 0/0/0/0 | 0/0/0/0/0 | False |
| 5 | S1 | A as b64nopad in case_id | run_case | REFUSED:secret | refused: the call carried a credential value; use {{SECRET:KEY}} | 0/0/0/0 | 0/0/0/0/0 | False |
| 6 | S1 | A as b32 in case_id | run_case | REFUSED:secret | refused: the call carried a credential value; use {{SECRET:KEY}} | 0/0/0/0 | 0/0/0/0/0 | False |
| 7 | S1 | A as hexl in case_id | run_case | REFUSED:secret | refused: the call carried a credential value; use {{SECRET:KEY}} | 0/0/0/0 | 0/0/0/0/0 | False |
| 8 | S1 | A as hexu in case_id | run_case | REFUSED:secret | refused: the call carried a credential value; use {{SECRET:KEY}} | 0/0/0/0 | 0/0/0/0/0 | False |
| 9 | S1 | A as pct in case_id | run_case | REFUSED:secret | refused: the call carried a credential value; use {{SECRET:KEY}} | 0/0/0/0 | 0/0/0/0/0 | False |
| 10 | S1 | A as pct2 in case_id | run_case | REFUSED:secret | refused: the call carried a credential value; use {{SECRET:KEY}} | 0/0/0/0 | 0/0/0/0/0 | False |
| 11 | S1 | A as rev in case_id | run_case | REFUSED:secret | refused: the call carried a credential value; use {{SECRET:KEY}} | 0/0/0/0 | 0/0/0/0/0 | False |
| 12 | S1 | A as upper in case_id | run_case | REFUSED:secret | refused: the call carried a credential value; use {{SECRET:KEY}} | 0/0/0/0 | 0/0/0/0/0 | False |
| 13 | S1 | A as spaced in case_id | run_case | REFUSED:secret | refused: the call carried a credential value; use {{SECRET:KEY}} | 0/0/0/0 | 0/0/0/0/0 | False |
| 14 | S1 | A as zw in case_id | run_case | REFUSED:nothing_to_do | no such case, or it has no steps to run | 0/0/0/0 | 0/0/0/0/0 | False |
| 15 | S1 | A as hexsp in case_id | run_case | REFUSED:secret | refused: the call carried a credential value; use {{SECRET:KEY}} | 0/0/0/0 | 0/0/0/0/0 | False |
| 16 | S1 | A cyrillic-homoglyph (A->U+0410, E->U+0415) | run_case | REFUSED:nothing_to_do | no such case, or it has no steps to run | 0/0/0/0 | 0/0/0/0/0 | False |
| 17 | S1 | A fullwidth form | run_case | REFUSED:secret | refused: the call carried a credential value; use {{SECRET:KEY}} | 0/0/0/0 | 0/0/0/0/0 | False |
| 18 | S1 | split A across case_id + key 'a' (letter key) | run_case | REFUSED:bad_arguments | invalid arguments (a: extra_forbidden) | 0/0/0/0 | 0/0/0/0/0 | False |
| 19 | S1 | split A across case_id + key '-' (punct key) | run_case | REFUSED:secret | refused: the call carried a credential value; use {{SECRET:KEY}} | 0/0/0/0 | 0/0/0/0/0 | False |
| 20 | S1 | split A across case_id + key ''  | run_case | REFUSED:secret | refused: the call carried a credential value; use {{SECRET:KEY}} | 0/0/0/0 | 0/0/0/0/0 | False |
| 21 | S1 | A nested list/dict inside case_id | run_case | REFUSED:secret | refused: the call carried a credential value; use {{SECRET:KEY}} | 0/0/0/0 | 0/0/0/0/0 | False |
| 22 | S1 | A as dict KEY | run_case | REFUSED:secret | refused: the call carried a credential value; use {{SECRET:KEY}} | 0/0/0/0 | 0/0/0/0/0 | False |
| 23 | S1 | A as dict key base64 | run_case | REFUSED:secret | refused: the call carried a credential value; use {{SECRET:KEY}} | 0/0/0/0 | 0/0/0/0/0 | False |
| 24 | S1 | A inside URL query in case_id | run_case | REFUSED:secret | refused: the call carried a credential value; use {{SECRET:KEY}} | 0/0/0/0 | 0/0/0/0/0 | False |
| 25 | S1 | A pct-encoded inside URL query | run_case | REFUSED:secret | refused: the call carried a credential value; use {{SECRET:KEY}} | 0/0/0/0 | 0/0/0/0/0 | False |
| 26 | S1 | A in tool NAME | run_case<A:raw> | REFUSED:secret | refused: the call carried a credential value; use {{SECRET:KEY}} | 0/0/0/0 | 0/0/0/0/0 | False |
| 27 | S1 | A as the tool name alone | <A:raw> | REFUSED:secret | refused: the call carried a credential value; use {{SECRET:KEY}} | 0/0/0/0 | 0/0/0/0/0 | False |
| 28 | S1 | B (2nd declared key, has reserved chars) raw | run_case | REFUSED:secret | refused: the call carried a credential value; use {{SECRET:KEY}} | 0/0/0/0 | 0/0/0/0/0 | False |
| 29 | S1 | B as pct in case_id | run_case | REFUSED:secret | refused: the call carried a credential value; use {{SECRET:KEY}} | 0/0/0/0 | 0/0/0/0/0 | False |
| 30 | S1 | B as pct2 in case_id | run_case | REFUSED:secret | refused: the call carried a credential value; use {{SECRET:KEY}} | 0/0/0/0 | 0/0/0/0/0 | False |
| 31 | S1 | B as b64 in case_id | run_case | REFUSED:secret | refused: the call carried a credential value; use {{SECRET:KEY}} | 0/0/0/0 | 0/0/0/0/0 | False |
| 32 | S1 | B as hexl in case_id | run_case | REFUSED:secret | refused: the call carried a credential value; use {{SECRET:KEY}} | 0/0/0/0 | 0/0/0/0/0 | False |
| 33 | S1 | B as rev in case_id | run_case | REFUSED:secret | refused: the call carried a credential value; use {{SECRET:KEY}} | 0/0/0/0 | 0/0/0/0/0 | False |
| 34 | S1 | B as spaced in case_id | run_case | REFUSED:secret | refused: the call carried a credential value; use {{SECRET:KEY}} | 0/0/0/0 | 0/0/0/0/0 | False |
| 35 | S1 | B pct-encoded inside URL query | run_case | REFUSED:secret | refused: the call carried a credential value; use {{SECRET:KEY}} | 0/0/0/0 | 0/0/0/0/0 | False |
| 36 | S1 | B double-pct inside URL query | run_case | REFUSED:secret | refused: the call carried a credential value; use {{SECRET:KEY}} | 0/0/0/0 | 0/0/0/0/0 | False |
| 37 | S1 | SHADOW (undeclared, other project key) raw | run_case | REFUSED:secret | refused: the call carried a credential value; use {{SECRET:KEY}} | 0/0/0/0 | 0/0/0/0/0 | False |
| 38 | S1 | SHADOW base64 | run_case | REFUSED:secret | refused: the call carried a credential value; use {{SECRET:KEY}} | 0/0/0/0 | 0/0/0/0/0 | False |
| 39 | S1 | A prefix only (10 chars) - not a secret | run_case | REFUSED:nothing_to_do | no such case, or it has no steps to run | 0/0/0/0 | 0/0/0/0/0 | False |
| 40 | S1 | A raw in crawl extra arg | crawl | REFUSED:secret | refused: the call carried a credential value; use {{SECRET:KEY}} | 0/0/0/0 | 0/0/0/0/0 | False |
| 41 | S1 | A raw in grade_case case_id | grade_case | REFUSED:secret | refused: the call carried a credential value; use {{SECRET:KEY}} | 0/0/0/0 | 0/0/0/0/0 | False |
| 42 | S1 | A raw in get_persona args | get_persona | REFUSED:secret | refused: the call carried a credential value; use {{SECRET:KEY}} | 0/0/0/0 | 0/0/0/0/0 | False |
| 43 | S1 | A in 2 concatenated JSON-ish strings via repr quote tricks | run_case | REFUSED:secret | refused: the call carried a credential value; use {{SECRET:KEY}} | 0/0/0/0 | 0/0/0/0/0 | False |
| 44 | S1 | placeholder {{SECRET:APP_PASS}} (declared) in case_id | run_case | REFUSED:nothing_to_do | no such case, or it has no steps to run | 0/0/0/0 | 0/0/0/0/0 | False |
| 45 | S1 | placeholder {{SECRET:NOPE_KEY}} (undeclared) in case_id | run_case | REFUSED:nothing_to_do | no such case, or it has no steps to run | 0/0/0/0 | 0/0/0/0/0 | False |
| 46 | S1 | placeholder in extra arg | run_case | REFUSED:bad_arguments | invalid arguments (login: extra_forbidden) | 0/0/0/0 | 0/0/0/0/0 | False |
| 47 | S1 | legit login case: FILL Password '{{SECRET:APP_PASS}}' on READ_ONLY | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 48 | S1 | stored case FILL value '{{SECRET:NOPE_KEY}}' (undeclared key) READ_ONLY | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 49 | S1 | stored case FILL value 'x{{SECRET:APP_PASS}}' (literal+placeholder) READ_ONLY | run_case | REFUSED:write_policy | refused under write_policy read_only: step 2 (fill 'Password'): fill with a literal value | 0/0/0/0 | 0/0/0/0/0 | False |
| 50 | S1 | stored case FILL profile field 'Display name' with placeholder (password into non-login field) READ_ONLY | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 51 | S2 | result.error raw A | run_case | EXECUTED | outcome errored: bad login [REDACTED]:APP_PASS | 1/1/0/0 | 0/0/0/0/0 | False |
| 52 | S2 | result.error A as b64 | run_case | REFUSED:secret | result withheld: it carried a credential | 1/1/0/0 | 0/0/1/0/0 | False |
| 53 | S2 | result.error A as b64nopad | run_case | REFUSED:secret | result withheld: it carried a credential | 1/1/0/0 | 0/0/1/0/0 | False |
| 54 | S2 | result.error A as hexl | run_case | REFUSED:secret | result withheld: it carried a credential | 1/1/0/0 | 0/0/1/0/0 | False |
| 55 | S2 | result.error A as pct | run_case | EXECUTED | outcome errored: bad login [REDACTED]:APP_PASS | 1/1/0/0 | 0/0/0/0/0 | False |
| 56 | S2 | result.error A as pct2 | run_case | EXECUTED | outcome errored: bad login [REDACTED]:APP_PASS | 1/1/0/0 | 0/0/0/0/0 | False |
| 57 | S2 | result.error A as rev | run_case | REFUSED:secret | result withheld: it carried a credential | 1/1/0/0 | 0/0/1/0/0 | False |
| 58 | S2 | result.error A as spaced | run_case | REFUSED:secret | result withheld: it carried a credential | 1/1/0/0 | 0/0/1/0/0 | False |
| 59 | S2 | result.error A as b32 | run_case | REFUSED:secret | result withheld: it carried a credential | 1/1/0/0 | 0/0/1/0/0 | False |
| 60 | S2 | result.error SHADOW raw | run_case | EXECUTED | outcome errored: x [REDACTED]:OTHER_PROJ_KEY | 1/1/0/0 | 0/0/0/0/0 | False |
| 61 | S2 | result.error B as raw | run_case | EXECUTED | outcome errored: bad login [REDACTED]:APP_TOKEN | 1/1/0/0 | 0/0/0/0/0 | False |
| 62 | S2 | result.error B as pct | run_case | REFUSED:secret | result withheld: it carried a credential | 1/1/0/0 | 0/0/1/0/0 | False |
| 63 | S2 | result.error B as pct2 | run_case | REFUSED:secret | result withheld: it carried a credential | 1/1/0/0 | 0/0/1/0/0 | False |
| 64 | S2 | result.error B as b64 | run_case | REFUSED:secret | result withheld: it carried a credential | 1/1/0/0 | 0/0/1/0/0 | False |
| 65 | S2 | result.error B as rev | run_case | REFUSED:secret | result withheld: it carried a credential | 1/1/0/0 | 0/0/1/0/0 | False |
| 66 | S2 | result.hitl_prompt raw A | run_case | EXECUTED | outcome errored | 1/1/0/0 | 0/0/0/0/0 | False |
| 67 | S2 | result.not_run_reason b64 A | run_case | EXECUTED | outcome errored | 1/1/0/0 | 0/0/1/0/0 | False |
| 68 | S2 | result.log_ref raw A | run_case | EXECUTED | outcome errored | 1/1/0/0 | 0/0/0/0/0 | False |
| 69 | S2 | result.evidence[0].label raw A | run_case | EXECUTED | outcome errored | 1/1/0/0 | 0/0/0/0/0 | False |
| 70 | S2 | result.evidence[0].path b64 A | run_case | EXECUTED | outcome errored | 1/1/0/0 | 0/0/1/0/0 | False |
| 71 | S2 | result.evidence url raw A in query | run_case | EXECUTED | outcome errored | 1/1/0/0 | 0/0/0/0/0 | False |
| 72 | S2 | execute.run_case raises RuntimeError raw A | run_case | RAISED:RuntimeError | RuntimeError: upstream said <A:raw> | 1/1/0/0 | 0/6/0/0/0 | False |
| 73 | S2 | execute.run_case raises ValueError b64 A | run_case | RAISED:ValueError | ValueError: <A:b64> | 1/1/0/0 | 0/3/0/0/0 | False |
| 74 | S2 | execute.run_case raises KeyError raw A | run_case | RAISED:KeyError | KeyError: '<A:raw>' | 1/1/0/0 | 0/6/0/0/0 | False |
| 75 | S2 | explore.run_crawl raises RuntimeError raw A | crawl | RAISED:RuntimeError | RuntimeError: crawl failed at <A:raw> | 1/0/1/0 | 0/6/0/0/0 | False |
| 76 | S2 | open_session (browser launch) raises raw A | run_case | RAISED:RuntimeError | RuntimeError: browser launch failed, proxy auth <A:raw> | 1/0/0/0 | 0/6/0/0/0 | False |
| 77 | S2 | catalog.catalog raises raw A | get_catalog | RAISED:RuntimeError | RuntimeError: cat <A:raw> | 0/0/0/0 | 0/6/0/0/0 | False |
| 78 | S2 | handler summary exact A | get_catalog | EXECUTED | typed [REDACTED]:APP_PASS | 0/0/0/0 | 0/0/0/0/0 | False |
| 79 | S2 | handler summary A as b64 | get_catalog | REFUSED:secret | result withheld: it carried a credential | 0/0/0/0 | 0/0/0/0/0 | False |
| 80 | S2 | handler summary A as hexl | get_catalog | REFUSED:secret | result withheld: it carried a credential | 0/0/0/0 | 0/0/0/0/0 | False |
| 81 | S2 | handler summary A as pct | get_catalog | EXECUTED | typed [REDACTED]:APP_PASS | 0/0/0/0 | 0/0/0/0/0 | False |
| 82 | S2 | handler summary A as rev | get_catalog | REFUSED:secret | result withheld: it carried a credential | 0/0/0/0 | 0/0/0/0/0 | False |
| 83 | S2 | handler summary A as spaced | get_catalog | REFUSED:secret | result withheld: it carried a credential | 0/0/0/0 | 0/0/0/0/0 | False |
| 84 | S2 | handler artifact_ref raw A | get_catalog | REFUSED:secret | result withheld: it carried a credential | 0/0/0/0 | 0/0/0/0/0 | False |
| 85 | S2 | handler artifact_ref b64 A | get_catalog | REFUSED:secret | result withheld: it carried a credential | 0/0/0/0 | 0/0/0/0/0 | False |
| 86 | S2 | handler returns tool=raw A (contrived: tool name is a constant) | get_catalog | REFUSED:secret | result withheld: it carried a credential | 0/0/0/0 | 6/0/0/0/0 | False |
| 87 | S2G | control: clean rubric+result -> judge prompt allowed | grade_case | EXECUTED | INCONCLUSIVE: judge output rejected | 0/0/0/1 | 0/0/0/0/0 | False |
| 88 | S2G | rubric text raw A | grade_case | EXECUTED | BLOCKED: not judged: prompt withheld | 0/0/0/0 | 0/0/1/0/0 | False |
| 89 | S2G | rubric text b64 A | grade_case | EXECUTED | BLOCKED: not judged: prompt withheld | 0/0/0/0 | 0/0/1/0/0 | False |
| 90 | S2G | stored result.error raw A (earlier persistence) | grade_case | EXECUTED | INCONCLUSIVE: judge output rejected | 0/0/0/1 | 0/0/1/0/0 | False |
| 91 | S2G | stored result.error b64 A | grade_case | EXECUTED | INCONCLUSIVE: judge output rejected | 0/0/0/1 | 0/0/1/0/0 | False |
| 92 | S2G | stored result.error pct2 A | grade_case | EXECUTED | INCONCLUSIVE: judge output rejected | 0/0/0/1 | 0/0/1/0/0 | False |
| 93 | S2G | stored result.error hex A | grade_case | EXECUTED | INCONCLUSIVE: judge output rejected | 0/0/0/1 | 0/0/1/0/0 | False |
| 94 | S2G | stored evidence label reversed A | grade_case | EXECUTED | INCONCLUSIVE: judge output rejected | 0/0/0/1 | 0/0/1/0/0 | False |
| 95 | S2G | stored evidence path raw SHADOW | grade_case | EXECUTED | BLOCKED: not judged: prompt withheld | 0/0/0/0 | 0/0/1/0/0 | False |
| 96 | S2G | judge provider raises with raw A | grade_case | RAISED:RuntimeError | RuntimeError: judge api error echoing key <A:raw> | 0/0/0/1 | 0/6/0/0/0 | False |
| 97 | S3 | no approval, no args | crawl | REFUSED:approval | refusing to start a crawl run against https://app.test — no approval exists for it Grant o | 0/0/0/0 | 0/0/0/0/0 | False |
| 98 | S3 | approval 50 actions, request none (default 200) | crawl | REFUSED:approval | refusing to start a crawl run against https://app.test — the approvals that exist do not c | 0/0/0/0 | 0/0/0/0/0 | False |
| 99 | S3 | approval 50, max_actions=50 | crawl | EXECUTED | running: 0 screens, 0 actions | 1/0/1/0 | 0/0/0/0/0 | False |
| 100 | S3 | approval 50, max_actions=51 | crawl | REFUSED:approval | refusing to start a crawl run against https://app.test — the approvals that exist do not c | 0/0/0/0 | 0/0/0/0/0 | False |
| 101 | S3 | approval 50, max_actions=5000 | crawl | REFUSED:approval | refusing to start a crawl run against https://app.test — the approvals that exist do not c | 0/0/0/0 | 0/0/0/0/0 | False |
| 102 | S3 | approval 50, max_actions='50' (string) | crawl | EXECUTED | running: 0 screens, 0 actions | 1/0/1/0 | 0/0/0/0/0 | False |
| 103 | S3 | approval 50, max_actions=50.0 (float) | crawl | EXECUTED | running: 0 screens, 0 actions | 1/0/1/0 | 0/0/0/0/0 | False |
| 104 | S3 | approval 50, max_actions=True | crawl | EXECUTED | running: 0 screens, 0 actions | 1/0/1/0 | 0/0/0/0/0 | False |
| 105 | S3 | approval 50, max_actions=1e30 | crawl | REFUSED:bad_arguments | invalid arguments (max_actions: int_parsing_size) | 0/0/0/0 | 0/0/0/0/0 | False |
| 106 | S3 | approval 50, max_actions=0 | crawl | REFUSED:bad_arguments | invalid arguments (max_actions: greater_than_equal) | 0/0/0/0 | 0/0/0/0/0 | False |
| 107 | S3 | approval 50, max_actions=-1 | crawl | REFUSED:bad_arguments | invalid arguments (max_actions: greater_than_equal) | 0/0/0/0 | 0/0/0/0/0 | False |
| 108 | S3 | approval 50/900s, wall_clock_s=900 | crawl | EXECUTED | running: 0 screens, 0 actions | 1/0/1/0 | 0/0/0/0/0 | False |
| 109 | S3 | approval 50/900s, wall_clock_s=901 | crawl | REFUSED:approval | refusing to start a crawl run against https://app.test — the approvals that exist do not c | 0/0/0/0 | 0/0/0/0/0 | False |
| 110 | S3 | approval 50/900s, wall_clock_s=inf | crawl | REFUSED:approval | refusing to start a crawl run against https://app.test — the approvals that exist do not c | 0/0/0/0 | 0/0/0/0/0 | False |
| 111 | S3 | approval 50/900s, wall_clock_s=nan | crawl | REFUSED:bad_arguments | invalid arguments (wall_clock_s: greater_than) | 0/0/0/0 | 0/0/0/0/0 | False |
| 112 | S3 | approval 50/900s, wall_clock_s='1e999' | crawl | REFUSED:approval | refusing to start a crawl run against https://app.test — the approvals that exist do not c | 0/0/0/0 | 0/0/0/0/0 | False |
| 113 | S3 | approval 0 actions ('zero means zero'), max_actions=1 | crawl | REFUSED:approval | refusing to start a crawl run against https://app.test — the approvals that exist do not c | 0/0/0/0 | 0/0/0/0/0 | False |
| 114 | S3 | approval ok, extra arg max_depth=99 | crawl | REFUSED:bad_arguments | invalid arguments (max_depth: extra_forbidden) | 0/0/0/0 | 0/0/0/0/0 | False |
| 115 | S3 | approval ok, extra arg max_screens=9999 | crawl | REFUSED:bad_arguments | invalid arguments (max_screens: extra_forbidden) | 0/0/0/0 | 0/0/0/0/0 | False |
| 116 | S3 | approval ok, extra arg allowed_domains=['evil.test'] | crawl | REFUSED:bad_arguments | invalid arguments (allowed_domains: extra_forbidden) | 0/0/0/0 | 0/0/0/0/0 | False |
| 117 | S3 | approval ok, extra arg start_url='https://evil.test/' | crawl | REFUSED:bad_arguments | invalid arguments (start_url: extra_forbidden) | 0/0/0/0 | 0/0/0/0/0 | False |
| 118 | S3 | approval ok, extra arg project='other' | crawl | REFUSED:bad_arguments | invalid arguments (project: extra_forbidden) | 0/0/0/0 | 0/0/0/0/0 | False |
| 119 | S3 | approval ok, extra arg target='https://sub.app.test' | crawl | REFUSED:bad_arguments | invalid arguments (target: extra_forbidden) | 0/0/0/0 | 0/0/0/0/0 | False |
| 120 | S3 | approval ok, extra arg write_policy='allow_writes' | crawl | REFUSED:bad_arguments | invalid arguments (write_policy: extra_forbidden) | 0/0/0/0 | 0/0/0/0/0 | False |
| 121 | S3 | approval ok, extra arg max_probes=1000000 | crawl | REFUSED:bad_arguments | invalid arguments (max_probes: extra_forbidden) | 0/0/0/0 | 0/0/0/0/0 | False |
| 122 | S3 | approval ok, extra arg bounds={'max_actions': 1000000} | crawl | REFUSED:bad_arguments | invalid arguments (bounds: extra_forbidden) | 0/0/0/0 | 0/0/0/0/0 | False |
| 123 | S3 | approval ok, extra arg approval='forged' | crawl | REFUSED:bad_arguments | invalid arguments (approval: extra_forbidden) | 0/0/0/0 | 0/0/0/0/0 | False |
| 124 | S3 | approval ok, extra arg run_id='x' | crawl | REFUSED:bad_arguments | invalid arguments (run_id: extra_forbidden) | 0/0/0/0 | 0/0/0/0/0 | False |
| 125 | S3 | approval for OTHER project | crawl | REFUSED:approval | refusing to start a crawl run against https://app.test — no approval exists for it Grant o | 0/0/0/0 | 0/0/0/0/0 | False |
| 126 | S3 | approval for subdomain target https://sub.app.test | crawl | REFUSED:approval | refusing to start a crawl run against https://app.test — no approval exists for it Grant o | 0/0/0/0 | 0/0/0/0/0 | False |
| 127 | S3 | approval for evil target | crawl | REFUSED:approval | refusing to start a crawl run against https://app.test — no approval exists for it Grant o | 0/0/0/0 | 0/0/0/0/0 | False |
| 128 | S3 | approval target with trailing slash | crawl | REFUSED:approval | refusing to start a crawl run against https://app.test — no approval exists for it Grant o | 0/0/0/0 | 0/0/0/0/0 | False |
| 129 | S3 | approval kind LIVE_CASE only (wrong kind) | crawl | REFUSED:approval | refusing to start a crawl run against https://app.test — no approval exists for it Grant o | 0/0/0/0 | 0/0/0/0/0 | False |
| 130 | S3 | approval kind READ only | crawl | REFUSED:approval | refusing to start a crawl run against https://app.test — no approval exists for it Grant o | 0/0/0/0 | 0/0/0/0/0 | False |
| 131 | S3 | approval kind ADVERSARIAL only | crawl | REFUSED:approval | refusing to start a crawl run against https://app.test — no approval exists for it Grant o | 0/0/0/0 | 0/0/0/0/0 | False |
| 132 | S3 | expired approval (2020-01-01) | crawl | REFUSED:approval | refusing to start a crawl run against https://app.test — the approvals that exist do not c | 0/0/0/0 | 0/0/0/0/0 | False |
| 133 | S3 | unsigned (forged) approval row | crawl | REFUSED:approval | refusing to start a crawl run against https://app.test — the approvals that exist do not c | 0/0/0/0 | 0/0/0/0/0 | False |
| 134 | S3 | approval signed with a WRONG key | crawl | REFUSED:approval | refusing to start a crawl run against https://app.test — the approvals that exist do not c | 0/0/0/0 | 0/0/0/0/0 | False |
| 135 | S3 | tampered approval: max_actions 5 -> 5000 after signing | crawl | REFUSED:approval | refusing to start a crawl run against https://app.test — the approvals that exist do not c | 0/0/0/0 | 0/0/0/0/0 | False |
| 136 | S3 | tampered approval: expires 2020 -> 2099 after signing | crawl | REFUSED:approval | refusing to start a crawl run against https://app.test — the approvals that exist do not c | 0/0/0/0 | 0/0/0/0/0 | False |
| 137 | S3 | tampered approval: signature chars flipped | crawl | REFUSED:approval | refusing to start a crawl run against https://app.test — the approvals that exist do not c | 0/0/0/0 | 0/0/0/0/0 | False |
| 138 | S3 | good approval + 1 bad row (still allowed) | crawl | EXECUTED | running: 0 screens, 0 actions | 1/0/1/0 | 0/0/0/0/0 | False |
| 139 | S3 | good approval, valid crawl w/ login_case missing | crawl | EXECUTED | running: 0 screens, 0 actions | 1/0/1/0 | 0/0/0/0/0 | False |
| 140 | S3 | incremental=True within approval | crawl | EXECUTED | running: 0 screens, 0 actions | 1/0/1/0 | 0/0/0/0/0 | False |
| 141 | S3 | incremental='maybe' | crawl | REFUSED:bad_arguments | invalid arguments (incremental: bool_parsing) | 0/0/0/0 | 0/0/0/0/0 | False |
| 142 | S3 | good approval row but signing key ABSENT at verify time | crawl | REFUSED:approval | refusing to start a crawl run against https://app.test — the approvals that exist do not c | 0/0/0/0 | 0/0/0/0/0 | False |
| 143 | S4-RO | READ_ONLY: CLICK 'Delete account' | run_case | REFUSED:write_policy | refused under write_policy read_only: step 2 (click 'Delete account'): destructive-name de | 0/0/0/0 | 0/0/0/0/0 | False |
| 144 | S4-RO | READ_ONLY: CLICK 'Submit' | run_case | REFUSED:write_policy | refused under write_policy read_only: step 2 (click 'Submit'): destructive-name deny-list | 0/0/0/0 | 0/0/0/0/0 | False |
| 145 | S4-RO | READ_ONLY: CLICK 'Save' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 146 | S4-RO | READ_ONLY: CLICK 'Save changes' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 147 | S4-RO | READ_ONLY: CLICK 'Continue' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 148 | S4-RO | READ_ONLY: CLICK 'Confirm' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 149 | S4-RO | READ_ONLY: CLICK 'Place order' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 150 | S4-RO | READ_ONLY: CLICK 'Update profile' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 151 | S4-RO | READ_ONLY: CLICK 'Register' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 152 | S4-RO | READ_ONLY: CLICK 'Sign up' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 153 | S4-RO | READ_ONLY: CLICK 'Apply now' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 154 | S4-RO | READ_ONLY: CLICK 'Add to cart' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 155 | S4-RO | READ_ONLY: CLICK 'Send message' | run_case | REFUSED:write_policy | refused under write_policy read_only: step 2 (click 'Send message'): destructive-name deny | 0/0/0/0 | 0/0/0/0/0 | False |
| 156 | S4-RO | READ_ONLY: CLICK 'Pay now' | run_case | REFUSED:write_policy | refused under write_policy read_only: step 2 (click 'Pay now'): destructive-name deny-list | 0/0/0/0 | 0/0/0/0/0 | False |
| 157 | S4-RO | READ_ONLY: CLICK 'Remove item' | run_case | REFUSED:write_policy | refused under write_policy read_only: step 2 (click 'Remove item'): destructive-name deny- | 0/0/0/0 | 0/0/0/0/0 | False |
| 158 | S4-RO | READ_ONLY: CLICK 'Approve' | run_case | REFUSED:write_policy | refused under write_policy read_only: step 2 (click 'Approve'): destructive-name deny-list | 0/0/0/0 | 0/0/0/0/0 | False |
| 159 | S4-RO | READ_ONLY: CLICK 'Yes, I am sure' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 160 | S4-RO | READ_ONLY: CLICK 'OK' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 161 | S4-RO | READ_ONLY: CLICK css '#btn-submit' | run_case | REFUSED:write_policy | refused under write_policy read_only: step 2 (click '#btn-submit'): destructive-name deny- | 0/0/0/0 | 0/0/0/0/0 | False |
| 162 | S4-RO | READ_ONLY: CLICK css 'button[type=submit]' | run_case | REFUSED:write_policy | refused under write_policy read_only: step 2 (click 'button[type=submit]'): destructive-na | 0/0/0/0 | 0/0/0/0/0 | False |
| 163 | S4-RO | READ_ONLY: CLICK '' (empty target) | run_case | REFUSED:write_policy | refused under write_policy read_only: step 2 (click ''): unnamed control | 0/0/0/0 | 0/0/0/0/0 | False |
| 164 | S4-RO | READ_ONLY: CLICK Hindi delete 'हटाएं' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 165 | S4-RO | READ_ONLY: CLICK 'DELETE' upper | run_case | REFUSED:write_policy | refused under write_policy read_only: step 2 (click 'DELETE'): destructive-name deny-list | 0/0/0/0 | 0/0/0/0/0 | False |
| 166 | S4-RO | READ_ONLY: CLICK 'De-lete' / 'D e l e t e' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 167 | S4-RO | READ_ONLY: CLICK 'Log out' (never-click) | run_case | REFUSED:write_policy | refused under write_policy read_only: step 2 (click 'Log out'): never-click pattern (logou | 0/0/0/0 | 0/0/0/0/0 | False |
| 168 | S4-RO | READ_ONLY: CLICK 'Sign-Out' | run_case | REFUSED:write_policy | refused under write_policy read_only: step 2 (click 'Sign-Out'): never-click pattern (logo | 0/0/0/0 | 0/0/0/0/0 | False |
| 169 | S4-RO | READ_ONLY: CLICK 'Dashboard' (benign) | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 170 | S4-RO | READ_ONLY: FILL 'Display name'='Eve' literal | run_case | REFUSED:write_policy | refused under write_policy read_only: step 2 (fill 'Display name'): fill with a literal va | 0/0/0/0 | 0/0/0/0/0 | False |
| 171 | S4-RO | READ_ONLY: FILL 'Search'='abc' literal | run_case | REFUSED:write_policy | refused under write_policy read_only: step 2 (fill 'Search'): fill with a literal value | 0/0/0/0 | 0/0/0/0/0 | False |
| 172 | S4-RO | READ_ONLY: FILL ''='' (empty value) | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 173 | S4-RO | READ_ONLY: FILL whitespace value '   ' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 174 | S4-RO | READ_ONLY: FILL value None | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 175 | S4-RO | READ_ONLY: FILL '{{SECRET:APP_PASS}}' into Password | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 176 | S4-RO | READ_ONLY: FILL '{{SECRET:APP_PASS}}{{SECRET:APP_TOKEN}}' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 177 | S4-RO | READ_ONLY: FILL '{{SECRET:APP_PASS}} ' + literal 'x' | run_case | REFUSED:write_policy | refused under write_policy read_only: step 2 (fill 'Password'): fill with a literal value | 0/0/0/0 | 0/0/0/0/0 | False |
| 178 | S4-RO | READ_ONLY: FILL '{{secret:app_pass}}' lowercase | run_case | REFUSED:write_policy | refused under write_policy read_only: step 2 (fill 'Password'): fill with a literal value | 0/0/0/0 | 0/0/0/0/0 | False |
| 179 | S4-RO | READ_ONLY: FILL '{{SECRET:APP PASS}}' malformed | run_case | REFUSED:write_policy | refused under write_policy read_only: step 2 (fill 'Password'): fill with a literal value | 0/0/0/0 | 0/0/0/0/0 | False |
| 180 | S4-RO | READ_ONLY: SELECT literal 'India' | run_case | REFUSED:write_policy | refused under write_policy read_only: step 2 (select 'Country'): select with a literal val | 0/0/0/0 | 0/0/0/0/0 | False |
| 181 | S4-RO | READ_ONLY: SELECT value None | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 182 | S4-RO | READ_ONLY: UPLOAD literal path | run_case | REFUSED:write_policy | refused under write_policy read_only: step 2 (upload 'Resume'): upload with a literal valu | 0/0/0/0 | 0/0/0/0/0 | False |
| 183 | S4-RO | READ_ONLY: UPLOAD value None | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 184 | S4-RO | READ_ONLY: UPLOAD placeholder | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 185 | S4-RO | READ_ONLY: PRESS_KEY 'Enter' (submits focused form) | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 186 | S4-RO | READ_ONLY: PRESS_KEY value 'Enter' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 187 | S4-RO | READ_ONLY: NAVIGATE '/account/delete?confirm=1' (GET mutation) | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 188 | S4-RO | READ_ONLY: NAVIGATE off-domain 'https://evil.test/' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 189 | S4-RO | READ_ONLY: NAVIGATE 'javascript:alert(1)' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 190 | S4-RO | READ_ONLY: NAVIGATE placeholder '{{SECRET:APP_PASS}}' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 191 | S4-RO | READ_ONLY: HOVER 'Menu' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 192 | S4-RO | READ_ONLY: SCROLL | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 193 | S4-RO | READ_ONLY: WAIT | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 194 | S4-RO | READ_ONLY: ASSERT | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 195 | S4-RO | READ_ONLY: BACK | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 196 | S4-TA | TEST_ACCOUNT: CLICK 'Delete account' | run_case | REFUSED:write_policy | refused under write_policy test_account: step 2 (click 'Delete account'): destructive-name | 0/0/0/0 | 0/0/0/0/0 | False |
| 197 | S4-TA | TEST_ACCOUNT: CLICK 'Submit' | run_case | REFUSED:write_policy | refused under write_policy test_account: step 2 (click 'Submit'): destructive-name deny-li | 0/0/0/0 | 0/0/0/0/0 | False |
| 198 | S4-TA | TEST_ACCOUNT: CLICK 'Save' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 199 | S4-TA | TEST_ACCOUNT: CLICK 'Save changes' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 200 | S4-TA | TEST_ACCOUNT: CLICK 'Continue' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 201 | S4-TA | TEST_ACCOUNT: CLICK 'Confirm' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 202 | S4-TA | TEST_ACCOUNT: CLICK 'Place order' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 203 | S4-TA | TEST_ACCOUNT: CLICK 'Update profile' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 204 | S4-TA | TEST_ACCOUNT: CLICK 'Register' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 205 | S4-TA | TEST_ACCOUNT: CLICK 'Sign up' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 206 | S4-TA | TEST_ACCOUNT: CLICK 'Apply now' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 207 | S4-TA | TEST_ACCOUNT: CLICK 'Add to cart' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 208 | S4-TA | TEST_ACCOUNT: CLICK 'Send message' | run_case | REFUSED:write_policy | refused under write_policy test_account: step 2 (click 'Send message'): destructive-name d | 0/0/0/0 | 0/0/0/0/0 | False |
| 209 | S4-TA | TEST_ACCOUNT: CLICK 'Pay now' | run_case | REFUSED:write_policy | refused under write_policy test_account: step 2 (click 'Pay now'): destructive-name deny-l | 0/0/0/0 | 0/0/0/0/0 | False |
| 210 | S4-TA | TEST_ACCOUNT: CLICK 'Remove item' | run_case | REFUSED:write_policy | refused under write_policy test_account: step 2 (click 'Remove item'): destructive-name de | 0/0/0/0 | 0/0/0/0/0 | False |
| 211 | S4-TA | TEST_ACCOUNT: CLICK 'Approve' | run_case | REFUSED:write_policy | refused under write_policy test_account: step 2 (click 'Approve'): destructive-name deny-l | 0/0/0/0 | 0/0/0/0/0 | False |
| 212 | S4-TA | TEST_ACCOUNT: CLICK 'Yes, I am sure' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 213 | S4-TA | TEST_ACCOUNT: CLICK 'OK' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 214 | S4-TA | TEST_ACCOUNT: CLICK css '#btn-submit' | run_case | REFUSED:write_policy | refused under write_policy test_account: step 2 (click '#btn-submit'): destructive-name de | 0/0/0/0 | 0/0/0/0/0 | False |
| 215 | S4-TA | TEST_ACCOUNT: CLICK css 'button[type=submit]' | run_case | REFUSED:write_policy | refused under write_policy test_account: step 2 (click 'button[type=submit]'): destructive | 0/0/0/0 | 0/0/0/0/0 | False |
| 216 | S4-TA | TEST_ACCOUNT: CLICK '' (empty target) | run_case | REFUSED:write_policy | refused under write_policy test_account: step 2 (click ''): unnamed control | 0/0/0/0 | 0/0/0/0/0 | False |
| 217 | S4-TA | TEST_ACCOUNT: CLICK Hindi delete 'हटाएं' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 218 | S4-TA | TEST_ACCOUNT: CLICK 'DELETE' upper | run_case | REFUSED:write_policy | refused under write_policy test_account: step 2 (click 'DELETE'): destructive-name deny-li | 0/0/0/0 | 0/0/0/0/0 | False |
| 219 | S4-TA | TEST_ACCOUNT: CLICK 'De-lete' / 'D e l e t e' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 220 | S4-TA | TEST_ACCOUNT: CLICK 'Log out' (never-click) | run_case | REFUSED:write_policy | refused under write_policy test_account: step 2 (click 'Log out'): never-click pattern (lo | 0/0/0/0 | 0/0/0/0/0 | False |
| 221 | S4-TA | TEST_ACCOUNT: CLICK 'Sign-Out' | run_case | REFUSED:write_policy | refused under write_policy test_account: step 2 (click 'Sign-Out'): never-click pattern (l | 0/0/0/0 | 0/0/0/0/0 | False |
| 222 | S4-TA | TEST_ACCOUNT: CLICK 'Dashboard' (benign) | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 223 | S4-TA | TEST_ACCOUNT: FILL 'Display name'='Eve' literal | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 224 | S4-TA | TEST_ACCOUNT: FILL 'Search'='abc' literal | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 225 | S4-TA | TEST_ACCOUNT: FILL ''='' (empty value) | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 226 | S4-TA | TEST_ACCOUNT: FILL whitespace value '   ' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 227 | S4-TA | TEST_ACCOUNT: FILL value None | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 228 | S4-TA | TEST_ACCOUNT: FILL '{{SECRET:APP_PASS}}' into Password | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 229 | S4-TA | TEST_ACCOUNT: FILL '{{SECRET:APP_PASS}}{{SECRET:APP_TOKEN}}' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 230 | S4-TA | TEST_ACCOUNT: FILL '{{SECRET:APP_PASS}} ' + literal 'x' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 231 | S4-TA | TEST_ACCOUNT: FILL '{{secret:app_pass}}' lowercase | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 232 | S4-TA | TEST_ACCOUNT: FILL '{{SECRET:APP PASS}}' malformed | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 233 | S4-TA | TEST_ACCOUNT: SELECT literal 'India' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 234 | S4-TA | TEST_ACCOUNT: SELECT value None | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 235 | S4-TA | TEST_ACCOUNT: UPLOAD literal path | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 236 | S4-TA | TEST_ACCOUNT: UPLOAD value None | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 237 | S4-TA | TEST_ACCOUNT: UPLOAD placeholder | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 238 | S4-TA | TEST_ACCOUNT: PRESS_KEY 'Enter' (submits focused form) | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 239 | S4-TA | TEST_ACCOUNT: PRESS_KEY value 'Enter' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 240 | S4-TA | TEST_ACCOUNT: NAVIGATE '/account/delete?confirm=1' (GET mutation) | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 241 | S4-TA | TEST_ACCOUNT: NAVIGATE off-domain 'https://evil.test/' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 242 | S4-TA | TEST_ACCOUNT: NAVIGATE 'javascript:alert(1)' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 243 | S4-TA | TEST_ACCOUNT: NAVIGATE placeholder '{{SECRET:APP_PASS}}' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 244 | S4-TA | TEST_ACCOUNT: HOVER 'Menu' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 245 | S4-TA | TEST_ACCOUNT: SCROLL | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 246 | S4-TA | TEST_ACCOUNT: WAIT | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 247 | S4-TA | TEST_ACCOUNT: ASSERT | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 248 | S4-TA | TEST_ACCOUNT: BACK | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 249 | S4-AW | ALLOW_WRITES: CLICK 'Delete account' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 250 | S4-AW | ALLOW_WRITES: CLICK 'Submit' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 251 | S4-AW | ALLOW_WRITES: CLICK 'Save' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 252 | S4-AW | ALLOW_WRITES: CLICK 'Save changes' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 253 | S4-AW | ALLOW_WRITES: CLICK 'Continue' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 254 | S4-AW | ALLOW_WRITES: CLICK 'Confirm' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 255 | S4-AW | ALLOW_WRITES: CLICK 'Place order' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 256 | S4-AW | ALLOW_WRITES: CLICK 'Update profile' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 257 | S4-AW | ALLOW_WRITES: CLICK 'Register' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 258 | S4-AW | ALLOW_WRITES: CLICK 'Sign up' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 259 | S4-AW | ALLOW_WRITES: CLICK 'Apply now' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 260 | S4-AW | ALLOW_WRITES: CLICK 'Add to cart' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 261 | S4-AW | ALLOW_WRITES: CLICK 'Send message' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 262 | S4-AW | ALLOW_WRITES: CLICK 'Pay now' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 263 | S4-AW | ALLOW_WRITES: CLICK 'Remove item' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 264 | S4-AW | ALLOW_WRITES: CLICK 'Approve' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 265 | S4-AW | ALLOW_WRITES: CLICK 'Yes, I am sure' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 266 | S4-AW | ALLOW_WRITES: CLICK 'OK' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 267 | S4-AW | ALLOW_WRITES: CLICK css '#btn-submit' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 268 | S4-AW | ALLOW_WRITES: CLICK css 'button[type=submit]' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 269 | S4-AW | ALLOW_WRITES: CLICK '' (empty target) | run_case | REFUSED:write_policy | refused under write_policy allow_writes: step 2 (click ''): unnamed control | 0/0/0/0 | 0/0/0/0/0 | False |
| 270 | S4-AW | ALLOW_WRITES: CLICK Hindi delete 'हटाएं' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 271 | S4-AW | ALLOW_WRITES: CLICK 'DELETE' upper | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 272 | S4-AW | ALLOW_WRITES: CLICK 'De-lete' / 'D e l e t e' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 273 | S4-AW | ALLOW_WRITES: CLICK 'Log out' (never-click) | run_case | REFUSED:write_policy | refused under write_policy allow_writes: step 2 (click 'Log out'): never-click pattern (lo | 0/0/0/0 | 0/0/0/0/0 | False |
| 274 | S4-AW | ALLOW_WRITES: CLICK 'Sign-Out' | run_case | REFUSED:write_policy | refused under write_policy allow_writes: step 2 (click 'Sign-Out'): never-click pattern (l | 0/0/0/0 | 0/0/0/0/0 | False |
| 275 | S4-AW | ALLOW_WRITES: CLICK 'Dashboard' (benign) | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 276 | S4-AW | ALLOW_WRITES: FILL 'Display name'='Eve' literal | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 277 | S4-AW | ALLOW_WRITES: FILL 'Search'='abc' literal | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 278 | S4-AW | ALLOW_WRITES: FILL ''='' (empty value) | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 279 | S4-AW | ALLOW_WRITES: FILL whitespace value '   ' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 280 | S4-AW | ALLOW_WRITES: FILL value None | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 281 | S4-AW | ALLOW_WRITES: FILL '{{SECRET:APP_PASS}}' into Password | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 282 | S4-AW | ALLOW_WRITES: FILL '{{SECRET:APP_PASS}}{{SECRET:APP_TOKEN}}' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 283 | S4-AW | ALLOW_WRITES: FILL '{{SECRET:APP_PASS}} ' + literal 'x' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 284 | S4-AW | ALLOW_WRITES: FILL '{{secret:app_pass}}' lowercase | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 285 | S4-AW | ALLOW_WRITES: FILL '{{SECRET:APP PASS}}' malformed | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 286 | S4-AW | ALLOW_WRITES: SELECT literal 'India' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 287 | S4-AW | ALLOW_WRITES: SELECT value None | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 288 | S4-AW | ALLOW_WRITES: UPLOAD literal path | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 289 | S4-AW | ALLOW_WRITES: UPLOAD value None | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 290 | S4-AW | ALLOW_WRITES: UPLOAD placeholder | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 291 | S4-AW | ALLOW_WRITES: PRESS_KEY 'Enter' (submits focused form) | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 292 | S4-AW | ALLOW_WRITES: PRESS_KEY value 'Enter' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 293 | S4-AW | ALLOW_WRITES: NAVIGATE '/account/delete?confirm=1' (GET mutation) | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 294 | S4-AW | ALLOW_WRITES: NAVIGATE off-domain 'https://evil.test/' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 295 | S4-AW | ALLOW_WRITES: NAVIGATE 'javascript:alert(1)' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 296 | S4-AW | ALLOW_WRITES: NAVIGATE placeholder '{{SECRET:APP_PASS}}' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 297 | S4-AW | ALLOW_WRITES: HOVER 'Menu' | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 298 | S4-AW | ALLOW_WRITES: SCROLL | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 299 | S4-AW | ALLOW_WRITES: WAIT | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 300 | S4-AW | ALLOW_WRITES: ASSERT | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 301 | S4-AW | ALLOW_WRITES: BACK | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 302 | S4-RO | READ_ONLY: 3 steps given out of order (order=3 delete first in list) | run_case | REFUSED:write_policy | refused under write_policy read_only: step 1 (click 'Delete'): destructive-name deny-list | 0/0/0/0 | 0/0/0/0/0 | False |
| 303 | S4-RO | READ_ONLY: 200 benign steps then one Delete | run_case | REFUSED:write_policy | refused under write_policy read_only: step 999 (click 'Delete'): destructive-name deny-lis | 0/0/0/0 | 0/0/0/0/0 | False |
| 304 | S4-AP | no approval at all | run_case | REFUSED:approval | refusing to start a live_case run against https://app.test — no approval exists for it Gra | 0/0/0/0 | 0/0/0/0/0 | False |
| 305 | S4-AP | only CRAWL approval | run_case | REFUSED:approval | refusing to start a live_case run against https://app.test — no approval exists for it Gra | 0/0/0/0 | 0/0/0/0/0 | False |
| 306 | S4-AP | only ADVERSARIAL approval | run_case | REFUSED:approval | refusing to start a live_case run against https://app.test — no approval exists for it Gra | 0/0/0/0 | 0/0/0/0/0 | False |
| 307 | S4-AP | LIVE_CASE expired | run_case | REFUSED:approval | refusing to start a live_case run against https://app.test — the approvals that exist do n | 0/0/0/0 | 0/0/0/0/0 | False |
| 308 | S4-AP | LIVE_CASE unsigned | run_case | REFUSED:approval | refusing to start a live_case run against https://app.test — the approvals that exist do n | 0/0/0/0 | 0/0/0/0/0 | False |
| 309 | S4-AP | LIVE_CASE other project | run_case | REFUSED:approval | refusing to start a live_case run against https://app.test — no approval exists for it Gra | 0/0/0/0 | 0/0/0/0/0 | False |
| 310 | S4-AP | LIVE_CASE other target | run_case | REFUSED:approval | refusing to start a live_case run against https://app.test — no approval exists for it Gra | 0/0/0/0 | 0/0/0/0/0 | False |
| 311 | S4-AP | LIVE_CASE max_actions=1 for a 2-step case | run_case | REFUSED:approval | refusing to start a live_case run against https://app.test — the approvals that exist do n | 0/0/0/0 | 0/0/0/0/0 | False |
| 312 | S4-AP | LIVE_CASE max_actions=2 for a 2-step case | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 313 | S4-AP | LIVE_CASE max_actions=0 | run_case | REFUSED:approval | refusing to start a live_case run against https://app.test — the approvals that exist do n | 0/0/0/0 | 0/0/0/0/0 | False |
| 314 | S4-AP | LIVE_CASE tampered actions 1->999 | run_case | REFUSED:approval | refusing to start a live_case run against https://app.test — the approvals that exist do n | 0/0/0/0 | 0/0/0/0/0 | False |
| 315 | S4-AP | LIVE_CASE wall_clock 0.0 ('zero means zero'; run_case passes no wall) | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 316 | S4-AP | valid LIVE_CASE approval | run_case | EXECUTED | outcome completed | 1/1/0/0 | 0/0/0/0/0 | False |
| 317 | S5 | tool name 'shell' | shell | REFUSED:unknown_tool | no such tool | 0/0/0/0 | 0/0/0/0/0 | False |
| 318 | S5 | tool name '' |  | REFUSED:unknown_tool | no such tool | 0/0/0/0 | 0/0/0/0/0 | False |
| 319 | S5 | tool name 'RUN_CASE' | RUN_CASE | REFUSED:unknown_tool | no such tool | 0/0/0/0 | 0/0/0/0/0 | False |
| 320 | S5 | tool name 'run_case ' | run_case  | REFUSED:unknown_tool | no such tool | 0/0/0/0 | 0/0/0/0/0 | False |
| 321 | S5 | tool name ' run_case' |  run_case | REFUSED:unknown_tool | no such tool | 0/0/0/0 | 0/0/0/0/0 | False |
| 322 | S5 | tool name '../../etc/passwd' | ../../etc/passwd | REFUSED:unknown_tool | no such tool | 0/0/0/0 | 0/0/0/0/0 | False |
| 323 | S5 | tool name '__class__' | __class__ | REFUSED:unknown_tool | no such tool | 0/0/0/0 | 0/0/0/0/0 | False |
| 324 | S5 | tool name '__init__' | __init__ | REFUSED:unknown_tool | no such tool | 0/0/0/0 | 0/0/0/0/0 | False |
| 325 | S5 | tool name 'run_case\x00' | run_case  | REFUSED:unknown_tool | no such tool | 0/0/0/0 | 0/0/0/0/0 | False |
| 326 | S5 | tool name 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa' | aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa | REFUSED:unknown_tool | no such tool | 0/0/0/0 | 0/0/0/0/0 | False |
| 327 | S5 | tool name 'run_case;rm -rf /' | run_case;rm -rf / | REFUSED:unknown_tool | no such tool | 0/0/0/0 | 0/0/0/0/0 | False |
| 328 | S5 | tool name 'run_case/../crawl' | run_case/../crawl | REFUSED:unknown_tool | no such tool | 0/0/0/0 | 0/0/0/0/0 | False |
| 329 | S5 | tool name 'tools.run_case' | tools.run_case | REFUSED:unknown_tool | no such tool | 0/0/0/0 | 0/0/0/0/0 | False |
| 330 | S5 | tool name 'report' | report | REFUSED:unknown_tool | no such tool | 0/0/0/0 | 0/0/0/0/0 | False |
| 331 | S5 | tool name 'capture_network' | capture_network | REFUSED:unknown_tool | no such tool | 0/0/0/0 | 0/0/0/0/0 | False |
| 332 | S5 | tool name 'dispatch' | dispatch | REFUSED:unknown_tool | no such tool | 0/0/0/0 | 0/0/0/0/0 | False |
| 333 | S5 | tool name '_crawl' | _crawl | REFUSED:unknown_tool | no such tool | 0/0/0/0 | 0/0/0/0/0 | False |
| 334 | S5 | tool name 'run-case' | run-case | REFUSED:unknown_tool | no such tool | 0/0/0/0 | 0/0/0/0/0 | False |
| 335 | S5 | tool name 'run_case\n' | run_case  | REFUSED:unknown_tool | no such tool | 0/0/0/0 | 0/0/0/0/0 | False |
| 336 | S5 | tool name 'рun_case' | рun_case | REFUSED:unknown_tool | no such tool | 0/0/0/0 | 0/0/0/0/0 | False |
| 337 | S5 | tool name None | None | REFUSED:unknown_tool | no such tool | 0/0/0/0 | 0/0/0/0/0 | False |
| 338 | S5 | tool name 123 | 123 | REFUSED:unknown_tool | no such tool | 0/0/0/0 | 0/0/0/0/0 | False |
| 339 | S5 | tool name list ['run_case'] | ['run_case'] | RAISED:TypeError | TypeError: unhashable type: 'list' | 0/0/0/0 | 0/0/0/0/0 | False |
| 340 | S5 | tool name bytes | b'run_case' | REFUSED:unknown_tool | no such tool | 0/0/0/0 | 0/0/0/0/0 | False |
| 341 | S5 | tool name dict | {'a': 1} | RAISED:TypeError | TypeError: unhashable type: 'dict' | 0/0/0/0 | 0/0/0/0/0 | False |
| 342 | S5 | args None | run_case | RAISED:TypeError | TypeError: autotester.schema.agent_layer.RunCaseArgs() argument after ** must be a mapping | 0/0/0/0 | 0/0/0/0/0 | False |
| 343 | S5 | args list | run_case | RAISED:TypeError | TypeError: autotester.schema.agent_layer.RunCaseArgs() argument after ** must be a mapping | 0/0/0/0 | 0/0/0/0/0 | False |
| 344 | S5 | args str | run_case | RAISED:TypeError | TypeError: autotester.schema.agent_layer.RunCaseArgs() argument after ** must be a mapping | 0/0/0/0 | 0/0/0/0/0 | False |
| 345 | S5 | args int | run_case | RAISED:TypeError | TypeError: autotester.schema.agent_layer.RunCaseArgs() argument after ** must be a mapping | 0/0/0/0 | 0/0/0/0/0 | False |
| 346 | S5 | args {1: 'x'} non-str key | run_case | RAISED:TypeError | TypeError: keywords must be strings | 0/0/0/0 | 0/0/0/0/0 | False |
| 347 | S5 | args missing case_id (run_case) | run_case | REFUSED:bad_arguments | invalid arguments (case_id: missing) | 0/0/0/0 | 0/0/0/0/0 | False |
| 348 | S5 | args missing case_id (grade_case) | grade_case | REFUSED:bad_arguments | invalid arguments (case_id: missing) | 0/0/0/0 | 0/0/0/0/0 | False |
| 349 | S5 | case_id int 5 | run_case | REFUSED:bad_arguments | invalid arguments (case_id: string_type) | 0/0/0/0 | 0/0/0/0/0 | False |
| 350 | S5 | case_id None | run_case | REFUSED:bad_arguments | invalid arguments (case_id: string_type) | 0/0/0/0 | 0/0/0/0/0 | False |
| 351 | S5 | case_id list | run_case | REFUSED:bad_arguments | invalid arguments (case_id: string_type) | 0/0/0/0 | 0/0/0/0/0 | False |
| 352 | S5 | case_id dict | run_case | REFUSED:bad_arguments | invalid arguments (case_id: string_type) | 0/0/0/0 | 0/0/0/0/0 | False |
| 353 | S5 | case_id bool | run_case | REFUSED:bad_arguments | invalid arguments (case_id: string_type) | 0/0/0/0 | 0/0/0/0/0 | False |
| 354 | S5 | case_id '' | run_case | REFUSED:bad_arguments | invalid arguments (case_id: string_too_short) | 0/0/0/0 | 0/0/0/0/0 | False |
| 355 | S5 | case_id 200 chars | run_case | REFUSED:nothing_to_do | no such case, or it has no steps to run | 0/0/0/0 | 0/0/0/0/0 | False |
| 356 | S5 | case_id 201 chars | run_case | REFUSED:bad_arguments | invalid arguments (case_id: string_too_long) | 0/0/0/0 | 0/0/0/0/0 | False |
| 357 | S5 | case_id 200001 chars | run_case | REFUSED:bad_arguments | invalid arguments (case_id: string_too_long) | 0/0/0/0 | 0/0/0/0/0 | False |
| 358 | S5 | case_id lone surrogate | run_case | REFUSED:bad_arguments | invalid arguments (case_id: string_unicode) | 0/0/0/0 | 0/0/0/0/0 | False |
| 359 | S5 | case_id NUL | run_case | REFUSED:nothing_to_do | no such case, or it has no steps to run | 0/0/0/0 | 0/0/0/0/0 | False |
| 360 | S5 | get_persona extra arg | get_persona | REFUSED:bad_arguments | invalid arguments (x: extra_forbidden) | 0/0/0/0 | 0/0/0/0/0 | False |
| 361 | S5 | get_catalog extra arg | get_catalog | REFUSED:bad_arguments | invalid arguments (x: extra_forbidden) | 0/0/0/0 | 0/0/0/0/0 | False |
| 362 | S5 | get_catalog args None | get_catalog | RAISED:TypeError | TypeError: autotester.schema.agent_layer.EmptyArgs() argument after ** must be a mapping,  | 0/0/0/0 | 0/0/0/0/0 | False |
| 363 | S5 | crawl max_actions 'abc' | crawl | REFUSED:bad_arguments | invalid arguments (max_actions: int_parsing) | 0/0/0/0 | 0/0/0/0/0 | False |
| 364 | S5 | crawl wall_clock_s -1 | crawl | REFUSED:bad_arguments | invalid arguments (wall_clock_s: greater_than) | 0/0/0/0 | 0/0/0/0/0 | False |
| 365 | S5 | crawl wall_clock_s 0 | crawl | REFUSED:bad_arguments | invalid arguments (wall_clock_s: greater_than) | 0/0/0/0 | 0/0/0/0/0 | False |
| 366 | S5 | HUGE case_id 1 MB 'a' | run_case | REFUSED:bad_arguments | invalid arguments (case_id: string_too_long) | 0/0/0/0 | 0/0/0/0/0 | False |
| 367 | S5 | HUGE case_id 4 MB 'a' | run_case | REFUSED:bad_arguments | invalid arguments (case_id: string_too_long) | 0/0/0/0 | 0/0/0/0/0 | False |
| 368 | S5 | HUGE 200 extra keys | run_case | REFUSED:bad_arguments | invalid arguments (case_id: missing; k0: extra_forbidden; k1: extra_forbidden; k2: extra_f | 0/0/0/0 | 0/0/0/0/0 | False |
| 369 | S5 | HUGE case_id 1 MB of punctuation (fold stress) | run_case | REFUSED:bad_arguments | invalid arguments (case_id: string_too_long) | 0/0/0/0 | 0/0/0/0/0 | False |
| 370 | S5 | HUGE case_id 1 MB of base64-ish chars | run_case | REFUSED:bad_arguments | invalid arguments (case_id: string_too_long) | 0/0/0/0 | 0/0/0/0/0 | False |
| 371 | S5 | HUGE case_id 1 MB of hex chars | run_case | REFUSED:bad_arguments | invalid arguments (case_id: string_too_long) | 0/0/0/0 | 0/0/0/0/0 | False |
| 372 | S5 | recursion: dict nested 100000 deep | run_case | RAISED:RecursionError | RecursionError: maximum recursion depth exceeded while getting the repr of an object | 0/0/0/0 | 0/0/0/0/0 | False |
| 373 | S5 | recursion: self-referential dict | run_case | REFUSED:bad_arguments | invalid arguments (case_id: string_type) | 0/0/0/0 | 0/0/0/0/0 | False |
| 374 | S5 | recursion: self-referential list | run_case | REFUSED:bad_arguments | invalid arguments (case_id: string_type) | 0/0/0/0 | 0/0/0/0/0 | False |
| 375 | S5 | arg object whose __repr__ raises (carrying A) | run_case | RAISED:RuntimeError | RuntimeError: repr boom <A:raw> | 0/0/0/0 | 0/6/0/0/0 | False |
| 376 | S5 | arg object with benign repr | run_case | REFUSED:bad_arguments | invalid arguments (case_id: string_type) | 0/0/0/0 | 0/0/0/0/0 | False |
| 377 | S6 | grade_case id '../../../etc/passwd' | grade_case | REFUSED:nothing_to_do | needs a stored case, its rubric and a result | 0/0/0/0 | 0/0/0/0/0 | False |
| 378 | S6 | run_case id '../../../etc/passwd' | run_case | REFUSED:nothing_to_do | no such case, or it has no steps to run | 0/0/0/0 | 0/0/0/0/0 | False |
| 379 | S6 | grade_case id '..\\..\\x' | grade_case | REFUSED:nothing_to_do | needs a stored case, its rubric and a result | 0/0/0/0 | 0/0/0/0/0 | False |
| 380 | S6 | run_case id '..\\..\\x' | run_case | REFUSED:nothing_to_do | no such case, or it has no steps to run | 0/0/0/0 | 0/0/0/0/0 | False |
| 381 | S6 | grade_case id 'C:/Windows/win.ini' | grade_case | REFUSED:nothing_to_do | needs a stored case, its rubric and a result | 0/0/0/0 | 0/0/0/0/0 | False |
| 382 | S6 | run_case id 'C:/Windows/win.ini' | run_case | REFUSED:nothing_to_do | no such case, or it has no steps to run | 0/0/0/0 | 0/0/0/0/0 | False |
| 383 | S6 | grade_case id 'other/../x' | grade_case | REFUSED:nothing_to_do | needs a stored case, its rubric and a result | 0/0/0/0 | 0/0/0/0/0 | False |
| 384 | S6 | run_case id 'other/../x' | run_case | REFUSED:nothing_to_do | no such case, or it has no steps to run | 0/0/0/0 | 0/0/0/0/0 | False |
| 385 | S6 | grade_case id '%2e%2e%2f%2e%2e%2fx' | grade_case | REFUSED:nothing_to_do | needs a stored case, its rubric and a result | 0/0/0/0 | 0/0/0/0/0 | False |
| 386 | S6 | run_case id '%2e%2e%2f%2e%2e%2fx' | run_case | REFUSED:nothing_to_do | no such case, or it has no steps to run | 0/0/0/0 | 0/0/0/0/0 | False |
| 387 | S6 | grade_case id 'a\x00b' | grade_case | REFUSED:nothing_to_do | needs a stored case, its rubric and a result | 0/0/0/0 | 0/0/0/0/0 | False |
| 388 | S6 | run_case id 'a\x00b' | run_case | REFUSED:nothing_to_do | no such case, or it has no steps to run | 0/0/0/0 | 0/0/0/0/0 | False |
| 389 | S6 | grade_case id '*' | grade_case | REFUSED:nothing_to_do | needs a stored case, its rubric and a result | 0/0/0/0 | 0/0/0/0/0 | False |
| 390 | S6 | run_case id '*' | run_case | REFUSED:nothing_to_do | no such case, or it has no steps to run | 0/0/0/0 | 0/0/0/0/0 | False |
| 391 | S6 | grade_case id 'case-*' | grade_case | REFUSED:nothing_to_do | needs a stored case, its rubric and a result | 0/0/0/0 | 0/0/0/0/0 | False |
| 392 | S6 | run_case id 'case-*' | run_case | REFUSED:nothing_to_do | no such case, or it has no steps to run | 0/0/0/0 | 0/0/0/0/0 | False |
| 393 | S6 | grade_case id 'r1' | grade_case | REFUSED:nothing_to_do | needs a stored case, its rubric and a result | 0/0/0/0 | 0/0/0/0/0 | False |
| 394 | S6 | run_case id 'r1' | run_case | REFUSED:nothing_to_do | no such case, or it has no steps to run | 0/0/0/0 | 0/0/0/0/0 | False |
| 395 | S6 | grade_case id '../rubrics/r1' | grade_case | REFUSED:nothing_to_do | needs a stored case, its rubric and a result | 0/0/0/0 | 0/0/0/0/0 | False |
| 396 | S6 | run_case id '../rubrics/r1' | run_case | REFUSED:nothing_to_do | no such case, or it has no steps to run | 0/0/0/0 | 0/0/0/0/0 | False |
| 397 | S6 | grade_case id 'run-1/../../project.json' | grade_case | REFUSED:nothing_to_do | needs a stored case, its rubric and a result | 0/0/0/0 | 0/0/0/0/0 | False |
| 398 | S6 | run_case id 'run-1/../../project.json' | run_case | REFUSED:nothing_to_do | no such case, or it has no steps to run | 0/0/0/0 | 0/0/0/0/0 | False |
| 399 | S6 | run_case id of ANOTHER project's real case | run_case | REFUSED:nothing_to_do | no such case, or it has no steps to run | 0/0/0/0 | 0/0/0/0/0 | False |
| 400 | S6 | grade_case id of ANOTHER project's real case | grade_case | REFUSED:nothing_to_do | needs a stored case, its rubric and a result | 0/0/0/0 | 0/0/0/0/0 | False |
| 401 | S6 | get_persona with no persona | get_persona | REFUSED:nothing_to_do | no portal persona yet; a crawl builds one | 0/0/0/0 | 0/0/0/0/0 | False |
| 402 | S6 | get_catalog empty project | get_catalog | EXECUTED | 0 of 15 case classes runnable | 0/0/0/0 | 0/0/0/0/0 | False |
| 403 | S6 | grade_case on a STORED case whose rubric_ref is '../../outside/evil' (store-controlled) | grade_case | EXECUTED | INCONCLUSIVE: judge output rejected | 0/0/0/1 | 0/0/0/0/0 | False |
