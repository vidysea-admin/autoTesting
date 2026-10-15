import os,pathlib,shutil,subprocess,sys,json,time,hashlib
root=pathlib.Path.cwd();out=root/'qa/evidence/narration-policy/checker-cycle2';work=root/'.work/checker-cycle2-copy'
assert not work.exists()
for d in ('src','tests','scripts'):
 shutil.copytree(root/d,work/d,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
for f in ('pyproject.toml','conftest.py','uv.lock'):
 if (root/f).exists():shutil.copy2(root/f,work/f)
env={k:os.environ[k] for k in ('SYSTEMROOT','WINDIR','PATH','PATHEXT','COMSPEC','USERPROFILE','APPDATA','LOCALAPPDATA','TEMP','TMP') if k in os.environ}
env.update(PYTHONPATH=str(work/'src'),PYTHONDONTWRITEBYTECODE='1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTHONUTF8='1')
names=['test_default_transcribe_never_launches_local_asr','test_persisted_empty_transcript_reused_byte_for_byte','test_video_sends_only_extracted_audio_and_cleans_scratch','test_extraction_bounds_reject_duration_and_truncated_output','test_extraction_failure_stays_explicit_and_cleans_scratch','test_media_prep_calls_narration_by_default','test_real_transport_requires_typed_safety_capabilities','test_audio_byte_limit_and_output_secret_scrubbing','test_cli_prep_does_not_opt_in_local_asr']
nodes=['tests/test_narration_policy.py::'+n for n in names]
nodes+=['tests/test_source_adapters_audio.py::'+n for n in ['test_audio_missing_provider_never_uses_local_asr','test_audio_provider_failure_is_incomplete','test_audio_supplied_empty_transcript_precedes_provider','test_audio_gemini_call_is_gated_by_assert_no_raw_secrets','test_audio_shares_the_one_store_and_enum_with_text_and_doc']]
nodes+=['tests/test_media_prep.py::test_prep_tells_the_operator_the_narration_is_unreadable_and_why']
records=[]
def run(label,args,expect):
 start=time.monotonic();cmd=[sys.executable,'-B',*args]
 r=subprocess.run(cmd,cwd=work,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=45)
 (out/(label+'.log')).write_bytes(r.stdout);records.append(dict(label=label,command=cmd,exit=r.returncode,duration_s=time.monotonic()-start,output_sha256=hashlib.sha256(r.stdout).hexdigest()))
 assert r.returncode==expect,(label,r.stdout.decode(errors='replace')[-1500:])
 return r.stdout.decode(errors='replace')
def pytest(nodes):return ['-m','pytest',*nodes,'--basetemp='+str(work/'.tmp'),'-p','no:cacheprovider']
run('selected',pytest(nodes),0)
target=work/'src/autotester/sources/audio.py';raw=target.read_bytes();old=b'if not audio_delivery_ready(provider):';assert raw.count(old)==1
changed=raw.replace(old,b'if False:',1);assert raw!=changed;target.write_bytes(changed)
node='tests/test_narration_policy.py::test_real_transport_requires_typed_safety_capabilities'
log=run('guard-red',pytest([node]),1);assert 'FAILED '+node in log and 'AssertionError' in log
(target).write_bytes(raw);assert target.read_bytes()==raw
run('guard-restored',pytest([node]),0)
changed_files=['src/autotester/media/narration.py','src/autotester/media/transcribe.py','src/autotester/sources/audio.py','src/autotester/schema/transcription.py','src/autotester/stages/media_prep.py','src/autotester/cli_video.py','tests/test_narration_policy.py','tests/test_source_adapters_audio.py']
run('ruff',['-m','ruff','check',*changed_files],0)
(out/'runtime-results.json').write_text(json.dumps(dict(records=records,nodes=nodes,guard=dict(anchor_count=1,original_sha256=hashlib.sha256(raw).hexdigest(),mutated_sha256=hashlib.sha256(changed).hexdigest(),restored_sha256=hashlib.sha256(target.read_bytes()).hexdigest()),copy=str(work)),indent=2))
print('15 selected nodes, independent capability green/red/restored, scoped Ruff PASS')
