"""AT-890 hostile matrix. Run: uv --directory <worktree> run python attack.py"""
from __future__ import annotations

import base64
import json
import sys
import tempfile
import urllib.parse
from pathlib import Path

import autotester
from autotester.providers.mock import MockProvider
from autotester.schema.case import ExpandedSteps
from autotester.schema.enums import Action
from autotester.schema.flowspec import ExpectedState, Flow, FlowSpec, Screen, Step
from autotester.schema.portal_persona import (
    FlowRunRef, PersonaScreen, PersonaTransition, PortalPersona, TaughtFlow)
from autotester.schema.project import Project, SecretRef
from autotester.stages.eval_compiler import compile_evals
from autotester.stages.expand import expand, expand_flow, propose_cases
from autotester.stages.review import approve
from autotester.store.project_store import ProjectStore

print("autotester imported from:", autotester.__file__, file=sys.stderr)
assert ".worktrees" in autotester.__file__ and "check-at887-a" in autotester.__file__

SECRET = "Hunter2-Zebra-4411"
SECRET2 = "p@ss&w0rd!Zq9x/ok"   # specials: url-encoding differs, contains '@'
SHORT = "Zq9xK"                 # 5 chars: under MIN_FOLDED_LEN
UNDECL = "Other-Projects-Key-9082"
EMAIL = "ada.lovelace@example.org"
ENV = f"ST_PASS={SECRET}\nST_PW2={SECRET2}\nST_SHORT={SHORT}\nOTHER_KEY={UNDECL}\n"
DECL = ["ST_PASS", "ST_PW2", "ST_SHORT"]
b64 = lambda s: base64.b64encode(s.encode()).decode()  # noqa: E731


def make_flow(*, name="Sign in", target="email field", value=None, step_extra=None,
              nav_target="https://app.test/signin", precond=None, nav_expected_url=None):
    return Flow(
        id="flow_x", name=name, entry_screen="scr_signin", exit_screen="scr_home",
        preconditions=precond or [],
        steps=[
            Step(order=1, action=Action.NAVIGATE, target=nav_target, screen_id="scr_signin",
                 expected=ExpectedState(url=nav_expected_url)),
            Step(order=2, action=Action.FILL, target=target, value=value, screen_id="scr_signin",
                 **(step_extra or {})),
            Step(order=3, action=Action.CLICK, target="Login button", screen_id="scr_signin"),
        ])


def build(tmp: Path, flow, *, with_project=True, screen_name="Sign in"):
    store = ProjectStore("demo", tmp)
    if with_project:
        store.save_project(Project(
            slug="demo", name="Demo", base_url="https://app.test", allowed_domains=["app.test"],
            secrets=[SecretRef(key=k, domains=["app.test"]) for k in DECL]))
    (tmp / ".env").write_text(ENV, encoding="utf-8")
    spec = approve(FlowSpec(project="demo", flows=[flow],
                            screens=[Screen(id="scr_signin", name=screen_name,
                                            url_pattern=f"https://app.test/?q={SECRET}"),
                                     Screen(id="scr_home", name="Home")]), by="umesh")
    store.save_flowspec(spec)
    rows = propose_cases(spec)
    store.stage_case_proposals(rows)
    for r in rows:
        store.review_case_proposal(r.id, "umesh", approved=True)
    persona = PortalPersona(
        project="demo",
        screens=[PersonaScreen(id="scr_signin", name="Sign in", controls=["email field"]),
                 PersonaScreen(id="scr_home", name="Home", controls=["x"])],
        transitions=[PersonaTransition(from_screen="Sign in", to_screen="Home", control="Login button")],
        taught_flows=[TaughtFlow(id=flow.id, name=flow.name, entry_screen="scr_signin",
                                 run_ref=FlowRunRef(project="demo", flow_id=flow.id,
                                                    entry_screen="scr_signin"))])
    return store, spec, persona


def run(flow, entry, *, with_project=True, screen_name="Sign in"):
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        store, spec, persona = build(tmp, flow, with_project=with_project, screen_name=screen_name)
        prov = MockProvider(responses={"agent": [ExpandedSteps(steps=[], rationale="n/a")] * 60})
        try:
            if entry == "expand":
                expand(store.load_flowspec(), prov, store=store)
            elif entry == "expand_flow":
                expand_flow(flow, "demo", prov, store=store)
            else:
                compile_evals(spec, persona, [], prov, store=store)
            status = "sent" if prov.prompts else "NO-CALL"
        except Exception as exc:  # noqa: BLE001
            status = f"refused:{type(exc).__name__}"
        return status, [p for _, p in prov.prompts]


# (id, flow kwargs, needles that must not reach provider, mask tokens, note)
C = []
def add(id_, needles, tokens=(), **kw):
    C.append((id_, kw, list(needles), list(tokens)))

# --- declared secret in each rendered/unrendered field
add("dec-flow-name", [SECRET], name=f"Sign in {SECRET}")
add("dec-step-value", [SECRET], value=SECRET)
add("dec-step-target", [SECRET], target=f"field {SECRET}")
add("dec-nav-target-query", [SECRET], nav_target=f"https://app.test/signin?token={SECRET}")
add("dec-expected-url", [SECRET], value="x", nav_expected_url=f"https://app.test/?t={SECRET}")
add("dec-step-note", [SECRET], value="x", step_extra=dict(note=SECRET))
add("dec-narration", [SECRET], value="x", step_extra=dict(narration=f"type {SECRET}"))
add("dec-on-screen-text", [SECRET], value="x", step_extra=dict(on_screen_text=SECRET))
add("dec-expected-visible", [SECRET], value="x", step_extra=dict(expected=ExpectedState(visible_text=[SECRET])))
add("dec-preconditions", [SECRET], value="x", precond=[f"logged in with {SECRET}"])
add("dec-screen-name+url (spec screens)", [SECRET], value="x")  # screen url_pattern carries SECRET in build()
add("dec2-specials-value", [SECRET2], value=SECRET2)
add("dec2-in-target-url", [SECRET2], nav_target=f"https://app.test/?p={SECRET2}")
add("undeclared-env-value", [UNDECL], value=UNDECL)
add("undeclared-env-name", [UNDECL], name=f"Sign in {UNDECL}")
add("undeclared-env-target", [UNDECL], target=f"f {UNDECL}")
# --- spelling variants
add("sec-lowercased", [SECRET.lower()], value=SECRET.lower())
add("sec-swapcase", [SECRET.swapcase()], value=SECRET.swapcase())
add("sec-uppercased", [SECRET.upper()], value=SECRET.upper())
add("sec-punct-wrapped", [SECRET], value=f"<<{SECRET}>>")
add("sec-in-longer-token", [SECRET], value=f"abc{SECRET}xyz")
add("sec-separators-changed", ["Hunter2/Zebra/4411", "Hunter2 Zebra 4411"], value="Hunter2/Zebra/4411 and Hunter2 Zebra 4411")
add("sec-no-separators", ["Hunter2Zebra4411"], value="Hunter2Zebra4411")
add("sec-spaced-chars", ["H u n t e r 2"], value="H u n t e r 2 - Z e b r a - 4 4 1 1")
add("sec-zero-width", ["Hunter2​-Zebra"], value="Hunter2​-Zebra-4411")
add("sec-homoglyph-cyrillic-e", ["Huntеr2-Zebra-4411"], value="Huntеr2-Zebra-4411")
add("sec-reversed", [SECRET[::-1]], value=SECRET[::-1])
add("sec-urlenc-full", [urllib.parse.quote(SECRET2, safe=""), urllib.parse.quote(SECRET2)], value=urllib.parse.quote(SECRET2, safe=""))
add("sec-urlenc-in-nav-query", [urllib.parse.quote(SECRET2, safe="")], nav_target="https://app.test/?p=" + urllib.parse.quote(SECRET2, safe=""))
add("sec-base64", [b64(SECRET)], value=b64(SECRET))
add("sec-base64-urlsafe-nopad", [base64.urlsafe_b64encode(SECRET.encode()).decode().rstrip("=")], value=base64.urlsafe_b64encode(SECRET.encode()).decode().rstrip("="))
add("sec-hex", [SECRET.encode().hex()], value=SECRET.encode().hex())
add("sec-html-entity", ["&#72;unter2"], value="&#72;&#117;nter2-Zebra-4411")
add("sec-split-in-two-fields", ["Hunter2-", "Zebra-4411"], target="part Hunter2-", value="Zebra-4411")
add("sec-short-plain", [SHORT], value=SHORT)
add("sec-short-base64 (AT-607 boundary)", [b64(SHORT)], value=b64(SHORT))
# --- placeholders
add("placeholder-in-value", [SECRET], tokens=["{{SECRET:ST_PASS}}"], value="{{SECRET:ST_PASS}}")
add("placeholder-in-target", [SECRET], tokens=["{{SECRET:ST_PASS}}"], target="field {{SECRET:ST_PASS}}")
add("placeholder-in-nav-url", [SECRET], tokens=["{{SECRET:ST_PASS}}"], nav_target="https://app.test/?t={{SECRET:ST_PASS}}")
# --- PII
for tag, em in [("plain", EMAIL), ("plus-tag", "ada+promo@example.org"), ("upper", "ADA.LOVELACE@EXAMPLE.ORG"),
                ("subdomain", "a.b@mail.uni.example.co.in"), ("idn", "adá@exämple.org")]:
    add(f"email-{tag}-value", [em], ["<email>"], value=em)
add("email-in-url-query", [EMAIL, "ada.lovelace%40"], ["<email>"], nav_target=f"https://app.test/signin?email={EMAIL}")
add("email-urlencoded-@", ["ada.lovelace%40example.org"], value="ada.lovelace%40example.org")
add("email-mailto", [EMAIL], ["<email>"], value=f"mailto:{EMAIL}")
add("email-in-flow-name", [EMAIL], ["<email>"], name=f"Sign in as {EMAIL}")
add("email-in-target", [EMAIL], ["<email>"], target=f"link {EMAIL}")
add("email-fullwidth-at", ["ada.lovelace＠example.org"], value="ada.lovelace＠example.org")
add("email-obfuscated-[at]", ["ada.lovelace[at]example.org"], value="ada.lovelace[at]example.org")
add("email-spelled-out", ["ada dot lovelace at example dot org"], value="ada dot lovelace at example dot org")
for tag, ph, nd in [
    ("10digit", "9876543210", ["9876543210"]),
    ("plus91-spaces", "+91 98765 43210", ["98765", "43210"]),
    ("plus91-dashes", "+91-98765-43210", ["98765", "43210"]),
    ("plus91-nospace", "+919876543210", ["9876543210"]),
    ("91-prefix-nospace", "919876543210", ["9876543210"]),
    ("paren-cc", "(+91) 98765 43210", ["98765", "43210"]),
    ("paren-area", "(98765) 43210", ["98765", "43210"]),
    ("groups-5-5", "98765 43210", ["98765", "43210"]),
    ("dash-5-5", "98765-43210", ["98765", "43210"]),
    ("zero-prefix", "09876543210", ["9876543210"]),
    ("dotted", "98765.43210", ["98765", "43210"]),
    ("3-3-4", "987-654-3210", ["987-654-3210"]),
    ("us", "+1 (415) 555-2671", ["555-2671"]),
    ("us-plain", "415-555-2671", ["555-2671"]),
    ("tel-uri", "tel:+919876543210", ["9876543210"]),
    ("spaced-digits", "9 8 7 6 5 4 3 2 1 0", ["9 8 7 6 5 4 3 2 1 0"]),
    ("devanagari-digits", "९८७६५४३२१०", ["९८७६५"]),
    ("fullwidth-digits", "９８７６５４３２１０", ["９８７６５"]),
    ("words", "nine eight seven six five four three two one zero", ["nine eight seven"]),
]:
    add(f"phone-{tag}", nd, ["<phone>"], value=ph)
add("phone-in-url-query", ["9876543210"], ["<phone>"], nav_target="https://app.test/otp?phone=9876543210")
add("phone-in-target", ["98765"], ["<phone>"], target="call 98765 43210 field")
add("phone-in-flow-name", ["9876543210"], ["<phone>"], name="OTP for 9876543210")
add("phone-in-note (unrendered)", ["9876543210"], value="x", step_extra=dict(note="9876543210"))
add("name-person (record only)", ["Ada Lovelace"], ["<name>"], target="First name", value="Ada Lovelace")
add("mixed-all", [SECRET, EMAIL, "98765"], value=f"{EMAIL} +91 98765 43210 {SECRET}")

rows = []
import time
T0=time.time()
for id_, kw, needles, tokens in C:
    for entry in ("expand", "expand_flow", "compile_evals"):
        try:
            flow = make_flow(**kw)
        except Exception as exc:  # noqa: BLE001
            rows.append((id_, entry, f"FLOW-INVALID {exc}", [], False)); continue
        status, prompts = run(flow, entry)
        leaked = [n for n in needles if any(n in p for p in prompts)]
        tok = {t: bool(prompts) and all(t in p for p in prompts) for t in tokens}
        rows.append((id_, entry, status, leaked, tok))
        print(f"[{time.time()-T0:6.1f}s] {id_} {entry} {status} leaked={leaked} tok={tok}", flush=True)

# placeholder: real value must not be substituted; also no mangling
out = []
for id_, entry, status, leaked, tok in rows:
    verdict = "LEAK" if leaked else ("refused" if status.startswith("refused") else ("no-call" if status == "NO-CALL" else "clean"))
    out.append(dict(case=id_, entry=entry, status=status, verdict=verdict, leaked=leaked, tokens=tok))
    print(f"{verdict:8} {entry:13} {id_:42} {status:28} leaked={leaked} tok={tok}")
Path(sys.argv[1] if len(sys.argv) > 1 else "matrix.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
