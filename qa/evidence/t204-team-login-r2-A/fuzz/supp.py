"""Second pass: classify binds with LINUX semantics (WSL2 Ubuntu, glibc) - the deployment OS - and rerun
the cases whose bindable/wildcard classification differs from the Windows first pass."""
import json, glob, re, subprocess, sys, os, ipaddress
from pathlib import Path
OUT=Path(__file__).parent
mode=sys.argv[1]
def load():
    rows=[]
    for f in sorted(glob.glob(str(OUT/'cases.[0-9].json'))): rows+=json.load(open(f,encoding='utf-8'))
    return rows
HN=re.compile(r'^(?=.*[A-Za-z])[A-Za-z0-9][A-Za-z0-9._-]*$')
def classify(h, lin):
    r=lin[h]
    if r['kind']=='bound':
        a=r['addr']; return dict(bindable=True,bound=a,wild=ipaddress.ip_address(a.split('%')[0]).is_unspecified)
    if r['kind']=='oserror': return dict(bindable=True,bound='concrete-non-local('+r['addr']+')',wild=False)
    if HN.match(h) and ':' not in h: return dict(bindable=True,bound='hostname-assumed-resolvable',wild=False)
    if ':' in h and '%' in h: return dict(bindable=True,bound='scoped-ipv6-assumed-concrete',wild=False)
    return dict(bindable=False,bound='linux gaierror: '+r['addr'],wild=None)
if mode=='prep':
    rows=load(); hosts=sorted({r['ref_host'] for r in rows if r.get('ref_host') is not None})
    json.dump(hosts,open(OUT/'hosts.json','w',encoding='utf-8'))
    subprocess.run(['wsl','-d','Ubuntu','--','python3','/mnt/d/autoTesting/qa/evidence/t204-team-login-r2-A/fuzz/linux_probe2.py','/mnt/d/autoTesting/qa/evidence/t204-team-login-r2-A/fuzz/hosts.json','/mnt/d/autoTesting/qa/evidence/t204-team-login-r2-A/fuzz/linux_bind.json'],check=True,env={**os.environ,'MSYS_NO_PATHCONV':'1'})
    lin=json.load(open(OUT/'linux_bind.json',encoding='utf-8'))
    cls={h:classify(h,lin) for h in hosts}
    redo=[]
    for r in rows:
        h=r.get('ref_host')
        if h is None: continue
        c=cls[h]; win_b = r['verdict']!='UNBINDABLE-os-refuses'; win_w = r.get('wild') if win_b else None
        if (c['bindable'],c['wild'])!=(win_b,win_w): redo.append(r['id'])
    json.dump(sorted(set(redo)),open(OUT/'redo_ids.json','w'))
    json.dump(cls,open(OUT/'linux_classes.json','w',indent=1) if False else open(OUT/'linux_classes.json','w'),indent=1)
    print(len(hosts),'hosts',len(redo),'cases to redo')
elif mode=='run':
    cls=json.load(open(OUT/'linux_classes.json')); ids=set(json.load(open(OUT/'redo_ids.json')))
    import harness
    def probe(host):
        c=dict(cls[host]); c['ip_unspecified']=None; return c
    harness.probe_bind=probe
    cases=[c for c in harness.CASES if c['id'] in ids]
    shard,n=(int(x) for x in os.environ.get('FUZZ_SHARD','0/1').split('/'))
    size=-(-len(cases)//n); mine=cases[shard*size:(shard+1)*size]
    rows=[harness.run_case(c) for c in mine]
    for r in rows: r['pass']='linux-rerun'
    json.dump(rows,open(OUT/f'supp.{shard}.json','w',encoding='utf-8'),indent=1,default=str)
    harness.mp.undo()
elif mode=='merge':
    import csv, collections
    cls=json.load(open(OUT/'linux_classes.json'))
    rows=load(); sup={}
    for f in glob.glob(str(OUT/'supp.[0-9].json')):
        for r in json.load(open(f,encoding='utf-8')): sup[r['id']]=r
    final=[]
    for r in rows:
        if r['id'] in sup: final.append(sup[r['id']]); continue
        h=r.get('ref_host')
        r['pass']='windows-first-pass-equal-to-linux'
        final.append(r)
    cols=list(dict.fromkeys(k for r in final for k in r))
    with open(OUT/'cases.csv','w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=cols); w.writeheader(); w.writerows(final)
    json.dump(final,open(OUT/'cases.json','w',encoding='utf-8'),indent=1,default=str)
    s={'total':len(final),'by_verdict':dict(collections.Counter(r['verdict'] for r in final)),
       'by_dim':{d:dict(collections.Counter(r['verdict'] for r in final if r['dim']==d)) for d in sorted({r['dim'] for r in final})}}
    json.dump(s,open(OUT/'summary.json','w'),indent=1); print(json.dumps(s,indent=1))
