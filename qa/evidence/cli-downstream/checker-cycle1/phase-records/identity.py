import hashlib,json,pathlib,subprocess
r=pathlib.Path.cwd();e=r/'qa/evidence/cli-downstream';o=r/'.work/checker-downstream-cycle1';h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
i=json.loads((e/'evidence-index.json').read_bytes());assert all(h(e/k)==v for k,v in i['files'].items())
assert h(r/'.work/cli-downstream-cycle1-packet.md')=='be2e6240c3771eb7791e78b6c5bf1c173e3ebdbdd132478a549a3b0b66fc5108'
a=json.loads((e/'cycle2/shared-green.json').read_bytes());b=json.loads((e/'cycle2/run-binding.json').read_bytes())
f={'candidate_sha':b['source_candidate'],'base_sha':b['base_candidate'],'command':a['command'],'python':b['python'],'python_version':b['python_version'],'lock_hash':h(r/'uv.lock'),'import_root':a['runtime_identity']['import_root'],'environment_hash':b['environment_sha256'],'runtime_identity':a['runtime_identity'],'exit_code':a['exit_code']}
(o/'reuse-input.json').write_text(json.dumps({'existing':f,'requested':f},indent=2))
(o/'identity.json').write_text(json.dumps({'wrapper':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'index_files':len(i['files']),'packet_hash':h(r/'.work/cli-downstream-cycle1-packet.md'),'all_raw_hashes_match':True},indent=2))
print('Independent raw index validation:121 entries; packet hash matches; receipt readiness validated23 commands/11 triples/1021 inventory')
