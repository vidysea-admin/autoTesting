"""Section 4: dispatcher robustness through the real dispatch. <python> -I s4_robust.py <copy> <out.json>"""
import contextlib
import io
import logging
import os
import sys
import tempfile
import time
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import probe_lib as L  # noqa: E402

L.confirm_copy(sys.argv[1])
from collections.abc import Mapping  # noqa: E402
from autotester.agents import tools  # noqa: E402
from autotester.schema.enums import Action as A, ApprovalKind, WritePolicy  # noqa: E402

SECRETS = {k: L.spellings(v) for k, v in L.CANARY.items()}
ALL = [(f"{k}:{sp}", s) for k, d in SECRETS.items() for sp, s in d.items()]


def leaks(text: str) -> list[str]:
    return sorted({lab for lab, s in ALL if s and s in text})


class Capture:
    def __enter__(self):
        self.buf = tempfile.TemporaryFile()
        sys.stdout.flush(); sys.stderr.flush()
        self.o1, self.o2 = os.dup(1), os.dup(2)
        os.dup2(self.buf.fileno(), 1); os.dup2(self.buf.fileno(), 2)
        self.log = []
        h = logging.Handler(); h.setLevel(1)
        h.emit = lambda rec: self.log.append(rec.getMessage() + " " + str(rec.exc_info))
        self.h = h
        logging.getLogger().addHandler(h)
        self.old_level = logging.getLogger().level
        logging.getLogger().setLevel(1)
        self.w = warnings.catch_warnings(record=True); self.wl = self.w.__enter__()
        warnings.simplefilter("always")
        return self

    def __exit__(self, *a):
        self.w.__exit__(*a)
        logging.getLogger().removeHandler(self.h); logging.getLogger().setLevel(self.old_level)
        sys.stdout.flush(); sys.stderr.flush()
        os.dup2(self.o1, 1); os.dup2(self.o2, 2); os.close(self.o1); os.close(self.o2)
        self.buf.seek(0)
        self.fd_text = self.buf.read().decode("utf-8", "replace")
        self.buf.close()
        self.warn_text = " ".join(str(w.message) for w in self.wl)
        self.log_text = " ".join(self.log)


def new_env():
    env = L.make_env(WritePolicy.TEST_ACCOUNT, [[L.step(1, A.NAVIGATE, "https://app.test/home")]])
    L.grant(env.ctx.store, ApprovalKind.CRAWL, actions=10**6)
    return env


class Hostile(str):
    def __str__(self):
        raise RuntimeError("hostile __str__ " + L.CANARY["APP_PASS"])

    def __len__(self):
        raise RuntimeError("hostile __len__ " + L.CANARY["APP_PASS"])


class HostileDict(dict):
    def __iter__(self):
        raise RuntimeError("hostile __iter__ " + L.CANARY["APP_PASS"])

    def items(self):
        raise RuntimeError("hostile items " + L.CANARY["APP_PASS"])


class NotDictMapping(Mapping):
    def __getitem__(self, k): raise KeyError(k)
    def __iter__(self): return iter(())
    def __len__(self): return 0


class BadRepr:
    def __repr__(self): raise RuntimeError("bad repr " + L.CANARY["APP_PASS"])


def nested(depth, kind="dict"):
    node = "x"
    for _ in range(depth):
        node = {"a": node} if kind == "dict" else [node]
    return node


def cycle():
    d = {}
    d["a"] = d
    return d


def lcycle():
    lst = []
    lst.append(lst)
    return {"case_id": lst}


class ErrStr(Exception):
    def __str__(self): raise ValueError("str raised " + L.CANARY["APP_PASS"])


class Cn(Exception):
    pass


CANARY_NAME_CLS = type("Err_" + SECRETS["APP_PASS"]["base64"].rstrip("="), (Exception,), {})
CAN = L.CANARY["APP_PASS"]
SP = SECRETS["APP_PASS"]
rows = []


def record(name, args_desc, call, prep=None, tool="run_case"):
    env = new_env()
    if prep:
        prep(env)
    case_id = env.case_ids[0]
    a = call(case_id) if callable(call) else call
    nm = tool
    cap = Capture()
    t0 = time.perf_counter()
    escaped = None
    out = None
    with cap:
        try:
            out = tools.dispatch(env.ctx, nm, a)
        except BaseException as e:  # noqa: BLE001
            escaped = f"{type(e).__name__}"
    dt = time.perf_counter() - t0
    r = {"row": name, "args": args_desc, "seconds": round(dt, 4),
         "stage_calls": {"run_case": len(env.spy.run_case), "crawl": env.spy.crawl, "grade": env.spy.grade,
                         "catalog": env.spy.catalog, "sessions": env.spy.sessions}}
    if escaped:
        r.update(escaped=escaped, typed=False, leaks=[])
    else:
        js = out.model_dump_json()
        r.update(escaped=None, typed=(out.ok is False and out.refusal is not None) or out.ok is True,
                 ok=out.ok, refusal=out.refusal.value if out.refusal else None, tool_label=out.tool,
                 label_ok=out.tool in {n.value for n in tools.Name} or out.tool == "unknown",
                 summary=L.label(out.summary)[:120],
                 leaks=leaks(js) + [f"stdout/err:{x}" for x in leaks(cap.fd_text)]
                 + [f"log:{x}" for x in leaks(cap.log_text)] + [f"warn:{x}" for x in leaks(cap.warn_text)])
    rows.append(r)
    return r


# --- tool-name types
for nm, d in [(None, "None"), (True, "True"), (0, "0"), (1.5, "1.5"), ([], "[]"), ({}, "{}"), (b"run_case", "bytes"),
              (("run_case",), "tuple"), (object(), "object()"), ("", "empty str"), (" run_case", "leading space"),
              ("RUN_CASE", "upper"), ("run_case\x00", "NUL suffix"), ("x" * 101, "101 chars"), ("x" * 100, "100 chars"),
              ("x" * 2_000_000, "2MB name"), ("run_case" + CAN, "name+canary"), (CAN, "canary as name"),
              (type("S", (str,), {})("run_case"), "str subclass run_case"), (Hostile("run_case"), "hostile str subclass name"),
              (float("nan"), "nan"), (frozenset(), "frozenset")]:
    record(f"name:{d}", d, lambda cid: {"case_id": cid}, tool=nm if not isinstance(nm, str) else nm)

# --- args non-mapping / key types
for a, d in [(None, "None"), ([], "list"), ("case", "str"), (5, "int"), (b"x", "bytes"), (NotDictMapping(), "Mapping non-dict"),
             (BadRepr(), "bad repr obj"), (HostileDict({"case_id": "x"}), "hostile dict subclass"), ((), "tuple"),
             ({1: "x"}, "int key"), ({None: "x"}, "None key"), ({(1, 2): "x"}, "tuple key"), ({b"k": "x"}, "bytes key"),
             ({"case_id": Hostile("x")}, "hostile str value"), ({"case_id": BadRepr()}, "bad repr value"),
             ({"case_id": float("nan")}, "nan"), ({"case_id": float("inf")}, "inf"), ({"case_id": 2**256}, "int 2^256 (257 bits)"),
             ({"case_id": 2**255}, "int 2^255 (256 bits)"), ({"case_id": -(2**300)}, "int -2^300"), ({"case_id": object()}, "object value"),
             ({"case_id": {1, 2}}, "set value"), ({"case_id": 1 + 2j}, "complex"), ({CAN: "x"}, "canary as key"), ({"case_id": CAN}, "canary as value"),
             ({"case_id": SP["base64"]}, "canary base64 as value"), ({"case_id": SP["reversed"]}, "canary reversed as value"),
             (cycle(), "self-referential dict"), (lcycle(), "self-referential list")]:
    record(f"args:{d}", d, a)

# --- nesting / size
for depth in (5, 6, 7, 8, 100, 1000, 100_000):
    record(f"nest dict depth {depth}", f"{depth} (dict)", lambda cid, d=depth: nested(d, "dict"))
    record(f"nest list-in-case_id depth {depth}", f"{depth} (list)", lambda cid, d=depth: {"case_id": nested(d, "list")})
record("2MB case_id", "2,000,000 chars", lambda cid: {"case_id": "a" * 2_000_000})
record("2MB key", "2,000,000 char key", lambda cid: {"a" * 2_000_000: 1})
record("2MB split over 100 fields", "100 x 20k", lambda cid: {f"k{i}": "a" * 20_000 for i in range(100)})

# --- caps, found by reading _call_texts: chars<=16384 incl. name; nodes<=256 (root counted); depth<=6
name_len = len("run_case")
for n, lab in ((16384 - name_len - len("case_id") - 1, "n-1"), (16384 - name_len - len("case_id"), "n"), (16384 - name_len - len("case_id") + 1, "n+1")):
    record(f"text cap {lab} (total chars {n + name_len + 7})", lab, lambda cid, n=n: {"case_id": "a" * n})
for k, lab in ((127, "k=127 (255 nodes)"), (128, "k=128 (257 nodes)"), (129, "k=129")):
    record(f"nodes dict {lab}", lab, lambda cid, k=k: {f"k{i}": 0 for i in range(k)})
for n in (252, 253, 254, 255, 256):
    record(f"nodes list in key a: {n} elems", str(n), lambda cid, n=n: {"a": [0] * n})
for d in range(3, 9):
    record(f"depth exact: {d} nested dicts + leaf", str(d), lambda cid, d=d: nested(d, "dict"))
record("list of 257 in case_id", "257", lambda cid: {"case_id": [0] * 257})

# --- exceptions carrying a canary
def raise_in(where, exc):
    return lambda env: env.spy.raise_in.__setitem__(where, exc)


exc_makers = {
    "RuntimeError(canary)": lambda: RuntimeError("boom " + CAN),
    "ValueError(reversed)": lambda: ValueError("boom " + SP["reversed"]),
    "KeyError(canary)": lambda: KeyError(CAN),
    "base64 in message": lambda: OSError("boom " + SP["base64"]),
    "canary split by tab": lambda: RuntimeError("boom " + CAN[:5] + "\t" + CAN[5:]),
    "hostile __str__": lambda: ErrStr(),
    "class name carries base64(canary)": lambda: CANARY_NAME_CLS("x"),
    "cause chain has canary": lambda: _chained(),
    "args tuple has canary": lambda: Cn(CAN, SP["hex"]),
    "300+ chars then canary (cut)": lambda: RuntimeError("z" * 295 + CAN),
    "canary straddles 300 cut": lambda: RuntimeError("z" * (300 - 10) + CAN),
    "canary base64 straddles 300 cut": lambda: RuntimeError("z" * (300 - 10) + SP["base64"]),
}


def _chained():
    try:
        try:
            raise RuntimeError("inner " + CAN)
        except RuntimeError as e:
            raise ValueError("outer") from e
    except ValueError as e2:
        return e2


for en, mk in exc_makers.items():
    record(f"run_case stage raises: {en}", en, lambda cid: {"case_id": cid}, prep=lambda env, mk=mk: env.spy.raise_in.__setitem__("run_case", mk()))
    record(f"crawl stage raises: {en}", en, {}, prep=lambda env, mk=mk: env.spy.raise_in.__setitem__("crawl", mk()), tool="crawl")
    record(f"get_catalog raises: {en}", en, {}, prep=lambda env, mk=mk: env.spy.raise_in.__setitem__("catalog", mk()), tool="get_catalog")


def prep_open_session(mk):
    def p(env):
        def bad(observer):
            raise mk()
        env.ctx.open_session = bad
    return p


def prep_persona(mk):
    def p(env):
        def bad():
            raise mk()
        env.ctx.store.load_portal_persona = bad
    return p


def prep_grade(mk):
    from autotester.schema.verdict import Criterion, Rubric
    from autotester.schema.run import RawResult
    from autotester.schema.enums import Outcome

    def p(env):
        c2 = L.make_case([L.step(1, A.NAVIGATE, "https://app.test/home")], flow="fg")
        c2 = c2.model_copy(update={"rubric_ref": "r1"})
        env.ctx.store.save_rubric(Rubric(id="r1", case_id=c2.id, criteria=[Criterion(id="c1", text="t")]))
        c2 = env.ctx.store.add_case(c2)
        env.ctx.store.save_result("run-1", RawResult(case_id=c2.id, outcome=Outcome.COMPLETED))
        env.case_ids[0] = c2.id
        if mk:
            env.spy.raise_in["grade"] = mk()
    return p


record("grade control (no raise, must reach the judge spy)", "control", lambda cid: {"case_id": cid}, prep=prep_grade(None), tool="grade_case")
for en in ("RuntimeError(canary)", "hostile __str__", "base64 in message", "canary straddles 300 cut"):
    mk = exc_makers[en]
    record(f"open_session raises: {en}", en, lambda cid: {"case_id": cid}, prep=prep_open_session(mk))
    record(f"get_persona reader raises: {en}", en, {}, prep=prep_persona(mk), tool="get_persona")
    record(f"grade/judge raises: {en}", en, lambda cid: {"case_id": cid}, prep=prep_grade(mk), tool="grade_case")

# --- BaseException subclasses (documented: dispatch catches Exception only)
for cls in (KeyboardInterrupt, SystemExit, GeneratorExit):
    record(f"run_case stage raises BaseException {cls.__name__}", cls.__name__, lambda cid: {"case_id": cid},
           prep=lambda env, cls=cls: env.spy.raise_in.__setitem__("run_case", cls("x " + CAN)))

worst = max(rows, key=lambda r: r["seconds"])
bad = [r for r in rows if r.get("escaped") or not r.get("typed") or r.get("leaks") or r.get("label_ok") is False]
L.dump(sys.argv[2], {"rows": rows, "worst": worst, "exceptions": bad})
print("rows", len(rows), "exception rows", len(bad), "worst", worst["row"], worst["seconds"])
for r in bad:
    print("EXC:", r["row"], r.get("escaped"), r.get("leaks"), r.get("refusal"))
print("rows >1s:", [(r["row"], r["seconds"]) for r in rows if r["seconds"] > 1])
