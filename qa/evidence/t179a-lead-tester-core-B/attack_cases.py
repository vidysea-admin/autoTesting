RO, TA, AW = WritePolicy.READ_ONLY, WritePolicy.TEST_ACCOUNT, WritePolicy.ALLOW_WRITES
LIVE = lambda: [appr(ApprovalKind.LIVE_CASE)]  # noqa: E731
CRAWLAP = lambda **k: [appr(ApprovalKind.CRAWL, **k)]  # noqa: E731
BENIGN = [mkcase([NAV])]
V = variants

# ---------------- S1: secrets in call arguments (run_case with a benign case + LIVE approval) -------------
def s1(desc, args, tool="run_case"):
    run("S1", desc, tool, args, approvals=LIVE(), cases=BENIGN)

s1("raw A in case_id", {"case_id": CA})
s1("raw A in extra key value (get_catalog)", {"note": CA}, "get_catalog")
for n in ("b64", "b64url", "b64nopad", "b32", "hexl", "hexu", "pct", "pct2", "rev", "upper", "spaced", "zw", "hexsp"):
    s1(f"A as {n} in case_id", {"case_id": V(CA)[n]})
s1("A cyrillic-homoglyph (A->U+0410, E->U+0415)", {"case_id": CA.replace("A", "\u0410").replace("E", "\u0415")})
s1("A fullwidth form", {"case_id": "".join(chr(ord(c) + 0xFEE0) if c.isalnum() and ord(c) < 128 else c for c in CA)})
s1("split A across case_id + key 'a' (letter key)", {"case_id": CA[:12], "a": CA[12:]})
s1("split A across case_id + key '-' (punct key)", {"case_id": CA[:12], "-": CA[12:]})
s1("split A across case_id + key '' ", {"case_id": CA[:12], "": CA[12:]})
s1("A nested list/dict inside case_id", {"case_id": ["x", {"k": [CA]}]})
s1("A as dict KEY", {CA: 1})
s1("A as dict key base64", {V(CA)["b64"]: 1})
s1("A inside URL query in case_id", {"case_id": "https://app.test/?token=" + CA})
s1("A pct-encoded inside URL query", {"case_id": "https://app.test/?token=" + V(CA)["pct"]})
s1("A in tool NAME", {"case_id": "x"}, "run_case" + CA)
s1("A as the tool name alone", {}, CA)
s1("B (2nd declared key, has reserved chars) raw", {"case_id": CB})
for n in ("pct", "pct2", "b64", "hexl", "rev", "spaced"):
    s1(f"B as {n} in case_id", {"case_id": V(CB)[n]})
s1("B pct-encoded inside URL query", {"case_id": "https://app.test/?t=" + V(CB)["pct"]})
s1("B double-pct inside URL query", {"case_id": "https://app.test/?t=" + V(CB)["pct2"]})
s1("SHADOW (undeclared, other project key) raw", {"case_id": CS})
s1("SHADOW base64", {"case_id": V(CS)["b64"]})
s1("A prefix only (10 chars) - not a secret", {"case_id": CA[:10]})
s1("A raw in crawl extra arg", {"max_actions": 10, "x": CA}, "crawl")
s1("A raw in grade_case case_id", {"case_id": CA}, "grade_case")
s1("A raw in get_persona args", {"q": CA}, "get_persona")
s1("A in 2 concatenated JSON-ish strings via repr quote tricks", {"case_id": "'+'".join([CA[:8], CA[8:]])})
s1("placeholder {{SECRET:APP_PASS}} (declared) in case_id", {"case_id": "{{SECRET:APP_PASS}}"})
s1("placeholder {{SECRET:NOPE_KEY}} (undeclared) in case_id", {"case_id": "{{SECRET:NOPE_KEY}}"})
s1("placeholder in extra arg", {"case_id": "x", "login": "{{SECRET:APP_PASS}}"})

# a stored LOGIN case: placeholder as step value is legitimate on READ_ONLY
login = mkcase([NAV, st(Action.FILL, "Password", "{{SECRET:APP_PASS}}")])
run("S1", "legit login case: FILL Password '{{SECRET:APP_PASS}}' on READ_ONLY", "run_case", None,
    approvals=LIVE(), cases=[login], argsfn=lambda ids: {"case_id": ids[0]})
undeclared = mkcase([NAV, st(Action.FILL, "Password", "{{SECRET:NOPE_KEY}}")])
run("S1", "stored case FILL value '{{SECRET:NOPE_KEY}}' (undeclared key) READ_ONLY", "run_case", None,
    approvals=LIVE(), cases=[undeclared], argsfn=lambda ids: {"case_id": ids[0]})
mixed = mkcase([NAV, st(Action.FILL, "Password", "x{{SECRET:APP_PASS}}")])
run("S1", "stored case FILL value 'x{{SECRET:APP_PASS}}' (literal+placeholder) READ_ONLY", "run_case", None,
    approvals=LIVE(), cases=[mixed], argsfn=lambda ids: {"case_id": ids[0]})
profile = mkcase([NAV, st(Action.FILL, "Display name", "{{SECRET:APP_PASS}}")])
run("S1", "stored case FILL profile field 'Display name' with placeholder (password into non-login field) READ_ONLY",
    "run_case", None, approvals=LIVE(), cases=[profile], argsfn=lambda ids: {"case_id": ids[0]})

# ---------------- S2: secrets coming BACK from stages ----------------
def stage_result(**kw):
    def patch():
        def rc(case, session):
            SPY.run_case += 1
            return RawResult(case_id=case.id, outcome=Outcome.ERRORED, **kw)
        tools.execute.run_case = rc
    return patch

def s2(desc, **kw):
    case = mkcase([NAV])
    run("S2", desc, "run_case", None, approvals=LIVE(), cases=[case], patch=stage_result(**kw),
        argsfn=lambda ids: {"case_id": ids[0]})

s2("result.error raw A", error=f"bad login {CA}")
for n in ("b64", "b64nopad", "hexl", "pct", "pct2", "rev", "spaced", "b32"):
    s2(f"result.error A as {n}", error=f"bad login {V(CA)[n]}")
s2("result.error SHADOW raw", error=f"x {CS}")
for n in ("raw", "pct", "pct2", "b64", "rev"):
    s2(f"result.error B as {n}", error=f"bad login {V(CB)[n]}")
s2("result.hitl_prompt raw A", hitl_prompt=f"supply {CA}")
s2("result.not_run_reason b64 A", not_run_reason=V(CA)["b64"])
s2("result.log_ref raw A", log_ref=f"logs/{CA}.txt")
s2("result.evidence[0].label raw A", evidence=[Evidence(kind=EvidenceKind.DOM, path="d", label=CA)])
s2("result.evidence[0].path b64 A", evidence=[Evidence(kind=EvidenceKind.URL, path="https://app.test/?p=" + V(CA)["b64"])])
s2("result.evidence url raw A in query", evidence=[Evidence(kind=EvidenceKind.URL, path="https://app.test/?p=" + CA)])

def raising(exc):
    def patch():
        def rc(case, session):
            SPY.run_case += 1
            raise exc
        tools.execute.run_case = rc
    return patch

for label, e in (("RuntimeError raw A", RuntimeError(f"upstream said {CA}")),
                 ("ValueError b64 A", ValueError(V(CA)["b64"])),
                 ("KeyError raw A", KeyError(CA))):
    run("S2", f"execute.run_case raises {label}", "run_case", None, approvals=LIVE(), cases=[mkcase([NAV])],
        patch=raising(e), argsfn=lambda ids: {"case_id": ids[0]})

def crawl_raises(exc):
    def patch():
        def cr(*a, **k):
            SPY.run_crawl += 1
            raise exc
        tools.explore.run_crawl = cr
    return patch
run("S2", "explore.run_crawl raises RuntimeError raw A", "crawl", {}, approvals=CRAWLAP(actions=500),
    patch=crawl_raises(RuntimeError(f"crawl failed at {CA}")))

def open_raises(ctx):
    def op(observer):
        SPY.sessions += 1
        raise RuntimeError(f"browser launch failed, proxy auth {CA}")
    ctx.open_session = op
run("S2", "open_session (browser launch) raises raw A", "run_case", None, approvals=LIVE(), cases=[mkcase([NAV])],
    setup=open_raises, argsfn=lambda ids: {"case_id": ids[0]})

def cat_raises(exc):
    def patch():
        def c(*a, **k):
            raise exc
        tools.catalog.catalog = c
    return patch
run("S2", "catalog.catalog raises raw A", "get_catalog", {}, patch=cat_raises(RuntimeError(f"cat {CA}")))

def handler_returns(**kw):
    def patch():
        tools._HANDLERS[AgentToolName.GET_CATALOG] = lambda c, a: ToolOutcome(tool="get_catalog", ok=True, **kw)
    return patch
run("S2", "handler summary exact A", "get_catalog", {}, patch=handler_returns(summary=f"typed {CA}"))
for n in ("b64", "hexl", "pct", "rev", "spaced"):
    run("S2", f"handler summary A as {n}", "get_catalog", {}, patch=handler_returns(summary=f"typed {V(CA)[n]}"))
run("S2", "handler artifact_ref raw A", "get_catalog", {}, patch=handler_returns(summary="ok", artifact_ref=f"x:{CA}"))
run("S2", "handler artifact_ref b64 A", "get_catalog", {}, patch=handler_returns(summary="ok", artifact_ref=V(CA)["b64"]))
def tool_field():
    tools._HANDLERS[AgentToolName.GET_CATALOG] = lambda c, a: ToolOutcome(tool=CA, ok=True, summary="ok")
run("S2", "handler returns tool=raw A (contrived: tool name is a constant)", "get_catalog", {}, patch=tool_field)

# grade_case through the REAL grade stage with a spy provider
def graded(crit_text=None, err=None, label=None, ev_path=None):
    case = mkcase([NAV], rubric=True)
    def setup(ctx):
        ctx.store.save_rubric(Rubric(id="r1", case_id=case.id, criteria=[Criterion(id="c1", text=crit_text or "page loads")]))
        ev = []
        if label or ev_path:
            ev = [Evidence(kind=EvidenceKind.DOM, path=ev_path or "dom", label=label)]
        ctx.store.save_result("run-1", RawResult(case_id=case.id, outcome=Outcome.COMPLETED, error=err, evidence=ev))
    return case, setup
def s2g(desc, **kw):
    case, setup = graded(**kw)
    run("S2G", desc, "grade_case", None, cases=[case], setup=setup, argsfn=lambda ids: {"case_id": ids[0]})
s2g("control: clean rubric+result -> judge prompt allowed")
s2g("rubric text raw A", crit_text=f"mentions {CA}")
s2g("rubric text b64 A", crit_text=f"mentions {V(CA)['b64']}")
s2g("stored result.error raw A (earlier persistence)", err=f"bad {CA}")
s2g("stored result.error b64 A", err=f"bad {V(CA)['b64']}")
s2g("stored result.error pct2 A", err=f"bad {V(CA)['pct2']}")
s2g("stored result.error hex A", err=f"bad {V(CA)['hexl']}")
s2g("stored evidence label reversed A", label=V(CA)["rev"])
s2g("stored evidence path raw SHADOW", ev_path=CS)
class BadJudge(MockProvider):
    def _next(self, role, prompt, **k):
        self.prompts.append((role, prompt))
        raise RuntimeError(f"judge api error echoing key {CA}")
case, setup = graded()
run("S2G", "judge provider raises with raw A", "grade_case", None, cases=[case], setup=setup,
    argsfn=lambda ids: {"case_id": ids[0]}, judge=BadJudge())

# ---------------- S3: crawl against approvals ----------------
def s3(desc, args, approvals, **kw):
    run("S3", desc, "crawl", args, approvals=approvals, **kw)
s3("no approval, no args", {}, [])
s3("approval 50 actions, request none (default 200)", {}, CRAWLAP(actions=50))
s3("approval 50, max_actions=50", {"max_actions": 50}, CRAWLAP(actions=50))
s3("approval 50, max_actions=51", {"max_actions": 51}, CRAWLAP(actions=50))
s3("approval 50, max_actions=5000", {"max_actions": 5000}, CRAWLAP(actions=50))
s3("approval 50, max_actions='50' (string)", {"max_actions": "50"}, CRAWLAP(actions=50))
s3("approval 50, max_actions=50.0 (float)", {"max_actions": 50.0}, CRAWLAP(actions=50))
s3("approval 50, max_actions=True", {"max_actions": True}, CRAWLAP(actions=50))
s3("approval 50, max_actions=1e30", {"max_actions": 1e30}, CRAWLAP(actions=50))
s3("approval 50, max_actions=0", {"max_actions": 0}, CRAWLAP(actions=50))
s3("approval 50, max_actions=-1", {"max_actions": -1}, CRAWLAP(actions=50))
s3("approval 50/900s, wall_clock_s=900", {"max_actions": 10, "wall_clock_s": 900}, CRAWLAP(actions=50))
s3("approval 50/900s, wall_clock_s=901", {"max_actions": 10, "wall_clock_s": 901}, CRAWLAP(actions=50))
s3("approval 50/900s, wall_clock_s=inf", {"max_actions": 10, "wall_clock_s": float("inf")}, CRAWLAP(actions=50))
s3("approval 50/900s, wall_clock_s=nan", {"max_actions": 10, "wall_clock_s": float("nan")}, CRAWLAP(actions=50))
s3("approval 50/900s, wall_clock_s='1e999'", {"max_actions": 10, "wall_clock_s": "1e999"}, CRAWLAP(actions=50))
s3("approval 0 actions ('zero means zero'), max_actions=1", {"max_actions": 1, "wall_clock_s": 1}, CRAWLAP(actions=0))
for k, v in (("max_depth", 99), ("max_screens", 9999), ("allowed_domains", ["evil.test"]), ("start_url", "https://evil.test/"),
             ("project", "other"), ("target", "https://sub.app.test"), ("write_policy", "allow_writes"),
             ("max_probes", 10**6), ("bounds", {"max_actions": 10**6}), ("approval", "forged"), ("run_id", "x")):
    s3(f"approval ok, extra arg {k}={v!r}", {"max_actions": 10, k: v}, CRAWLAP(actions=50))
s3("approval for OTHER project", {"max_actions": 10}, [appr(ApprovalKind.CRAWL, project_slug="other")])
s3("approval for subdomain target https://sub.app.test", {"max_actions": 10}, [appr(ApprovalKind.CRAWL, target="https://sub.app.test")])
s3("approval for evil target", {"max_actions": 10}, [appr(ApprovalKind.CRAWL, target="https://app.test.evil.com")])
s3("approval target with trailing slash", {"max_actions": 10}, [appr(ApprovalKind.CRAWL, target=BASE + "/")])
s3("approval kind LIVE_CASE only (wrong kind)", {"max_actions": 10}, [appr(ApprovalKind.LIVE_CASE)])
s3("approval kind READ only", {"max_actions": 10}, [appr(ApprovalKind.READ)])
s3("approval kind ADVERSARIAL only", {"max_actions": 10}, [appr(ApprovalKind.ADVERSARIAL)])
s3("expired approval (2020-01-01)", {"max_actions": 10}, [appr(ApprovalKind.CRAWL, expires="2020-01-01")])
s3("unsigned (forged) approval row", {"max_actions": 10}, [appr(ApprovalKind.CRAWL, signed=False)])
s3("approval signed with a WRONG key", {"max_actions": 10}, [appr(ApprovalKind.CRAWL, key="some-other-key")])
s3("tampered approval: max_actions 5 -> 5000 after signing", {"max_actions": 4000},
   [(appr(ApprovalKind.CRAWL, actions=5)[0], (r'"max_actions":5\b', '"max_actions":5000'))])
s3("tampered approval: expires 2020 -> 2099 after signing", {"max_actions": 10},
   [(appr(ApprovalKind.CRAWL, expires="2020-01-01")[0], (r'2020-01-01', '2099-01-01'))])
s3("tampered approval: signature chars flipped", {"max_actions": 10},
   [(appr(ApprovalKind.CRAWL)[0], (r'"signature":"[0-9a-f]{4}', '"signature":"0000'))])
s3("good approval + 1 bad row (still allowed)", {"max_actions": 10}, CRAWLAP(actions=50) + [appr(ApprovalKind.CRAWL, signed=False)])
s3("good approval, valid crawl w/ login_case missing", {"max_actions": 10}, CRAWLAP(actions=50))
s3("incremental=True within approval", {"max_actions": 10, "incremental": True}, CRAWLAP(actions=50))
s3("incremental='maybe'", {"max_actions": 10, "incremental": "maybe"}, CRAWLAP(actions=50))

def no_key():
    os.environ.pop("AUTOTESTER_APPROVAL_KEY", None)
def restore_key():
    os.environ["AUTOTESTER_APPROVAL_KEY"] = "attack-harness-fake-signing-key-not-real"
good = CRAWLAP(actions=50)
def _nokey_patch():
    no_key()
run("S3", "good approval row but signing key ABSENT at verify time", "crawl", {"max_actions": 10}, approvals=[], patch=None,
    setup=lambda ctx: (ctx.store.add_approval(good[0][0]), no_key()))
restore_key()

# ---------------- S4: run_case write policy ----------------
STEPS = [
    ("CLICK 'Delete account'", st(Action.CLICK, "Delete account")),
    ("CLICK 'Submit'", st(Action.CLICK, "Submit")),
    ("CLICK 'Save'", st(Action.CLICK, "Save")),
    ("CLICK 'Save changes'", st(Action.CLICK, "Save changes")),
    ("CLICK 'Continue'", st(Action.CLICK, "Continue")),
    ("CLICK 'Confirm'", st(Action.CLICK, "Confirm")),
    ("CLICK 'Place order'", st(Action.CLICK, "Place order")),
    ("CLICK 'Update profile'", st(Action.CLICK, "Update profile")),
    ("CLICK 'Register'", st(Action.CLICK, "Register")),
    ("CLICK 'Sign up'", st(Action.CLICK, "Sign up")),
    ("CLICK 'Apply now'", st(Action.CLICK, "Apply now")),
    ("CLICK 'Add to cart'", st(Action.CLICK, "Add to cart")),
    ("CLICK 'Send message'", st(Action.CLICK, "Send message")),
    ("CLICK 'Pay now'", st(Action.CLICK, "Pay now")),
    ("CLICK 'Remove item'", st(Action.CLICK, "Remove item")),
    ("CLICK 'Approve'", st(Action.CLICK, "Approve")),
    ("CLICK 'Yes, I am sure'", st(Action.CLICK, "Yes, I am sure")),
    ("CLICK 'OK'", st(Action.CLICK, "OK")),
    ("CLICK css '#btn-submit'", st(Action.CLICK, "#btn-submit")),
    ("CLICK css 'button[type=submit]'", st(Action.CLICK, "button[type=submit]")),
    ("CLICK '' (empty target)", st(Action.CLICK, "")),
    ("CLICK Hindi delete 'हटाएं'", st(Action.CLICK, "हटाएं")),
    ("CLICK 'DELETE' upper", st(Action.CLICK, "DELETE")),
    ("CLICK 'De-lete' / 'D e l e t e'", st(Action.CLICK, "D e l e t e")),
    ("CLICK 'Log out' (never-click)", st(Action.CLICK, "Log out")),
    ("CLICK 'Sign-Out'", st(Action.CLICK, "Sign-Out")),
    ("CLICK 'Dashboard' (benign)", st(Action.CLICK, "Dashboard")),
    ("FILL 'Display name'='Eve' literal", st(Action.FILL, "Display name", "Eve")),
    ("FILL 'Search'='abc' literal", st(Action.FILL, "Search", "abc")),
    ("FILL ''='' (empty value)", st(Action.FILL, "Display name", "")),
    ("FILL whitespace value '   '", st(Action.FILL, "Display name", "   ")),
    ("FILL value None", st(Action.FILL, "Display name", None)),
    ("FILL '{{SECRET:APP_PASS}}' into Password", st(Action.FILL, "Password", "{{SECRET:APP_PASS}}")),
    ("FILL '{{SECRET:APP_PASS}}{{SECRET:APP_TOKEN}}'", st(Action.FILL, "Password", "{{SECRET:APP_PASS}}{{SECRET:APP_TOKEN}}")),
    ("FILL '{{SECRET:APP_PASS}} ' + literal 'x'", st(Action.FILL, "Password", "{{SECRET:APP_PASS}}x")),
    ("FILL '{{secret:app_pass}}' lowercase", st(Action.FILL, "Password", "{{secret:app_pass}}")),
    ("FILL '{{SECRET:APP PASS}}' malformed", st(Action.FILL, "Password", "{{SECRET:APP PASS}}")),
    ("SELECT literal 'India'", st(Action.SELECT, "Country", "India")),
    ("SELECT value None", st(Action.SELECT, "Country", None)),
    ("UPLOAD literal path", st(Action.UPLOAD, "Resume", "C:/x/resume.pdf")),
    ("UPLOAD value None", st(Action.UPLOAD, "Resume", None)),
    ("UPLOAD placeholder", st(Action.UPLOAD, "Resume", "{{SECRET:APP_PASS}}")),
    ("PRESS_KEY 'Enter' (submits focused form)", st(Action.PRESS_KEY, "Enter")),
    ("PRESS_KEY value 'Enter'", st(Action.PRESS_KEY, "body", "Enter")),
    ("NAVIGATE '/account/delete?confirm=1' (GET mutation)", st(Action.NAVIGATE, "/account/delete?confirm=1")),
    ("NAVIGATE off-domain 'https://evil.test/'", st(Action.NAVIGATE, "https://evil.test/")),
    ("NAVIGATE 'javascript:alert(1)'", st(Action.NAVIGATE, "javascript:alert(1)")),
    ("NAVIGATE placeholder '{{SECRET:APP_PASS}}'", st(Action.NAVIGATE, "{{SECRET:APP_PASS}}")),
    ("HOVER 'Menu'", st(Action.HOVER, "Menu")),
    ("SCROLL", st(Action.SCROLL, "page")),
    ("WAIT", st(Action.WAIT, "1s")),
    ("ASSERT", st(Action.ASSERT, "Welcome")),
    ("BACK", st(Action.BACK, "")),
]
for label, step in STEPS:
    run("S4-RO", f"READ_ONLY: {label}", "run_case", None, policy=RO, approvals=LIVE(), cases=[mkcase([NAV, step])],
        argsfn=lambda ids: {"case_id": ids[0]})
for pol, tag in ((TA, "S4-TA"), (AW, "S4-AW")):
    for label, step in STEPS:
        run(tag, f"{pol.value.upper()}: {label}", "run_case", None, policy=pol, approvals=LIVE(), cases=[mkcase([NAV, step])],
            argsfn=lambda ids: {"case_id": ids[0]})

# multi-step: mutating step last / out of order
run("S4-RO", "READ_ONLY: 3 steps given out of order (order=3 delete first in list)", "run_case", None, policy=RO, approvals=LIVE(),
    cases=[mkcase([st(Action.CLICK, "Delete", order=1), NAV.model_copy(update={"order": 0})])],
    argsfn=lambda ids: {"case_id": ids[0]})
run("S4-RO", "READ_ONLY: 200 benign steps then one Delete", "run_case", None, policy=RO, approvals=LIVE(),
    cases=[mkcase([st(Action.HOVER, "m", order=i) for i in range(1, 200)] + [st(Action.CLICK, "Delete", order=999)])],
    argsfn=lambda ids: {"case_id": ids[0]})

# run_case approval variants
def rc_ap(desc, approvals, cases=None):
    run("S4-AP", desc, "run_case", None, approvals=approvals, cases=cases or [mkcase([NAV])], argsfn=lambda ids: {"case_id": ids[0]})
rc_ap("no approval at all", [])
rc_ap("only CRAWL approval", [appr(ApprovalKind.CRAWL)])
rc_ap("only ADVERSARIAL approval", [appr(ApprovalKind.ADVERSARIAL)])
rc_ap("LIVE_CASE expired", [appr(ApprovalKind.LIVE_CASE, expires="2020-01-01")])
rc_ap("LIVE_CASE unsigned", [appr(ApprovalKind.LIVE_CASE, signed=False)])
rc_ap("LIVE_CASE other project", [appr(ApprovalKind.LIVE_CASE, project_slug="other")])
rc_ap("LIVE_CASE other target", [appr(ApprovalKind.LIVE_CASE, target="https://sub.app.test")])
rc_ap("LIVE_CASE max_actions=1 for a 2-step case", [appr(ApprovalKind.LIVE_CASE, actions=1)], [mkcase([NAV, st(Action.HOVER, "m")])])
rc_ap("LIVE_CASE max_actions=2 for a 2-step case", [appr(ApprovalKind.LIVE_CASE, actions=2)], [mkcase([NAV, st(Action.HOVER, "m")])])
rc_ap("LIVE_CASE max_actions=0", [appr(ApprovalKind.LIVE_CASE, actions=0)])
rc_ap("LIVE_CASE tampered actions 1->999", [(appr(ApprovalKind.LIVE_CASE, actions=1)[0], (r'"max_actions":1\b', '"max_actions":999'))],
      [mkcase([NAV, st(Action.HOVER, "m")])])
rc_ap("LIVE_CASE wall_clock 0.0 ('zero means zero'; run_case passes no wall)", [appr(ApprovalKind.LIVE_CASE, wall=0.0)])
rc_ap("valid LIVE_CASE approval", LIVE())

# ---------------- S5: dispatcher robustness ----------------
def s5(desc, tool, args, **kw):
    run("S5", desc, tool, args, approvals=LIVE(), cases=BENIGN, **kw)
for nm in ("shell", "", "RUN_CASE", "run_case ", " run_case", "../../etc/passwd", "__class__", "__init__", "run_case\x00",
           "a" * 10000, "run_case;rm -rf /", "run_case/../crawl", "tools.run_case", "report", "capture_network", "dispatch",
           "_crawl", "run-case", "run_case\n", "\u0440un_case"):
    s5(f"tool name {nm[:30]!r}", nm, {"case_id": "x"})
s5("tool name None", None, {"case_id": "x"})
s5("tool name 123", 123, {"case_id": "x"})
s5("tool name list ['run_case']", ["run_case"], {"case_id": "x"})
s5("tool name bytes", b"run_case", {"case_id": "x"})
s5("tool name dict", {"a": 1}, {"case_id": "x"})
s5("args None", "run_case", None)
s5("args list", "run_case", ["x"])
s5("args str", "run_case", "case_id=x")
s5("args int", "run_case", 5)
s5("args {1: 'x'} non-str key", "run_case", {1: "x"})
s5("args missing case_id (run_case)", "run_case", {})
s5("args missing case_id (grade_case)", "grade_case", {})
s5("case_id int 5", "run_case", {"case_id": 5})
s5("case_id None", "run_case", {"case_id": None})
s5("case_id list", "run_case", {"case_id": ["a"]})
s5("case_id dict", "run_case", {"case_id": {"a": 1}})
s5("case_id bool", "run_case", {"case_id": True})
s5("case_id ''", "run_case", {"case_id": ""})
s5("case_id 200 chars", "run_case", {"case_id": "a" * 200})
s5("case_id 201 chars", "run_case", {"case_id": "a" * 201})
s5("case_id 200001 chars", "run_case", {"case_id": "a" * 200001})
s5("case_id lone surrogate", "run_case", {"case_id": "\ud800"})
s5("case_id NUL", "run_case", {"case_id": "a\x00b"})
s5("get_persona extra arg", "get_persona", {"x": 1})
s5("get_catalog extra arg", "get_catalog", {"x": 1})
s5("get_catalog args None", "get_catalog", None)
s5("crawl max_actions 'abc'", "crawl", {"max_actions": "abc"})
s5("crawl wall_clock_s -1", "crawl", {"wall_clock_s": -1})
s5("crawl wall_clock_s 0", "crawl", {"wall_clock_s": 0})
t0 = time.monotonic()
s5("HUGE case_id 1 MB 'a'", "run_case", {"case_id": "a" * 1_000_000})
s5("HUGE case_id 4 MB 'a'", "run_case", {"case_id": "a" * 4_000_000})
s5("HUGE 200 extra keys", "run_case", {f"k{i}": "v" * 1000 for i in range(200)})
s5("HUGE case_id 1 MB of punctuation (fold stress)", "run_case", {"case_id": "-_." * 350_000})
s5("HUGE case_id 1 MB of base64-ish chars", "run_case", {"case_id": "QUJD" * 250_000})
s5("HUGE case_id 1 MB of hex chars", "run_case", {"case_id": "ab" * 500_000})
deep = {}
cur = deep
for _ in range(100000):
    cur["a"] = {}
    cur = cur["a"]
s5("recursion: dict nested 100000 deep", "run_case", {"case_id": deep})
selfref: dict = {}
selfref["a"] = selfref
s5("recursion: self-referential dict", "run_case", {"case_id": selfref})
selflist: list = []
selflist.append(selflist)
s5("recursion: self-referential list", "run_case", {"case_id": selflist})
class Weird:
    def __repr__(self):
        raise RuntimeError(f"repr boom {CA}")
s5("arg object whose __repr__ raises (carrying A)", "run_case", {"case_id": Weird()})
class Weird2:
    def __repr__(self):
        return "x"
s5("arg object with benign repr", "run_case", {"case_id": Weird2()})

# ---------------- S6: persona / catalog / grade_case ids ----------------
def s6(desc, tool, cid, **kw):
    run("S6", desc, tool, {"case_id": cid}, approvals=LIVE(), cases=BENIGN, **kw)
for cid in ("../../../etc/passwd", "..\\..\\x", "C:/Windows/win.ini", "other/../x", "%2e%2e%2f%2e%2e%2fx", "a\x00b", "*", "case-*",
            "r1", "../rubrics/r1", "run-1/../../project.json"):
    s6(f"grade_case id {cid!r}", "grade_case", cid)
    s6(f"run_case id {cid!r}", "run_case", cid)

def other_project_case(ctx):
    root = ctx.store.paths.dir.parent
    other = ProjectStore("other", root)
    other.paths.ensure()
    other.save_project(project(slug="other"))
    other.add_case(mkcase([NAV, st(Action.HOVER, "other-only")], slug="other"))
    global OTHER_ID
    OTHER_ID = other.list_cases()[0].id
run("S6", "run_case id of ANOTHER project's real case", "run_case", None, approvals=LIVE(), cases=BENIGN, setup=other_project_case,
    argsfn=lambda ids: {"case_id": OTHER_ID})
run("S6", "grade_case id of ANOTHER project's real case", "grade_case", None, approvals=LIVE(), cases=BENIGN, setup=other_project_case,
    argsfn=lambda ids: {"case_id": OTHER_ID})
run("S6", "get_persona with no persona", "get_persona", {})
run("S6", "get_catalog empty project", "get_catalog", {})
# rubric_ref traversal in a STORED case (store content, not model-controlled) -> reads outside the project?
def trav_setup(ctx):
    root = ctx.store.paths.dir.parent
    (root / "outside").mkdir(exist_ok=True)
    ru = Rubric(id="evil", case_id="x", criteria=[Criterion(id="c1", text="OUTSIDE-RUBRIC-MARKER")])
    (root / "outside" / "evil.json").write_text(ru.model_dump_json(), "utf-8")
    ctx.store.save_result("run-1", RawResult(case_id=TRAV_ID[0], outcome=Outcome.COMPLETED))
TRAV_ID: list = []
tcase = mkcase([NAV], rubric_ref="../../outside/evil")
TRAV_ID.append(tcase.id)
run("S6", "grade_case on a STORED case whose rubric_ref is '../../outside/evil' (store-controlled)", "grade_case", None,
    cases=[tcase], setup=trav_setup, argsfn=lambda ids: {"case_id": ids[0]})

print("done cases", len(REC))
