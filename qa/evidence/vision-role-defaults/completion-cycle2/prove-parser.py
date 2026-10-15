import pathlib,subprocess,os,sys,time,json,hashlib,xml.etree.ElementTree as ET
r=pathlib.Path.cwd(); e=r/'qa/evidence/vision-role-defaults/completion-cycle2'; p=r/'src/autotester/providers/__init__.py'; good=p.read_bytes(); nl=b'\r\n' if b'\r\n' in good else b'\n'
anchor=b'    members = []\n    for member in dict.fromkeys(part.strip() for part in spec.split(",")):\n        name, member_options = parse_spec(member)'.replace(b'\n',nl)
replacement=b'    provider_id, options = parse_spec(spec)\n    members = []\n    for name in dict.fromkeys(part.strip() for part in provider_id.split(",")):\n        member_options = dict(options)'.replace(b'\n',nl)
assert good.count(anchor)==1; bad=good.replace(anchor,replacement); assert good!=bad
os.environ['PYTHONPATH']=str(r/'src'); os.environ['PYTHONDONTWRITEBYTECODE']='1'; rows=[]
def run(name):
 cmd=[sys.executable,'-B','-m','pytest','tests/test_vision_roles.py::test_actual_parser_preserves_distinct_ensemble_model_tags_and_custom_settings','--tb=short','--basetemp='+str(r/'.work/vision-completion-temp'/name),'--junitxml='+str(e/(name+'.xml'))]; start=time.perf_counter(); proc=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=40); (e/(name+'.log')).write_bytes(proc.stdout); rows.append(dict(name=name,exit=proc.returncode,duration_s=time.perf_counter()-start,command=cmd)); print(name,proc.returncode,proc.stdout.decode(errors='replace'),flush=True); return proc
try:
 p.write_bytes(bad); assert p.read_bytes()==bad
 red=run('parser-red'); assert red.returncode==1
 xml=ET.parse(e/'parser-red.xml'); failures=[x for x in xml.iter('testcase') if x.find('failure') is not None]; assert len(failures)==1 and failures[0].get('name')=='test_actual_parser_preserves_distinct_ensemble_model_tags_and_custom_settings'; assert b'AssertionError' in red.stdout
finally: p.write_bytes(good)
assert p.read_bytes()==good; green=run('parser-restored'); assert green.returncode==0
(e/'parser-proof.json').write_text(json.dumps(dict(anchor_count=1,original_sha256=hashlib.sha256(good).hexdigest(),mutated_sha256=hashlib.sha256(bad).hexdigest(),restored_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),rows=rows),indent=2)+'\n')
