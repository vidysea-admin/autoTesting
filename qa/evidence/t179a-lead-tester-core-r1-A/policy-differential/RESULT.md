# policy-differential RESULT (unit t179a-lead-tester-core, repair cycle 1)

Script (identical on both copies): `differential.py`. Run: `uv --directory <HEAD> run python differential.py HEAD head.csv`
and `PYTHONPATH=<BASE>/src uv --directory <HEAD> run python differential.py BASE base.csv`.
`autotester.__file__` printed (see head.stdout / base.stdout): HEAD copy `...\head\src\autotester`, BASE copy `...\base\src\autotester`.
Method: `tools.dispatch(ctx,"run_case",{"case_id"})` with a spy on `tools.execute.run_case` and the session factory; per row we record
ok, refusal class, sessions opened, run_case calls, plus (identical code, both copies) the act-time verdict
(`SecretStore.resolve_for_navigation` when a placeholder is present, then `browser.session.check_destination`) and `host_of`.
Files: head.csv, base.csv, diff.txt (all 165 differing rows, all policies), compare.py, supplement_head.py/.out
(HEAD `guards._destination` vs act-time, direct calls), guard_accepts_act_refuses.txt.

Rows: 357 per copy = 119 x 3 policies (TEST_ACCOUNT, ALLOW_WRITES, READ_ONLY) over 5 projects
(demo [3 allowed domains], lhost localhost, ip4 127.0.0.1, ip6 allowed "::1", ip6b allowed "[::1]").
Differing rows: 165 total = TEST_ACCOUNT 42 + ALLOW_WRITES 42 + READ_ONLY 81.
TEST_ACCOUNT and ALLOW_WRITES differ in exactly the same 42 rows; all 42 are NAVIGATE (or a multi-step case containing a NAVIGATE),
all BASE ok -> HEAD refused with class `destination`, zero sessions opened, zero run_case calls. No CLICK / PRESS_KEY / FILL / SELECT /
UPLOAD / ASSERT row differs under TEST_ACCOUNT or ALLOW_WRITES. No row is more permissive at HEAD under any policy. The ordinary
mutating multi-step case `[NAVIGATE https://app.example.test/form, FILL Name Eve, SELECT Plan pro, CLICK Save, ASSERT]` is identical
(ok, 1 session, 1 run_case) at both under both policies. The claim "ALLOW_WRITES/TEST_ACCOUNT refuse nothing new except DESTINATION" holds
at the level of the non-NAVIGATE steps; for NAVIGATE, see the narrowing section.

## TEST_ACCOUNT == ALLOW_WRITES: the 42 differing rows (BASE ok -> HEAD refused destination)
Column: project | row | act-time verdict from check_destination (same code on both copies) | host_of(raw target)

### A. also refused at act time (BASE would have refused at `BrowserSession.goto`): 29 rows
- demo | NAVIGATE:'https://app.example.test./x' | REFUSE NavigationRefused | 'app.example.test.'
- demo | NAVIGATE:'https://user:pw@app.example.test/x' | REFUSE NavigationRefused | ''
- demo | NAVIGATE:'https://app.example.test\\\\x' | REFUSE NavigationRefused | ''
- demo | NAVIGATE:'https://evil.test\\\\@app.example.test/x' | REFUSE NavigationRefused | ''
- demo | NAVIGATE:'//evil.test/x' | REFUSE NavigationRefused | 'evil.test'
- demo | NAVIGATE:'https://xn--bcher-kva.example.test/x' | REFUSE NavigationRefused | 'xn--bcher-kva.example.test'
- demo | NAVIGATE:'https://\u0430pp.example.test/x' | REFUSE NavigationRefused | '\u0430pp.example.test'
- demo | NAVIGATE:'javascript:alert(1)' | REFUSE NavigationRefused | 'javascript'
- demo | NAVIGATE:'data:text/html,<b>x</b>' | REFUSE NavigationRefused | 'data'
- demo | NAVIGATE:'file:///etc/passwd' | REFUSE NavigationRefused | ''
- demo | NAVIGATE:'about:blank' | REFUSE NavigationRefused | 'about'
- demo | NAVIGATE:'https://evil.test/x' | REFUSE NavigationRefused | 'evil.test'
- demo | NAVIGATE:'https://evil.test/app.example.test' | REFUSE NavigationRefused | 'evil.test'
- demo | NAVIGATE:'https://app.example.test.evil.test/x' | REFUSE NavigationRefused | 'app.example.test.evil.test'
- demo | NAVIGATE:'https://evilapp.example.test/x' | REFUSE NavigationRefused | 'evilapp.example.test'
- demo | NAVIGATE:'https://[invalid/x' | REFUSE ValueError | EXC ValueError
- demo | NAVIGATE:'https://app.example.test@evil.test/x' | REFUSE NavigationRefused | ''
- demo | NAVIGATE:'https://@app.example.test/x' | REFUSE NavigationRefused | ''
- demo | NAVIGATE:'localhost:3000/' | REFUSE NavigationRefused | 'localhost'
- demo | NAVIGATE:'mailto:a@app.example.test' | REFUSE NavigationRefused | ''
- demo | NAVIGATE:'https://user:{{SECRET:APP_PASS}}@app.example.test/x' | REFUSE SecretScopeError | ''
- lhost | NAVIGATE:'http://127.0.0.1:3000/' | REFUSE NavigationRefused | '127.0.0.1'
- lhost | NAVIGATE:'http://localhost.evil.test/' | REFUSE NavigationRefused | 'localhost.evil.test'
- ip4 | NAVIGATE:'http://localhost:8080/' | REFUSE NavigationRefused | 'localhost'
- ip4 | NAVIGATE:'http://127.0.0.2/' | REFUSE NavigationRefused | '127.0.0.2'
- ip6 | NAVIGATE:'http://[::2]:8080/' | REFUSE NavigationRefused | '::2'
- ip6b | NAVIGATE:'http://[::1]:8080/' | REFUSE NavigationRefused | '::1'
- ip6b | NAVIGATE:'http://[::1]/x?y=1' | REFUSE NavigationRefused | '::1'
- ip6b | MULTI:form | REFUSE NavigationRefused | '::1'

### B. ACCEPTED by check_destination (would have run at BASE), refused by the HEAD guard: 13 rows
- demo | NAVIGATE:'\\thttps://app.example.test/x' | ACCEPT host=app.example.test | 'app.example.test'
- demo | NAVIGATE:'javascript://app.example.test/%0aalert(1)' | ACCEPT host=app.example.test | 'app.example.test'
- demo | NAVIGATE:'file://app.example.test/x' | ACCEPT host=app.example.test | 'app.example.test'
- demo | NAVIGATE:'ftp://app.example.test/x' | ACCEPT host=app.example.test | 'app.example.test'
- demo | NAVIGATE:'ws://app.example.test/x' | ACCEPT host=app.example.test | 'app.example.test'
- demo | NAVIGATE:'https://app.example.test/x\\ny' | ACCEPT host=app.example.test | 'app.example.test'
- demo | NAVIGATE:'https://app.exa\\tmple.test/x' | ACCEPT host=app.example.test | 'app.example.test'
- demo | NAVIGATE:'https://app.example.test/x\\x00' | ACCEPT host=app.example.test | 'app.example.test'
- demo | NAVIGATE:'https://app.example.test/x\\x7f' | ACCEPT host=app.example.test | 'app.example.test'
- demo | NAVIGATE:'https://{{SECRET:HOST}}/x' | ACCEPT host=app.example.test | '{{secret'
- demo | NAVIGATE:'https://{{SECRET:HOST}}' | ACCEPT host=app.example.test | '{{secret'
- demo | NAVIGATE:'//{{SECRET:HOST}}/x' | ACCEPT host=app.example.test | '{{secret'
- demo | NAVIGATE:'https://{{SECRET:HOST}}:8443/x' | ACCEPT host=app.example.test | '{{secret'

## Narrowing analysis (is a legitimate ALLOW_WRITES / TEST_ACCOUNT run narrowed?)
Code read: session.py `goto` L~143 (`resolve_for_navigation` if a placeholder, then `check_destination`), `check_destination` L~54
(`host_of` then `project.allows_domain`; NO scheme check), secrets.py `host_of` L71, `Project.allows_domain` (schema/project.py L205,
exact match or `.suffix`), guards.py `_destination` (HEAD).

- Group A (29 rows): every one is also refused by `check_destination` at act time (off-domain, lookalike/punycode host, trailing-dot
  host, userinfo, backslash, `javascript:`/`data:`/`file:///`/`about:`/`mailto:`, invalid IPv6 -> ValueError, protocol-relative off-domain).
  BASE would have opened a session and then failed in the browser; HEAD refuses earlier. No narrowing.
- Group B (13 rows) = URLs `check_destination` ACCEPTS that the HEAD guard now REFUSES. These are the narrowing findings:
  1. Placeholder in the authority, 4 matrix rows (+2 more in the supplement): `https://{{SECRET:HOST}}/x`, `https://{{SECRET:HOST}}`,
     `//{{SECRET:HOST}}/x`, `https://{{SECRET:HOST}}:8443/x`, `https://{{SECRET:SUB}}.app.example.test/x`,
     `https://{{SECRET:SUB}}.{{SECRET:HOST}}/x`. `_destination` runs `host_of` on the RAW string (host `'{{secret'`), so it refuses;
     `goto` first resolves the placeholder (resolve_for_navigation) and the resolved host is in-domain, so act time accepts.
     This narrows a legitimate, secret-scope-checked ALLOW_WRITES/TEST_ACCOUNT run. Placeholder forms where the placeholder is the whole
     target or sits in path/port/scheme-less leading position (`{{SECRET:BASE}}/x`, `{{SECRET:BASE}}`, `{{SECRET:LOGINURL}}`,
     `{{SECRET:HOST}}/x`, `https://app.example.test/{{SECRET:APP_PASS}}`, `...:{{SECRET:PORT}}/x`) are unchanged (accepted at BASE and HEAD).
  2. Control characters in an otherwise in-domain http(s) URL, 5 matrix rows + 3 supplement (`\t` prefix, `\n`/`\r\n`/`\t` suffix,
     mid-string `\n`/`\t`, `\x00`, `\x7f`). `_CONTROL` is tested on the raw string BEFORE `strip()`, so a trailing newline/tab is refused
     while a trailing/leading SPACE is stripped and accepted. `check_destination` accepts them (urlparse strips tab/CR/LF). This is the
     stated design (control char refused at every policy) but it is a real narrowing of a URL that the browser would navigate
     (a trailing `\n` is the likeliest accidental case, e.g. a multi-line YAML/JSON value).
  3. Non-http(s) scheme with an in-domain host, 4 rows (`javascript://app.example.test/%0aalert(1)`, `file://app.example.test/x`,
     `ftp://app.example.test/x`, `ws://app.example.test/x` = 4 rows). `check_destination` has no scheme check, so act time ACCEPTS them;
     the HEAD guard refuses. By design, and not a legitimate test target. (see the list above.) Group B = 4 placeholder + 5 control-char + 4 scheme = 13.
- Local-dev targets are NOT narrowed: `http(s)://localhost[:3000]/`, `http://LOCALHOST:3000/x`, `http://localhost/`, `http://sub.localhost:3000/x`,
  `http://127.0.0.1[:8080]/x?y=1`, `https://127.0.0.1:8443/x`, `http://[::1]:8080/`, `http://[::1]/x?y=1` (project allowed_domains `["::1"]`) are
  accepted by BASE, HEAD and check_destination alike (`host_of` strips the brackets and port; `allows_domain` compares `'::1'`).
  The only IPv6 rows that differ are for project ip6b whose allowed_domains is the bracketed string `"[::1]"`: HEAD refuses
  `http://[::1]:8080/`, but `check_destination` refuses it too (host `'::1'` != `'[::1]'`), so a real run of that misconfigured project
  already fails at act time (HEAD only moves the failure earlier, with class `destination`).
- Guard ACCEPTS but check_destination REFUSES (harmless; session still refuses at act time; BASE and HEAD identical): bare paths `/reports`, `/home`,
  `reports`, a description `Admin portal URL`, `app.example.test`-less `evil.test/x`, a bare `{{SECRET:APP_PASS}}` (SecretScopeError),
  an undeclared placeholder, local project `/app`, and the multi-step case whose NAVIGATE is the bare `/form`. Note this means the
  BASE test's bare `/home` NAVIGATE could never actually navigate: `host_of('/home')` is `''` -> NavigationRefused at act time.
  List: guard_accepts_act_refuses.txt.
- Unchanged and accepted at both: uppercase host/scheme, `:443`, `:8443`, `:99999` (invalid port: hostname still parsed; browser fails later),
  second allowed domain, sub-domain, in-domain unicode IDN `b\u00fccher.example.test` (host_of keeps unicode; the allow-list entry is unicode),
  http (not https), leading/trailing space, `//app.example.test/x`, `https://app.example.test?x=1`, `#frag`, and `app.example.test/x` (no scheme).

## READ_ONLY (expected to differ; reported separately)
81 differing rows; 39 BASE ok -> HEAD `write_policy`, 41 BASE ok -> HEAD `destination`, 1 BASE `write_policy` -> HEAD `destination` (ip6b MULTI:form,
different refusal class for the same case, with the destination rule evaluated first). No READ_ONLY row is more permissive at HEAD. Full list in diff.txt.

## FINDINGS (each reproduced; commands: the two differential runs + `supplement_head.py`)
F1. HEAD guards.py `_destination` (L~83-95, `host_of(cleaned)` on the unresolved target) refuses `https://{{SECRET:HOST}}/x`,
    `//{{SECRET:HOST}}/x`, `https://{{SECRET:HOST}}:8443/x`, `https://{{SECRET:SUB}}.app.example.test/x` with class `destination` under
    TEST_ACCOUNT and ALLOW_WRITES, although `BrowserSession.goto` (session.py L143: resolve_for_navigation then check_destination) accepts the resolved
    in-domain URL and BASE ran them (1 session, 1 run_case). Narrows a legitimate ALLOW_WRITES run; contradicts the docstring "the session refuses the same
    hosts at act time". Evidence: head.csv/base.csv rows `NAVIGATE:'https://{{SECRET:HOST}}/x'` etc.; supplement_head.out.
F2. A trailing/leading control character (`\n`, `\r\n`, `\t`, `\x00`, `\x7f`) on an in-domain http(s) URL is refused by HEAD but accepted by
    `check_destination`; trailing space is stripped and accepted (inconsistent: `_CONTROL.search(target)` runs before `.strip()`).
    Stated as intended in the brief; reported as narrowing of a URL the browser would load.
F3. (Low, by design) `javascript://`, `file://`, `ftp://`, `ws://` with an in-domain host: `check_destination` has no scheme check; only the HEAD guard does.
    Not a legitimate target; the guard is stricter than act time.
No other row narrows TEST_ACCOUNT or ALLOW_WRITES. Non-NAVIGATE steps (all CLICK labels, PRESS_KEY, FILL, SELECT, UPLOAD, WAIT, ASSERT) are identical.
Local-dev (localhost, 127.0.0.1, [::1] with `::1` allowed) is not narrowed.

## QUESTIONS / not run
- No browser: whether Chromium would actually load the F2/F3 URLs is reasoned (WHATWG strips tab/LF/CR; `javascript:` navigation by `page.goto` is unlikely to be a test target), not run.
- Whether `[::1]` as an allowed_domains entry should be normalised is outside this check (BASE and act time both refuse it).
