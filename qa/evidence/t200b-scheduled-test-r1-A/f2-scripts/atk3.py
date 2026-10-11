import sys, os, json, time, tempfile, shutil, hashlib
import multiprocessing as mp
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from atk2 import mk

def snap(base):
    return {str(p.relative_to(base)): p.read_bytes() for p in sorted(Path(base).rglob("*")) if p.is_file()}

def neighbour_shared(path, n, out):
    from autotester.stages.schedule_store import append_record
    ok = 0
    for i in range(n):
        ok += bool(append_record(Path(path), mk("q", 1000+i)[2]))
    Path(out).write_text(str(ok))

def main():
    from autotester.stages.schedule_store import claim, append_record, purge_project, read_records, list_claims
    root = Path(tempfile.mkdtemp(prefix="atk3-", dir=sys.argv[1]))
    def seed(sub):
        b = root/sub; (b/"claims").mkdir(parents=True)
        for i in range(2):
            k,c,r = mk("p", i); claim(b/"claims", k, c)
        f = b/"shared.jsonl"
        for i in range(2): append_record(f, mk("p", i)[2])
        return b, f
    # 3a: foreign row in the middle + concurrent neighbour appends
    b, f = seed("a")
    append_record(f, mk("q", 0)[2])
    for i in range(2,4): append_record(f, mk("p", i)[2])
    ctx = mp.get_context("spawn"); out = b/"out.txt"
    before_claims = {k for k in list_claims(b/"claims")}
    before = f.read_bytes()
    child = ctx.Process(target=neighbour_shared, args=(str(f), 150, str(out))); child.start()
    errs = []; tries = 0
    while child.is_alive() or tries == 0:
        tries += 1
        try: purge_project(b/"claims", f, "p"); errs.append("NO RAISE")
        except ValueError: errs.append("ValueError")
        except Exception as e: errs.append(repr(e))
    child.join(60)
    after = f.read_bytes()
    print("3a middle foreign row + live neighbour:", {"purge_attempts": tries, "outcomes": sorted(set(errs)),
          "prefix_preserved": after.startswith(before), "neighbour_acked": out.read_text(), "q_rows_in_file": sum(1 for r in read_records(f) if r.project=="q")-1,
          "claims_unchanged": set(list_claims(b/"claims"))==before_claims, "stage": [p.name for p in b.rglob(".purge-*")]})
    # 3b: foreign row is LAST line
    b, f = seed("b"); append_record(f, mk("q", 0)[2])
    s0 = snap(b)
    try: purge_project(b/"claims", f, "p"); r = "NO RAISE"
    except ValueError as e: r = "ValueError"
    print("3b foreign LAST line:", r, "byte-identical:", snap(b)==s0)
    # 3c: foreign TORN line (last), 3d: foreign valid-JSON but newer-schema row, 3e: foreign torn line in middle
    for tag, junk, where in [("3c torn foreign last line", mk("q",0)[2].model_dump_json()[:40], "end"),
                             ("3d foreign row w/ unknown field (newer schema) last", None, "end"),
                             ("3e torn foreign line in middle", mk("q",0)[2].model_dump_json()[:40], "mid")]:
        b, f = seed(tag[:2])
        if junk is None:
            d = json.loads(mk("q",0)[2].model_dump_json()); d["new_field"]=1; junk = json.dumps(d)
        lines = f.read_text().splitlines()
        if where=="mid": lines.insert(1, junk)
        else: lines.append(junk)
        f.write_bytes(("\n".join(lines)+"\n").encode()) if where=="mid" or tag.startswith("3d") else f.write_bytes(("\n".join(lines)).encode())
        try: purge_project(b/"claims", f, "p"); r = "NO RAISE"
        except ValueError: r = "ValueError"
        print(tag+":", r, "| file still exists:", f.exists(), "| p claims left:", len(list_claims(b/"claims")), "| foreign data silently deleted:", (r=="NO RAISE" and not f.exists()))
    shutil.rmtree(root, ignore_errors=True)

if __name__ == "__main__":
    import autotester; print("autotester.__file__ =", autotester.__file__)
    main()
