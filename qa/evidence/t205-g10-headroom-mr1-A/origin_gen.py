import sys, json
import autotester
from autotester.schema.project import Source
from autotester.schema.enums import SourceKind
tag = sys.argv[1]
out = []
try:
    from autotester.schema.intake import UploadOrigin, ZipOrigin, DriveOrigin
    models = [UploadOrigin(file_name="a.mp4"), ZipOrigin(archive_name="z.zip", member_path="d/a.mp4"), DriveOrigin(file_id="F1")]
except Exception as e:
    models = []
try:
    from autotester.schema.team_enums import SourceOriginKind
    kinds = list(SourceOriginKind)
except Exception:
    kinds = []
sources = [Source(project="demo", kind=SourceKind.VIDEO, path="p.mp4", uploaded_by="a@b.c")]
for m in models: sources.append(Source(project="demo", kind=SourceKind.VIDEO, path="p.mp4", origin=m))
for k in kinds:
    try: sources.append(Source(project="demo", kind=SourceKind.VIDEO, path="p.mp4", origin=k))
    except Exception as e: print(tag, "construct fail", k, type(e).__name__)
with open(sys.argv[2], "w", newline="") as f:
    for s in sources:
        f.write(s.model_dump_json(exclude_none=True) + "\n")
print(tag, autotester.__file__, len(sources))
