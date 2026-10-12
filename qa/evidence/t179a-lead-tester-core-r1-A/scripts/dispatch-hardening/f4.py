"""F4: call gate scans real strings; caps at the boundary; legit maximal calls still work."""
from __future__ import annotations
import csv, sys, tempfile, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import *  # noqa
from seps import SEPS
from common import _grant, _nav, _case, _project
from autotester.core.redact import assert_no_raw_secrets
from autotester.schema.case import Case

OUT = ROOT / "evidence" / "dispatch-hardening"
tmp = Path(tempfile.mkdtemp(prefix="dh-f4-"))
spy = Spy()
ctx = make_ctx(tmp / "data", spy)
case = add_case(ctx, rubric=True, result=True)
restore = patch_stages(spy)

handler_calls = {"n": 0}
for nm, h in list(tools._HANDLERS.items()):
    def wrap(c, a, h=h):
        handler_calls["n"] += 1
        return h(c, a)
    tools._HANDLERS[nm] = wrap

scans: list[int] = []
_real_guard = tools.guards.guard_model_bound
def counting_guard(secrets, text):
    scans.append(len(text))
    return _real_guard(secrets, text)
tools.guards.guard_model_bound = counting_guard


def reset():
    handler_calls["n"] = 0
    spy.calls.clear()
    spy.sessions = 0
    scans.clear()


def refuses(text):
    try:
        assert_no_raw_secrets(text, [CANARY])
        return False
    except ValueError:
        return True


def nest_list(leaf, depth):  # value that puts `leaf` at the given nesting
    node = leaf
    for _ in range(depth):
        node = [node]
    return node


def nest_dict(leaf, depth):
    node = leaf
    for _ in range(depth):
        node = {"a": node}
    return node


rows = []


def run(position, sepname, shape, text, name, args, check_text=None):
    reset()
    out = tools.dispatch(ctx, name, args)
    ran = handler_calls["n"] + spy.total()
    ct = check_text if check_text is not None else text
    ref_before = out.refusal in (RefusalClass.SECRET, RefusalClass.BAD_ARGUMENTS, RefusalClass.UNKNOWN_TOOL)
    rows.append(dict(position=position, sep=sepname, shape=shape, assert_no_raw_secrets_refuses=refuses(ct),
                     dispatch_refusal=getattr(out.refusal, "value", out.refusal) or "", dispatch_ok=out.ok,
                     handler_or_stage_calls=ran, refused_before_handler=ref_before and ran == 0,
                     summary=out.summary[:60]))


for sname, sep in SEPS.items():
    for shape in ("mid", "every", "rev_every"):
        if shape == "mid":
            text = CANARY[:8] + sep + CANARY[8:]
        elif shape == "every":
            text = sep.join(CANARY)
        else:
            text = sep.join(CANARY[::-1])
        run("run_case.case_id", sname, shape, text, "run_case", {"case_id": text})
        run("grade_case.case_id", sname, shape, text, "grade_case", {"case_id": text})
        run("crawl.extra_value", sname, shape, text, "crawl", {"max_actions": 40, "note": text})
        run("get_catalog.extra_value", sname, shape, text, "get_catalog", {"note": text})
        run("run_case.extra_key", sname, shape, text, "run_case", {"case_id": case.id, text: 1})
        run("get_catalog.extra_key", sname, shape, text, "get_catalog", {text: 1})
        run("tool_name_suffix", sname, shape, text, "run_case" + text, {"case_id": case.id})
        run("tool_name_only", sname, shape, text, text, {})
        run("nested_list_d5", sname, shape, text, "get_catalog", {"note": nest_list(text, 4)})
        run("nested_dict_d5", sname, shape, text, "get_catalog", {"note": nest_dict(text, 4)})
        run("nested_key_d5", sname, shape, text, "get_catalog", {"a": {"b": {"c": {"d": {text: 1}}}}})
        run("list_value_two_pieces", sname, shape, text, "get_catalog", {"note": [text[:len(text) // 2], text[len(text) // 2:]]})

# two pieces in different leaves: not joinable by any gate that scans leaves independently
half = len(CANARY) // 2
run("two_leaves_split", "-", "halves", CANARY, "get_catalog", {"a": CANARY[:half], "b": CANARY[half:]},
    check_text=CANARY[:half] + CANARY[half:])

with open(OUT / "f4_rows.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
n = len(rows)
gap = [r for r in rows if r["assert_no_raw_secrets_refuses"] and not r["refused_before_handler"]]
over = [r for r in rows if (not r["assert_no_raw_secrets_refuses"]) and r["dispatch_refusal"] == "secret"]
ran = [r for r in rows if r["handler_or_stage_calls"]]
print("rows", n, "assert_no_raw_secrets-refuses-but-dispatch-lets-through", len(gap), "handler ran in", len(ran))
for r in gap:
    print("GAP", r["position"], r["sep"], r["shape"], r["dispatch_refusal"], r["dispatch_ok"], r["handler_or_stage_calls"], r["summary"])
print("dispatch refuses SECRET though assert_no_raw_secrets(text) does not:", len(over))
for r in over[:20]:
    print("OVER", r["position"], r["sep"], r["shape"])
from collections import Counter
print(Counter(r["position"] for r in gap))

# ------------------------- boundaries -------------------------------------------------------
brows = []


def brow(label, name, args, expect):
    reset()
    t0 = time.perf_counter()
    out = tools.dispatch(ctx, name, args)
    dt = time.perf_counter() - t0
    brows.append(dict(row=label, refusal=getattr(out.refusal, "value", out.refusal) or "", summary=out.summary[:70],
                      scans=len(scans), scanned_chars=sum(scans), handler_ran=handler_calls["n"], secs=round(dt, 4),
                      expect=expect))


NAME = "get_catalog"  # 11 chars
for total in (16383, 16384, 16385, 16386):
    brow(f"chars_total_{total}", NAME, {"k": "a" * (total - len(NAME) - 1)}, "<=16384 reaches validation; >16384 too big")
# keys counted too
for total in (16384, 16385):
    brow(f"chars_total_{total}_inkey", NAME, {"a" * (total - len(NAME) - 1): 1}, "same, key variant")
for total in (16384, 16385):
    brow(f"chars_total_{total}_split_many_leaves", NAME,
         {"a": ["b" * 1000] * 16 + ["c" * (total - len(NAME) - 1 - 16000)]}, "same, many leaves")
for n_ in range(120, 136):
    brow(f"flat_dict_keys_{n_}", NAME, {f"k{i}": 1 for i in range(n_)}, "node cap")
for n_ in range(248, 260):
    brow(f"list_items_{n_}", NAME, {"a": [0] * n_}, "node cap")
for d in range(3, 10):
    brow(f"depth_leaf_at_{d}", NAME, {"a": nest_list("x", d - 1)}, "leaf depth cap 6")
for d in range(3, 10):
    brow(f"depth_dict_leaf_at_{d}", NAME, {"a": nest_dict("x", d - 1)}, "leaf depth cap 6 (dict)")
brow("empty_nested_containers_deep7", NAME, {"a": [[[[[[[]]]]]]]}, "empty list at depth 7")
brow("empty_nested_containers_deep6", NAME, {"a": [[[[[[]]]]]]}, "empty list at depth 6")
t0 = time.perf_counter()
brow("string_2MB_value", "run_case", {"case_id": "a" * 2_000_000}, "refused, not scanned")
brow("string_2MB_key", "run_case", {"a" * 2_000_000: 1}, "refused, not scanned")
brow("string_2MB_name", "a" * 2_000_000, {}, "refused, not scanned")
brow("string_100k_value", "run_case", {"case_id": "a" * 100_000}, "refused")
brow("string_2MB_with_canary_at_end", "run_case", {"case_id": "a" * 2_000_000 + CANARY}, "refused too big (canary never looked at)")
brow("list_of_2000_strings_of_1000", NAME, {"a": ["b" * 1000] * 2000}, "refused")
# timing of the scan itself on max-size text (16 KB) for reference
brow("scan_time_at_cap_16384", NAME, {"k": "a" * (16384 - 12)}, "scan cost reference")

with open(OUT / "f4_boundaries.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(brows[0]))
    w.writeheader()
    w.writerows(brows)
for b in brows:
    print(b)

# ------------------------- legitimate maximal calls ----------------------------------------
restore()
tools.guards.guard_model_bound = _real_guard
tmp2 = Path(tempfile.mkdtemp(prefix="dh-f4b-"))
spy2 = Spy()
ctx2 = make_ctx(tmp2 / "data", spy2)
restore2 = patch_stages(spy2)
legit = []
long_id = "c" * 200
hindi_id = "क" * 200
from autotester.store.project_store import ProjectStore  # noqa
for cid in (long_id, hindi_id):
    c = _case([_nav()], rubric=True)
    try:
        c = c.model_copy(update={"id": cid})
        ctx2.store.add_case(c)
        ctx2.store.save_rubric(Rubric(id="r1", case_id=cid, criteria=[Criterion(id="c1", text="t")]))
        ctx2.store.save_result("run-1", RawResult(case_id=cid, outcome=Outcome.COMPLETED))
    except Exception as e:  # noqa
        print("could not store 200-char case:", type(e).__name__, str(e)[:100])
    for tool in ("run_case", "grade_case"):
        out = tools.dispatch(ctx2, tool, {"case_id": cid})
        legit.append((tool, f"{len(cid)}-char case_id", out.ok, getattr(out.refusal, "value", None), out.summary[:60]))
# crawl with all fields set, huge-but-valid numbers
_grant(ctx2.store, ApprovalKind.CRAWL, actions=10 ** 9)
for args in ({"max_actions": 40, "wall_clock_s": 600.0, "incremental": True},
             {"max_actions": 2 ** 200, "wall_clock_s": 1e300, "incremental": True},
             {"max_actions": 10 ** 9, "wall_clock_s": 31_536_000.5, "incremental": False}):
    out = tools.dispatch(ctx2, "crawl", args)
    legit.append(("crawl", str(args)[:60], out.ok, getattr(out.refusal, "value", None), out.summary[:70]))
legit.append(("get_persona", "{}", *(lambda o: (o.ok, getattr(o.refusal, "value", None), o.summary[:50]))(tools.dispatch(ctx2, "get_persona", {}))))
legit.append(("get_catalog", "{}", *(lambda o: (o.ok, getattr(o.refusal, "value", None), o.summary[:50]))(tools.dispatch(ctx2, "get_catalog", {}))))
for l in legit:
    print("LEGIT", l)
restore2()
with open(OUT / "f4_legit.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["tool", "args", "ok", "refusal", "summary"])
    w.writerows(legit)
