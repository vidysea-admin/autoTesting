"""F2: every raising path returns a typed, scrubbed refusal; BaseException propagates."""
from __future__ import annotations
import asyncio, base64, csv, sys, tempfile, time
from decimal import Decimal
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import *  # noqa
from common import REAL_GRADE

OUT = ROOT / "evidence" / "dispatch-hardening"
rows = []


def longest_partial(text: str, minlen: int = 6):
    best = (0, "")
    for name, v in variants().items():
        if name in ("spaced", "zw_split", "dash_split", "lower", "upper"):
            continue
        for L in range(len(v), max(minlen - 1, best[0]), -1):
            if any(v[i:i + L] in text for i in range(0, len(v) - L + 1)):
                best = (L, name)
                break
    return best


def new(real_grade=False, judge=None):
    tmp = Path(tempfile.mkdtemp(prefix="dh-f2-"))
    spy = Spy()
    ctx = make_ctx(tmp / "data", spy, judge=judge)
    case = add_case(ctx, rubric=True, result=True)
    restore = patch_stages(spy)
    if real_grade:
        tools.grade.grade = REAL_GRADE
    return ctx, spy, case, restore


def judge_out(out, marker=None):
    problems = []
    if not isinstance(out, ToolOutcome):
        return ["not a ToolOutcome"], ""
    js = out.model_dump_json()
    if out.refusal is None or out.ok:
        problems.append("no typed refusal / ok=True")
    if out.tool not in KNOWN:
        problems.append(f"tool label not known: {out.tool[:40]!r}")
    h = hits_in_text(js)
    if h:
        problems.append(f"canary variants in outcome: {h}")
    if marker and marker in js:
        problems.append("caller marker echoed")
    return problems, js


def record(group, row, fn, marker=None):
    t0 = time.perf_counter()
    try:
        out = fn()
        raised = ""
    except BaseException as e:  # noqa
        out, raised = None, f"{type(e).__name__}"
    dt = time.perf_counter() - t0
    if out is not None:
        problems, js = judge_out(out, marker)
        pl, pn = longest_partial(js)
        rows.append(dict(group=group, row=row, returned=type(out).__name__, ok=out.ok,
                         refusal=getattr(out.refusal, "value", out.refusal), tool=out.tool[:30],
                         problems="; ".join(problems) or "-", partial_len=pl, partial_form=pn,
                         summary=out.summary[:120].replace("\n", " "), secs=round(dt, 3)))
    else:
        rows.append(dict(group=group, row=row, returned="RAISED " + raised, ok="", refusal="", tool="",
                         problems="dispatch raised " + raised, partial_len=0, partial_form="",
                         summary="", secs=round(dt, 3)))


def msg_forms():
    c = CANARY
    half = len(c) // 2
    v = variants()
    f = {"raw": f"boom {c}", "reversed": f"boom {c[::-1]}", "b64": f"boom {v['b64_std_off0']}",
         "hex": f"boom {v['hex_lower']}", "pct": f"boom {v['pct_all']}", "spaced": f"boom {v['spaced']}",
         "zw": f"boom {v['zw_split']}", "split2": f"boom {c[:half]} ... {c[half:]}",
         "only_first_half": f"boom {c[:half]}"}
    for form in ("raw", "reversed", "b64_std_off0", "hex_lower"):
        val = v[form] if form != "raw" else c
        for cut in (3, 6, 8, 10):
            pad = 300 - len("RuntimeError: ") - cut
            f[f"pad_cut{cut}_{form}"] = "x" * pad + val
    return f


class BadStr(Exception):
    def __str__(self):
        raise RuntimeError(f"str failed {CANARY}")


def _raise(exc):
    raise exc()


class Sources:
    @staticmethod
    def run_case(exc):
        ctx, spy, case, restore = new()
        tools.execute.run_case = lambda c, s: _raise(exc)
        try:
            return tools.dispatch(ctx, "run_case", {"case_id": case.id})
        finally:
            restore()

    @staticmethod
    def open_session(exc):
        ctx, spy, case, restore = new()
        ctx.open_session = lambda observer: _raise(exc)
        try:
            return tools.dispatch(ctx, "run_case", {"case_id": case.id})
        finally:
            restore()

    @staticmethod
    def judge(exc):
        class J(MockProvider):
            def judge(self, *a, **k):
                raise exc()
        ctx, spy, case, restore = new(real_grade=True, judge=J())
        try:
            return tools.dispatch(ctx, "grade_case", {"case_id": case.id})
        finally:
            restore()

    @staticmethod
    def get_case(exc):
        ctx, spy, case, restore = new()
        ctx.store.get_case = lambda cid: _raise(exc)
        try:
            return tools.dispatch(ctx, "run_case", {"case_id": case.id})
        finally:
            restore()

    @staticmethod
    def catalog(exc):
        ctx, spy, case, restore = new()
        tools.catalog.catalog = lambda *a, **k: _raise(exc)
        try:
            return tools.dispatch(ctx, "get_catalog", {})
        finally:
            restore()

    @staticmethod
    def crawl(exc):
        ctx, spy, case, restore = new()
        tools.explore.run_crawl = lambda *a, **k: _raise(exc)
        try:
            return tools.dispatch(ctx, "crawl", {"max_actions": 40, "wall_clock_s": 600})
        finally:
            restore()

    @staticmethod
    def persona(exc):
        ctx, spy, case, restore = new()
        ctx.store.load_portal_persona = lambda: _raise(exc)
        try:
            return tools.dispatch(ctx, "get_persona", {})
        finally:
            restore()

    @staticmethod
    def save_result(exc):
        ctx, spy, case, restore = new()
        ctx.store.save_result = lambda *a, **k: _raise(exc)
        try:
            return tools.dispatch(ctx, "run_case", {"case_id": case.id})
        finally:
            restore()

    @staticmethod
    def save_verdict(exc):
        ctx, spy, case, restore = new()
        ctx.store.save_verdict = lambda *a, **k: _raise(exc)
        try:
            return tools.dispatch(ctx, "grade_case", {"case_id": case.id})
        finally:
            restore()

    @staticmethod
    def load_results(exc):
        ctx, spy, case, restore = new()
        ctx.store.load_results = lambda *a, **k: _raise(exc)
        try:
            return tools.dispatch(ctx, "grade_case", {"case_id": case.id})
        finally:
            restore()

    @staticmethod
    def load_rubric(exc):
        ctx, spy, case, restore = new()
        ctx.store.load_rubric = lambda *a, **k: _raise(exc)
        try:
            return tools.dispatch(ctx, "grade_case", {"case_id": case.id})
        finally:
            restore()


SOURCES = ["run_case", "open_session", "judge", "get_case", "catalog", "crawl", "persona",
           "save_result", "save_verdict", "load_results", "load_rubric"]

for src in SOURCES:
    fn = getattr(Sources, src)
    for form, msg in msg_forms().items():
        record("handler-msg", f"{src}/{form}", lambda fn=fn, msg=msg: fn(lambda: RuntimeError(msg)))
    record("handler-exc", f"{src}/__str__raises", lambda fn=fn: fn(lambda: BadStr()))
    record("handler-exc", f"{src}/canary_in_typename",
           lambda fn=fn: fn(lambda: type(f"X{CANARY}", (Exception,), {})("m")))
    record("handler-exc", f"{src}/canary_in_args_tuple",
           lambda fn=fn: fn(lambda: Exception(CANARY, CANARY[::-1])))
    record("handler-exc", f"{src}/ValueError_canary",
           lambda fn=fn: fn(lambda: ValueError(f"refusing {CANARY}")))
    record("handler-exc", f"{src}/MemoryError",
           lambda fn=fn: fn(lambda: MemoryError(f"oom {CANARY}")))
    record("handler-exc", f"{src}/RecursionError",
           lambda fn=fn: fn(lambda: RecursionError(f"rec {CANARY}")))
    record("handler-exc", f"{src}/UnicodeError",
           lambda fn=fn: fn(lambda: UnicodeDecodeError("utf-8", CANARY.encode(), 0, 3, "bad")))
    record("handler-exc", f"{src}/KeyError_canary", lambda fn=fn: fn(lambda: KeyError(CANARY)))
    record("handler-exc", f"{src}/OSError_path",
           lambda fn=fn: fn(lambda: FileNotFoundError(2, "No such file", f"C:/x/{CANARY}.json")))
    record("handler-exc", f"{src}/huge_msg_10MB",
           lambda fn=fn: fn(lambda: RuntimeError("y" * 10_000_000 + CANARY)))


class Hostile:
    def __str__(self): raise RuntimeError(CANARY)
    __repr__ = __str__
    def __eq__(self, o): raise RuntimeError(CANARY)
    def __hash__(self): raise RuntimeError(CANARY)
    def __len__(self): raise RuntimeError(CANARY)
    def __iter__(self): raise RuntimeError(CANARY)


class HostileStr(str):
    def __eq__(self, o): raise RuntimeError(CANARY)
    def __hash__(self): raise RuntimeError(CANARY)
    def __len__(self): raise RuntimeError(CANARY)


class LyingStr(str):
    def __hash__(self): return hash("run_case")
    def __eq__(self, o): return True


name_cases = {
    "None": None, "int5": 5, "list": ["run_case"], "bytes": b"run_case", "dict": {"a": 1},
    "tuple": ("run_case",), "Hostile": Hostile(), "HostileStr": HostileStr("ZQMARK-x"),
    "LyingStr": LyingStr("ZQMARK-lying-content"),
    "canary_plain": CANARY, "known_prefix_canary": "run_case" + CANARY, "known_space_canary": "run_case " + CANARY,
    "canary_x10_160": CANARY * 10, "known_prefix_long": "run_case" + "ZQMARK" * 30,
    "long_101": "ZQMARK" + "x" * 95, "exact_100_unknown": "ZQMARK" + "x" * 94, "empty": "", "known_upper": "RUN_CASE",
    "known_trailing_space": "run_case ", "known_nul": "run_case\x00", "unicode_homoglyph": "run_c\u0430se",
    "canary_reversed_name": CANARY[::-1], "canary_b64_name": base64.b64encode(CANARY.encode()).decode(),
}
for k, nm in name_cases.items():
    def go(nm=nm):
        ctx, spy, case, restore = new()
        try:
            return tools.dispatch(ctx, nm, {})
        finally:
            restore()
    record("name", k, go, marker="ZQMARK")


def cyc_dict():
    d = {}
    d["case_id"] = d
    return d


def cyc_list():
    l = []
    l.append(l)
    return {"case_id": l}


def deep(n, wrap="list"):
    node = "x"
    for _ in range(n):
        node = [node] if wrap == "list" else {"a": node}
    return node


class DictIterRaises(dict):
    def __iter__(self): raise ValueError("iter " + CANARY)


class ListIterRaises(list):
    def __iter__(self): raise OSError("iter " + CANARY)


class IntBadRepr(int):
    def __repr__(self): raise RuntimeError("repr " + CANARY)


class IntCanaryRepr(int):
    def __repr__(self): return CANARY


class FloatBigRepr(float):
    def __repr__(self): return "9" * 20000


class StrSubLen(str):
    def __len__(self): raise RuntimeError(CANARY)


args_cases = {
    "None": None, "list_empty": [], "str": "str", "int5": 5, "list_of_pairs": [("case_id", "a")],
    "tuple": (), "bytes": b"{}", "set": {1},
    "key_int": {1: "x"}, "key_None": {None: "x"}, "key_tuple": {(1, 2): "x"}, "key_bytes": {b"k": "x"},
    "key_canary": {CANARY: "x"}, "key_x_canary": {"x" + CANARY: 1}, "key_canary_reversed": {CANARY[::-1]: 1},
    "key_mixed": {"a": 1, 2: 3},
    "val_canary": {"case_id": CANARY}, "val_canary_b64": {"case_id": base64.b64encode(CANARY.encode()).decode()},
    "cycle_dict": cyc_dict(), "cycle_list": cyc_list(),
    "depth5": {"case_id": deep(4)}, "depth6": {"case_id": deep(5)}, "depth7": {"case_id": deep(6)},
    "depth50": {"case_id": deep(50)}, "depth5000": {"case_id": deep(5000)}, "depth100000": {"case_id": deep(100000)},
    "depth_dict_5000": {"case_id": deep(5000, "dict")},
    "int_2e256": {"case_id": 2 ** 256}, "int_2e257": {"case_id": 2 ** 257}, "int_2e300": {"case_id": 2 ** 300},
    "int_neg_big": {"case_id": -(2 ** 300)}, "int_digits_limit": {"case_id": 10 ** 4300},
    "nan": {"case_id": float("nan")}, "inf": {"case_id": float("inf")}, "ninf": {"case_id": float("-inf")},
    "bytes_val": {"case_id": b"bytes"}, "bytearray": {"case_id": bytearray(b"x")}, "set_val": {"case_id": {1, 2}},
    "frozenset": {"case_id": frozenset({1})}, "object_val": {"case_id": object()}, "complex": {"case_id": 1j},
    "Decimal": {"case_id": Decimal("1.5")}, "Hostile_val": {"case_id": Hostile()},
    "HostileStr_val": {"case_id": HostileStr("a")}, "StrSubLen_val": {"case_id": StrSubLen("a")},
    "dict_subclass_iter_raises": DictIterRaises(case_id="a"),
    "list_subclass_iter_raises": {"case_id": ListIterRaises(["a"])},
    "int_bad_repr": {"case_id": IntBadRepr(5)}, "int_canary_repr": {"case_id": IntCanaryRepr(5)},
    "float_big_repr": {"case_id": FloatBigRepr(1.0)},
    "bool_val": {"case_id": True}, "None_val": {"case_id": None}, "float_val": {"case_id": 1.5},
    "list_5M_ints": {"case_id": list(range(5_000_000))}, "dict_300_keys": {str(i): 1 for i in range(300)},
    "tuple_val": {"case_id": ("a", "b")},
}
for k, a in args_cases.items():
    for tool in ("run_case", "get_catalog"):
        def go(a=a, tool=tool):
            ctx, spy, case, restore = new()
            try:
                return tools.dispatch(ctx, tool, a)
            finally:
                restore()
        record("args", f"{tool}/{k}", go)

BASES = {"KeyboardInterrupt": KeyboardInterrupt, "SystemExit": SystemExit, "GeneratorExit": GeneratorExit,
         "CancelledError": asyncio.CancelledError, "MemoryError": MemoryError, "BaseException": BaseException}
base_rows = []
for src in SOURCES:
    fn = getattr(Sources, src)
    for bn, bc in BASES.items():
        try:
            out = fn(lambda bc=bc: bc(f"x {CANARY}"))
            res = f"RETURNED {type(out).__name__} refusal={getattr(out.refusal, 'value', None)} tool={out.tool}"
        except BaseException as e:  # noqa
            res = f"PROPAGATED {type(e).__name__}"
        base_rows.append(dict(source=src, exc=bn, result=res))


class KIStr(Exception):
    def __str__(self): raise KeyboardInterrupt()


try:
    out = Sources.run_case(lambda: KIStr())
    res = f"RETURNED {out.refusal} {out.summary[:60]}"
except BaseException as e:  # noqa
    res = f"PROPAGATED {type(e).__name__}"
base_rows.append(dict(source="run_case", exc="Exception whose __str__ raises KeyboardInterrupt", result=res))

with open(OUT / "f2_rows.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
with open(OUT / "f2_baseexc.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=["source", "exc", "result"])
    w.writeheader()
    w.writerows(base_rows)

bad = [r for r in rows if r["problems"] != "-"]
part = [r for r in rows if r["partial_len"] >= 6]
print("rows", len(rows), "problems", len(bad), "partials>=6", len(part))
for r in bad[:80]:
    print("PROBLEM", r["group"], r["row"], r["problems"], r["summary"][:80])
for r in part[:60]:
    print("PARTIAL", r["row"], r["partial_len"], r["partial_form"], "|", r["summary"][:100])
from collections import Counter
print(Counter(b["result"].split(" refusal")[0] for b in base_rows))
for b in base_rows:
    if not b["result"].startswith("PROPAGATED"):
        print("BASE", b)
