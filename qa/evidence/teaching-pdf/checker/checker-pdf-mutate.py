import json,os,sys
from pathlib import Path
root=Path.cwd();sys.path.insert(0,str(root/'scripts'));import mutation_check as h
spec=json.loads((root/'qa/evidence/teaching-pdf/mutations.json').read_text());m=spec['mutations'][1];spec={'tests':m['kills'],'mutations':[m],'timeout_s':45}
original=h._run_pytest
count=0
def run(cwd,tests,*extra,timeout=45):
 global count
 os.environ['PYTHONPATH']=str(cwd/'src');(cwd/'.work').mkdir(exist_ok=True)
 code,out=original(cwd,tests,*extra,'--basetemp',str(cwd/'.work'/f'temp-{count}'),'-p','no:cacheprovider',timeout=timeout)
 (root/'.work'/f'checker-pdf-mutation-{count}.log').write_text(out);count+=1;return code,out
h._run_pytest=run
results=h.check(spec,root);(root/'.work/checker-pdf-mutation.json').write_text(json.dumps(results,indent=2));assert all(r['killed'] for r in results);print(json.dumps(results))
proof=json.loads((root/'qa/evidence/teaching-pdf/mutation-results.json').read_text());assert len(proof)==22;assert all(r['killed'] and r['exit']==1 and set(r['expected'])<=set(r['failed']) and not r['timed_out'] for r in proof);print('22 maker mutation rows independently cross-checked')
