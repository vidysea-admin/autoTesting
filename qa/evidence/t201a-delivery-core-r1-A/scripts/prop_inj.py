"""Checker A property test: injectivity of delivery_key + exact-match lookups. Throwaway."""
import itertools, random, re, sys, tempfile, pathlib
from datetime import datetime
import autotester
print("autotester at", autotester.__file__)
from autotester.delivery.inbox import delivery_key, DeliveryLog, _encode_part
from autotester.schema.delivery import (DeliveryChannel, DeliveryRecord, DeliveryStatus, SAFE_ID, SAFE_KEY, safe_id)

CH = list(DeliveryChannel)
def valid(s): 
    try: safe_id(s); return True
    except ValueError: return False

def decode_part(enc):
    out=[];i=0
    while i<len(enc):
        c=enc[i]
        if c=="_":
            n=enc[i+1]
            out.append("_" if n=="0" else n.upper()); assert n=="0" or n.isalpha() and n.islower(); i+=2
        else:
            assert c in "abcdefghijklmnopqrstuvwxyz0123456789.-", c
            out.append(c); i+=1
    return "".join(out)

def split_key(key):
    ch, rest = key.split("__",1)
    # rest = R __ U ; R has no "__" and does not end in "_"; first "__" is the separator
    j = rest.index("__")
    return ch, rest[:j], rest[j+2:]

def check_pair(r,u,ch):
    k=delivery_key(r,ch,u)
    assert SAFE_KEY.fullmatch(k)
    assert k==k.lower(), k
    c,er,eu=split_key(k)
    assert c==ch.value and decode_part(er)==r and decode_part(eu)==u, (r,u,k)
    assert "__" not in er and "__" not in eu and not er.endswith("_") and not eu.endswith("_")
    return k

# 1. exhaustive small alphabet
alpha="aA_0.-xX1"
ids=[]
for n in range(1,5):
    for t in itertools.product(alpha,repeat=n):
        s="".join(t)
        if valid(s): ids.append(s)
print("exhaustive ids",len(ids))
# keys over all (run,user) would be N^2*2 -- do ids up to length 3 pairs fully, length4 sampled
small=[i for i in ids if len(i)<=3]
print("small",len(small))
seen={}
cnt=0
for ch in CH:
    for r in small:
        for u in small:
            k=check_pair(r,u,ch); cnt+=1
            assert k not in seen, (k,seen.get(k),(ch,r,u))
            seen[k]=(ch,r,u)
            assert k.casefold() not in seen or seen[k]  # placeholder
print("exhaustive pairs ok",cnt)
# case-insensitive uniqueness
fold={}
for k,v in seen.items():
    assert fold.setdefault(k.casefold(),v)==v,(k,v)
print("casefold injective over",len(fold))
# 2. random from full alphabet, mixed lengths, biased to structure chars
rnd=random.Random(20261012)
FULL="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-"
def rid():
    while True:
        n=rnd.choice([1,2,3,4,5,8,16,40,64])
        pool=rnd.choice([FULL,"aA_0.-","_x.-0A","Aa_","x_"+"_"*3+"y"])
        s=rnd.choice("aA0xX")+"".join(rnd.choice(pool) for _ in range(n-1)) if n>1 else rnd.choice("aA0xX")
        s=s[:64]
        if valid(s): return s
seen2={}
raised=0
for _ in range(6000):
    r,u,ch=rid(),rid(),rnd.choice(CH)
    try: k=delivery_key(r,ch,u)
    except ValueError: raised+=1; continue
    check_pair(r,u,ch)
    assert seen2.setdefault(k,(ch,r,u))==(ch,r,u)
print("random ok",len(seen2),"raised(too long)",raised)
# 3. adversarial hand-picked
adv=[("x__email__y","z"),("x","y__email__z"),("a","A"),("A","a"),("_a","A"),("a_","a_0"),("a_0","a_"),("A_","a_a"),("a","a.01"),("alice","alice.smith"),
     ("a_a","aA"),("a_A","a_a"),("x","x"),("X","x"),("a_0","a_0")]
adv=[(r,u) for r,u in adv if valid(r) and valid(u)]
ks={}
for r,u in adv:
    for ch in CH:
        k=check_pair(r,u,ch); assert ks.setdefault(k,(r,u,ch))==(r,u,ch)
print("adversarial skipped invalid:",[p for p in [("x__email__y","z"),("x","y__email__z"),("_a","A")] if not (valid(p[0]) and valid(p[1]))])
# 4. on-disk lookups with exact patterns
with tempfile.TemporaryDirectory(dir=sys.argv[1]) as d:
    log=DeliveryLog(pathlib.Path(d))
    runs=[r for r in small if len(r)<=2][:40]; users=[u for u in small if len(u)<=3][:60]
    pairs=set()
    for r in runs:
        for u in rnd.sample(users,10): pairs.add((r,u))
    for (r,u) in pairs:
        for ch in CH:
            k=delivery_key(r,ch,u)
            for att in (1,2):
                log.append(k,DeliveryRecord(run_id=r,channel=ch,recipient_user_id=u,status=DeliveryStatus.FAILED,error="e",attempts=att))
    bad=0
    for (r,u) in pairs:
        for ch in CH:
            k=delivery_key(r,ch,u)
            got=log.records_for_key(k)
            assert len(got)==2 and all(g.run_id==r and g.recipient_user_id==u and g.channel==ch for g in got),(r,u)
    for r in set(p[0] for p in pairs):
        got=log.records_for_run(r)
        exp=sum(1 for p in pairs if p[0]==r)*2*2
        assert len(got)==exp and all(g.run_id==r for g in got),(r,len(got),exp)
    print("disk lookups ok: files",len(list(log.records_dir.iterdir())),"pairs",len(pairs),"runs",len(set(p[0] for p in pairs)))
# 5. what SAFE_ID admits
for bad in ["a\n","\u212a","\u0661a","a\u00e9","\uff21","a b","a/b","a..b","_a","",".a","-a","a"*65, "\u0130","a\x00"]:
    print(ascii(bad), valid(bad))
print("ALL OK")
