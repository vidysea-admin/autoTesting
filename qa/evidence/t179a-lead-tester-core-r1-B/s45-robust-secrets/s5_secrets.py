"""Section 5: secrets returned by stages through the real dispatch; byte-level grep of the whole data root.
<python> -I s5_secrets.py <copy> <out.json>. Outputs carry LABELS only, never canary values."""
import base64
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import probe_lib as L  # noqa: E402

L.confirm_copy(sys.argv[1])
from autotester.agents import tools  # noqa: E402
from autotester.schema.enums import Action as A, Outcome, Result, WritePolicy  # noqa: E402
from autotester.schema.run import Evidence, RawResult  # noqa: E402
from autotester.schema.enums import EvidenceKind  # noqa: E402
from autotester.schema.verdict import Criterion, Failure, Rubric, Verdict  # noqa: E402


def b64(s: str) -> str:
    return base64.b64encode(s.encode()).decode()


def split_every(s: str, sep: str, n: int = 4) -> str:
    return sep.join(s[i:i + n] for i in range(0, len(s), n))


def variants(secret: str) -> dict[str, str]:
    v = dict(L.spellings(secret))
    v.pop("lower", None) if v["lower"] == v["raw"] else None
    v["tab_split"] = split_every(secret, "\t")
    v["newline_split"] = split_every(secret, "\n")
    v["zero_width_split"] = split_every(secret, "​")
    v["soft_hyphen_split"] = split_every(secret, "­")
    v["nested_b64_of_b64"] = b64(b64(secret))
    v["nested_json_object"] = json.dumps({"password": secret})
    v["nested_b64_of_json"] = b64(json.dumps({"p": secret}))
    v["percent_upper"] = "".join(f"%{b:02X}" for b in secret.encode())
    v["unicode_escape"] = "".join(f"\\u{ord(c):04x}" for c in secret)
    v["html_entity"] = "".join(f"&#{ord(c)};" for c in secret)
    return v


BEYOND = {"percent_upper", "unicode_escape", "html_entity", "nested_b64_of_json"}
V = {k: variants(val) for k, val in L.CANARY.items()}
# scan patterns: each variant literal, json-escaped (ascii and utf-8), case-folded compare
PAT = []
for sk, d in V.items():
    for lab, s in d.items():
        for form, text in (("lit", s), ("json_ascii", json.dumps(s)[1:-1]), ("json_utf8", json.dumps(s, ensure_ascii=False)[1:-1])):
            PAT.append((f"{sk}:{lab}:{form}", text.encode("utf-8"), text.lower().encode("utf-8")))
RAWS = [(f"{k}:raw", v.encode()) for k, v in L.CANARY.items()]


def json_strings(obj, out):
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            out.append(str(k)); json_strings(v, out)
    elif isinstance(obj, list):
        for v in obj:
            json_strings(v, out)


def scan_root(root: Path) -> dict:
    hits, files = set(), []
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root).as_posix()
        names = rel.encode("utf-8")
        for lab, b, lb in PAT:
            if b in names or lb in names.lower():
                hits.add(("filename", lab))
        if not p.is_file():
            continue
        files.append(rel)
        data = p.read_bytes()
        low = data.lower()
        for lab, b, lb in PAT:
            if b in data:
                hits.add((rel.split("/")[-1], lab))
            elif lb in low:
                hits.add((rel.split("/")[-1], lab + ":casefold"))
        if p.suffix in (".json", ".jsonl"):
            strs = []
            try:
                for line in data.decode("utf-8", "replace").splitlines() if p.suffix == ".jsonl" else [data.decode("utf-8", "replace")]:
                    if line.strip():
                        json_strings(json.loads(line), strs)
            except Exception:
                continue
            joined = "\n".join(strs).encode("utf-8")
            lowj = joined.lower()
            for lab, _b, _lb in PAT:
                if lab.endswith(":lit"):
                    text = next(s for k2, d2 in V.items() for l2, s in d2.items() if f"{k2}:{l2}:lit" == lab)
                    if text.encode("utf-8") in joined or text.lower().encode("utf-8") in lowj:
                        hits.add((rel.split("/")[-1] + "(decoded)", lab))
    return {"files": files, "hits": sorted({f"{f}|{l}" for f, l in hits})}


def hit_labels(scan):
    return sorted({h.split("|")[1] for h in scan["hits"]})


def grade_env():
    env = L.make_env(WritePolicy.TEST_ACCOUNT, [[L.step(1, A.NAVIGATE, "https://app.test/home")]])
    c2 = L.make_case([L.step(1, A.NAVIGATE, "https://app.test/home")], flow="fg").model_copy(update={"rubric_ref": "r1"})
    env.ctx.store.save_rubric(Rubric(id="r1", case_id=c2.id, criteria=[Criterion(id="c1", text="t")]))
    c2 = env.ctx.store.add_case(c2)
    env.ctx.store.save_result("run-1", RawResult(case_id=c2.id, outcome=Outcome.COMPLETED))
    env.case_ids[0] = c2.id
    return env


def result_with(field, text):
    def f(case):
        kw = dict(case_id=case.id, outcome=Outcome.ERRORED)
        if field == "error": kw["error"] = text
        elif field == "hitl_prompt": kw["hitl_prompt"] = text
        elif field == "not_run_reason": kw["not_run_reason"] = text
        elif field == "log_ref": kw["log_ref"] = text
        elif field == "evidence.path": kw["evidence"] = [Evidence(kind=EvidenceKind.URL, path=text)]
        elif field == "evidence.label": kw["evidence"] = [Evidence(kind=EvidenceKind.URL, path="u", label=text)]
        elif field == "case_id": kw["case_id"] = text
        return RawResult(**kw)
    return f


def verdict_with(field, text):
    def f(rubric, result, run_id):
        kw = dict(run_id=run_id, case_id=result.case_id, result=Result.FAIL, rubric_hash="h", grader_provider="mock",
                  criteria_total=1, criteria_met=0)
        fail = dict(criterion_id="c1", reason="r")
        if field == "note": kw["note"] = text
        elif field == "scoreboard": kw["scoreboard"] = text
        elif field == "grader_provider": kw["grader_provider"] = text
        elif field == "rubric_hash": kw["rubric_hash"] = text
        elif field == "failure.reason": fail["reason"] = text
        elif field == "failure.fix_hint": fail["fix_hint"] = text
        elif field == "failure.criterion_id": fail["criterion_id"] = text
        elif field == "failure.evidence_ref": fail["evidence_refs"] = [text]
        kw["failures"] = [Failure(**fail)]
        return Verdict(**kw)
    return f


rows = []


def one(section, secret, spelling, field, text, expect_store=False):
    tool = "run_case" if section == "run_case" else "grade_case"
    env = L.make_env(WritePolicy.TEST_ACCOUNT, [[L.step(1, A.NAVIGATE, "https://app.test/home")]]) if section == "run_case" else grade_env()
    if section == "run_case":
        env.spy.result_factory = result_with(field, text)
    else:
        env.spy.verdict_factory = verdict_with(field, text)
    pre = set(scan_root(env.root)["files"])
    err = None
    try:
        out = tools.dispatch(env.ctx, tool, {"case_id": env.case_ids[0]})
    except BaseException as e:  # noqa: BLE001
        out, err = None, type(e).__name__
    scan = scan_root(env.root)
    new_files = sorted(set(scan["files"]) - pre)
    leak = []
    if out is not None:
        js = out.model_dump_json()
        decoded = (out.summary or "") + chr(10) + (out.artifact_ref or "")
        for lab, b, _ in PAT:
            if lab.endswith(":lit") and (b.decode("utf-8") in js or b.decode("utf-8") in decoded):
                leak.append(lab)
    stored_secretish = bool(hit_labels(scan))
    rows.append({"section": section, "secret": secret, "spelling": spelling, "field": field,
                 "beyond_required_list": spelling in BEYOND, "escaped": err,
                 "ok": None if out is None else out.ok, "refusal": None if out is None or out.refusal is None else out.refusal.value,
                 "stored_new_files": [f.split("/")[-1] if "r1b-" not in f else "?" for f in new_files],
                 "disk_hits": hit_labels(scan), "disk_hit_detail": scan["hits"], "tool_output_hits": leak,
                 "summary": L.label(out.summary)[:100] if out is not None else None})
    return rows[-1]


# --- positive control for the grep (would a canary on disk be seen?)
import tempfile, os  # noqa: E402
ctl = Path(tempfile.mkdtemp(prefix="r1b-ctl-", dir=os.environ.get("R1B_TMP")))
(ctl / "a.json").write_text(json.dumps({"x": V["APP_PASS"]["base64"], "y": V["APP_USER"]["tab_split"]}))
(ctl / f"{V['APP_PASS']['hex']}.txt").write_text("f")
(ctl / "decoy.json").write_text(json.dumps({"x": "Cnry-PASS only a prefix", "hex": "ab" * 20}))
c = scan_root(ctl)
control = {"hits": sorted({h.split("|")[0] + "|" + h.split("|")[1].split(":")[1] for h in c["hits"]})}
print("grep control:", control)

# --- run_case: every spelling x both secrets at `error`
for sk in L.CANARY:
    for lab, text in V[sk].items():
        one("run_case", sk, lab, "error", "saw " + text + " end")
# --- other fields: raw, reversed, base64, tab_split for APP_PASS
for field in ("hitl_prompt", "not_run_reason", "log_ref", "evidence.path", "evidence.label", "case_id"):
    for lab in ("raw", "reversed", "base64", "tab_split"):
        one("run_case", "APP_PASS", lab, field, V["APP_PASS"][lab])
# --- grade_case: every spelling x both secrets at `note`
for sk in L.CANARY:
    for lab, text in V[sk].items():
        one("grade_case", sk, lab, "note", "saw " + text + " end")
for field in ("scoreboard", "grader_provider", "rubric_hash", "failure.reason", "failure.fix_hint", "failure.criterion_id", "failure.evidence_ref"):
    for lab in ("raw", "reversed", "base64", "tab_split"):
        one("grade_case", "APP_PASS", lab, field, V["APP_PASS"][lab])
# --- secrets as dict keys: not representable in the typed models (extra=forbid); prove it
dk = {}
for name, cls, kw in (("RawResult", RawResult, dict(case_id="c", outcome=Outcome.ERRORED)),
                      ("Verdict", Verdict, dict(run_id="r", case_id="c", result=Result.PASS))):
    try:
        cls(**kw, **{V["APP_PASS"]["raw"]: 1})
        dk[name] = "ACCEPTED an unknown key"
    except Exception as e:  # noqa: BLE001
        dk[name] = "rejected: " + type(e).__name__
print("dict-key construction:", dk)
# --- decoys: benign text that must be stored (over-blocking count)
DECOYS = ["login failed for the account", "Cnry", "Cnry-PASS", "7Qx41", "zeta-0993", "password reset email sent",
          "user 5581", "fake.test", b64("hello world 12345"), "ab" * 20, "9f8c1d2e-5b7a-4c3d-8e2f-1a0b9c8d7e6f",
          "cnry user", "PASS", "the quick brown fox jumps over the lazy dog", "x" * 200, "Password field is required",
          "error 500 at /api/login", "token expired", "a.b.c.d.e.f.g", "https://app.test/home"]
for t in DECOYS:
    one("run_case", "decoy", "benign", "error", t)
    one("grade_case", "decoy", "benign", "note", t)

# --- direct guard table: the gate the dispatcher applies, on raw text vs on JSON-escaped text
gt = []
genv = L.make_env(WritePolicy.TEST_ACCOUNT, [[L.step(1, A.NAVIGATE, "https://app.test/home")]])
for sk, d in V.items():
    for lab, text in d.items():
        def caught(t):
            try:
                genv.ctx.secrets.guard_prompt(t)
                return False
            except ValueError:
                return True
        as_model = RawResult(case_id="c", outcome=Outcome.ERRORED, error="saw " + text + " end").model_dump_json()
        gt.append({"secret": sk, "spelling": lab, "beyond_required_list": lab in BEYOND,
                   "raw_text_caught": caught("saw " + text + " end"), "model_dump_json_caught": caught(as_model)})
miss_json = [g for g in gt if not g["model_dump_json_caught"]]
print("guard table rows", len(gt), "missed on model_dump_json:", [(g["secret"], g["spelling"], "raw-text-caught" if g["raw_text_caught"] else "raw-text-MISSED") for g in miss_json])

bad_disk = [r for r in rows if r["disk_hits"] or r["tool_output_hits"] or r["escaped"]]
decoy_refused = [r for r in rows if r["secret"] == "decoy" and r["refusal"]]
L.dump(sys.argv[2], {"rows": rows, "control": control, "dict_key": dk, "guard_table": gt})
n = {s: sum(1 for r in rows if r["section"] == s and r["secret"] != "decoy") for s in ("run_case", "grade_case")}
print("rows", len(rows), "attack rows", n, "rows with a hit on disk / tool output / escape:", len(bad_disk), "decoys refused:", len(decoy_refused), "of", 2 * len(DECOYS))
for r in bad_disk:
    print("HIT:", r["section"], r["secret"], r["spelling"], r["field"], r["refusal"], r["disk_hits"][:4], r["tool_output_hits"][:3], r["escaped"])
for r in decoy_refused:
    print("DECOY REFUSED:", r["section"], r["field"], r["refusal"])
