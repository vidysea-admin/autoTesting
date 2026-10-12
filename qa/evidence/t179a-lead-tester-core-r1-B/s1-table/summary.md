# S1 attack table, base vs head (t179a r1-B, sub-checker). FINDINGS ONLY, no verdict.
Secrets are labels only (<APP_PASS>, <APP_USER>). Scripts: s1_table.py (generator+dispatch driver, independent oracle),
s1_analyze.py (merge+answers), s1_nav.py (NAVIGATE dispatch + REAL BrowserSession.goto per copy), s1_extra.py (login-credit probes),
run_shards.sh. Raw: out/*.json (base1, head1, head2 = 10/10/20 shards), analysis.txt, nav_table.txt, extra_table.txt.
Harness note: probe_lib.goto_would_refuse sets `s.page` = AttributeError (read-only property); s1_nav.py uses `s._page` (same REAL goto).

## Volume
21,744 run_case calls per copy via tools.dispatch (21,588 generated + 156 composed login sequences) x {base, head, head-again}.
Step/Case rejections: 0 (Step has no validators; every combo constructible). Escaped exceptions: 0 / 0 / 0. head vs head2: 0 rows differ.
Wall: ~12 min per run (10-20 parallel shards).

## Totals (rows executed/refused)
| policy | base exec/ref | head exec/ref |
|---|---|---|
| READ_ONLY | 6688/560 | 3340/3908 |
| TEST_ACCOUNT | 7116/132 | 6934/314 |
| ALLOW_WRITES | 7174/74 | 6992/256 |
Per action at head READ_ONLY exec/ref: assert/back/hover/scroll/wait 644/0 each; click 0/644; press_key 0/952; select 0/644; upload 0/644;
fill 28/616; navigate 84/364; composed 8/44. TEST_ACCOUNT and ALLOW_WRITES at head: only navigate (266/182) and click (policy deny-list, unchanged vs base) refuse.
Head refusal classes seen: write_policy, destination only.

## (a) READ_ONLY at head
Independent-oracle count (loose: login FILL = placeholders only after strip): 0. Base same oracle: 2980 of 6688.
STRICT oracle (whole FILL value must be >=1 declared placeholder and nothing else): 7 rows executed.
 - read_only|fill|'Search box'|'   '|{single,first,middle,last,s6-first,s6-mid,s6-last}|login  (whitespace-only FILL in the login case)
 - extra probes (s1_extra): login case [FILL "   "/"\t"/"\n" , CLICK "Place order"] EXECUTES; [FILL "   ", PRESS_KEY Enter] EXECUTES;
   [FILL <APP_PASS>-placeholder+" ", CLICK "Place order"] EXECUTES. Base also executed all. Cause: guards._declared_credential accepts
   any non-empty whitespace value (PLACEHOLDER_RE.sub strip == "" and all() over an empty key list), so a blank FILL arms
   credential_pending and buys one submit CLICK with any non-deny name.
Executed READ_ONLY rows at head (3340), why none can mutate:
 - 3220 rows = WAIT/ASSERT/BACK/HOVER/SCROLL as tested step (644 each; reads/waits) 
 - 84 NAVIGATE rows, deduped: https://app.test/home (+value "x"), HTTPS://APP.TEST/home, http://app.test:8080/, https://sub.app.test/home
   (all in-domain no-query, each x7 positions, plain+login); login-only: https://app.test/home?page=2, https://app.test/search?q=x
 - 28 FILL rows = login case, values <APP_USER>/<APP_PASS>/both placeholders (carve-out) + the 7 whitespace rows above
 - 8 composed login rows: u+p+signin, p+enter, p+enterNone, p+click "Save", p+nav-query, nav-query-then-p, p+hover+click, p+click on target=<APP_PASS> literal
Slack inside the carve-out (not oracle violations, observations): the submit CLICK is name-agnostic apart from the deny-list: login
[FILL <APP_PASS>, CLICK "Save"] and [.., CLICK "<canary literal>"] and [.., CLICK "   "] execute; with 2 credential FILLs, 2 clicks
("Sign in","Place order") execute. A login case may NAVIGATE to a same-domain URL WITH a query (e.g. https://app.test/home?action=buy&id=1) and runs.

## (b) TEST_ACCOUNT / ALLOW_WRITES base-executed -> head-refused
364 rows (182 per policy, identical sets), ALL tested-action NAVIGATE, ALL class `destination`. Zero non-destination differences.
Zero head-executes-but-base-refused. 13 distinct targets; base REAL goto exception (canary secrets):
| target | base goto | note |
|---|---|---|
| https://evil.test/, //evil.test/x, https://app.test.evil.test/, javascript:alert(1), data:text/html,hi, file:///etc/passwd, https://app.test\@evil.test/, https://user@app.test/ | NavigationRefused | base session refuses anyway |
| https://{{SECRET:APP_PASS}}/ | SecretScopeError (canary), UndeclaredSecret (undeclared), **None when <APP_PASS> value is the in-domain host app.test** | NARROWING in that mode |
| //{{SECRET:APP_USER}}/x, https://{{SECRET:APP_USER}} | SecretScopeError/Undeclared (hostvals: SecretScopeError) | base refuses anyway |
| https://{{SECRET:NOPE}}/ | UndeclaredSecret | base refuses anyway |
| ftp://app.test/ | **None** | NARROWING: base goto checks host only |
| https://app.test/ho<TAB>me ; https://app.test/home<LF> | **None** | NARROWING: control chars refused at head; browsers strip TAB/LF so base would navigate to app.test/home |
Placeholder-only target {{SECRET:APP_PASS}}/{{SECRET:APP_USER}}: head executes (no destination judged); base goto: SecretScopeError (canary), navigates (hostvals), UndeclaredSecret (undeclared) -> same as base. Bare paths/descriptions ("/reports", "Admin portal URL", "home", "", "   "): head executes at non-RO, base goto raises NavigationRefused at act time (unchanged).

## (c) Refused multi-step rows
Head: 3,844 refused rows with >1 steps (1906 x3-step, 1896 x6-step, 36 x2, 6 x4 composed). Violations (sessions>0, run_case calls>0, files written>0, data-root tree hash changed): 0.
All 4,478 head-refused rows: 0 violations. Base: 658 refused multi-step, 0 violations. Executed rows: exactly 1 session and 1 run_case call each, 0 anomalies.
6-step fillers included NAVIGATE/HOVER/SCROLL/WAIT/ASSERT/BACK ahead of the bad step, so no partial execution was observed.

## (d) Item 7 cost: BENIGN READ_ONLY rows (benign=True) executed at base, refused at head
483 rows (all positions, plain+login) of 1,120 benign rows executed at base. By action: click 112, press_key 98, fill 70, select 70, upload 70, navigate 63.
Single-step, non-login: 35 distinct rows: click 8 (Home, Next, Products, Dashboard, Tab; 'Search box' with values hello/Home/100), fill 5, select 5, upload 5,
press_key 7 (targets Home/Next/Products/Dashboard/Tab with value None, i.e. defaults to Enter, plus Search box Tab and Escape), navigate 5 (//app.test/x, /reports, "Admin portal URL", home, https://app.test/home?page=2).
Caveat: PRESS_KEY value None executes as Enter (execute.py `step.value or "Enter"`), so 5 of the 7 press_key rows are not truly benign.
Also READ_ONLY benign rows refused at base already: 126 (fill/select/upload with 'Search box'+value).
