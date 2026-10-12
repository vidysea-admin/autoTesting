import sys, json
import autotester
from autotester.schema.project import Source
tag = sys.argv[1]
print("##", tag, autotester.__file__)
for fn in sys.argv[2:]:
    for line in open(fn, newline="").read().splitlines():
        try:
            s = Source.model_validate_json(line)
            re = s.model_dump_json(exclude_none=True)
            o = s.origin
            print("  ", fn.split("/")[-1][:8], "OK", "byte-identical" if re == line else "DIFF", type(o).__name__, "id=", s.id[:10], "|", line[line.find('"origin"'):][:70] if '"origin"' in line else "-")
        except Exception as e:
            print("  ", fn.split("/")[-1][:8], "ERR", str(e).splitlines()[0][:80], "|", line[:90])
