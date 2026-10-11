import hashlib, random, shutil, sys, tempfile, time, zipfile, collections, traceback
from pathlib import Path
SRC, N = Path(sys.argv[1]), int(sys.argv[2])
sys.path.insert(0, str(SRC))
from autotester.sources.zip_intake import expand_zip
from autotester.store.project_store import ProjectStore
def noise(tag,size=3000):
    out,n=b"",0
    while len(out)<size:
        out+=hashlib.sha256(f"{tag}{n}".encode()).digest(); n+=1
    return out[:size]
M={"stored":zipfile.ZIP_STORED,"deflate":zipfile.ZIP_DEFLATED,"bzip2":zipfile.ZIP_BZIP2,"lzma":zipfile.ZIP_LZMA}
base={}
tmp=Path(tempfile.mkdtemp(prefix="b1fuzz-",dir=sys.argv[3]))
for k,m in M.items():
    p=tmp/f"{k}.zip"
    with zipfile.ZipFile(p,"w",compression=m) as z:
        for n in ("a.mp4","b.mp4","c.mp4"): z.writestr(n,noise(n))
    base[k]=p.read_bytes()
rng=random.Random(1198)
exc=collections.Counter(); ex={}
slow=[]
t0=time.time()
for i in range(N):
    k=rng.choice(list(M)); raw=bytearray(base[k])
    for _ in range(rng.choice((1,1,2,3))):
        # bias: 60% into headers (first 40 bytes of each record / last 300 bytes)
        r=rng.random()
        if r<0.35: pos=len(raw)-rng.randint(1,min(len(raw),260))
        elif r<0.6:
            sig=rng.choice((b"PK\x03\x04",b"PK\x01\x02")); idxs=[j for j in range(len(raw)-4) if raw[j:j+4]==sig]
            pos=min(len(raw)-1,rng.choice(idxs)+rng.randint(0,45)) if idxs else rng.randrange(len(raw))
        else: pos=rng.randrange(len(raw))
        raw[pos]=rng.randrange(256)
    d=tmp/f"r{i%5}"; shutil.rmtree(d,ignore_errors=True); d.mkdir()
    arc=d/"in.zip"; arc.write_bytes(bytes(raw)); root=d/"root"; root.mkdir()
    st=ProjectStore("demo",root=root); st.paths.dir.mkdir(parents=True,exist_ok=True)
    t=time.time()
    try:
        rep=expand_zip(st,arc,max_file_bytes=10*1024*1024)
        exc["ok:"+rep.status.value]+=1
    except BaseException as e:
        key=type(e).__name__+": "+str(e)[:60]; exc[key]+=1
        if key not in ex:
            ex[key]=(i,k,traceback.format_exc().splitlines()[-3:])
            (tmp/f"keep-{len(ex)}.zip").write_bytes(bytes(raw))
    if time.time()-t>5: slow.append((i,time.time()-t))
print("N",N,"secs",round(time.time()-t0,1))
for k,v in exc.most_common(): print(v,k)
for k,v in ex.items(): print("FIRST",k,v)
print("slow",slow)
shutil.rmtree(tmp,ignore_errors=True)
