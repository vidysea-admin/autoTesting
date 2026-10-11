"""F3: a secret in a stage result (RawResult / Verdict) must leave nothing under the data root."""
from __future__ import annotations
import base64, codecs, csv, hashlib, html, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import *  # noqa
from autotester.schema.run import Evidence
from autotester.schema.enums import EvidenceKind
from autotester.schema.verdict import Verdict

OUT = ROOT / "evidence" / "dispatch-hardening"

V = variants()
b64 = base64.b64encode(CANARY.encode()).decode()
EXTRA = {
    "double_b64": base64.b64encode(b64.encode()).decode().rstrip("="),
    "html_entity": "".join(f"&#{ord(c)};" for c in CANARY),
    "u_escape": "".join(f"\\u{ord(c):04x}" for c in CANARY),
    "swapcase": CANARY.swapcase(),
    "rot13": codecs.encode(CANARY, "rot13"),
    "tab_split": "\t".join(CANARY), "nl_split": "\n".join(CANARY), "nbsp_split": "\xa0".join(CANARY),
    "split_at_hyphens": " ".join(CANARY.split("-")),
    "reversed_spaced": " ".join(CANARY[::-1]),
    "crlf_mid": CANARY[:8] + "\r\n" + CANARY[8:],
    "softhyphen_mid": CANARY[:8] + "­" + CANARY[8:],
    "zwj_mid": CANARY[:8] + "‍" + CANARY[8:],
    "bom_mid": CANARY[:8] + "﻿" + CANARY[8:],
    "fullwidth": CANARY.translate({ord(c): ord(c) + 0xFEE0 for c in "CANRYpwfac" if True}) if False else "".join(
        chr(ord(c) + 0xFEE0) if "!" <= c <= "~" else c for c in CANARY),
}
ALL = {**V, **EXTRA}
NEEDLES = {k: v for k, v in ALL.items()}


def tree_hits(root: Path):
    out = []
    for p in root.rglob("*"):
        if p.is_file():
            text = p.read_bytes().decode("utf-8", "ignore")
            h = hits_in_text(text, NEEDLES)
            # utf-16 / raw-byte forms
            raw = p.read_bytes()
            for enc in ("utf-16-le", "utf-16-be"):
                if CANARY.encode(enc) in raw:
                    h.append("utf16:" + enc)
            if h:
                out.append((str(p.relative_to(root)), h))
    return out


def snap(root: Path):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob("*") if p.is_file()}


def fresh(result_factory=None, verdict_factory=None):
    tmp = Path(tempfile.mkdtemp(prefix="dh-f3-"))
    spy = Spy()
    root = tmp / "data"
    ctx = make_ctx(root, spy)
    case = add_case(ctx, rubric=True, result=True)
    restore = patch_stages(spy, result_factory)
    if verdict_factory:
        from autotester.schema.verdict import Verdict as V_
        tools.grade.grade = lambda rub, res, run_id, *a, **k: (spy.hit("grade"), verdict_factory(run_id, res.case_id))[1]
    return ctx, spy, case, root, restore


rows = []


def rec(kind, variant, carrier, fn):
    ctx, spy, case, root, restore = fn[0]()
    before = snap(root)
    try:
        out = fn[1](ctx, case)
    finally:
        restore()
    after = snap(root)
    added = sorted(set(after) - set(before))
    changed = sorted(k for k in before if k in after and before[k] != after[k])
    th = tree_hits(root)
    oh = hits_in_text(out.model_dump_json(), NEEDLES)
    rows.append(dict(kind=kind, variant=variant, carrier=carrier, ok=out.ok,
                     refusal=getattr(out.refusal, "value", out.refusal) or "", tool=out.tool,
                     files_added=len(added), files_changed=len(changed),
                     added="|".join(a.replace("\\", "/").split("/")[-1] for a in added)[:80],
                     tree_leak="|".join(f"{f}:{','.join(h)}" for f, h in th)[:200] or "-",
                     outcome_leak=",".join(oh) or "-"))


def result_for(variant_text, carrier):
    def factory(case):
        kw = dict(case_id=case.id, outcome=Outcome.ERRORED)
        if carrier == "error":
            kw["error"] = f"failure: {variant_text} end"
        elif carrier == "hitl_prompt":
            kw["outcome"] = Outcome.BLOCKED_HITL
            kw["hitl_prompt"] = f"supply {variant_text}"
        elif carrier == "not_run_reason":
            kw["outcome"] = Outcome.NOT_RUN
            kw["not_run_reason"] = f"because {variant_text}"
        elif carrier == "evidence_path":
            kw["evidence"] = [Evidence(kind=EvidenceKind.URL, path=f"https://app.test/?q={variant_text}")]
        elif carrier == "evidence_label":
            kw["evidence"] = [Evidence(kind=EvidenceKind.DOM, path="dom", label=variant_text)]
        elif carrier == "log_ref":
            kw["log_ref"] = f"logs/{variant_text}.txt"
        elif carrier == "case_id":
            kw["case_id"] = f"c-{variant_text}".replace("/", "_").replace("\\", "_")
        return RawResult(**kw)
    return factory


CARRIERS_R = ["error", "hitl_prompt", "not_run_reason", "evidence_path", "evidence_label", "log_ref", "case_id"]
for name, text in [("benign", "everything fine")] + list(ALL.items()):
    for carrier in CARRIERS_R:
        rec("result", name, carrier, (
            lambda t=text, c=carrier: fresh(result_factory=result_for(t, c)),
            lambda ctx, case: tools.dispatch(ctx, "run_case", {"case_id": case.id})))

# cross-field split (each field clean alone)
def split_fields(case):
    h = len(CANARY) // 2
    return RawResult(case_id=case.id, outcome=Outcome.ERRORED, error=CANARY[:h], hitl_prompt=CANARY[h:])
rec("result", "split_across_fields", "error|hitl_prompt", (
    lambda: fresh(result_factory=split_fields),
    lambda ctx, case: tools.dispatch(ctx, "run_case", {"case_id": case.id})))


def verdict_for(text, carrier):
    def factory(run_id, case_id):
        kw = dict(run_id=run_id, case_id=case_id, result=Result.FAIL, rubric_hash="h", grader_provider="mock")
        if carrier == "note":
            kw["note"] = f"n {text}"
        elif carrier == "scoreboard":
            kw["scoreboard"] = f"s {text}"
        elif carrier == "grader_provider":
            kw["grader_provider"] = text
        elif carrier == "rubric_hash":
            kw["rubric_hash"] = text
        elif carrier == "failure_reason":
            from autotester.schema.verdict import Failure
            kw["failures"] = [Failure(criterion_id="c1", reason=text, evidence_refs=[text], fix_hint=text)]
        elif carrier == "case_id":
            kw["case_id"] = f"c-{text}".replace("/", "_").replace("\\", "_")
        return Verdict(**kw)
    return factory


CARRIERS_V = ["note", "scoreboard", "grader_provider", "rubric_hash", "failure_reason", "case_id"]
for name, text in [("benign", "all good")] + list(ALL.items()):
    for carrier in CARRIERS_V:
        rec("verdict", name, carrier, (
            lambda t=text, c=carrier: fresh(verdict_factory=verdict_for(t, c)),
            lambda ctx, case: tools.dispatch(ctx, "grade_case", {"case_id": case.id})))

with open(OUT / "f3_rows.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)

n = len(rows)
leaks = [r for r in rows if r["tree_leak"] != "-"]
oleaks = [r for r in rows if r["outcome_leak"] != "-"]
stored = [r for r in rows if r["files_added"] or r["files_changed"]]
refused_wrote = [r for r in rows if (not r["ok"]) and (r["files_added"] or r["files_changed"])]
print("rows", n, "tree-leak rows", len(leaks), "outcome-leak rows", len(oleaks), "rows that wrote files", len(stored),
      "refusal-but-wrote", len(refused_wrote))
for r in leaks:
    print("TREELEAK", r["kind"], r["variant"], r["carrier"], r["ok"], r["refusal"], r["tree_leak"])
for r in oleaks:
    print("OUTLEAK", r["kind"], r["variant"], r["carrier"], r["outcome_leak"])
for r in refused_wrote:
    print("REFUSED-BUT-WROTE", r["kind"], r["variant"], r["carrier"], r["refusal"], r["added"])
for r in rows:
    if r["variant"] in ("benign", "split_across_fields"):
        print("CONTROL", r["kind"], r["variant"], r["carrier"], r["ok"], r["refusal"], r["files_added"], r["added"], r["tree_leak"])
from collections import Counter
print(Counter((r["kind"], r["ok"], r["refusal"]) for r in rows))
