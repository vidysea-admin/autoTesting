import autotester
from autotester.schema.project import Source
from autotester.schema.enums import SourceKind
from autotester.schema.intake import DriveOrigin, ZipOrigin
k=list(SourceKind)[0]
res={}
for label,o in {"none":None,"DriveOrigin":DriveOrigin(file_id="F1"),"ZipOrigin":ZipOrigin(archive_name="a",member_path="b"),"'drive'":"drive","dict drive":{"kind":"drive","file_id":"x"},"'email'":"email"}.items():
    try:
        s=Source(project="demo",kind=k,path="p.mp4",sha256="a"*64,origin=o); res[label]=(type(s.origin).__name__,s.id)
    except Exception as e: res[label]=type(e).__name__
print(list(SourceKind)); [print(a,b) for a,b in res.items()]
