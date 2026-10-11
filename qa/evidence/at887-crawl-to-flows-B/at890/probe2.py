import sys, os, logging, hashlib, json
import probe1 as p
from probe1 import *  # noqa

def line_with(prompts, needle_fn):
    for pr in prompts[:1]:
        return [l for l in pr.splitlines() if needle_fn(l)]
    return []

mode = sys.argv[1]
n = 0
def R():
    global n; n += 1
    return p.ROOT / f"r{n}"

if mode == "pii":
    entry = sys.argv[2]
    payloads = {"email": "alice.smith@example.com", "email_urlenc": "alice.smith%40example.com",
                "phone_intl": "+91 98765 43210", "phone_10": "9876543210", "phone_us": "(415) 555-2671",
                "name": "Priya Sharma"}
    for pos in p.POS:
        for pn, pv in payloads.items():
            res = p.run(entry, p.place(pos, pv), R())
            leak = any(pv in x for x in res["prompts"])
            rendered = [l for l in (res["prompts"][0].splitlines() if res["prompts"] else []) if "Login" in l or "app.test" in l or "field" in l or "fill" in l]
            print(f"{entry} | {pos} | {pn} | {'RAW-REACHES-ACT' if leak else 'masked'} n={res['n']} exc={res['exc']} | {rendered}", flush=True)
elif mode == "placeholders":
    for entry in ("expand", "expand_flow", "compile_evals"):
        fl = p.mkflow(name="Login", target="password {{SECRET:PROBE_PW}} field", value="{{SECRET:PROBE_PW}}",
                      extra=[p.Step(order=4, action=p.Action.FILL, target="{{SECRET:UNDECLARED_KEY}}", value="{{SECRET:UNDECLARED_KEY}}")])
        res = p.run(entry, fl, R())
        pr = res["prompts"][0] if res["prompts"] else ""
        print(entry, "exc=", res["exc"], "n=", res["n"],
              "declared_in_value+target:", pr.count("{{SECRET:PROBE_PW}}"), "undeclared:", pr.count("{{SECRET:UNDECLARED_KEY}}"),
              "all12_have_placeholders:", all(x.count("{{SECRET:PROBE_PW}}") == 2 and x.count("{{SECRET:UNDECLARED_KEY}}") == 2 for x in res["prompts"]))
        if entry == "expand":
            print("\n".join(l for l in pr.splitlines() if "SECRET" in l and ("fill" in l or "navigate" in l)))
    # placeholder mangled by a short undeclared .env value (F8-ish natural trigger)
    root = R(); root.mkdir(parents=True)
    fl = p.mkflow(value="{{SECRET:PROBE_PW}}")
    store, spec = p.build(root, fl)
    (root / ".env").write_text(f"PROBE_PW={p.D}\nPROBE_TOKEN={p.D2}\nPORT=PROBE\n", encoding="utf-8")
    spy = p.Spy(); p.expand(spec, spy, store=store)
    print("short .env value 'PROBE' -> placeholder in prompt:", [l for l in spy.prompts[0].splitlines() if "fill" in l])
    (root / ".env").write_text(f"PROBE_PW={p.D}\nPROBE_TOKEN={p.D2}\nDEBUG=1\n", encoding="utf-8")
    spy = p.Spy(); p.expand(spec, spy, store=store)
    print("short .env value '1' -> prompt lines:", [l for l in spy.prompts[0].splitlines() if l.startswith("[RED") or l.startswith("2") or "REDACTED" in l][:6])
elif mode == "noproject":
    for entry in ("expand", "expand_flow", "compile_evals"):
        for label, fl in (("declared-looking .env value in value", p.place("value", p.D)),
                          ("undeclared .env value in url_query", p.place("url_query", p.U)),
                          ("email in name", p.place("name", "bob@example.org")),
                          ("phone in target", p.place("target", "9876543210"))):
            res = p.run(entry, fl, R(), with_project=False)
            pay = {"declared-looking .env value in value": p.D, "undeclared .env value in url_query": p.U,
                   "email in name": "bob@example.org", "phone in target": "9876543210"}[label]
            print(entry, "|", label, "| exc=", res["exc"], "n=", res["n"], "| payload-reaches-act:", any(pay in x for x in res["prompts"]), flush=True)
    # store=None
    store, spec = p.build(R(), p.place("value", p.D))
    spy = p.Spy()
    try:
        p.expand(spec, spy, store=None)
    except Exception as e:
        print("expand(store=None) ->", type(e).__name__, e, "n=", len(spy.prompts))
elif mode == "cannotmask":
    import logging
    class H(logging.Handler):
        def __init__(s): super().__init__(); s.recs = []
        def emit(s, r): s.recs.append(r.getMessage())
    h = H(); logging.getLogger().addHandler(h); logging.getLogger().setLevel(logging.DEBUG)
    for entry in ("expand", "expand_flow", "compile_evals"):
        for vname in ("b64", "urlenc", "upper", "hex", "reversed", "spaced"):
            payload = p.enc_variants(p.D)[vname]
            h.recs.clear()
            res = p.run(entry, p.place("value", payload), R())
            exc = res["exc"] or ""
            echoed = any(v in exc for v in p.enc_variants(p.D).values()) or p.D in exc or payload in exc
            logleak = any(payload in m or p.D in m for m in h.recs)
            print(f"{entry} | {vname} | {exc[:110]!r} | act_calls={res['n']} | secret_in_exc_text={echoed} | secret_in_logs={logleak} (log recs={len(h.recs)})", flush=True)
    # multi-flow: clean flow A then tainted flow B -> partial spend?
    root = R()
    a = p.mkflow(name="A clean"); a = a.model_copy(update={"id": "flow_a"})
    b = p.mkflow(value=p.enc_variants(p.D)["b64"]).model_copy(update={"id": "flow_b", "name": "B tainted"})
    root.mkdir(parents=True); (root / ".env").write_text(f"PROBE_PW={p.D}\n", encoding="utf-8")
    st = p.ProjectStore(p.SLUG, root)
    st.save_project(p.Project(slug=p.SLUG, name="D", base_url="https://app.test", allowed_domains=["app.test"], secrets=[p.SecretRef(key="PROBE_PW", domains=["app.test"])]))
    spec = p.approve(p.FlowSpec(project=p.SLUG, screens=[p.Screen(id="scr_signin", name="s"), p.Screen(id="scr_home", name="h")], flows=[a, b]), by="umesh")
    st.save_flowspec(spec); rows = p.propose_cases(spec); st.stage_case_proposals(rows)
    for r in rows: st.review_case_proposal(r.id, "umesh", approved=True)
    spy = p.Spy()
    try: p.expand(spec, spy, store=st)
    except Exception as e: print("MULTI-FLOW expand: exc", type(e).__name__, "| act calls before refusal:", len(spy.prompts))
elif mode == "happy":
    secret_email = "alice.smith@example.com"
    fl = p.mkflow(name=f"Login {secret_email}", value=secret_email, target=f"field 9876543210", url=f"https://app.test/cb?u={p.D}")
    for entry in ("expand", "expand_flow", "compile_evals"):
        root = R(); store, spec = p.build(root, fl)
        def snap():
            return {str(f.relative_to(root)): hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(root.rglob("*")) if f.is_file()}
        before = snap(); spy = p.Spy()
        if entry == "expand": cases = p.expand(spec, spy, store=store)
        elif entry == "expand_flow": cases = p.expand_flow(fl, p.SLUG, spy, store=store)
        else: cases = p.compile_evals(spec, p.fx.persona(fl), [], spy, store=store).cases
        after = snap()
        happy = [c for c in cases if c.case_class.value == "happy"]
        raw_in_prompt = any(x in pr for pr in spy.prompts for x in (secret_email, "9876543210", p.D))
        print(entry, "happy_cases=", len(happy), "steps_verbatim=", [s.model_dump() for s in happy[0].steps] == [s.model_dump() for s in fl.steps],
              "title=", happy[0].title, "| disk_unchanged=", before == after, "| raw_in_prompt=", raw_in_prompt,
              "| flowspec_on_disk_still_raw=", secret_email in (root / "projects" / p.SLUG / "flowspec.json").read_text(encoding="utf-8"), flush=True)
        if entry == "expand": print("   rendered:", [l for l in spy.prompts[0].splitlines() if "navigate" in l or "fill" in l or "Login" in l])
