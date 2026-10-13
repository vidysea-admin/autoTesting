import os, sys, tempfile, re
arch = open('arch_path.txt').read().strip()
root = tempfile.mkdtemp(prefix='walkroot_', dir=os.path.dirname(os.path.abspath(__file__)))
os.environ['AUTOTESTER_ROOT'] = root
for k in list(os.environ):
    if k.startswith('AUTOTESTER_') and k!='AUTOTESTER_ROOT': del os.environ[k]
sys.path.insert(0, arch + '/src')
import autotester
print('autotester from', autotester.__file__)
from autotester.ui.app import app
from autotester.auth.policy import route_for, ROUTE_POLICY
from fastapi.testclient import TestClient
def flat(routes):
    for r in routes:
        inner = getattr(r, 'original_router', None)
        if inner is not None: yield from flat(inner.routes)
        else: yield r
pairs=set()
for r in flat(app.routes):
    p=getattr(r,'path',None); ms=getattr(r,'methods',None) or []
    if p is None: continue
    for m in ms:
        if m=='HEAD': continue
        pairs.add((m,p))
print('served pairs', len(pairs))
missing=[(m,p) for m,p in sorted(pairs) if route_for(m,p.replace(':path','')) is None and True]
# route_for needs a concrete path-form; use the template itself (the {x} segments match [^/]+)
missing=[]
for m,p in sorted(pairs):
    concrete=re.sub(r'\{[^}:]+(:path)?\}', 'x', p)
    if route_for(m, concrete) is None: missing.append((m,p))
print('served without policy row:', missing)
served_keys={(m,p) for m,p in pairs}
orphan=[k for k in ROUTE_POLICY if k not in served_keys]
print('policy rows for unserved routes:', orphan)
# unauthenticated probe of every pair
c = TestClient(app, base_url='http://localhost', follow_redirects=False)
bad=[]
public={('GET','/auth/login'),('POST','/auth/login'),('GET','/auth/signup'),('POST','/auth/signup'),('GET','/healthz')}
for m,p in sorted(pairs):
    concrete=re.sub(r'\{[^}:]+(:path)?\}', 'x', p)
    h={'Origin':'http://localhost'} if m!='GET' else {}
    resp=c.request(m, concrete, headers=h)
    if (m,p) in public: continue
    if resp.status_code not in (302,401,403):
        bad.append((m,p,resp.status_code))
print('unauth non-public answering other than 302/401/403:', bad)
# undeclared route added after import
@app.get('/zz-undeclared')
def zz(): return {'x':1}
print('undeclared route unauth ->', c.get('/zz-undeclared').status_code)
