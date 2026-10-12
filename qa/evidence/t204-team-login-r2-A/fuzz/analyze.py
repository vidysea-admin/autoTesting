import json, glob, collections, sys
rows=[]
for f in sorted(glob.glob('cases.[0-9].json')): rows+=json.load(open(f,encoding='utf-8'))
print(len(rows),'rows from',len(glob.glob('cases.[0-9].json')),'shards')
print(collections.Counter(r['verdict'] for r in rows))
for d in sorted({r['dim'] for r in rows}):
    print(d, dict(collections.Counter(r['verdict'] for r in rows if r['dim']==d)))
print('bind_parse_mismatch',sum(1 for r in rows if r.get('bind_parse_mismatch')))
mode=sys.argv[1] if len(sys.argv)>1 else 'DISAGREE'
for r in rows:
    if r['verdict'].startswith(mode) or r['verdict'].startswith('CRASH'):
        print('|'.join(str(r.get(k)) for k in ('id','verdict','startup','msg_head','argv','uvicorn_host','uvicorn_port','hosts','origins','public','bound','served')))
