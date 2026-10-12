import json
import autotester
from autotester.schema.project import Source
base = {"project":"demo","kind":"video","path":"p.mp4"}
cases = {
 "bare zip": "zip", "bare recording": "recording", "bare ZIP upper": "ZIP", "bare empty": "", "bare email": "email",
 "dict zip full": {"kind":"zip","archive_name":"z","member_path":"m"},
 "dict zip no detail": {"kind":"zip"},
 "dict recording": {"kind":"recording"},
 "dict upload full": {"kind":"upload","file_name":"x"},
 "dict upload extra key": {"kind":"upload","file_name":"x","bogus":1},
 "dict upload with drive field": {"kind":"upload","file_name":"x","file_id":"F"},
 "dict drive": {"kind":"drive","file_id":"F"},
 "dict email": {"kind":"email","file_name":"x"},
 "dict no kind": {"file_name":"x"},
 "list": ["zip"], "int": 3, "null": None,
}
for name, o in cases.items():
    d = dict(base, origin=o)
    for mode, fn in (("json", lambda d: Source.model_validate_json(json.dumps(d))), ("py", lambda d: Source.model_validate(d))):
        try:
            s = fn(d); print(f"{name:32s} {mode:4s} -> {type(s.origin).__name__}:{s.origin!r}"[:150])
        except Exception as e:
            print(f"{name:32s} {mode:4s} -> ERR {type(e).__name__} {str(e).splitlines()[0][:60]} | n_errors={e.error_count() if hasattr(e,'error_count') else '-'}")
