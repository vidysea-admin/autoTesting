"""Blind probe for AT-890: what text reaches Provider.act from expand / expand_flow / compile_evals."""
import base64, binascii, json, logging, os, shutil, sys, tempfile
from pathlib import Path
from urllib.parse import quote

import autotester
print("autotester.__file__ =", autotester.__file__)
sys.path.insert(0, str(Path(autotester.__file__).parents[2] / "tests"))
import eval_compiler_fixtures as fx  # noqa: E402  (helper builders only)

from autotester.providers.base import Provider  # noqa: E402
from autotester.schema.case import ExpandedSteps  # noqa: E402
from autotester.schema.enums import Action  # noqa: E402
from autotester.schema.flowspec import Flow, Screen, FlowSpec, Step  # noqa: E402
from autotester.schema.project import Project, SecretRef  # noqa: E402
from autotester.stages.eval_compiler import compile_evals  # noqa: E402
from autotester.stages.expand import expand, expand_flow, propose_cases  # noqa: E402
from autotester.stages.review import approve  # noqa: E402
from autotester.store.project_store import ProjectStore  # noqa: E402

ROOT = Path(os.environ["PROBE_ROOT"])
D = "Zq9!declaredSecretVal77"          # declared (PROBE_PW)
D2 = "Tk5-declaredTokenAbc123"          # declared (PROBE_TOKEN)
U = "Xk3#undeclaredOtherVal55"         # undeclared .env value
SLUG = "demo"


class Spy(Provider):
    id = "spy"
    def __init__(self):
        super().__init__()
        self.prompts = []
    def available(self): return True
    def act(self, prompt, schema=None, *, prompt_file=None, fed_id=None):
        self.prompts.append(prompt)
        return ExpandedSteps(steps=[], rationale="n/a")


def mkflow(name="Login", target="email field", value=None, url="https://app.test/signin", extra=None):
    steps = [Step(order=1, action=Action.NAVIGATE, target=url, screen_id="scr_signin"),
             Step(order=2, action=Action.FILL, target=target, value=value, screen_id="scr_signin"),
             Step(order=3, action=Action.CLICK, target="Login button", screen_id="scr_signin")]
    if extra:
        steps += extra
    return Flow(id="flow_login", name=name, entry_screen="scr_signin", exit_screen="scr_home", steps=steps)


def build(root, flow, with_project=True, env=True):
    fx.SLUG  # noqa
    root.mkdir(parents=True, exist_ok=True)
    if env:
        (root / ".env").write_text(f"PROBE_PW={D}\nPROBE_TOKEN={D2}\nOTHER_UNDECLARED={U}\n", encoding="utf-8")
    store = ProjectStore(SLUG, root)
    if with_project:
        store.save_project(Project(slug=SLUG, name="Demo", base_url="https://app.test",
                                   allowed_domains=["app.test"],
                                   secrets=[SecretRef(key="PROBE_PW", domains=["app.test"]),
                                            SecretRef(key="PROBE_TOKEN", domains=["app.test"])]))
    spec = approve(FlowSpec(project=SLUG, screens=[Screen(id="scr_signin", name="Sign in"),
                                                   Screen(id="scr_home", name="Home")], flows=[flow]), by="umesh")
    store.save_flowspec(spec)
    rows = propose_cases(spec)
    store.stage_case_proposals(rows)
    for r in rows:
        store.review_case_proposal(r.id, "umesh", approved=True)
    return store, spec


def run(entry, flow, root, **kw):
    store, spec = build(root, flow, **kw)
    spy = Spy()
    out = {"entry": entry, "exc": None}
    try:
        if entry == "expand":
            expand(spec, spy, store=store)
        elif entry == "expand_flow":
            expand_flow(flow, SLUG, spy, store=store)
        else:
            compile_evals(spec, fx.persona(flow), [], spy, store=store)
    except Exception as e:  # noqa
        out["exc"] = f"{type(e).__name__}: {e}"
    out["n"] = len(spy.prompts)
    out["prompts"] = spy.prompts
    return out


def enc_variants(v):
    return {"raw": v, "b64": base64.b64encode(v.encode()).decode(), "b64url": base64.urlsafe_b64encode(v.encode()).decode().rstrip("="),
            "urlenc": quote(v, safe=""), "upper": v.upper(), "lower": v.lower(), "hex": binascii.hexlify(v.encode()).decode(),
            "spaced": " ".join(v), "reversed": v[::-1]}


POS = ["name", "value", "target", "url_query", "url_path"]
def place(pos, payload):
    if pos == "name": return mkflow(name=f"Login {payload}")
    if pos == "value": return mkflow(value=payload)
    if pos == "target": return mkflow(target=f"field {payload}")
    if pos == "url_query": return mkflow(url=f"https://app.test/cb?token={payload}&x=1")
    if pos == "url_path": return mkflow(url=f"https://app.test/u/{payload}/home")


def classify(res, payload):
    if res["exc"]:
        return f"RAISE[{res['exc'].split(':')[0]}] n={res['n']}"
    leak = any(payload in p for p in res["prompts"])
    return f"{'LEAK' if leak else 'clean'} n={res['n']}"


if __name__ == "__main__":
    mode = sys.argv[1]
    rows = []
    n = 0
    def R():
        global n
        n += 1
        return ROOT / f"r{n}"
    if mode == "secrets":
        for entry in sys.argv[2].split(","):
            for pos in POS:
                for sname, base in (("declD", D), ("undeclU", U)):
                    for vname, payload in enc_variants(base).items():
                        res = run(entry, place(pos, payload), R())
                        rows.append((entry, pos, sname, vname, classify(res, payload), res["exc"]))
        for r in rows:
            print(" | ".join(str(x) for x in r[:5]), flush=True)
        # split spelling: first half in value, second half in target of another step
        half = len(D) // 2
        for entry in sys.argv[2].split(","):
            fl = mkflow(value=D[:half], target=f"field {D[half:]}")
            res = run(entry, fl, R())
            print("SPLIT", entry, classify(res, D), "joined_in_prompt=", any(D[:half] in p and D[half:] in p for p in res["prompts"]))
            fl = mkflow(value=D[:half], extra=[Step(order=4, action=Action.FILL, target="x", value=D[half:])])
            res = run(entry, fl, R())
            print("SPLIT2steps", entry, classify(res, D), "both_halves_in_prompt=", any(D[:half] in p and D[half:] in p for p in res["prompts"]))
    shutil.rmtree(ROOT, ignore_errors=True)
