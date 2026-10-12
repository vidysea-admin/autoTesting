import json, os, sys
from harness import *
def ptr(text): return {"p.txt": text.encode("utf-8")}
def big(n):
    lines = []
    extra = (n - 100 * 13) - 100 * 314
    for i in range(100): lines.append("0:10-0:20 | " + "a" * (315 if i < extra else 314))
    t = "\n".join(lines) + "\n"
    b = t.encode(); assert len(b) == n, (len(b), n); return {"p.txt": b}
def confirm(world):
    for f in (world / "projects" / "demo" / "reviews").glob("rv_*.json"):
        d = json.loads(f.read_text("utf-8"))
        if d.get("items"): d["items"][0]["status"] = "confirmed"; f.write_text(json.dumps(d), "utf-8")
RV = ["ingest", "review", "demo", "{SRC}"]
J = ["--output", "json"]
P = ["--pointers", "{WORLD}/files/p.txt"]
good_ptr = "0:30-0:50 | check this\n~1:10\n1:40 | and this\n"
rows = []
def add(id, extra, fake="ok", variant="approved", files=None, **kw):
    rows.append({"id": id, "args": RV + extra if not (extra and extra[0] == "RAW") else extra[1:], "fake": fake, "variant": variant, "files": files or {}, **kw})
add("r01-ok-text", [])
add("r02-ok-json", J)
add("r03-dry-text", ["--dry-run"])
add("r04-dry-json", J + ["--dry-run"])
add("r05-dry-noapproval-json", J + ["--dry-run"], variant="noapproval")
add("r06a-dry-pointers-json", J + P + ["--dry-run"], files=ptr(good_ptr))
add("r06b-partial-cap0-json", J + ["--max-cost", "0"])
add("r06c-partial-costly-json", J + P + ["--max-cost", "0.5"], fake="costly", files=ptr(good_ptr))
add("r06d-partial-costly-text", P + ["--max-cost", "0.5"], fake="costly", files=ptr(good_ptr))
add("r07-failed-badreply-json", J, fake="badreply")
add("r07b-failed-badreply-text", [], fake="badreply")
add("r08-provider-error-json", J, fake="raise_provider")
add("r09-runtime-json", J, fake="raise_runtime")
add("r09b-runtime-text", [], fake="raise_runtime")
add("r10-oserror-json", J, fake="raise_os")
add("r10b-oserror-text", [], fake="raise_os")
add("r11-interrupt-json", J, fake="interrupt")
add("r11b-interrupt-text", [], fake="interrupt")
bad = "99:99\n1:00 | fine\n14:00-12:30\n-1:00\n2:00 | ok\n"
add("r12-ptrerr-text", P, files=ptr(bad))
add("r12b-ptrerr-json", J + P, files=ptr(bad))
add("r13-ptr-ok-json", J + P, files=ptr(good_ptr))
add("r13b-ptr-bom-crlf-json", J + P, files=ptr("﻿0:30-0:50 | check\r\n~1:10\r\n"))
add("r14a-ptr-32768-json", J + P, files=big(32768))
add("r14b-ptr-32769-json", J + P, files=big(32769))
add("r14c-ptr-32769-text", P, files=big(32769))
add("r15-ptr-missing-json", J + ["--pointers", "{WORLD}/files/nope.txt"])
add("r15b-ptr-nonutf8-json", J + P, files={"p.txt": b"\xff\xfe\x00bad\n"})
add("r16-noapproval-text", [], variant="noapproval")
add("r16b-noapproval-json", J, variant="noapproval")
add("r16c-wrongprov-json", J, variant="wrongprov")
add("r16d-wrongproject-json", J, variant="wrongproject")
add("r17a-unreadable-empty-json", J, variant="truncated")
add("r17b-unreadable-empty-text", [], variant="truncated")
add("r17c-missingfile-json", J, variant="missingfile")
add("r17d-corrupt-json", J, variant="corrupt")
add("r17e-audioonly-json", J, variant="audioonly")
add("r18a-usage-cap-abc-json", J + ["--max-cost", "abc"])
add("r18b-usage-cap-abc-text", ["--max-cost", "abc"])
add("r18c-usage-cap-empty-json", J + ["--max-cost", ""])
add("r18d-usage-missing-arg-json", ["RAW", "ingest", "review", "demo", "--output", "json"])
add("r18e-usage-missing-arg-text", ["RAW", "ingest", "review", "demo"])
add("r18f-usage-unknown-opt-json", J + ["--bogus"])
add("r18g-usage-unknown-opt-text", ["--bogus"])
add("r18h-usage-output-xml", ["--output", "xml"])
add("r18i-usage-output-bare-text", ["--output"])
add("r18j-usage-output-eq-json-bad", ["--output=json", "--max-cost", "x"])
add("r19a-redact-bad-json", J + ["--redact", "bad"])
add("r19b-redact-bad-text", ["--redact", "bad"])
add("r19c-redact-beyond-json", J + ["--redact", "5:00-6:00"])
add("r19d-redact-reversed-json", J + ["--redact", "1:00-0:30"])
add("r19e-redact-ok-json", J + ["--redact", "0:20-0:40"])
add("r19f-redact-ok-text", ["--redact", "0:20-0:40"])
add("r19g-redact-two-ok-json", J + ["--redact", "0:20-0:40", "--redact", "1:00-1:10"])
for i, v in enumerate(["nan", "inf", "-inf", "-1", "-0.01", "1e999", "NaN"]):
    add(f"r20{chr(97+i)}-cap-{v}-json", J + ["--max-cost", v])
add("r20h-cap-nan-text", ["--max-cost", "nan"])
add("r21a-provider-unknown-json", J + ["--provider", "nonesuch"], fake="")
add("r21b-provider-gemini-noapproval-json", J + ["--provider", "gemini"], fake="", variant="noapproval")
add("r21c-provider-unavailable-json", J, fake="unavailable")
add("r22a-noproject-json", J, variant="noproject")
add("r22b-noproject-text", [], variant="noproject")
add("r22c-nosuchsource-json", ["ingest", "review", "demo", "src_deadbeef", "--output", "json"])
add("r22d-emptyproject-json", ["ingest", "review", "demo", "src_deadbeef", "--output", "json"], variant="emptyproject")
add("r23a-rerun-json", J, then=[RV + J, RV + J + ["--refresh"]])
add("r23b-rerun-confirm-json", J, then=[RV + J], mutate=confirm)
add("r23c-pointer-changes-id-json", J + P, files=ptr(good_ptr), then=[RV + J + P])
add("r24a-many-json", J, fake="many")
add("r24b-many-text", [], fake="many")
add("r25-maxcost-model-json", J + ["--model", "m-x", "--max-cost", "1.5"])
add("r26-help", ["--help"])
if __name__ == "__main__":
    which = sys.argv[1]
    res = run_all(which, rows, workers=int(os.environ.get("W", "6")))
    json.dump(res, open(PR / f"res-review-{which}.json", "w"), indent=1, sort_keys=True)
    print(which, len(res), "rows done", sum(1 for r in res if not r["at_file_ok"]), "at_file_bad")
