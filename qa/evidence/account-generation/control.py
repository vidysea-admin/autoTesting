"""Existing interpreter/import/temp preflight, touched-source shape and scoped lint."""
import ast
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import autotester

expected = Path(sys.argv[1]).resolve()
actual = Path(autotester.__file__).resolve()
assert actual.is_relative_to(expected)
deps = sorted((d.metadata.get('Name', ''), d.version) for d in importlib.metadata.distributions())
identity = dict(python=sys.executable, version=sys.version, import_file=str(actual),
                import_root=str(expected), dependencies_sha256=hashlib.sha256(
                    json.dumps(deps, sort_keys=True).encode()).hexdigest())
print('__RUNTIME__'+json.dumps(identity, sort_keys=True), flush=True)
with tempfile.TemporaryDirectory(dir=Path.cwd()) as scratch:
    file = Path(scratch)/'roundtrip.txt'
    file.write_text('preflight', encoding='utf-8')
    assert file.read_text() == 'preflight'
for name in sys.argv[2:]:
    text = Path(name).read_text(encoding='utf-8')
    assert len(text.splitlines()) <= 300, name
    tree = ast.parse(text)
    assert ast.get_docstring(tree), name
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            assert node.end_lineno-node.lineno+1 <= 50, (name, node.name)
command = [sys.executable, '-m', 'ruff', 'check', *sys.argv[2:], '--no-cache']
print('__CONTROL__'+json.dumps(dict(command=command), sort_keys=True), flush=True)
raise SystemExit(subprocess.run(command).returncode)
