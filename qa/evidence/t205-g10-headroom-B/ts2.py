import os, tempfile
from pathlib import Path
from autotester.store import team_store

root = Path(tempfile.mkdtemp(prefix="b-ts2-"))
print("nul: first ", team_store.create_marker(root, "nul:", body="x"))
print("nul: second", team_store.create_marker(root, "nul:", body="x"))
print("nul: file exists?", (root / ".work" / "team" / "nul:").exists())
print("ab:stream first ", team_store.create_marker(root, "ab:stream", body="hidden"))
print("ab:stream second", team_store.create_marker(root, "ab:stream", body="hidden"))
print("listing:", sorted(str(p.relative_to(root)) for p in root.rglob("*")))
print("control: plain marker first/second:", team_store.create_marker(root, "m1"), team_store.create_marker(root, "m1"))
