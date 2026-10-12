import pathlib, sys, hashlib
from autotester.schema.project import Source, Project
from autotester.store.filestore import read_jsonl
root = pathlib.Path(sys.argv[1])
for f in sorted(root.glob("projects/*/sources.jsonl")):
    raw = f.read_bytes().decode().splitlines()
    items = read_jsonl(f, Source)
    out = [i.model_dump_json(exclude_none=True) for i in items]
    same = [a == b for a, b in zip(raw, out)]
    print(f.relative_to(root).as_posix(), "lines", len(raw), "loaded", len(items), "byte-identical-lines", sum(same), "ids-preserved", all(i.id for i in items))
for f in sorted(root.glob("projects/*/project.json")):
    p = Project.model_validate_json(f.read_text(encoding="utf-8"))
    again = Project.model_validate_json(p.model_dump_json(exclude_none=True))
    print(f.relative_to(root).as_posix(), "loads, round-trip equal:", p == again)
