import json,sys
rows=[json.loads(l) for l in open(sys.argv[1]) if l.startswith('{')]
bad=[]
for r in rows:
    if r.get('started'):
        ok = r.get('get_login')==200 and r.get('post_login')==303 and r.get('post_foreign_origin')==403
        r['verdict']='START-OK' if ok else 'START-BUT-REJECTS'
    else:
        msg=(r['tail'][0] if r['tail'] else '')
        r['verdict']='REFUSE' if r.get('exit')==3 else 'ODD:%s'%r.get('exit')
    print(r['id'],r['verdict'],r.get('get_login'),r.get('post_login'),r.get('post_foreign_origin'),(r['tail'][0][-110:] if r.get('tail') and not r.get('started') else ''))
