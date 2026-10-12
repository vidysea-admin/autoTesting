import sys, json
from autotester.schema.project import Source
from autotester.schema.enums import SourceKind
import autotester, inspect
print("FILE", autotester.__file__)
def mk(origin):
    return Source(kind=SourceKind.VIDEO if hasattr(SourceKind,"VIDEO") else list(SourceKind)[0], path="a/b.mp4", origin=origin) if origin is not None else None
print([k.value for k in SourceKind])
