import json,sys,collections
o=json.load(open(sys.argv[1])); n=json.load(open(sys.argv[2]))
od={r['case']:r for r in o}; nd={r['case']:r for r in n}
chg=[]
for k in nd:
    a,b=od[k],nd[k]
    key=lambda r:(r.get('raised'),r.get('status'),r.get('exit'),json.dumps(r.get('members')),json.dumps(r.get('rows')),json.dumps(r.get('leftover')))
    if key(a)!=key(b): chg.append(k)
print("changed cases:",len(chg))
for k in chg:
    a,b=od[k],nd[k]
    print(k,"\n  OLD",a.get('raised') or (a.get('status'),[ (m[0],m[1]) for m in a.get('members',[])],len(a['rows'])),"\n  NEW",b.get('raised') or (b.get('status'),[(m[0],m[1],m[2]) for m in b.get('members',[])],len(b['rows'])))
print("--- leftovers (new):",[ (r['case'],r['leftover']) for r in n if r['leftover']])
print("--- raised new:",[ (r['case'],r['raised']) for r in n if r.get('raised')])
print("--- raised old:",[ (r['case'],r['raised']) for r in o if r.get('raised')])
