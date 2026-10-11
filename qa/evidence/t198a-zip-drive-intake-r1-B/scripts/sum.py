import json,sys,collections
o={r['case']:r for r in json.load(open(sys.argv[1]))}; n=json.load(open(sys.argv[2]))
print("leftover (excluding sources.jsonl):",[(r['case'],r['leftover']) for r in n if [x for x in r['leftover'] if not x.endswith('sources.jsonl')]])
print("src_files != rows:",[(r['case'],r['src_files'],len(r['rows'])) for r in n if r['src_files']!=len(r['rows'])])
for r in n:
    a=o[r['case']]
    if (a.get('raised'),a.get('status'),json.dumps(a.get('members')),json.dumps(a['rows']))!=(r.get('raised'),r.get('status'),json.dumps(r.get('members')),json.dumps(r['rows'])) and not r['case'].startswith(('flip-lzma','ver-64','ver-99','ver-255','ver-65535')):
        print("CHG",r['case'],"OLD",a.get('raised') or (a.get('status'),[m[1] for m in a['members']]),"NEW",r.get('raised') or (r.get('status'),[(m[1],m[2]) for m in r['members']]))
# group new outcomes
g=collections.defaultdict(list)
for r in n:
    sig=r.get('raised') or (r['status'],tuple(m[1] for m in r['members']),len(r['rows']))
    g[str(sig)].append(r['case'])
for k,v in sorted(g.items(),key=lambda x:-len(x[1])): print(len(v),k,v[:4])
