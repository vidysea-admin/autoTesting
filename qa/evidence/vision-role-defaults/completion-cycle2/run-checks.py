import os,sys,subprocess,time,json,pathlib,datetime
r=pathlib.Path.cwd(); e=r/'qa/evidence/vision-role-defaults/completion-cycle2'; py=sys.executable
os.environ['PYTHONPATH']=str(r/'src'); os.environ['PYTHONDONTWRITEBYTECODE']='1'; temp=r/'.work/vision-completion-temp'; temp.mkdir(exist_ok=True)
commands=[('preflight',[py,'C:/Users/product/.agents/skills/checker/scripts/review_budget.py','preflight','--root',str(r),'--import-name','autotester','--import-root',str(r/'src'),'--temp-parent',str(temp)]),('consumer',[py,'-B','-m','pytest','tests/test_vision_roles.py::test_actual_parser_preserves_distinct_ensemble_model_tags_and_custom_settings','tests/test_vision_roles.py::test_lazy_group_preserves_override_tags_all_ensemble_members_and_dedup','--tb=short','--basetemp='+str(temp/'cycle2'),'--junitxml='+str(e/'consumer.xml')]),('ruff',[py,'-m','ruff','check','src/autotester/providers/__init__.py','tests/test_vision_roles.py'])]
rows=[]
for name,cmd in commands:
 start=time.perf_counter(); done=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT); duration=time.perf_counter()-start; (e/(name+'.log')).write_bytes(done.stdout); rows.append(dict(name=name,command=cmd,exit=done.returncode,duration_s=duration)); print(name,done.returncode,duration,done.stdout.decode(errors='replace'),flush=True)
 if done.returncode: break
(e/'checks.json').write_text(json.dumps(rows,indent=2)+'\n'); sys.exit(any(x['exit'] for x in rows))
