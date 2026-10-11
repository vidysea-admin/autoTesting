"""Seat A throwaway counterexample sweep for DC4 error path (not part of the repo)."""
import copy
import html as htmllib
import json
import os
import shutil
import sys
import tempfile
import urllib.parse
from pathlib import Path

MAIN = Path(sys.argv[1])
sys.path.insert(0, str(MAIN / "src"))
sys.path.insert(0, str(MAIN / "tests"))

import test_unified_report_secrets as T  # noqa: E402
from autotester.stages.unified_report import ReportUnavailable, build_report, export_unified_html  # noqa: E402
from autotester.store.project_store import ProjectStore  # noqa: E402

S = T.S
FORMS = [S, htmllib.escape(S), htmllib.escape(S, quote=False), urllib.parse.quote(S),
         urllib.parse.quote(S, safe="")]
UNDECLARED = "sk_live_ABCDEF1234567890abcd"

base = Path(tempfile.mkdtemp(prefix="A-base-"))
os.environ["AUTOTESTER_ROOT"] = str(base)
(base / ".env").write_text(f'DEMO_PASSWORD="{S}"\n', encoding="utf-8")
T._seed_everywhere(base)

files = [p for p in base.rglob("*") if p.is_file() and p.suffix in (".json", ".jsonl")]
print("stored files:", len(files))


def paths(obj, prefix=()):
    yield prefix
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from paths(v, prefix + (k,))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from paths(v, prefix + (i,))


def setp(obj, path, value):
    cur = obj
    for p in path[:-1]:
        cur = cur[p]
    cur[path[-1]] = value


def mutants(doc):
    for p in paths(doc):
        if not p:
            continue
        d = copy.deepcopy(doc)
        setp(d, p, S)
        yield ("val", p, d)
    for p in paths(doc):
        node = doc
        for k in p:
            node = node[k]
        if isinstance(node, dict):
            for name, tag in ((S, "extraS"), (UNDECLARED, "extraUNDECL")):
                d = copy.deepcopy(doc)
                tgt = d
                for k in p:
                    tgt = tgt[k]
                tgt[name] = 1
                yield (tag, p, d)


results = {"runs": 0, "built": 0, "unreadable": 0, "unavail": 0, "other_exc": [], "leaks": [],
           "undecl_echo": []}
for f in files:
    raw = f.read_text(encoding="utf-8")
    docs = []
    if f.suffix == ".jsonl":
        lines = [json.loads(x) for x in raw.splitlines() if x.strip()]
        variants = []
        for li, d in enumerate(lines):
            for tag, p, m in mutants(d):
                nl = list(lines)
                nl[li] = m
                variants.append((tag, (li,) + p, "\n".join(json.dumps(x) for x in nl) + "\n"))
    else:
        d = json.loads(raw)
        variants = [(tag, p, json.dumps(m)) for tag, p, m in mutants(d)]
    for tag, p, text in variants:
        f.write_text(text, encoding="utf-8")
        results["runs"] += 1
        outs = []
        try:
            build_report(ProjectStore("demo", base), None)
            results["built"] += 1
        except ReportUnavailable as e:
            results["unavail"] += 1
            outs.append(str(e))
        except ValueError as e:
            results["unreadable"] += 1
            outs.append(str(e))
            if e.__cause__ is not None or not e.__suppress_context__:
                results["leaks"].append((f.name, tag, p, "chain-not-suppressed"))
        except Exception as e:  # noqa: BLE001
            results["other_exc"].append((f.name, tag, p, type(e).__name__, str(e)[:160]))
        try:
            export_unified_html("demo", None, base / "o.html", base)
        except ValueError as e:
            outs.append(str(e))
        except Exception as e:  # noqa: BLE001
            results["other_exc"].append((f.name, tag, p, "export:" + type(e).__name__, str(e)[:160]))
        for o in outs:
            if any(form in o for form in FORMS):
                results["leaks"].append((f.name, tag, p, o[:200]))
            if UNDECLARED in o:
                results["undecl_echo"].append((f.name, tag, p, o[:200]))
        # success-path artifact must not hold S either
        o = base / "o.html"
        if o.exists():
            page = o.read_text(encoding="utf-8")
            if any(form in page for form in FORMS):
                results["leaks"].append((f.name, tag, p, "ARTIFACT holds secret"))
            o.unlink()
    f.write_text(raw, encoding="utf-8")

print({k: (v if not isinstance(v, list) else len(v)) for k, v in results.items()})
seen = set()
for key in ("leaks", "undecl_echo", "other_exc"):
    print("==", key)
    for item in results[key][:25]:
        print(item)
shutil.rmtree(base, ignore_errors=True)
