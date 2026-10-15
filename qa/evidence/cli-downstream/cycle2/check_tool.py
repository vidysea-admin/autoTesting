"""Identify the actual copied runtime, then perform a scoped static tool check."""
import ast,hashlib,importlib.metadata,json,pathlib,runpy,sys
import autotester
root=pathlib.Path(sys.argv[1]);tool=sys.argv[2];files=sys.argv[3:]
actual=pathlib.Path(autotester.__file__).resolve();assert actual.is_relative_to(root.resolve())
deps=sorted((d.metadata.get("Name", ""),d.version) for d in importlib.metadata.distributions())
print("__RUNTIME__"+json.dumps({"python":sys.executable,"version":sys.version,"import_file":str(actual),"import_root":str(root),"dependencies_sha256":hashlib.sha256(json.dumps(deps,sort_keys=True).encode()).hexdigest()},sort_keys=True),flush=True)
if tool=="ruff":
 sys.argv=["ruff","check",*files]
 runpy.run_module("ruff",run_name="__main__")
elif tool=="shape":
 failures=[]
 for name in files:
  text=pathlib.Path(name).read_text();tree=ast.parse(text)
  if len(text.splitlines())>300:failures.append([name,"file",len(text.splitlines())])
  for node in ast.walk(tree):
   if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.end_lineno-node.lineno+1>50:
    failures.append([name,node.name,node.end_lineno-node.lineno+1])
 print(json.dumps({"files":len(files),"violations":failures}))
 raise SystemExit(bool(failures))
else:raise ValueError(tool)
