import sys
path, start = sys.argv[1], sys.argv[2].encode()
b=open(path,"rb").read().split(b"\n")
keep=[l for l in b if not l.strip().startswith(start)]
assert len(b)-len(keep)==1,(len(b)-len(keep))
open(path,"wb").write(b"\n".join(keep))
