"""Run selected offline checks with explicit copied-source identity before pytest."""
import hashlib, importlib.metadata, json, pathlib, sys
import autotester
expected=pathlib.Path(sys.argv[1]).resolve()
actual=pathlib.Path(autotester.__file__).resolve()
assert actual.is_relative_to(expected), (str(actual),str(expected))
deps=sorted((d.metadata.get("Name", ""),d.version) for d in importlib.metadata.distributions())
identity={"python":sys.executable,"version":sys.version,"import_file":str(actual),"import_root":str(expected),"dependencies_sha256":hashlib.sha256(json.dumps(deps,sort_keys=True).encode()).hexdigest()}
print("__RUNTIME__"+json.dumps(identity,sort_keys=True),flush=True)
import pytest
raise SystemExit(pytest.main(sys.argv[2:]))
