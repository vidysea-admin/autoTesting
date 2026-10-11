import os, sys, pathlib, shutil, unicodedata, autotester
print("autotester at", autotester.__file__)
from autotester.store.team_store import create_marker
from autotester.core.paths import team_path
from autotester.core.safe_names import safe_name, UnsafeName
base = pathlib.Path(sys.argv[1]); shutil.rmtree(base, ignore_errors=True)
root = base/"root"; root.mkdir(parents=True); (base/"sentinel.txt").write_text("S")
BS=chr(92)
names = ["ab:stream","nul:","NUL:x","CON .txt","CON","con.txt","CONIN$","conin$.x","CONOUT$","CONOUT$ .txt","LPT"+chr(0xb9),"lpt"+chr(0xb2)+".log","COM"+chr(0xb3),"com"+chr(0xb9)+" .x","COM1","com9.x","LPT1 ","x.","x ","x..","...","..","a<b","a>b",'a"b',"a|b","a?b","a*b","a:b","C:","c:"+BS+"x","a/b","a"+BS+"b","/abs",BS+BS+"srv"+BS+"sh",chr(0xff41)+chr(0xff42),chr(0xff23)+chr(0xff2f)+chr(0xff2e),chr(0xff2e)+chr(0xff35)+chr(0xff2c),"con"+chr(0xa0),"CON"+chr(0x200b),"a"+chr(0)+"b","a"+chr(9)+"b","a"+chr(0x1f)+"b","a"+chr(0x7f)+"b","a::$DATA","$MFT","AUX .tar.gz","prn  .x","com0","lpt0","com10","conn","console","a$b","aux-1","nul-x","CLOCK$","LPT"+chr(0x2074),"COM"+chr(0xff11),"conin","a b","a.b","a..b","x"*121,"x"*120,chr(0xe9),chr(0x202e)+"cod.txt","a"+chr(0x2024),"con"+chr(0xfe52),chr(0xff41)+chr(0xff1a)+"b","a"+chr(0xff0f)+"b","a"+chr(0xff3c)+"b",chr(0x2025),chr(0xff0e)+chr(0xff0e)]
res=[]
for n in names:
    # 1: pure validator
    try: safe_name(n); v="accept"
    except UnsafeName: v="refuse"
    except Exception as e: v="ERR "+type(e).__name__
    # 2: product path: create_marker
    try:
        created = create_marker(root, n, body="x"); out = "created" if created else "exists"
    except UnsafeName: out="UnsafeName"
    except Exception as e: out="OSERR "+type(e).__name__+":"+str(e)[:60]
    res.append((n,v,out))
# verify: only inside root; sentinel intact; accepted names yielded a real regular file of exactly that name
team = root/".work"/"team"
listing = set(os.listdir(team)) if team.exists() else set()
outside = [p for p in base.iterdir() if p.name not in ("root","sentinel.txt")]
print("sentinel intact:", (base/"sentinel.txt").read_text()=="S", "| extra entries beside root:", outside)
allfiles = [str(p.relative_to(base)) for p in base.rglob("*")]
bad=[]
for n,v,out in res:
    disp = ascii(n)[:40]
    real = n in listing
    flag=""
    if v=="accept" and out=="created" and not real: flag="  <-- ACCEPTED BUT NO REGULAR FILE (device/odd?)"
    if v=="refuse" and out!="UnsafeName": flag="  <-- INCONSISTENT"
    if v=="accept" and out.startswith("OSERR"): flag="  <-- accepted but OS rejected"
    if v=="refuse" and real: flag="  <-- refused yet file exists"
    print(f"{disp:44} validator={v:7} create_marker={out:12} file_in_team_dir={real}{flag}")
print("files created under root:", len(listing)); 
# nothing escaped: every created path resolves inside root
esc=[p for p in base.rglob("*") if root not in p.resolve().parents and p.resolve()!=root and p.name not in ("root","sentinel.txt")]
print("escaped paths:", esc)
